"""北斗星 — 对话 intake（GUI）+ 画像 / 趋势 / 收藏 / 矩阵查看。与编码助手 Skill intake 等价，共用 data/。"""
from __future__ import annotations

import html
import os
import sys
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

import yaml

from career_compass.gui.chat_ui import CHAT_EXTRA_SCRIPT, CHAT_EXTRA_STYLES, CHAT_PANEL_HTML
from career_compass.gui.md import content_page, render_markdown
from career_compass.gui.platform import webview_gui
from career_compass.gui.static_files import spa_available
from career_compass.gui.view_data import build_all_views
from career_compass.intake import IntakeEngine, get_llm_config
from career_compass.intake.preview import build_intake_status
from career_compass.journey import build_journey_status
from career_compass.pipeline import detect_stage, run_validation
from career_compass.schema import (
    EducationStatus,
    load_constraints,
    load_opportunities,
    load_profile,
    load_saved_jobs,
    load_sectors,
    load_signals,
)

WINDOW_TITLE = "北斗星"
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 760


def _find_repo_root() -> Path:
    cwd = Path.cwd()
    if (cwd / "pyproject.toml").exists() and (cwd / "src" / "career_compass").exists():
        return cwd
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists() and (parent / "src" / "career_compass").exists():
            return parent
    return cwd


def _templates_dir() -> Path:
    return _find_repo_root() / "templates"


