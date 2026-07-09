from pathlib import Path

from career_compass.journey import JourneyStep, build_journey_status, current_journey_step
from career_compass.journey import assess_journey_progress
from career_compass.pipeline import Stage, detect_stage


def test_journey_know_self_when_profile_missing(tmp_path: Path):
    status = build_journey_status(tmp_path)
    assert status.current == JourneyStep.know_self
    assert status.engine_stage == Stage.intake.value
    assert not status.progress.know_self_done


def test_journey_explore_after_valid_profile(examples_dir: Path):
    status = build_journey_status(examples_dir)
    assert status.progress.know_self_done
    assert status.current in (JourneyStep.explore, JourneyStep.decide, JourneyStep.act, JourneyStep.track)
    assert len(status.steps) == 5
    assert sum(1 for s in status.steps if s["current"]) == 1


def test_journey_steps_have_titles():
    status = build_journey_status(Path("/nonexistent"))
    titles = [s["title"] for s in status.steps]
    assert titles == ["认识自己", "探索世界", "做出决策", "开始行动", "持续追踪"]


def test_core_complete_rest_at_track(examples_dir: Path, tmp_path: Path):
    """机会矩阵渲染后 = 核心完成，当前步骤停留在持续追踪（不经 L3）。"""
    import shutil

    for name in ("profile.yaml", "constraints.yaml", "narrative.md", "opportunities.yaml"):
        shutil.copy(examples_dir / name, tmp_path / name)
    signals_dst = tmp_path / "signals"
    signals_dst.mkdir()
    shutil.copy(examples_dir / "signals" / "trends.yaml", signals_dst / "trends.yaml")
    from career_compass.render import render_opportunities

    (tmp_path / "opportunities.md").write_text(
        render_opportunities(tmp_path / "opportunities.yaml"), encoding="utf-8"
    )
    progress = assess_journey_progress(tmp_path)
    assert progress.core_done
    assert current_journey_step(progress) == JourneyStep.track
    status = build_journey_status(tmp_path)
    assert status.progress.decide_done
    assert status.current == JourneyStep.track
    assert status.current_title == "已完成"
    assert status.to_dict()["core_complete"]
    assert not any(s["current"] for s in status.steps)
    assert all(s["done"] for s in status.steps[:3])


def test_decide_without_explore_or_saved_jobs(examples_dir: Path, tmp_path: Path):
    """画像通过后可直接进入做出决策，无需信号或岗位收藏。"""
    import shutil

    for name in ("profile.yaml", "constraints.yaml", "narrative.md"):
        shutil.copy(examples_dir / name, tmp_path / name)

    progress = assess_journey_progress(tmp_path)
    assert progress.know_self_done
    assert not progress.explore_done
    assert current_journey_step(progress) == JourneyStep.decide

    status = build_journey_status(tmp_path)
    assert status.current == JourneyStep.decide
    assert status.engine_stage == "analyze"


def test_current_step_progression(tmp_path: Path):
    progress = assess_journey_progress(tmp_path)
    assert current_journey_step(progress) == JourneyStep.know_self

    state = detect_stage(tmp_path)
    assert state.stage == Stage.intake
