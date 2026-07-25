"""诊断脚本：直接调 CloudBase / LLM 抽取简历，把每一步的结果打印到终端。

用途：上传简历后画像不更新时，用这个脚本看 LLM 实际返回了什么，
定位是 JSON 没解析、extracted_profile 为空、字段名不匹配、还是别的问题。

用法::

    uv run python scripts/diagnose_resume.py <简历文件路径>

例如::

    uv run python scripts/diagnose_resume.py ~/Downloads/resume.pdf
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from career_compass.intake.llm import create_llm_client, get_llm_config
from career_compass.intake.resume import (
    _RESUME_JSON_BLOCK,
    _RESUME_SYSTEM_PROMPT,
    extract_text,
    merge_profile,
)


def _hr(title: str) -> None:
    line = f"=== {title} ==="
    print("\n" + line)


def main() -> None:
    if len(sys.argv) < 2:
        print("用法: uv run python scripts/diagnose_resume.py <简历文件路径>")
        print('例如: uv run python scripts/diagnose_resume.py "~/Downloads/resume.pdf"')
        sys.exit(1)

    resume_path = Path(sys.argv[1]).expanduser()
    if not resume_path.exists():
        print(f"❌ 文件不存在: {resume_path}")
        sys.exit(1)

    # ---- LLM 配置 ----
    cfg = get_llm_config()
    _hr("LLM 配置")
    print(f"  provider : {cfg.provider}")
    print(f"  model    : {cfg.model}")
    print(f"  base_url : {cfg.base_url}")
    print(f"  configured: {cfg.configured}")
    if not cfg.configured:
        print("\n❌ LLM 未配置，无法继续诊断。请设置环境变量后重试。")
        sys.exit(1)

    # ---- Step 1: 文件 → 纯文本 ----
    content = resume_path.read_bytes()
    _hr(f"Step 1 · extract_text（{resume_path.name}, {len(content)} bytes）")
    text = extract_text(resume_path.name, content)
    print(f"  抽取到 {len(text)} 字符的纯文本")
    if len(text) < 30:
        print("  ❌ 文本过短，简历可能没解析出内容")
        sys.exit(1)
    print("  —— 前 500 字符 ——")
    print(text[:500])

    # ---- Step 2: 调 LLM（不走 _call_llm_for_extraction，手动调，保留 raw）----
    _hr("Step 2 · 调用 LLM（用强化后的 _RESUME_SYSTEM_PROMPT）")
    llm = create_llm_client()
    truncated = text[:8000]
    user_msg = (
        f"简历原文（已截断到 8000 字符）：\n\n```\n{truncated}\n```\n\n"
        "请按系统提示的 JSON 格式输出抽取结果。"
    )
    raw = llm.complete(
        system=_RESUME_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    print(f"  LLM raw 返回长度: {len(raw)} 字符")
    print("  —— raw 前 3000 字符 ——")
    print(raw[:3000])

    # ---- Step 3: 解析 JSON 块 ----
    _hr("Step 3 · 解析 ```json``` 代码块")
    match = _RESUME_JSON_BLOCK.search(raw)
    if not match:
        print("  ❌ 没匹配到 ```json``` 代码块！")
        print(f"  raw 里有没有 '```'   : {'```' in raw}")
        print(f"  raw 里有没有 '{{'    : {'{' in raw}")
        print("  —— raw 完整内容 ——")
        print(raw)
        sys.exit(1)
    print(f"  ✅ 匹配到 JSON 块，长度 {len(match.group(1))} 字符")
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        print(f"  ❌ JSON 解析失败: {e}")
        print("  —— matched block ——")
        print(match.group(1))
        sys.exit(1)
    print(f"  ✅ JSON 解析成功，payload 顶层 keys: {list(payload.keys())}")

    # ---- Step 4: extracted_profile 分析 ----
    _hr("Step 4 · extracted_profile 分析（定位关键）")
    extracted = payload.get("extracted_profile") or {}
    notes = str(payload.get("notes", "")).strip()
    print(f"  notes 内容: {notes or '（空）'}")
    if not extracted:
        print("  ❌ extracted_profile 为空！这就是画像不更新的直接原因。")
        alt_keys = [k for k in payload if k not in ("notes", "extracted_profile")]
        if alt_keys:
            print(f"  ⚠️  payload 里有其他 key，可能是 LLM 用了别名替代 extracted_profile:")
            for k in alt_keys:
                val = payload[k]
                val_preview = json.dumps(val, ensure_ascii=False)[:400]
                print(f"    {k}: {val_preview}")
        else:
            print("  ⚠️  payload 里没有其他 key——LLM 把所有内容都写进了 notes 自由文本。")
            print("     notes 完整内容:")
            print(f"     {notes}")
    else:
        if isinstance(extracted, dict):
            print(f"  ✅ extracted_profile 非空，keys: {list(extracted.keys())}")
            print(f"     完整内容（前 800 字符）:")
            print(f"     {json.dumps(extracted, ensure_ascii=False)[:800]}")
        else:
            print(f"  ❌ extracted_profile 不是 dict，实际类型: {type(extracted).__name__}")
            print(f"     值: {extracted!r}")

    # ---- Step 5: merge 测试 ----
    _hr("Step 5 · merge_profile 测试（用空 existing 模拟新用户）")
    if not isinstance(extracted, dict):
        print("  ⏭  跳过（extracted 不是 dict）")
        return
    existing: dict = {}
    merged, filled, skipped = merge_profile(existing, extracted)
    print(f"  filled   : {filled}")
    print(f"  skipped  : {skipped}")
    if filled:
        print("  ✅ merge 成功，这些字段会写入 profile.yaml，画像会更新。")
        print("     —— merged profile ——")
        print(json.dumps(merged, ensure_ascii=False, indent=2)[:1500])
    else:
        print("  ❌ merge 一项都没填！extracted 的字段名/结构与 schema 不匹配。")
        print("     schema 期望的顶层 key:")
        print("       - current_role（标量）")
        print("       - education（list of dict）")
        print("       - experience（list of dict）")
        print("       - skills（dict，含 core / adjacent / frontier）")
        print("       - strength_evidence（list of dict）")
        print(f"     extracted 实际 key: {list(extracted.keys())}")


if __name__ == "__main__":
    main()