def _app_icon_path() -> str | None:
    """Dock 图标路径（macOS Cocoa 通过 pywebview.start(icon=...) 设置）。"""
    candidates = [
        _find_repo_root() / "assets" / "app-icon.png",
        Path(__file__).resolve().parent / "assets" / "app-icon.png",
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return None


_REPO_ROOT = _find_repo_root()


_CLI_PATH_ATTRS = (
    "DATA",
    "PROFILE",
    "CONSTRAINTS",
    "NARRATIVE",
    "SIGNALS",
    "SECTORS",
    "PROJECTS",
    "OPPORTUNITIES_YAML",
    "OPPORTUNITIES_DRAFT",
    "OPPORTUNITIES_MD",
    "JOB_PACK",
    "EXECUTION_PACK",
    "APPLICATIONS",
    "SAVED_JOBS",
    "OPPORTUNITIES_REVISED",
    "INDUSTRY_GRAPH",
    "ROLE_TAXONOMY",
    "EMPLOYER_TYPES",
    "STRATEGY",
)

_CLI_DERIVED_PATHS = {
    "PROFILE": "profile.yaml",
    "CONSTRAINTS": "constraints.yaml",
    "NARRATIVE": "narrative.md",
    "SIGNALS": "signals",
    "SECTORS": "sectors.yaml",
    "PROJECTS": "projects.yaml",
    "OPPORTUNITIES_YAML": "opportunities.yaml",
    "OPPORTUNITIES_DRAFT": "opportunities.draft.yaml",
    "OPPORTUNITIES_MD": "opportunities.md",
    "JOB_PACK": "job_pack.md",
    "EXECUTION_PACK": "execution_pack.md",
    "APPLICATIONS": "applications.yaml",
    "SAVED_JOBS": "saved_jobs.yaml",
    "OPPORTUNITIES_REVISED": "opportunities.revised.yaml",
    "INDUSTRY_GRAPH": "industry_graph.yaml",
    "ROLE_TAXONOMY": "role_taxonomy.yaml",
    "EMPLOYER_TYPES": "employer_types.yaml",
    "STRATEGY": "strategy.md",
}


def _run_cli(args: list[str], data_dir: Path) -> dict:
    import career_compass.cli as cli_module

    env_old = os.environ.get("CC_DATA")
    argv_old = sys.argv[:]
    os.environ["CC_DATA"] = str(data_dir)
    saved_attrs = {name: getattr(cli_module, name) for name in _CLI_PATH_ATTRS}
    try:
        cli_module.DATA = data_dir
        for attr, filename in _CLI_DERIVED_PATHS.items():
            setattr(cli_module, attr, data_dir / filename)
        sys.argv = ["career-compass", *args]
        buf = StringIO()
        try:
            with redirect_stdout(buf), redirect_stderr(buf):
                code = cli_module.main()
            return {"ok": code == 0, "code": code, "output": buf.getvalue().strip()}
        except SystemExit as e:
            code = int(e.code) if isinstance(e.code, int) else 1
            return {"ok": code == 0, "code": code, "output": buf.getvalue().strip()}
    finally:
        for name, value in saved_attrs.items():
            setattr(cli_module, name, value)
        sys.argv = argv_old
        if env_old is None:
            os.environ.pop("CC_DATA", None)
        else:
            os.environ["CC_DATA"] = env_old


def _esc(text: str) -> str:
    return html.escape(text or "")


def _load_profile_html(data_dir: Path) -> str:
    profile_path = data_dir / "profile.yaml"
    constraints_path = data_dir / "constraints.yaml"
    narrative_path = data_dir / "narrative.md"

    if not profile_path.exists():
        return content_page(
            "<p class='empty'>尚无个人画像。请在「<strong>对话</strong>」Tab 开始「认识自己」，"
            "或在 Claude Code / Cursor 中说「帮我做职业规划」。</p>"
        )

    profile = load_profile(profile_path)
    parts: list[str] = ["<section class='block'>"]
    parts.append(f"<h2>{_esc(profile.current_role or '个人画像')}</h2>")

    if profile.education:
        parts.append("<h3>教育背景</h3><table><tr><th>层次</th><th>院校</th><th>专业</th><th>时间</th><th>备注</th></tr>")
        for edu in profile.sorted_education():
            tier = f" <span class='tag'>{_esc(edu.school_tier)}</span>" if edu.school_tier else ""
            school = _esc(edu.school) + tier
            major = _esc(edu.major)
            if edu.department:
                major += f" · {_esc(edu.department)}"
            years: list[str] = []
            if edu.start_year:
                years.append(str(edu.start_year))
            grad = edu.graduation_hint()
            if grad:
                years.append(grad)
            time_col = "–".join(years) if years else "—"
            status = "在读" if edu.status == EducationStatus.enrolled else ""
            notes: list[str] = []
            if status:
                notes.append(status)
            if edu.ranking_or_gpa:
                notes.append(edu.ranking_or_gpa)
            if edu.honors:
                notes.append(edu.honors)
            if edu.thesis_or_focus:
                notes.append(edu.thesis_or_focus)
            if edu.advisor:
                notes.append(f"导师: {edu.advisor}")
            parts.append(
                f"<tr><td>{_esc(edu.level_label())}</td>"
                f"<td>{school}</td><td>{major}</td>"
                f"<td>{_esc(time_col)}</td>"
                f"<td>{_esc(' · '.join(notes)) if notes else '—'}</td></tr>"
            )
        parts.append("</table>")

    errors, warnings = run_validation(data_dir)
    if errors:
        parts.append("<div class='alert warn'><strong>待补齐</strong><ul>")
        for e in errors[:8]:
            parts.append(f"<li>{_esc(e)}</li>")
        parts.append("</ul></div>")
    elif warnings:
        parts.append("<div class='alert hint'><strong>建议完善</strong><ul>")
        for w in warnings[:5]:
            parts.append(f"<li>{_esc(w)}</li>")
        parts.append("</ul></div>")
    else:
        parts.append("<div class='alert ok'>✅ 画像校验通过</div>")

    parts.append("<h3>核心技能</h3><ul>")
    for s in profile.skills.core:
        parts.append(f"<li>{_esc(s)}</li>")
    parts.append("</ul>")

    if profile.skills.adjacent:
        parts.append("<h3>相邻技能</h3><ul>")
        for s in profile.skills.adjacent[:8]:
            parts.append(f"<li>{_esc(s)}</li>")
        parts.append("</ul>")

    parts.append("<h3>优势证据</h3>")
    for ev in profile.strength_evidence:
        parts.append(
            f"<div class='evidence'><strong>{_esc(ev.claim)}</strong>"
            f"<p>{_esc(ev.proof)}</p></div>"
        )

    if constraints_path.exists():
        c = load_constraints(constraints_path)
        parts.append("<h3>硬约束</h3><ul>")
        if c.age:
            parts.append(f"<li>年龄: {c.age}</li>")
        parts.append(f"<li>风险偏好: {_esc(c.risk_appetite.value)}</li>")
        if c.notes:
            parts.append(f"<li>{_esc(c.notes)}</li>")
        parts.append("</ul>")

    if narrative_path.exists():
        text = narrative_path.read_text(encoding="utf-8")
        parts.append("<hr class='section-divider'/>")
        parts.append(render_markdown(text))

    parts.append("</section>")
    return content_page("\n".join(parts))


def _load_trends_html(data_dir: Path) -> str:
    signals_dir = data_dir / "signals"
    sectors_path = data_dir / "sectors.yaml"
    parts: list[str] = []

    signals = load_signals(signals_dir)
    if signals:
        parts.append("<section class='block'><h2>外部信号</h2><p class='muted'>带来源与日期 · 分析依据</p>")
        domain_labels = {"trends": "行业趋势", "market": "市场供需", "landscape": "产业格局"}
        for domain, sigs in signals.items():
            label = domain_labels.get(domain, domain)
            parts.append(f"<h3>{_esc(label)}</h3>")
            for s in sigs:
                url = f' <a href="{s.source_url}">链接</a>' if s.source_url else ""
                parts.append(
                    f"<div class='signal'>"
                    f"<div class='signal-head'><strong>{_esc(s.topic)}</strong>"
                    f" <span class='tag'>{_esc(s.confidence)}</span>"
                    f" <span class='muted'>{s.retrieved_on}</span></div>"
                    f"<p>{_esc(s.finding)}</p>"
                    f"<p class='muted'>来源: {_esc(s.source)}{url}</p>"
                    f"</div>"
                )
        parts.append("</section>")
    else:
        parts.append("<p class='empty'>「探索世界」尚无市场信号。让 Agent 联网调研，或使用 CLI 写入 <code>data/signals/</code>。</p>")

    if sectors_path.exists():
        sectors = load_sectors(sectors_path)
        parts.append("<section class='block'><h2>热门赛道池</h2>")
        for sec in sectors[:9]:
            parts.append(f"<div class='sector'><strong>{_esc(sec.name)}</strong>")
            if sec.why_hot:
                parts.append(f"<p>🔥 {_esc(sec.why_hot)}</p>")
            if sec.value_is_in:
                parts.append(f"<p>价值在: {_esc(sec.value_is_in)}</p>")
            if sec.trap:
                parts.append(f"<p class='trap'>⚠️ 陷阱: {_esc(sec.trap)}</p>")
            parts.append("</div>")
        parts.append("</section>")

    return content_page("\n".join(parts) if parts else "<p class='empty'>「探索世界」暂无趋势数据。完成认识自己后，开始采集行业信号。</p>")


def _load_jobs_html(data_dir: Path) -> str:
    jobs_path = data_dir / "saved_jobs.yaml"
    if not jobs_path.exists():
        return content_page(
            "<p class='empty'>「探索世界」尚无收藏岗位。</p>"
            "<p class='muted'>浏览 JD 时可终端收藏: <code>career-compass job add \"公司\" \"岗位\" --file jd.txt</code></p>"
        )

    from career_compass.jobs import analyze_saved_job

    data = load_saved_jobs(jobs_path)
    profile_path = data_dir / "profile.yaml"
    profile = load_profile(profile_path) if profile_path.exists() else None
    projects_path = data_dir / "projects.yaml"
    projects = None
    if projects_path.exists():
        from career_compass.schema import load_projects
        projects = load_projects(projects_path)
    constraints = None
    cp = data_dir / "constraints.yaml"
    if cp.exists():
        constraints = load_constraints(cp)

    parts = [f"<p class='muted'>共 {len(data.jobs)} 个收藏 · 对照画像分析</p>"]
    for job in data.jobs:
        parts.append(
            f"<div class='job-card'>"
            f"<h3>{_esc(job.company)} · {_esc(job.role)}</h3>"
            f"<p class='muted'>{_esc(job.location)} · {job.saved_on} · [{job.status.value}]</p>"
        )
        if job.notes:
            parts.append(f"<p><em>{_esc(job.notes)}</em></p>")
        if profile:
            report = analyze_saved_job(job, profile, projects, constraints, data_dir=data_dir)
            parts.append(f"<p><strong>匹配摘要:</strong> {_esc(report.summary)}</p>")
            if report.linked_direction:
                parts.append(f"<p>关联方向: {_esc(report.linked_direction)}</p>")
            if report.barriers:
                parts.append("<ul class='barriers'>")
                for b in report.barriers:
                    parts.append(f"<li>⚠️ {_esc(b)}</li>")
                parts.append("</ul>")
        parts.append("</div>")
    return content_page("\n".join(parts))


def _matrix_table_html(opps: list, *, title: str) -> str:
    if not opps:
        return f"<h3>{_esc(title)}</h3><p class='empty'>暂无方向</p>"
    headers = ["#", "方向", "岗位名称", "组织类型", "比较优势", "Ikigai", "顺风", "试错成本", "综合"]
    rows = [f"<h3>{_esc(title)}</h3><table><tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>"]
    for i, o in enumerate(opps, 1):
        top_role = o.role_families[0].role if o.role_families else "—"
        row = (
            f"<tr><td>{i}</td>"
            f"<td>{_esc(o.direction)}</td>"
            f"<td>{_esc(top_role)}</td>"
            f"<td>{_esc(o.employer_label or '—')}</td>"
            f"<td>{_esc(o.fit)}</td>"
            f"<td>{_esc(o.match)}</td>"
            f"<td>{_esc(o.wind)}</td>"
            f"<td>{_esc(o.risk)}</td>"
            f"<td><strong>{_esc(o.composite)}</strong></td>"
        )
        row += "</tr>"
        rows.append(row)
    rows.append("</table>")
    return "\n".join(rows)


def _load_matrix_html(data_dir: Path) -> str:
    md_path = data_dir / "opportunities.md"
    if md_path.exists():
        return content_page(render_markdown(md_path.read_text(encoding="utf-8")))
    yaml_path = data_dir / "opportunities.yaml"
    if yaml_path.exists():
        matrix = load_opportunities(yaml_path)
        parts: list[str] = []
        if matrix.unified_theme:
            parts.append(
                f"<div class='alert hint'><strong>统一架构</strong>"
                f"<p>{_esc(matrix.unified_theme)}</p></div>"
            )
        if matrix.shared_assets:
            parts.append(
                "<p><strong>共享资产</strong></p><ul>"
                + "".join(f"<li>{_esc(a)}</li>" for a in matrix.shared_assets)
                + "</ul>"
            )
        parts.append(_matrix_table_html(matrix.ranked_primary(), title="方向（Primary）"))
        parts.append("<p class='muted'>YAML 摘要 · 点击「渲染矩阵」生成完整 Markdown</p>")
        return content_page("\n".join(parts))
    return content_page(
        "<p class='empty'>「做出决策」尚无机会矩阵。</p>"
        "<p class='muted'>完成探索世界后，让 Agent 运行 analyze 生成 <code>opportunities.yaml</code>，"
        "再点击「渲染矩阵」。</p>"
    )


HTML_SHELL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<title>北斗星</title>
<style>
  :root {
    color-scheme: light dark;
    --bg: #f5f5f7; --card: #fff; --text: #1d1d1f; --muted: #6e6e73;
    --accent: #0071e3; --border: #d2d2d7; --ok: #248a3d; --warn: #b45309;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #1c1c1e; --card: #2c2c2e; --text: #f5f5f7; --muted: #98989d; --border: #3a3a3c; }
  }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--bg); color: var(--text); height: 100vh; display: flex; flex-direction: column; }
  header { padding: 12px 20px; background: var(--card); border-bottom: 1px solid var(--border);
    display: flex; align-items: baseline; gap: 10px; -webkit-app-region: drag; }
  header h1 { margin: 0; font-size: 17px; }
  header .sub { color: var(--muted); font-size: 12px; }
  header .path { margin-left: auto; font-size: 11px; color: var(--muted); -webkit-app-region: no-drag; }
  nav { display: flex; gap: 0; padding: 0 16px; background: var(--card); border-bottom: 1px solid var(--border); }
  nav button { flex: 1; max-width: 160px; background: none; border: none; border-bottom: 2px solid transparent;
    color: var(--muted); padding: 12px 8px; font-size: 13px; cursor: pointer; -webkit-app-region: no-drag; }
  nav button.active { color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }
  .toolbar { padding: 8px 20px; display: flex; gap: 8px; background: var(--card);
    border-bottom: 1px solid var(--border); -webkit-app-region: no-drag; }
  .toolbar button { background: var(--accent); color: #fff; border: none; border-radius: 6px;
    padding: 6px 12px; font-size: 12px; cursor: pointer; }
  .toolbar button.secondary { background: var(--border); color: var(--text); }
  main { flex: 1; overflow: auto; padding: 16px 20px 24px; }
  .panel { display: none; } .panel.active { display: block; }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px 20px; }

  /* 各 Tab 统一排版 */
  .content { font-size: 14px; line-height: 1.55; color: var(--text); }
  .content h1 { font-size: 20px; font-weight: 700; margin: 0 0 14px; line-height: 1.3; }
  .content h2 { font-size: 17px; font-weight: 600; margin: 22px 0 10px; line-height: 1.35; }
  .content h3 { font-size: 15px; font-weight: 600; margin: 18px 0 8px; line-height: 1.35; }
  .content h4 { font-size: 14px; font-weight: 600; margin: 14px 0 6px; line-height: 1.35; }
  .content h1:first-child, .content h2:first-child, .content h3:first-child { margin-top: 0; }
  .content p { margin: 8px 0; }
  .content ul, .content ol { margin: 8px 0 10px; padding-left: 22px; }
  .content li { margin: 4px 0; }
  .content li > ul, .content li > ol { margin-top: 4px; }
  .content blockquote { margin: 10px 0; padding: 8px 12px; border-left: 3px solid var(--accent);
    background: rgba(0,113,227,0.06); color: var(--text); }
  .content blockquote p { margin: 4px 0; }
  .content hr, .content .section-divider { border: none; border-top: 1px solid var(--border); margin: 20px 0; }
  .content strong { font-weight: 600; }
  .content em { font-style: italic; }
  .content code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.92em;
    background: rgba(0,0,0,0.06); padding: 1px 5px; border-radius: 4px; }
  .content pre { background: rgba(0,0,0,0.05); border-radius: 8px; padding: 12px; overflow: auto;
    font-size: 13px; line-height: 1.45; }
  .content pre code { background: none; padding: 0; }
  .content table { border-collapse: collapse; width: 100%; font-size: 13px; margin: 10px 0 14px; }
  .content th, .content td { border: 1px solid var(--border); padding: 7px 9px; text-align: left;
    vertical-align: top; }
  .content th { background: rgba(0,0,0,0.04); font-weight: 600; }
  .content a { color: var(--accent); text-decoration: none; }
  .content a:hover { text-decoration: underline; }

  .empty { color: var(--muted); }
  .muted { color: var(--muted); font-size: 13px; }
  .alert { border-radius: 8px; padding: 10px 12px; margin: 10px 0; font-size: 14px; }
  .alert p { margin: 6px 0 0; }
  .alert ul { margin: 6px 0 0; padding-left: 18px; }
  .alert.ok { background: rgba(36,138,61,0.12); color: var(--ok); }
  .alert.warn { background: rgba(180,83,9,0.12); }
  .alert.hint { background: rgba(0,113,227,0.08); }
  .evidence { margin: 10px 0; padding: 10px 12px; background: rgba(0,0,0,0.03); border-radius: 8px; }
  .evidence strong { display: block; margin-bottom: 4px; font-weight: 600; }
  .evidence p { margin: 0; color: var(--muted); font-size: 13px; }
  .signal, .sector, .job-card { margin: 12px 0; padding: 12px; border: 1px solid var(--border); border-radius: 8px; }
  .signal-head { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .tag { font-size: 11px; background: var(--border); padding: 2px 6px; border-radius: 4px; }
  .trap { color: var(--warn); }
  .barriers { color: var(--warn); padding-left: 18px; }
  #toast { position: fixed; bottom: 16px; right: 16px; background: var(--card); border: 1px solid var(--border);
    padding: 10px 14px; border-radius: 8px; font-size: 13px; display: none; max-width: 360px; white-space: pre-wrap; }
  .journey-bar { display: flex; gap: 4px; padding: 10px 12px; background: var(--card);
    border-bottom: 1px solid var(--border); overflow-x: auto; -webkit-app-region: no-drag; }
  .journey-step { flex: 1; min-width: 88px; text-align: center; font-size: 11px; color: var(--muted); padding: 2px 4px; }
  .journey-step .num { display: block; width: 24px; height: 24px; line-height: 24px; border-radius: 50%;
    background: var(--border); font-size: 11px; margin: 0 auto 4px; font-weight: 600; }
  .journey-step .label { display: block; white-space: nowrap; }
  .journey-step.done { color: var(--ok); }
  .journey-step.done .num { background: rgba(36,138,61,0.18); color: var(--ok); }
  .journey-step.current { color: var(--accent); }
  .journey-step.current .num { background: var(--accent); color: #fff; }
  .journey-step.optional .label::after { content: ' · 可选'; font-size: 10px; color: var(--muted); }
  .journey-bar.complete { background: rgba(36,138,61,0.06); }
  .journey-bar.complete .journey-step.done .num { background: rgba(36,138,61,0.22); }
  .journey-complete-badge { flex: 0 0 auto; align-self: center; margin-left: 8px; padding: 4px 12px;
    border-radius: 999px; font-size: 12px; font-weight: 600; color: var(--ok);
    background: rgba(36,138,61,0.15); white-space: nowrap; }
  .journey-hint.complete { background: rgba(36,138,61,0.08); color: var(--ok); }
  .journey-hint { padding: 8px 20px; font-size: 12px; color: var(--muted);
    background: rgba(0,113,227,0.05); border-bottom: 1px solid var(--border); -webkit-app-region: no-drag; }
""" + CHAT_EXTRA_STYLES + """
</style>
</head>
<body>
<header>
  <h1>北斗星</h1>
  <span class="sub" id="journeySubtitle">认识自己 → 探索世界 → 做出决策 → 开始行动 → 持续追踪</span>
  <span class="path" id="dataPath"></span>
</header>
<div class="journey-bar" id="journeyBar"></div>
<p class="journey-hint" id="journeyHint">加载中…</p>
<nav>
  <button id="tab-chat" class="active" onclick="showTab('chat')">对话</button>
  <button id="tab-profile" onclick="showTab('profile')">我的画像</button>
  <button id="tab-trends" class="locked" onclick="showTabSafe('trends')">行业趋势</button>
  <button id="tab-jobs" class="locked" onclick="showTabSafe('jobs')">岗位收藏</button>
  <button id="tab-matrix" class="locked" onclick="showTabSafe('matrix')">机会矩阵</button>
</nav>
<div class="toolbar" id="toolbar">
  <button onclick="run('chat-reset')">重置对话</button>
  <button class="secondary" onclick="refresh()">刷新</button>
</div>
<main>
""" + CHAT_PANEL_HTML + """
  <section id="panel-profile" class="panel"><div class="card" id="profile"></div></section>
  <section id="panel-trends" class="panel"><div class="card" id="trends"></div></section>
  <section id="panel-jobs" class="panel"><div class="card" id="jobs"></div></section>
  <section id="panel-matrix" class="panel"><div class="card" id="matrix"></div></section>
</main>
<div id="toast"></div>
<script>
const TOOLBARS = {
  chat: [['重置对话', 'chat-reset'], ['刷新', 'refresh']],
  profile: [['校验画像', 'validate'], ['刷新', 'refresh']],
  trends: [['刷新', 'refresh']],
  jobs: [['分析收藏', 'job-analyze'], ['刷新', 'refresh']],
  matrix: [['渲染矩阵', 'render-opportunities'], ['刷新', 'refresh']],
};
let currentTab = 'chat';

function showTab(name) {
  currentTab = name;
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
  document.getElementById('panel-' + name).classList.add('active');
  document.getElementById('tab-' + name).classList.add('active');
  const tb = document.getElementById('toolbar');
  const items = TOOLBARS[name] || [['刷新', 'refresh']];
  tb.innerHTML = items.map(([label, cmd]) =>
    `<button class="${cmd==='refresh'?'secondary':''}" onclick="${cmd==='refresh'?'refresh()':`run('${cmd}')`}">${label}</button>`
  ).join('');
  if (name === 'chat') loadChatState();
}

function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.style.display = 'block';
  setTimeout(() => { el.style.display = 'none'; }, 4000);
}

