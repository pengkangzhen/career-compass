"""SQLAlchemy declarative models for the SaaS layer.

M1: `User` table (managed by FastAPI Users via SQLAlchemyBaseUserTableUUID).
M3: Per-user career data tables (profile / constraints / narrative / saved_jobs
     / opportunity_matrices / matrix_feedback_actions / chat_messages / projects).

Design choice: large nested Pydantic models (Profile, Constraints, ProjectsFile,
OpportunityMatrix) are stored as JSONB rather than fully normalised. Only fields
that need real SQL queries / indexes (saved_jobs.status, matrix_feedback_actions
timestamp) are pulled out as columns. This trades minor write overhead for a
much smaller M3 surface area — the migration can stay localised to the data
layer without rewriting every Pydantic model.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON, BigInteger, Integer

# sqlite needs INTEGER PRIMARY KEY for autoincrement; BigInteger renders as
# BIGINT which silently loses autoincrement on sqlite. Use Integer on sqlite
# and BIGINT on Postgres.
BigIntAutoincrement = BigInteger().with_variant(Integer(), "sqlite")


class Base(DeclarativeBase):
    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "user"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# -----------------------------------------------------------------------
# M3 — per-user career data
# -----------------------------------------------------------------------


class Profile(Base):
    """A user's career profile (serialised Profile pydantic model)."""

    __tablename__ = "profile"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    content: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Constraints(Base):
    """A user's hard constraints."""

    __tablename__ = "constraints"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    content: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Narrative(Base):
    """A user's free-form narrative markdown."""

    __tablename__ = "narrative"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SavedJob(Base):
    """A saved job (JD watchlist). Columns that the SPA filters / groups on
    are pulled out; the rest stays in `extra` for forward-compat."""

    __tablename__ = "saved_job"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    company: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    location: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="手动添加")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="interested")
    linked_direction: Mapped[str] = mapped_column(Text, nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    saved_on: Mapped[datetime] = mapped_column(
        Date, server_default=func.current_date(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_saved_job_user_status", "user_id", "status"),
        Index("ix_saved_job_user_company_role", "user_id", "company", "role"),
    )


class OpportunityMatrix(Base):
    """The user's latest opportunity matrix (draft / published / revised).

    M3 keeps a single published row per user; `kind` is reserved for future
    draft/revised versions but indexed anyway to avoid a second migration.
    """

    __tablename__ = "opportunity_matrix"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="published")
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    generated_on: Mapped[datetime] = mapped_column(
        Date, server_default=func.current_date(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_opportunity_matrix_user_kind_date",
            "user_id",
            "kind",
            "generated_on",
        ),
    )


class MatrixFeedbackAction(Base):
    """Append-only log of user actions on the opportunity matrix UI."""

    __tablename__ = "matrix_feedback_action"

    id: Mapped[int] = mapped_column(BigIntAutoincrement, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(Text, nullable=False, default="")
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_matrix_feedback_user_ts", "user_id", "timestamp"),)


class ChatMessage(Base):
    """Intake conversation history. `session_id` groups a single conversation
    thread; chat_reset starts a new session_id without deleting history."""

    __tablename__ = "chat_message"

    id: Mapped[int] = mapped_column(BigIntAutoincrement, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(nullable=False, default=uuid.uuid4)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_chat_message_user_session_created", "user_id", "session_id", "created_at"),
    )


class ChatSessionState(Base):
    """Per-session metadata for intake (current stage, draft partial fields, etc).

    IntakeEngine keeps intermediate state in `intake_session.json`; we persist
    that as JSONB keyed by `(user_id, session_id)` so the engine can resume.
    """

    __tablename__ = "chat_session_state"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    state: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Projects(Base):
    """A user's harvested project evidence (scan-projects output)."""

    __tablename__ = "projects"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    content: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


__all__ = [
    "Base",
    "User",
    "Profile",
    "Constraints",
    "Narrative",
    "SavedJob",
    "OpportunityMatrix",
    "MatrixFeedbackAction",
    "ChatMessage",
    "ChatSessionState",
    "Projects",
]
