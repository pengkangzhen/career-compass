from pathlib import Path

from career_compass.gather import add_signal, scan_plan, stale_signals
from career_compass.schema import Constraints, load_profile, load_sectors


def test_scan_plan_includes_sectors(examples_dir: Path):
    profile = load_profile(examples_dir / "profile.yaml")
    constraints = Constraints.model_validate({"geo": ["上海"], "financial_runway_months": 6})
    sectors = examples_dir.parent / "sectors.yaml"
    queries = scan_plan(profile, sectors_path=sectors, constraints=constraints)
    assert any("上海" in q or "tech" in q.lower() for q in queries)
    if sectors.exists():
        sectors_list = load_sectors(sectors)
        if sectors_list:
            assert any(sectors_list[0].name.split("/")[0][:2] in q for q in queries)


def test_scan_plan_from_profile(examples_dir: Path):
    profile = load_profile(examples_dir / "profile.yaml")
    queries = scan_plan(profile)
    assert len(queries) >= 1
    assert "LLM" in queries[0] or "RAG" in queries[0] or "Spark" in queries[0]


def test_add_signal_deduplicates_by_topic(tmp_path: Path):
    signals_dir = tmp_path / "signals"
    add_signal(signals_dir, "trends", "Topic A", "finding v1", "src", retrieved_on=__import__("datetime").date(2026, 1, 1))
    add_signal(signals_dir, "trends", "Topic A", "finding v2", "src2", retrieved_on=__import__("datetime").date(2026, 1, 2))
    raw = (signals_dir / "trends.yaml").read_text(encoding="utf-8")
    assert raw.count("Topic A") == 1
    assert "finding v2" in raw


def test_stale_signals(tmp_path: Path):
    from datetime import date, timedelta

    signals_dir = tmp_path / "signals"
    old = date.today() - timedelta(days=100)
    add_signal(signals_dir, "market", "old topic", "x", "s", retrieved_on=old)
    stale = stale_signals(signals_dir, max_age_days=90)
    assert len(stale) == 1
