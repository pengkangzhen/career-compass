"""外部信号采集辅助。

真正的联网检索由 Claude 用 web-search-prime / deep-research / WebSearch 完成；
本模块只做两件事：
  (a) scan_plan —— 从画像**派生**检索查询，确保信号围绕"这个人"而不是泛泛而谈；
  (b) add_signal —— 校验并持久化一条信号到 data/signals/{domain}.yaml。
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import yaml

from .schema import Constraints, Profile, Signal, is_signal_stale, load_sectors


def scan_plan(
    profile: Profile,
    sectors_path: Path | None = None,
    constraints: Constraints | None = None,
) -> list[str]:
    """基于画像（及可选 sectors/constraints）生成检索查询。"""
    queries: list[str] = []
    for skill in profile.skills.frontier:
        queries.append(f'"{skill}" 行业趋势 需求增速 供给 2026')
    for skill in profile.skills.core[:3]:
        queries.append(f'"{skill}" 人才市场 供需 薪酬范围')
    for exp in profile.experience[:2]:
        queries.append(f"{exp.company} 所在行业 未来三年格局 头部玩家")
    if profile.current_role:
        queries.append(f'"{profile.current_role}" 职业发展路径 典型下一步 转型方向')

    if sectors_path and sectors_path.exists():
        sectors = load_sectors(sectors_path)
        for sector in sectors[:5]:
            if sector.name:
                queries.append(f'"{sector.name}" 2026 人才需求 竞争 内卷 薪酬')
            if sector.trap:
                queries.append(f'"{sector.name}" {sector.trap} 岗位陷阱 壁垒')

    if constraints:
        if constraints.geo:
            geo = " ".join(constraints.geo[:2])
            queries.append(f"{geo}  tech 就业市场 岗位供需 2026")
        queries.append(
            f"职业转型 risk appetite {constraints.risk_appetite.value} "
            f"runway {constraints.financial_runway_months} months 低试错成本决策"
        )

    if not queries:
        queries.append("(画像太单薄，先回到 playbook 1-intake 补齐 core skills / experience)")
    return queries


def add_signal(
    signals_dir: Path,
    domain: str,
    topic: str,
    finding: str,
    source: str,
    retrieved_on: date,
    source_url: Optional[str] = None,
    confidence: str = "medium",
) -> Path:
    """校验并写入信号；同 topic 去重（更新而非追加）。"""
    signals_dir.mkdir(parents=True, exist_ok=True)
    path = signals_dir / f"{domain}.yaml"
    existing: list[dict] = []
    if path.exists():
        existing = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("signals", [])
    if source_url is not None:
        source_url = source_url.strip() or None
    sig = Signal(
        topic=topic,
        finding=finding,
        source=source,
        source_url=source_url,
        retrieved_on=retrieved_on,
        confidence=confidence,
    )
    payload = sig.model_dump(mode="json")
    topic_key = topic.strip().lower()
    updated = False
    for i, item in enumerate(existing):
        if str(item.get("topic", "")).strip().lower() == topic_key:
            existing[i] = payload
            updated = True
            break
    if not updated:
        existing.append(payload)
    path.write_text(
        yaml.safe_dump({"signals": existing}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path


def stale_signals(
    signals_dir: Path,
    max_age_days: int = 90,
) -> list[tuple[str, Signal]]:
    """返回 (domain, signal) 列表，均为超过 max_age_days 的 stale 信号。"""
    out: list[tuple[str, Signal]] = []
    if not signals_dir.exists():
        return out
    for p in sorted(signals_dir.glob("*.yaml")):
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        for item in raw.get("signals", []):
            sig = Signal.model_validate(item)
            if is_signal_stale(sig, max_age_days):
                out.append((p.stem, sig))
    return out
