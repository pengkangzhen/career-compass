from pathlib import Path

from career_compass.pipeline import Stage, detect_stage, run_validation


def test_run_validation_passes_examples(examples_dir: Path):
    errors, warnings = run_validation(examples_dir)
    assert not errors


def test_detect_stage_analyze_with_signals_only(examples_dir: Path):
    state = detect_stage(examples_dir)
    # 有 profile + 1 signal，无 opportunities.md → analyze
    assert state.stage in (Stage.analyze, Stage.scan)
    assert state.signal_count >= 1


def test_detect_stage_intake_missing_profile(tmp_path: Path):
    state = detect_stage(tmp_path)
    assert state.stage == Stage.intake
    assert state.validation_errors
