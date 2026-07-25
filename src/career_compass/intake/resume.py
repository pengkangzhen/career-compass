"""Resume upload → structured profile extraction.

Pipeline: file bytes → plain text (PDF / txt / md) → LLM extracts a partial
Profile YAML → field-level merge into existing ``profile.yaml`` (only fills
empty slots, never overwrites user-edited content).

设计约束：
- 简历里通常没有 ``values_ranked`` / ``strength_evidence.proof`` / ``constraints``，
  这些字段交给后续 intake 对话补，抽取时不强制填写。
- 抽取结果必须经过 ``merge_profile`` 过滤，避免覆盖已有内容。
- 抽取的 YAML 是 partial profile（只有 ``profile.yaml`` 一个文件），不走
  ``apply_updates`` 的多文件全量覆盖路径。
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..schema import ValidationError, load_profile
from .llm import LLMClient, LLMError

# 上传大小限制：5MB（防止 OCR 扫描件等巨型 PDF 拖垮请求）
MAX_RESUME_BYTES = 5 * 1024 * 1024

# 接受的文件扩展名（display 用；后端按 content 判断）
ACCEPTED_EXTS: frozenset[str] = frozenset({".pdf", ".txt", ".md", ".markdown", ".text"})

_RESUME_JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)

# 模块 logger：CloudBase 等模型 JSON following 能力参差，抽取失败时把 LLM
# 原始返回留在日志里，方便定位是 prompt 不够硬、还是某个 provider 的特殊行为。
_log = logging.getLogger("career_compass.intake.resume")


class ResumeError(Exception):
    """简历解析或抽取失败。"""


@dataclass
class ResumeExtractResult:
    """``extract_profile_from_resume`` 的结构化返回。"""

    ok: bool
    reply: str = ""
    extracted: dict[str, Any] = field(default_factory=dict)
    merged_keys: list[str] = field(default_factory=list)
    skipped_keys: list[str] = field(default_factory=list)
    files_updated: list[str] = field(default_factory=list)
    error: str = ""


# --------------------------------------------------------------------------
# Step 1: 文件 → 纯文本
# --------------------------------------------------------------------------

def extract_text(filename: str, content: bytes) -> str:
    """根据扩展名把上传内容转成纯文本。

    - PDF: 用 pypdf 抽取（扫描件 / 纯图片 PDF 会返回空，调用方决定如何提示）
    - txt/md/markdown: 直接 utf-8 解码
    """
    name = filename.lower()
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError as e:  # pragma: no cover - 依赖缺失由调用方提示
            raise ResumeError("服务器缺少 pypdf 依赖，无法解析 PDF") from e
        try:
            reader = PdfReader(__import__("io").BytesIO(content))
        except Exception as e:
            raise ResumeError(f"PDF 解析失败：{e}") from e
        chunks: list[str] = []
        for page in reader.pages:
            try:
                chunks.append(page.extract_text() or "")
            except Exception:
                continue
        text = "\n".join(chunks).strip()
        if not text:
            raise ResumeError(
                "PDF 未抽取到任何文本 —— 可能是扫描件或纯图片 PDF，"
                "请改用可复制文字的 PDF，或粘贴纯文本简历"
            )
        return text

    if name.endswith((".txt", ".md", ".markdown", ".text")):
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                return content.decode("gbk")
            except UnicodeDecodeError as e:
                raise ResumeError("文本编码无法识别，请用 UTF-8 保存后重试") from e

    raise ResumeError(
        f"不支持的文件类型：{filename}（仅支持 PDF / txt / md）"
    )


# --------------------------------------------------------------------------
# Step 2: 纯文本 → partial Profile YAML（LLM 抽取）
# --------------------------------------------------------------------------

_RESUME_SYSTEM_PROMPT = """你是北斗星的简历解析助手。给定一份简历的纯文本，你的任务是把信息结构化成 ``profile.yaml`` 的 **部分字段**，供后续合并到用户画像。

## ⚠️ 最关键要求（违反 = 抽取失败，画像不会更新）

1. **所有结构化内容必须放进 ``extracted_profile`` 字段**。这个 key 名必须严格是 ``extracted_profile``——不能用 ``profile`` / ``result`` / ``data`` / ``resume`` 等任何别名。
2. **``notes`` 只写一句自然语言总结**（"抽取到了什么 / 明显缺什么"）。**绝对不要**把结构化数据（学校、公司、技能等）写进 notes。系统只读 ``extracted_profile``，如果它是 ``{}`` 而内容只在 notes 里，本次抽取会被判定为失败。
3. ``extracted_profile`` 内部字段名必须严格按下面的 schema：``current_role`` / ``education`` / ``experience`` / ``skills`` / ``strength_evidence``。不要用中文 key，不要加额外嵌套层级。

## 输出格式

只输出一个 JSON 代码块，schema：

