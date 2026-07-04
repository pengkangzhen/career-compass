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

from .schema import Profile, Signal


def scan_plan(profile: Profile) -> list[str]:
    """基于画像生成检索查询。优先级：前沿技能 > 核心技能 > 所在行业 > 当前角色的下一步。"""
    queries: list[str] = []
    for skill in profile.skills.frontier:
        queries.append(f'"{skill}" 行业趋势 需求增速 供给 2026')
    for skill in profile.skills.core[:3]:
        queries.append(f'"{skill}" 人才市场 供需 薪酬范围')
    for exp in profile.experience[:2]:
        queries.append(f"{exp.company} 所在行业 未来三年格局 头部玩家")
    if profile.current_role:
        queries.append(f'"{profile.current_role}" 职业发展路径 典型下一步 转型方向')
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
    """校验并追加一条信号到 data/signals/{domain}.yaml。domain 如 trends / market / landscape。"""
    signals_dir.mkdir(parents=True, exist_ok=True)
    path = signals_dir / f"{domain}.yaml"
    existing: list[dict] = []
    if path.exists():
        existing = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("signals", [])
    if source_url is not None:
        source_url = source_url.strip() or None  # 空串 → None，避免 HttpUrl 校验失败
    sig = Signal(
        topic=topic,
        finding=finding,
        source=source,
        source_url=source_url,
        retrieved_on=retrieved_on,
        confidence=confidence,
    )
    existing.append(sig.model_dump(mode="json"))
    path.write_text(
        yaml.safe_dump({"signals": existing}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path
