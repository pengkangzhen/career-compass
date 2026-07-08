"""Intake 对话会话持久化。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class ChatMessage:
    role: str  # "user" | "assistant"
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}

    @classmethod
    def from_dict(cls, data: dict) -> ChatMessage:
        return cls(role=str(data["role"]), content=str(data["content"]))


@dataclass
class IntakeSession:
    messages: list[ChatMessage] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "messages": [m.to_dict() for m in self.messages],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> IntakeSession:
        return cls(messages=[ChatMessage.from_dict(m) for m in data.get("messages", [])])


def session_path(data_dir: Path) -> Path:
    return data_dir / "intake_session.json"


def load_session(data_dir: Path) -> IntakeSession:
    path = session_path(data_dir)
    if not path.is_file():
        return IntakeSession()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return IntakeSession.from_dict(raw)
    except (json.JSONDecodeError, KeyError, TypeError):
        return IntakeSession()


def save_session(data_dir: Path, session: IntakeSession) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    session_path(data_dir).write_text(
        json.dumps(session.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def clear_session(data_dir: Path) -> None:
    path = session_path(data_dir)
    if path.is_file():
        path.unlink()