```json
{
  "extracted_profile": {
    "current_role": "字符串或省略",
    "education": [
      {"level": "bachelor|master|phd", "school": "院校全名", "major": "专业", "degree": "工学学士等", "start_year": 2015, "end_year": 2019, "status": "graduated|enrolled"}
    ],
    "experience": [
      {"company": "公司", "role": "职位", "period": "2020.07-至今", "scope": "负责什么、规模", "quantified_outcomes": ["带数字的成果"]}
    ],
    "skills": {
      "core": ["靠它吃饭的核心技能"],
      "adjacent": ["能快速上手的相邻技能"],
      "frontier": ["在学/刚接触的"]
    },
    "strength_evidence": [
      {"claim": "擅长 X", "proof": "客观数字 / 事件 / 结果"}
    ]
  },
  "notes": "给用户看的 1-2 句总结：抽取到了什么、明显缺了什么"
}
```

## 抽取规则（严格遵守）

1. **只填简历里明确出现的内容**，不要编造、不要补全、不要从公司名猜测行业
2. **skills 分层**：
   - core = 简历里反复出现、有项目/工作支撑的技能
   - adjacent = 提到但没深入用的
   - frontier = 在学课程、近期证书
3. **strength_evidence.proof 必须有数字或事件**：如果简历只有"负责 X"没说效果，**不要**写入 strength_evidence（缺 proof 的优势对决策无用）
4. **不要抽取 name** —— 北斗星做职业决策不需要真实姓名
5. **不要抽取 values_ranked / preferences** —— 价值观由 intake 对话推断，简历不可信
6. **education.level** 必须是 bachelor/master/phd 三选一；分不清时按学位文案推断
7. **若整份简历信息不足以填任何字段**，返回空对象 ``{}`` 并在 notes 说明
8. **status**: 在读/在读研 → enrolled；已毕业 → graduated
"""


def _call_llm_for_extraction(*, llm: LLMClient, resume_text: str) -> dict[str, Any]:
    """让 LLM 从简历文本抽取结构化字段。返回 parsed JSON dict。"""
    truncated = resume_text[:8000]  # 防止超长简历撑爆 context
    user_msg = (
        f"简历原文（已截断到 8000 字符）：\n\n```\n{truncated}\n```\n\n"
        "请按系统提示的 JSON 格式输出抽取结果。"
    )
    raw = llm.complete(system=_RESUME_SYSTEM_PROMPT, messages=[{"role": "user", "content": user_msg}])

    match = _RESUME_JSON_BLOCK.search(raw)
    if not match:
        # 现场留痕：某些模型会把 JSON 散落在散文里或忘了用 ```json``` 包裹
        _log.warning(
            "resume extract: LLM 未返回 ```json``` 代码块。raw 前 800 字符: %r",
            raw[:800],
        )
        raise ResumeError("LLM 未返回可解析的 JSON 块")
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        _log.warning(
            "resume extract: JSON 解析失败: %s。matched block 前 800 字符: %r",
            e, match.group(1)[:800],
        )
        raise ResumeError(f"LLM 返回的 JSON 解析失败：{e}") from e

    extracted = payload.get("extracted_profile") or {}
    notes = str(payload.get("notes", "")).strip()

    # 诊断核心：CloudBase 等模型有时会偷懒——把抽取内容全写进 notes 自由文本，
    # extracted_profile 留成 {} 或用别名 key（profile / result / data），
    # 导致 merge_profile 一项都填不进、画像不更新。这里把 payload 结构留下，
    # 下次复现一眼能看出是哪种偏差。
    if not extracted:
        alt_keys = [k for k in payload if k not in ("notes", "extracted_profile")]
        _log.warning(
            "resume extract: extracted_profile 为空。payload keys=%s, "
            "疑似替代 key=%s, notes 前 200 字符=%r",
            list(payload.keys()), alt_keys, notes[:200],
        )
    else:
        _log.info(
            "resume extract: extracted_profile keys=%s",
            list(extracted.keys()) if isinstance(extracted, dict) else type(extracted).__name__,
        )

    if not isinstance(extracted, dict):
        raise ResumeError("LLM 返回的 extracted_profile 不是对象")
    return {"extracted": extracted, "notes": notes}


# --------------------------------------------------------------------------
# Step 3: 字段级 merge（只填空）
# --------------------------------------------------------------------------

def _is_empty(value: Any) -> bool:
    """字段是否视为"未填"，可被简历内容覆盖。"""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, list | tuple | dict):
        return len(value) == 0
    return False


def merge_profile(existing: dict[str, Any], extracted: dict[str, Any]) -> tuple[dict[str, Any], list[str], list[str]]:
    """把抽取出来的字段合并进 existing profile，只填空。

    返回 ``(merged_dict, filled_keys, skipped_keys)``：
    - ``filled_keys``: 本次新写入的字段路径
    - ``skipped_keys``: 抽取到了但 existing 已有内容、跳过的字段
    """
    merged = json.loads(json.dumps(existing))  # deep copy via json（YAML 标量都兼容 JSON）
    filled: list[str] = []
    skipped: list[str] = []

    # 标量字段
    for key in ("current_role",):
        new_val = extracted.get(key)
        if _is_empty(new_val):
            continue
        if _is_empty(merged.get(key)):
            merged[key] = new_val
            filled.append(key)
        else:
            skipped.append(key)

    # 列表字段：education / experience / strength_evidence / skills.core|adjacent|frontier
    for key in ("education", "experience", "strength_evidence"):
        new_list = extracted.get(key)
        if not isinstance(new_list, list) or not new_list:
            continue
        existing_list = merged.get(key) or []
        if isinstance(existing_list, list) and existing_list:
            skipped.append(key)
        else:
            # 只保留结构合法的项
            cleaned = [item for item in new_list if isinstance(item, dict) and item]
            if cleaned:
                merged[key] = cleaned
                filled.append(key)

    # skills: 三档分别处理
    new_skills = extracted.get("skills")
    if isinstance(new_skills, dict):
        existing_skills = merged.get("skills")
        if not isinstance(existing_skills, dict) or not existing_skills:
            existing_skills = {"core": [], "adjacent": [], "frontier": []}
        for tier in ("core", "adjacent", "frontier"):
            new_list = new_skills.get(tier)
            if not isinstance(new_list, list):
                continue
            cleaned = [str(s).strip() for s in new_list if str(s).strip()]
            if not cleaned:
                continue
            current = existing_skills.get(tier) or []
            if current:
                skipped.append(f"skills.{tier}")
            else:
                existing_skills[tier] = cleaned
                filled.append(f"skills.{tier}")
        merged["skills"] = existing_skills

    return merged, filled, skipped


# --------------------------------------------------------------------------
# Step 4: 顶层编排
# --------------------------------------------------------------------------

def extract_profile_from_resume(
    *,
    data_dir: Path,
    filename: str,
    content: bytes,
    llm: LLMClient,
) -> ResumeExtractResult:
    """端到端：解析文件 → LLM 抽取 → merge 进 ``profile.yaml``。

    不会触碰 ``constraints.yaml`` / ``narrative.md`` —— 简历无法可靠推断这些。
    """
    if len(content) > MAX_RESUME_BYTES:
        return ResumeExtractResult(
            ok=False,
            error=f"文件过大（{len(content) // 1024 // 1024}MB），上限 5MB",
        )

    try:
        resume_text = extract_text(filename, content)
    except ResumeError as e:
        return ResumeExtractResult(ok=False, error=str(e))

    if len(resume_text.strip()) < 30:
        return ResumeExtractResult(
            ok=False,
            error="简历内容过短（少于 30 字），无法提取有效信息",
        )

    try:
        llm_result = _call_llm_for_extraction(llm=llm, resume_text=resume_text)
    except LLMError as e:
        return ResumeExtractResult(ok=False, error=f"LLM 调用失败：{e}")
    except ResumeError as e:
        return ResumeExtractResult(ok=False, error=str(e))

    extracted = llm_result["extracted"]
    notes = llm_result["notes"]

    profile_path = data_dir / "profile.yaml"
    try:
        existing_profile = load_profile(profile_path).model_dump(mode="json")
    except (ValidationError, OSError):
        existing_profile = {}

    merged, filled, skipped = merge_profile(existing_profile, extracted)
    if not filled:
        # merge 一项都没填：可能是 extracted 字段名与 schema 不匹配，
        # 也可能是简历确实没有可补的内容。把现场留下方便区分。
        _log.warning(
            "resume extract: merge 一项未填（画像不会更新）。"
            "extracted keys=%s, skipped=%s",
            list(extracted.keys()) if isinstance(extracted, dict) else type(extracted).__name__,
            skipped,
        )
        return ResumeExtractResult(
            ok=True,
            reply=notes or "简历已解析，但未发现可补充的字段（可能画像已更完整）。",
            extracted=extracted,
            merged_keys=filled,
            skipped_keys=skipped,
        )

    # 写回 profile.yaml
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(
        yaml.safe_dump(merged, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    summary_parts = [f"已从简历补充 {len(filled)} 项：{', '.join(filled)}"]
    if skipped:
        summary_parts.append(f"跳过已有内容：{', '.join(skipped)}")
    summary_parts.append(
        "简历通常不含价值观排序 / 优势证据 —— 接下来聊几句补全即可。"
    )
    if notes:
        summary_parts.append(f"（{notes}）")

    return ResumeExtractResult(
        ok=True,
        reply="\n".join(summary_parts),
        extracted=extracted,
        merged_keys=filled,
        skipped_keys=skipped,
        files_updated=["profile.yaml"],
    )
