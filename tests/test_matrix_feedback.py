"""Tests for matrix_feedback logging (remove / reorder / reset / note)."""
from pathlib import Path

import pytest

from career_compass.matrix_feedback import (
    append_action,
    hidden_directions,
    list_actions,
    notes_by_direction,
    order_overrides,
    reset,
)
from career_compass.schema import MatrixFeedbackFile, load_matrix_feedback


def test_append_remove_round_trip(tmp_path: Path):
    path = tmp_path / "matrix_feedback.yaml"
    assert not path.exists()
    assert list_actions(path) == []

    entry = append_action(path, action="remove", direction="定价 / 收益管理科学家")
    assert entry.action == "remove"
    assert entry.direction == "定价 / 收益管理科学家"
    assert entry.timestamp  # auto-filled ISO string

    actions = list_actions(path)
    assert len(actions) == 1
    assert actions[0].direction == "定价 / 收益管理科学家"

    reloaded = load_matrix_feedback(path)
    assert isinstance(reloaded, MatrixFeedbackFile)
    assert reloaded.actions[0].action == "remove"


def test_append_reorder_with_details(tmp_path: Path):
    path = tmp_path / "matrix_feedback.yaml"
    append_action(path, action="reorder", direction="A", details={"from_rank": 2, "to_rank": 0})
    append_action(path, action="reorder", direction="B", details={"from_rank": 1, "to_rank": 0})
    actions = list_actions(path)
    assert len(actions) == 2
    assert actions[1].details["to_rank"] == 0


def test_reset_clears_history_and_keeps_marker(tmp_path: Path):
    path = tmp_path / "matrix_feedback.yaml"
    append_action(path, action="remove", direction="X")
    append_action(path, action="reorder", direction="Y", details={"from_rank": 1, "to_rank": 0})
    assert len(list_actions(path)) == 2

    reset(path)
    actions = list_actions(path)
    assert len(actions) == 1
    assert actions[0].action == "reset"


def test_invalid_action_rejected(tmp_path: Path):
    path = tmp_path / "matrix_feedback.yaml"
    with pytest.raises(ValueError):
        append_action(path, action="bogus", direction="X")


def test_missing_direction_rejected(tmp_path: Path):
    path = tmp_path / "matrix_feedback.yaml"
    with pytest.raises(ValueError):
        append_action(path, action="remove")  # no direction


def test_hidden_directions_resets_after_reset(tmp_path: Path):
    path = tmp_path / "matrix_feedback.yaml"
    append_action(path, action="remove", direction="A")
    append_action(path, action="remove", direction="B")
    actions = list_actions(path)
    assert hidden_directions(actions) == ["A", "B"]

    reset(path)
    actions = list_actions(path)
    assert hidden_directions(actions) == []


def test_order_overrides_is_stable(tmp_path: Path):
    path = tmp_path / "matrix_feedback.yaml"
    # Move C to position 0 (working list: [A, B, C] → insert C then move)
    append_action(path, action="reorder", direction="A", details={"from_rank": 0, "to_rank": 0})
    append_action(path, action="reorder", direction="B", details={"from_rank": 1, "to_rank": 1})
    append_action(path, action="reorder", direction="C", details={"from_rank": 2, "to_rank": 0})
    # Engine order was [A, B, C]; user moved C to top → [C, A, B]
    assert order_overrides(list_actions(path)) == ["C", "A", "B"]


def test_atomic_write_via_tmp(tmp_path: Path):
    path = tmp_path / "matrix_feedback.yaml"
    append_action(path, action="remove", direction="X")
    # After write, no .tmp file should remain (rename replaced it)
    assert not path.with_suffix(path.suffix + ".tmp").exists()
    assert path.exists()


def test_append_note_round_trip(tmp_path: Path):
    path = tmp_path / "matrix_feedback.yaml"
    entry = append_action(
        path,
        action="note",
        direction="定价 / 收益管理科学家（民企 / 互联网 / 独角兽）",
        details={"text": "美团、滴滴等大厂已经饱和"},
    )
    assert entry.action == "note"
    assert entry.details["text"] == "美团、滴滴等大厂已经饱和"

    reloaded = load_matrix_feedback(path)
    assert isinstance(reloaded, MatrixFeedbackFile)
    assert reloaded.actions[0].action == "note"
    assert reloaded.actions[0].details["text"] == "美团、滴滴等大厂已经饱和"


def test_note_requires_non_empty_text(tmp_path: Path):
    path = tmp_path / "matrix_feedback.yaml"
    with pytest.raises(ValueError):
        append_action(path, action="note", direction="X", details={"text": ""})
    with pytest.raises(ValueError):
        append_action(path, action="note", direction="X", details={})
    with pytest.raises(ValueError):
        append_action(path, action="note", direction="X", details={"text": "   "})
    # nothing should have been written
    assert not path.exists()


def test_notes_by_direction_latest_wins_and_reset_clears(tmp_path: Path):
    path = tmp_path / "matrix_feedback.yaml"
    append_action(
        path,
        action="note",
        direction="定价 / 收益管理科学家",
        details={"text": "first"},
    )
    append_action(
        path,
        action="note",
        direction="供应链 / 物流优化",
        details={"text": "supply chain note"},
    )
    append_action(
        path,
        action="note",
        direction="定价 / 收益管理科学家",
        details={"text": "second (overrides)"},
    )

    notes = notes_by_direction(list_actions(path))
    assert notes == {
        "定价 / 收益管理科学家": "second (overrides)",
        "供应链 / 物流优化": "supply chain note",
    }

    # After reset, all notes are cleared (reset is a terminal marker)
    reset(path)
    notes = notes_by_direction(list_actions(path))
    assert notes == {}

    # Notes after the reset count from scratch
    append_action(
        path,
        action="note",
        direction="定价 / 收益管理科学家",
        details={"text": "post-reset"},
    )
    notes = notes_by_direction(list_actions(path))
    assert notes == {"定价 / 收益管理科学家": "post-reset"}


def test_notes_coexist_with_remove_and_reorder(tmp_path: Path):
    path = tmp_path / "matrix_feedback.yaml"
    append_action(path, action="remove", direction="A")
    append_action(path, action="note", direction="B", details={"text": "on B"})
    append_action(path, action="reorder", direction="C", details={"from_rank": 0, "to_rank": 1})
    append_action(path, action="note", direction="A", details={"text": "even though removed"})

    actions = list_actions(path)
    # All four actions are preserved in the append-only log
    assert [a.action for a in actions] == ["remove", "note", "reorder", "note"]
    # Derived views are independent
    assert hidden_directions(actions) == ["A"]
    assert order_overrides(actions) == ["C"]
    assert notes_by_direction(actions) == {"B": "on B", "A": "even though removed"}
