from pathlib import Path

from career_compass.registry import (
    capability_label,
    clear_registry_cache,
    jd_skill_vocab,
    load_capability_registry,
    load_method_patterns,
    load_skill_aliases,
)

REPO_DATA = Path(__file__).resolve().parent.parent / "data"


def test_load_skill_aliases_has_molecular_modeling():
    sa = load_skill_aliases(REPO_DATA)
    assert "分子建模" in sa.aliases
    assert "强化学习" in sa.aliases


def test_capability_label_from_registry():
    assert capability_label("semi_fab_or") == "半导体制造排程 / 厂内物流 OR"
    assert capability_label("unknown_id", "fallback") == "fallback"


def test_method_patterns_unknown_domain_anchor():
    mp = load_method_patterns(REPO_DATA)
    assert mp.unknown_domain_anchor == 0.35
    assert "or" in mp.patterns
    assert mp.affinity["domain_min"] == 0.5


def test_jd_skill_vocab_includes_aliases_and_extra():
    vocab = jd_skill_vocab(REPO_DATA)
    assert "python" in vocab or "Python" in vocab
    assert "Java" in vocab


def test_clear_registry_cache():
    clear_registry_cache()
    reg = load_capability_registry(REPO_DATA)
    assert len(reg.capabilities) >= 5
