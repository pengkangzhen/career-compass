"""JD 文本 → 机会矩阵方向关联（数据驱动，替代 jobs.py 硬编码）。"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from .registry import capability_label
from .schema import OpportunityMatrix, load_opportunities

_DATA_DIR = Path.cwd() / "data"


class JdLinkRule(BaseModel):
    capability_id: str
    patterns: list[str] = Field(default_factory=list)


class EmployerHint(BaseModel):
    employer_id: str
    patterns: list[str] = Field(default_factory=list)


class JdLinkRulesFile(BaseModel):
    rules: list[JdLinkRule] = Field(default_factory=list)
    employer_hints: list[EmployerHint] = Field(default_factory=list)


@lru_cache(maxsize=1)
def load_jd_link_rules(data_dir: Path | None = None) -> JdLinkRulesFile:
    path = (data_dir or _DATA_DIR) / "jd_link_rules.yaml"
    if not path.is_file():
        return JdLinkRulesFile()
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return JdLinkRulesFile.model_validate(raw)


def clear_jd_link_cache() -> None:
    load_jd_link_rules.cache_clear()


def _normalize_blob(blob: str) -> str:
    return blob.strip().lower()


def _pattern_hits(blob: str, pattern: str) -> int:
    pat = pattern.strip().lower()
    if not pat:
        return 0
    if ".*" in pat or pat.startswith("("):
        return len(re.findall(pat, blob, re.I))
    return blob.count(pat)


def score_capability(blob: str, rules: JdLinkRulesFile) -> tuple[str, int]:
    """返回 (capability_id, hit_count)。"""
    norm = _normalize_blob(blob)
    best_cap = ""
    best_hits = 0
    for rule in rules.rules:
        hits = sum(_pattern_hits(norm, p) for p in rule.patterns)
        if hits > best_hits:
            best_hits = hits
            best_cap = rule.capability_id
    return best_cap, best_hits


def infer_employer_id(blob: str, rules: JdLinkRulesFile) -> str:
    norm = _normalize_blob(blob)
    for hint in rules.employer_hints:
        if any(_pattern_hits(norm, p) > 0 for p in hint.patterns):
            return hint.employer_id
    return ""


def format_direction(
    capability_id: str,
    matrix: OpportunityMatrix | None,
    employer_id: str = "",
) -> str:
    """合成与 opportunities 一致的 direction 展示名。"""
    if matrix and matrix.uses_orthogonal_matrix():
        cap_map = {c.id: c for c in matrix.capability_axes}
        emp_map = {e.id: e for e in matrix.employer_axes}
        candidates = [
            c for c in matrix.ranked_cross_matrix()
            if c.capability_id == capability_id and not c.blocked
        ]
        if employer_id:
            preferred = [c for c in candidates if c.employer_id == employer_id]
            if preferred:
                candidates = preferred
        if candidates:
            cell = candidates[0]
            cap = cap_map.get(cell.capability_id)
            emp = emp_map.get(cell.employer_id)
            cap_name = cap.name if cap else capability_label(capability_id)
            emp_name = emp.name if emp else cell.employer_id
            return f"{cap_name}（{emp_name}）"

    return capability_label(capability_id)


def load_matrix_for_linking(data_dir: Path | None = None) -> OpportunityMatrix | None:
    """优先 opportunities.yaml，其次 draft。"""
    base = data_dir or _DATA_DIR
    for name in ("opportunities.yaml", "opportunities.draft.yaml"):
        path = base / name
        if path.is_file():
            return load_opportunities(path)
    return None


def resolve_linked_direction(
    blob: str,
    *,
    matrix: OpportunityMatrix | None = None,
    data_dir: Path | None = None,
) -> str:
    """从 JD/岗位文本推断关联机会矩阵方向。"""
    rules = load_jd_link_rules(data_dir)
    cap_id, hits = score_capability(blob, rules)
    if not cap_id or hits == 0:
        return ""
    employer_id = infer_employer_id(blob, rules)
    return format_direction(cap_id, matrix, employer_id)
