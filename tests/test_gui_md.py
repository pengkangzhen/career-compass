from career_compass.gui.md import content_page, render_markdown


def test_render_markdown_bold_and_table():
    html = render_markdown("## 标题\n\n**加粗** 文本\n\n| a | b |\n|---|---|\n| 1 | 2 |")
    assert "<h2>标题</h2>" in html
    assert "<strong>加粗</strong>" in html
    assert "<table>" in html
    assert "**加粗**" not in html


def test_render_markdown_list_after_paragraph():
    md = "已落地两套系统：\n- **MAKO** —— LangGraph\n- **SOP-MAC** —— 更早框架"
    html = render_markdown(md)
    assert "<ul>" in html
    assert "<li>" in html
    assert "**MAKO**" not in html


def test_content_page_wraps():
    out = content_page("<p>hi</p>")
    assert out.startswith('<div class="content">')
    assert out.endswith("</div>")
