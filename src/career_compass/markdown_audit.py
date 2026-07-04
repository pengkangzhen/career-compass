"""Markdown 结构审计 —— 检测 Jinja 渲染后常见的「粘行」问题。"""
from __future__ import annotations

import re


def audit_glued_lines(text: str, source: str = "markdown") -> list[str]:
    """行内出现 table 管道符但未以 | 开头 → 表格被粘到上一段文字。"""
    issues: list[str] = []
    in_code = False
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not stripped:
            continue
        if not stripped.startswith("|"):
            if re.search(r"[^\|]\| [^|]+ \| [^|]+ \|", line):
                issues.append(f"{source}:{i}: text+table glued: {line[:120]}")
        if re.search(r"\*\*[^*]+\*\*[^|\n]*?:\s*- ", line) and not stripped.startswith("|"):
            issues.append(f"{source}:{i}: bold+list glued: {line[:120]}")
    return issues


def audit_markdown_html(text: str, source: str = "markdown") -> list[str]:
    """Markdown → HTML 后：表格数量、列表是否误包进 <p>。"""
    from career_compass.gui.md import render_markdown

    issues: list[str] = []
    html = render_markdown(text)
    if re.search(r"<p>\s*<strong>[^<]+</strong>\s*\n-", html):
        issues.append(f"{source}: list rendered inside <p> (need blank line before list)")
    if re.search(r"<p>[^<]*\| [^<]+\|", html):
        issues.append(f"{source}: table pipe syntax inside <p>")
    sep_rows = len(re.findall(r"^\|[-: |]+\|\s*$", text, re.MULTILINE))
    html_tables = html.count("<table>")
    if sep_rows != html_tables:
        issues.append(
            f"{source}: table count mismatch (md separators={sep_rows}, html tables={html_tables})"
        )
    return issues


def audit_markdown(text: str, source: str = "markdown") -> list[str]:
    return audit_glued_lines(text, source) + audit_markdown_html(text, source)
