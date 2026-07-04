"""App 内 Markdown → HTML（统一样式入口）。"""
from __future__ import annotations

import re

import markdown

_processor = markdown.Markdown(
    extensions=["tables", "fenced_code", "sane_lists"],
)

_LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d+\.)\s")


def normalize_markdown_lists(text: str) -> str:
    """段落后直接接 `- item` 时补空行，否则 CommonMark 不识别为列表。"""
    lines = text.splitlines()
    out: list[str] = []
    for line in lines:
        if out and _LIST_ITEM.match(line):
            prev = out[-1]
            if prev.strip() and not _LIST_ITEM.match(prev) and not prev.lstrip().startswith(
                ("|", "#", ">", "```")
            ):
                out.append("")
        out.append(line)
    return "\n".join(out)


def render_markdown(text: str) -> str:
    """将 Markdown 转为 HTML 片段（不含外层 .content 容器）。"""
    _processor.reset()
    return _processor.convert(normalize_markdown_lists(text))


def content_page(inner_html: str) -> str:
    """包一层 .content，统一各 Tab 排版。"""
    return f'<div class="content">{inner_html}</div>'
