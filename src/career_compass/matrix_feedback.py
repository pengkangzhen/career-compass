"""矩阵反馈记录 —— 用户在 UI 上 remove / reorder / reset / note 矩阵方向的操作日志。

独立于 `data/opportunities.yaml`（引擎产物），写入 `data/matrix_feedback.yaml`。
未来 LLM Agent 在 replan / re-analyze 时应读取本文件，把 remove 视为 user_dislikes
信号、reorder-to-top 视为 user_prefers 信号、note 视为定性观察信号。
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from .schema import (
    MatrixFeedbackAction,
    MatrixFeedbackFile,
    load_matrix_feedback,
    save_matrix_feedback,
)

VALID_ACTIONS: tuple[str, ...] = ("remove", "reorder", "reset", "note")


def _now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def append_action(
    path: Path,
    *,
    action: str,
    direction: str = "",
    details: dict | None = None,
    timestamp: str | None = None,
) -> MatrixFeedbackAction:
    """校验并追加一条反馈。reset 会清空历史，只保留这一条 reset 标记。"""
    if action not in VALID_ACTIONS:
        raise ValueError(f"unknown feedback action: {action!r} (expected {VALID_ACTIONS})")
    if action != "reset" and not direction:
        raise ValueError(f"direction required for action={action!r}")

    details = details or {}
    if action == "note":
        text = details.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("note action requires non-empty details.text")
        details = {"text": text.strip()}

    entry = MatrixFeedbackAction(
        action=action,
        direction=direction,
        timestamp=timestamp or _now_iso(),
        details=details,
    )

    if action == "reset":
        save_matrix_feedback(
            path,
            MatrixFeedbackFile(updated_on=date.today(), actions=[entry]),
        )
        return entry

    data = load_matrix_feedback(path)
    data.actions.append(entry)
    data.updated_on = date.today()
    save_matrix_feedback(path, data)
    return entry


def list_actions(path: Path) -> list[MatrixFeedbackAction]:
    return load_matrix_feedback(path).actions


def reset(path: Path) -> None:
    """清空全部历史（写入一条 reset 标记作为终结事件）。"""
    append_action(path, action="reset")


def hidden_directions(actions: Iterable[MatrixFeedbackAction]) -> list[str]:
    """根据最新 reset 之后的 remove 事件，返回应隐藏的 direction 列表。"""
    out: list[str] = []
    for a in actions:
        if a.action == "reset":
            out = []
        elif a.action == "remove":
            if a.direction and a.direction not in out:
                out.append(a.direction)
    return out


def order_overrides(actions: Iterable[MatrixFeedbackAction]) -> list[str]:
    """返回用户拖拽后的 direction 顺序（最新 reset 之后所有 reorder 累计后的稳定顺序）。

    规则：
    - 遇到 reset 清空
    - 遇到 reorder(from_rank, to_rank)：先把 direction 放进列表末尾（若不存在），
      然后按 from/to 在当前 working list 上执行 move
    - 多次 reorder 累计；最终列表就是用户期望的展示顺序
    """
    working: list[str] = []
    for a in actions:
        if a.action == "reset":
            working = []
            continue
        if a.action != "reorder":
            continue
        d = a.direction
        if not d:
            continue
        if d not in working:
            working.append(d)
        try:
            frm = int(a.details.get("from_rank"))
            to = int(a.details.get("to_rank"))
        except (TypeError, ValueError):
            continue
        if frm == to:
            continue
        if not (0 <= frm < len(working)) or not (0 <= to < len(working)):
            continue
        item = working.pop(frm)
        working.insert(to, item)
    return working


def notes_by_direction(actions: Iterable[MatrixFeedbackAction]) -> dict[str, str]:
    """每个 direction 的最新 note 文本（最新一条 note 覆盖旧的；reset 清空）。

    append-only 日志里同方向可能有多个 note，UI 只展示最新；完整历史保留在 YAML 里
    供 LLM Agent 当定性信号消费。
    """
    out: dict[str, str] = {}
    for a in actions:
        if a.action == "reset":
            out = {}
            continue
        if a.action != "note":
            continue
        text = a.details.get("text")
        if isinstance(text, str) and text.strip() and a.direction:
            out[a.direction] = text.strip()
    return out
