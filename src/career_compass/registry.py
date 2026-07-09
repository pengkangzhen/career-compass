"""数据驱动注册表 —— 技能别名、能力轴命名、方法论模式。

设计：Python 只保留加载与 fallback；扩展匹配能力 = 改 data/*.yaml，无需改代码。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

_DATA_DIR = Path.cwd() / "data"


class SkillAliasesFile(BaseModel):
    aliases: dict[str, list[str]] = Field(default_factory=dict)
    jd_vocab_extra: list[str] = Field(default_factory=list)

    def as_tuple_map(self) -> dict[str, tuple[str, ...]]:
        return {k: tuple(v) for k, v in self.aliases.items()}


class CapabilityRegistry(BaseModel):
    capabilities: dict[str, str] = Field(default_factory=dict)


class MethodPattern(BaseModel):
    markers: list[str] = Field(default_factory=list)
    domain_specific_skills: list[str] = Field(default_factory=list)


class MethodPatternsFile(BaseModel):
    patterns: dict[str, MethodPattern] = Field(default_factory=dict)
    affinity: dict[str, float] = Field(default_factory=lambda: {
        "domain_min": 0.5,
        "match_min": 0.55,
    })
    cross_track_scoring: dict[str, float] = Field(default_factory=lambda: {
        "method_weight": 0.65,
        "domain_weight": 0.35,
        "or_native_blend": 0.8,
    })
    unknown_domain_anchor: float = 0.35


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def load_skill_aliases(data_dir: Path | None = None) -> SkillAliasesFile:
    path = (data_dir or _DATA_DIR) / "skill_aliases.yaml"
    if not path.is_file():
        return SkillAliasesFile()
    return SkillAliasesFile.model_validate(_load_yaml(path))


@lru_cache(maxsize=1)
def load_capability_registry(data_dir: Path | None = None) -> CapabilityRegistry:
    path = (data_dir or _DATA_DIR) / "capability_registry.yaml"
    if not path.is_file():
        return CapabilityRegistry()
    return CapabilityRegistry.model_validate(_load_yaml(path))


@lru_cache(maxsize=1)
def load_method_patterns(data_dir: Path | None = None) -> MethodPatternsFile:
    path = (data_dir or _DATA_DIR) / "method_patterns.yaml"
    if not path.is_file():
        return MethodPatternsFile()
    return MethodPatternsFile.model_validate(_load_yaml(path))


def capability_label(capability_id: str, fallback_role: str = "") -> str:
    reg = load_capability_registry()
    return reg.capabilities.get(capability_id) or fallback_role or capability_id


def jd_skill_vocab(data_dir: Path | None = None) -> tuple[str, ...]:
    """JD 技能词表 = aliases keys + jd_vocab_extra。"""
    sa = load_skill_aliases(data_dir)
    keys = list(sa.aliases.keys())
    # 别名 canonical key 首字母大写变体 + extra
    vocab: list[str] = []
    for k in keys:
        vocab.append(k)
        if k.isascii() and k.islower():
            vocab.append(k.title())
    vocab.extend(sa.jd_vocab_extra)
    return tuple(dict.fromkeys(vocab))


def clear_registry_cache() -> None:
    """测试用：清缓存以便 reload yaml。"""
    load_skill_aliases.cache_clear()
    load_capability_registry.cache_clear()
    load_method_patterns.cache_clear()
