"""Tests for saved jobs watchlist."""
from pathlib import Path

from career_compass.jobs import add_saved_job, analyze_saved_job, list_saved_jobs
from career_compass.schema import load_profile

REPO_DATA = Path(__file__).resolve().parent.parent / "data"


def test_job_add_and_analyze(tmp_path: Path, examples_dir: Path):
    jobs_path = tmp_path / "saved_jobs.yaml"
    jd = "Python Gurobi 整数规划 LangGraph LLM Agent 运筹优化"
    job = add_saved_job(jobs_path, "测试公司", "OR工程师", jd)
    assert job.id
    assert len(list_saved_jobs(jobs_path)) == 1

    profile = load_profile(examples_dir / "profile.yaml")
    report = analyze_saved_job(job, profile, data_dir=REPO_DATA)
    assert report.coverage_rate >= 0
    assert report.company == "测试公司"
    assert report.linked_direction
    assert "Agent" in job.description or "决策" in report.linked_direction or "OR" in report.linked_direction
