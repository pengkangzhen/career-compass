"""Intake 文件 bootstrap 与 LLM 产出写入。"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from ..pipeline import run_validation
from ..schema import ValidationError, is_placeholder, load_profile
from .gaps import suggest_followups

ALLOWED_FILES = frozenset({"profile.yaml", "constraints.yaml", "narrative.md"})

NARRATIVE_SKELETON = """# Narrative

## 职业故事


## 我想要的


## 红线

"""

# 新用户空骨架：不要拷贝 profile.example.yaml（内含「Alex（示例，请替换）」等占位，
# LLM 常漏改 name，导致校验一直报「name 仍为占位」）。
PROFILE_SKELETON = """name: null
current_role: null

education: []
experience: []

skills:
  core: []
  adjacent: []
  frontier: []

strength_evidence: []

preferences:
  values_ranked: []
"""

CONSTRAINTS_TEMPLATE = "constraints.example.yaml"
_NAME_LINE = re.compile(r"(?m)^name:\s*.*$")


def bootstrap_data_dir(data_dir: Path, templates_dir: Path) -> None:
    """首次 intake 时初始化 data/（画像用空骨架，constraints 可参考模板）。"""
    data_dir.mkdir(parents=True, exist_ok=True)

    profile_path = data_dir / "profile.yaml"
    if not profile_path.exists():
        profile_path.write_text(PROFILE_SKELETON, encoding="utf-8")
    else:
        clear_placeholder_profile_name(profile_path)

    constraints_path = data_dir / "constraints.yaml"
    if not constraints_path.exists():
        src = templates_dir / CONSTRAINTS_TEMPLATE
        if src.is_file():
            shutil.copy2(src, constraints_path)
        else:
            constraints_path.write_text("risk_appetite: medium\n", encoding="utf-8")

    narrative_path = data_dir / "narrative.md"
    if not narrative_path.exists():
        narrative_path.write_text(NARRATIVE_SKELETON, encoding="utf-8")


def clear_placeholder_profile_name(profile_path: Path) -> bool:
    """若 name 仍是模板占位，清成 null，方便后续写入用户真实称呼。"""
    try:
        profile = load_profile(profile_path)
    except Exception:
        return False
    if not profile.name or not is_placeholder(profile.name):
        return False
    text = profile_path.read_text(encoding="utf-8")
    new_text, n = _NAME_LINE.subn("name: null", text, count=1)
    if n:
        profile_path.write_text(new_text, encoding="utf-8")
        return True
    return False


def apply_updates(data_dir: Path, updates: dict[str, str]) -> list[str]:
    """写入 LLM 返回的文件更新；返回已写入的文件名列表。"""
    written: list[str] = []
    for name, content in updates.items():
        if name not in ALLOWED_FILES:
            continue
        if not content or not content.strip():
            continue
        path = data_dir / name
        path.write_text(content.rstrip() + "\n", encoding="utf-8")
        written.append(name)
    profile_path = data_dir / "profile.yaml"
    if profile_path.is_file():
        clear_placeholder_profile_name(profile_path)
    return written


def build_context_snapshot(data_dir: Path) -> str:
    """供 LLM 参考的当前文件内容与 validate 缺口。"""
    parts: list[str] = []

    for name in ("profile.yaml", "constraints.yaml", "narrative.md"):
        path = data_dir / name
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            parts.append(f"### 当前 {name}\n```\n{text.strip()}\n```")
        else:
            parts.append(f"### 当前 {name}\n（尚未创建）")

    # 姓名占位是高频事故：模板示例名被原样保留
    try:
        profile = load_profile(data_dir / "profile.yaml")
        if profile.name and is_placeholder(profile.name):
            parts.append(
                "### 紧急：profile.name 仍为占位\n"
                f"- 当前值：{profile.name!r}\n"
                "- 用户若已自报姓名/称呼，本轮必须立刻用用户说的内容覆盖 name，"
                "严禁保留「Alex」「示例」「请替换」等模板字样"
            )
        elif not profile.name:
            parts.append(
                "### 提醒：profile.name 为空\n"
                "- 用户若已自报姓名或称呼，本轮写入 profile.name（可用昵称/化名）"
            )
    except (ValidationError, OSError):
        pass

    errors, warnings = run_validation(data_dir)
    if errors:
        parts.append("### validate 错误（必须补齐）\n" + "\n".join(f"- {e}" for e in errors))
    else:
        parts.append("### validate 错误\n无")

    if warnings:
        parts.append("### validate 警告\n" + "\n".join(f"- {w}" for w in warnings))

    try:
        profile = load_profile(data_dir / "profile.yaml")
        gaps = profile.gaps()
        if gaps:
            parts.append("### profile.gaps()\n" + "\n".join(f"- {g}" for g in gaps))
        else:
            parts.append("### profile.gaps()\n无")
    except (ValidationError, OSError):
        parts.append("### profile.gaps()\n（profile.yaml 尚不可解析）")

    profile_gaps: list[str] = []
    try:
        profile_gaps = load_profile(data_dir / "profile.yaml").gaps()
    except (ValidationError, OSError):
        pass

    hints = suggest_followups(errors, profile_gaps)
    if hints and errors:
        parts.append(
            "### 优先追问（本轮请自然融入对话）\n"
            + "\n".join(f"- {h}" for h in hints)
        )

    return "\n\n".join(parts)