async function refresh() {
  const data = await pywebview.api.load_all();
  document.getElementById('dataPath').textContent = data.data_dir;
  document.getElementById('profile').innerHTML = data.profile_html;
  document.getElementById('trends').innerHTML = data.trends_html;
  document.getElementById('jobs').innerHTML = data.jobs_html;
  document.getElementById('matrix').innerHTML = data.matrix_html;
  if (data.journey && typeof renderJourney === 'function') {
    renderJourney(data.journey);
  }
  if (typeof updateTabLocks === 'function') {
    updateTabLocks(!!data.intake_complete);
  }
}

async function run(cmd) {
  if (cmd === 'refresh') { await refresh(); return; }
  if (cmd === 'chat-reset') {
    await pywebview.api.chat_reset();
    await loadChatState();
    toast('对话已重置');
    return;
  }
  const res = await pywebview.api.run_command(cmd);
  toast('career-compass ' + cmd + ' (exit ' + res.code + ')');
  await refresh();
  if (cmd === 'validate') showTab('profile');
  if (cmd === 'render-opportunities') showTab('matrix');
  if (cmd === 'job-analyze') showTab('jobs');
}

""" + CHAT_EXTRA_SCRIPT + """

window.addEventListener('pywebviewready', async () => {
  await refresh();
  const state = await loadChatState();
  showTab(state.intake_complete ? 'profile' : 'chat');
});
</script>
</body>
</html>
"""


class AppApi:
    def __init__(self, data_dir: Path | None = None) -> None:
        # Single-user desktop mode: resolve from CC_DATA / repo default.
        # SaaS mode: the caller passes a per-user data_dir (see web.user_data).
        if data_dir is None:
            data_dir = Path(os.getenv("CC_DATA", _REPO_ROOT / "data"))
        self.data_dir = data_dir.resolve()
        self._intake: IntakeEngine | None = None

    def _intake_engine(self) -> IntakeEngine:
        if self._intake is None:
            self._intake = IntakeEngine(self.data_dir, templates_dir=_templates_dir())
        return self._intake

    def chat_state(self) -> dict:
        cfg = get_llm_config()
        status = build_intake_status(self.data_dir)
        pipeline = detect_stage(self.data_dir)
        journey = build_journey_status(self.data_dir)
        return {
            "messages": self._intake_engine().get_messages(),
            "llm": {
                "provider": cfg.provider,
                "model": cfg.model,
                "configured": cfg.configured,
            },
            "stage": pipeline.stage.value,
            "journey": journey.to_dict(),
            **status,
        }

    def chat_send(self, message: str) -> dict:
        result = self._intake_engine().chat(message)
        status = build_intake_status(self.data_dir)
        journey = build_journey_status(self.data_dir)
        return {
            "reply": result.reply,
            "ok": result.ok,
            "messages": self._intake_engine().get_messages(),
            "files_updated": result.files_updated,
            "just_completed": result.just_completed,
            "llm": {
                "provider": result.llm_provider,
                "model": result.llm_model,
                "configured": get_llm_config().configured,
            },
            "journey": journey.to_dict(),
            **status,
        }

    def chat_reset(self) -> dict:
        self._intake_engine().reset()
        return {"ok": True}

    def load_all(self) -> dict:
        status = build_intake_status(self.data_dir)
        journey = build_journey_status(self.data_dir)
        views = build_all_views(self.data_dir)
        payload: dict = {
            "data_dir": str(self.data_dir),
            "intake_complete": status["intake_complete"],
            "journey": journey.to_dict(),
            "views": views,
            "spa": spa_available(),
        }
        # Legacy inline-HTML UI fallback
        payload["profile_html"] = _load_profile_html(self.data_dir)
        payload["trends_html"] = _load_trends_html(self.data_dir)
        payload["jobs_html"] = _load_jobs_html(self.data_dir)
        payload["matrix_html"] = _load_matrix_html(self.data_dir)
        return payload

    def run_command(self, cmd: str) -> dict:
        mapping = {
            "validate": ["validate"],
            "render-opportunities": ["render-opportunities"],
            "render-execution": ["render-execution"],
            "replan": ["replan", "--write"],
            "job-analyze": ["job", "analyze"],
            "refresh": [],
        }
        if cmd == "refresh":
            return {"ok": True, "code": 0, "output": ""}
        args = mapping.get(cmd, [cmd])
        return _run_cli(args, self.data_dir)

    # ---- 感兴趣岗位（用户在 UI 上手动新增 / 上传 JD）----
    def jobs_add(
        self,
        company: str,
        role: str,
        description: str,
        *,
        location: str = "",
        source: str = "手动添加",
        linked_direction: str = "",
        notes: str = "",
    ) -> dict:
        from career_compass.jobs import add_saved_job

        path = self.data_dir / "saved_jobs.yaml"
        try:
            job = add_saved_job(
                path,
                company=company,
                role=role,
                description=description,
                location=location,
                source=source,
                linked_direction=linked_direction,
                notes=notes,
            )
        except (ValueError, TypeError) as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True, "job": job.model_dump(mode="json")}

    def jobs_update(self, job_id: str, **fields: object) -> dict:
        from career_compass.jobs import update_saved_job
        from career_compass.schema import SavedJobStatus

        path = self.data_dir / "saved_jobs.yaml"
        kwargs: dict = {}
        for key in (
            "company", "role", "description", "location",
            "source", "linked_direction", "notes",
        ):
            if key in fields and fields[key] is not None:
                kwargs[key] = str(fields[key])
        if "status" in fields and fields["status"] is not None:
            raw_status = str(fields["status"]).strip()
            try:
                kwargs["status"] = SavedJobStatus(raw_status)
            except ValueError:
                return {"ok": False, "error": f"invalid status: {raw_status}"}
        try:
            job = update_saved_job(path, job_id, **kwargs)
        except (ValueError, TypeError) as e:
            return {"ok": False, "error": str(e)}
        if job is None:
            return {"ok": False, "error": "job not found"}
        return {"ok": True, "job": job.model_dump(mode="json")}

    def jobs_remove(self, job_id: str) -> dict:
        from career_compass.jobs import remove_saved_job

        path = self.data_dir / "saved_jobs.yaml"
        removed = remove_saved_job(path, job_id)
        if not removed:
            return {"ok": False, "error": "job not found"}
        return {"ok": True, "removed": job_id}

    # ---- 矩阵反馈（用户在 UI 上 remove / reorder / reset）----
    def matrix_feedback(self) -> dict:
        from career_compass.matrix_feedback import list_actions

        path = self.data_dir / "matrix_feedback.yaml"
        return {"actions": [a.model_dump(mode="json") for a in list_actions(path)]}

    def matrix_feedback_add(
        self,
        action: str,
        direction: str = "",
        details: dict | None = None,
        timestamp: str | None = None,
    ) -> dict:
        from career_compass.matrix_feedback import append_action

        path = self.data_dir / "matrix_feedback.yaml"
        try:
            entry = append_action(
                path,
                action=action,
                direction=direction,
                details=details,
                timestamp=timestamp,
            )
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True, "action": entry.model_dump(mode="json")}


def main(argv: list[str] | None = None) -> None:
    from career_compass.env import ensure_llm_env_defaults

    ensure_llm_env_defaults()
    args = list(argv if argv is not None else sys.argv[1:])
    api = AppApi()

    legacy = "--legacy" in args
    desktop = "--desktop" in args
    no_browser = "--no-browser" in args

    port = 8765
    if "--port" in args:
        idx = args.index("--port")
        if idx + 1 < len(args):
            port = int(args[idx + 1])

    from .web_server import run_web_server, start_web_server_background

    if legacy:
        run_web_server(api, legacy_html=HTML_SHELL, port=port, open_browser=not no_browser)
        return

    if desktop:
        server, url = start_web_server_background(api, legacy_html=HTML_SHELL, port=port)
        try:
            import webview as _webview
        except ImportError:
            server.shutdown()
            print("未安装 pywebview，改用浏览器模式:")
            print(f"  uv run career-compass-app --port {port}")
            raise SystemExit(1) from None

        print(f"北斗星桌面版: {url}")
        _webview.create_window(
            WINDOW_TITLE,
            url=url,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            min_size=(820, 580),
            text_select=True,
        )
        icon = _app_icon_path()
        gui = webview_gui()
        kwargs: dict = {"icon": icon} if icon else {}
        try:
            if gui:
                _webview.start(gui=gui, **kwargs)
            else:
                _webview.start(**kwargs)
        except Exception as e:
            msg = str(e)
            if "QT or GTK" in msg or "WebViewException" in type(e).__name__:
                print("桌面窗口不可用，请在浏览器打开:")
                print(f"  {url}")
                raise SystemExit(1) from e
            raise
        finally:
            server.shutdown()
        return

    if not spa_available():
        print("提示: 未检测到前端构建产物，将使用旧版 UI。")
        print("  构建现代化界面: ./scripts/build-frontend.sh")
    run_web_server(api, legacy_html=HTML_SHELL, port=port, open_browser=not no_browser)


if __name__ == "__main__":
    main()
