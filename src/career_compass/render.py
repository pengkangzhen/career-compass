"""渲染辅助：聚合 brief、渲染机会矩阵（核心交付物）、渲染 strategy.md 骨架。"""
from __future__ import annotations

from pathlib import Path

import yaml
from jinja2 import Template

from .schema import (
    load_constraints,
    load_opportunities,
    load_projects,
    load_profile,
    load_sectors,
    load_signals,
)


def brief(
    profile_path: Path,
    constraints_path: Path,
    narrative_path: Path,
    signals_dir: Path,
    sectors_path: Path,
    projects_path: Path,
) -> str:
    """聚合所有数据文件为一份分析用 brief。"""
    profile = load_profile(profile_path)
    constraints = load_constraints(constraints_path)
    signals = load_signals(signals_dir)
    sectors = load_sectors(sectors_path)
    projects = load_projects(projects_path).projects if projects_path.exists() else []
    narrative = narrative_path.read_text(encoding="utf-8") if narrative_path.exists() else "(narrative.md 尚未填写)"

    lines: list[str] = ["# Career-Compass Brief\n"]

    lines.append("## Profile")
    lines.append("```yaml\n" + yaml.safe_dump(
        profile.model_dump(mode="json"), allow_unicode=True, sort_keys=False
    ) + "```")

    lines.append("## Constraints（硬边界，分析必须遵守）")
    lines.append("```yaml\n" + yaml.safe_dump(
        constraints.model_dump(mode="json"), allow_unicode=True, sort_keys=False
    ) + "```")

    lines.append("## Narrative（职业故事 / 偏好 / 红线）\n")
    lines.append(narrative)

    lines.append("\n## 目标行业池（用户调研；source 未补齐的视为待验证）")
    if sectors:
        for s in sectors:
            tag = "✅已验证" if s.source.strip() else "⚠️待验证"
            lines.append(f"\n- **{s.name}** [{tag}]")
            if s.why_hot:
                lines.append(f"  - why hot: {s.why_hot}")
            if s.value_is_in:
                lines.append(f"  - 价值在: {s.value_is_in}")
            if s.trap:
                lines.append(f"  - ⚠️陷阱: {s.trap}")
            if s.fit_notes:
                lines.append(f"  - 与你的交叉: {s.fit_notes}")
    else:
        lines.append("\n(尚无目标行业池 —— 把调研的赛道写进 data/sectors.yaml)")

    lines.append("\n## Projects（scan-projects 自动采集的证据）")
    if projects:
        for p in projects:
            head = f"**{p.name}** — {p.description}" if p.description else f"**{p.name}**"
            lines.append(f"\n- {head}")
            if p.inferred_signals:
                lines.append(f"  - 信号: {', '.join(p.inferred_signals)}")
            if p.key_dependencies:
                lines.append(f"  - 关键依赖: {', '.join(p.key_dependencies)}")
            lang = ", ".join(f"{k}({v})" for k, v in list(p.languages.items())[:4])
            if lang:
                lines.append(f"  - 语言: {lang}")
            bits = [f"{p.scale.files} files"]
            if p.scale.commits is not None:
                bits.append(f"{p.scale.commits} commits")
            if p.scale.has_tests:
                bits.append("有测试")
            if p.artifacts:
                bits.append("·".join(p.artifacts))
            lines.append(f"  - 规模/成果: {' · '.join(bits)}")
    else:
        lines.append("\n(尚无项目证据 —— 跑 `uv run career-compass scan-projects <dir...>` 采集)")

    lines.append("\n## External Signals（带来源与日期）")
    if signals:
        for domain, sigs in signals.items():
            lines.append(f"\n### {domain}")
            for s in sigs:
                url = f"  {s.source_url}" if s.source_url else ""
                lines.append(
                    f"- [{s.confidence}] {s.topic}: {s.finding} — {s.source}{url} ({s.retrieved_on})"
                )
    else:
        lines.append("\n(尚无外部信号 —— 先跑 playbook 2-scan)")

    return "\n".join(lines)


# 机会矩阵渲染 —— 本项目的核心交付物。
_OPPORTUNITIES_TEMPLATE = """# 机会矩阵 — {{ generated_on }}

> 本项目的**核心交付物**：N 个可比较、有依据的职业方向。
> 数据源是 `opportunities.yaml`（改评分改那里）；本文件由 `career-compass render-opportunities` 渲染，不要手改。

## 总览

| # | 方向 | 契合(L1) | 匹配(L2) | 顺风(L3) | 可逆(L4) | 综合 |
|---|------|----------|----------|----------|----------|------|
{% for o in ranked -%}
| {{ loop.index }} | {{ o.direction }} | {{ o.fit }} | {{ o.match }} | {{ o.wind }} | {{ o.risk }} | {{ o.composite }} |
{% endfor %}

## 各方向详情

{% for o in ranked %}
### {{ o.direction }}　·　综合 {{ o.composite }}

- **契合度 ({{ o.fit }})** — {{ o.fit_rationale }}
- **匹配 / 期权 ({{ o.match }})** — {{ o.match_rationale }}
- **顺风 / 逆风 ({{ o.wind }})** — {{ o.wind_rationale }}
- **可逆性 ({{ o.risk }})** — {{ o.risk_rationale }}

**打开的选项**（这条路通向什么）：
{% for x in o.opens_up -%}
- {{ x }}
{% else -%}
- (待填)
{% endfor %}
**机会成本**（选它会排除什么）：
{% for x in o.costs -%}
- {{ x }}
{% else -%}
- (待填)
{% endfor %}
**可逆的第一步**：{{ o.first_step or "(待填)" }}

---
{% endfor %}

## 下一步

这张表本身就是交付物。若想深入某个方向，从中**挑一个**，再跑 `playbooks/4-plan.md` 展开成短/中/长期路径。
"""


def render_opportunities(opportunities_path: Path) -> str:
    matrix = load_opportunities(opportunities_path)
    return Template(_OPPORTUNITIES_TEMPLATE).render(
        generated_on=matrix.generated_on.isoformat(),
        ranked=matrix.ranked(),
    )


# strategy.md 骨架（可选阶段）。
_STRATEGY_TEMPLATE = """# Career Strategy — {{ date }}　·　方向：{{ direction | default("(待选定)") }}

> 由 playbook 4-plan 生成（用户从机会矩阵里选定一个方向后才进入此阶段）。每次覆盖重写，历史在 git 里。

## 选定方向及理由
{{ direction_rationale | default("(待填：为什么从机会矩阵里选这个，为什么不选第二名)") }}

## 路径

### 短期 (0-6 月)
{{ short_term | default("(待填：下一步具体动作)") }}

### 中期 (6-18 月)
{{ mid_term | default("(待填)") }}

### 长期 (1-3 年)
{{ long_term | default("(待填：保留分叉点，不要写成预言)") }}

## 关键假设与退出条件
> 每条路径写明"假设 X 成立"和"若 Y 发生则退出/转向"。由 playbook 5-stress-test 挑战。

{{ assumptions | default("(待填)") }}
"""


def render_strategy(ctx: dict) -> str:
    return Template(_STRATEGY_TEMPLATE).render(**ctx)
