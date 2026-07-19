"""m3 per-user career data tables

Adds the file-based per-user data model to Postgres: profile, constraints,
narrative, saved_job, opportunity_matrix, matrix_feedback_action,
chat_message, chat_session_state, projects.

JSON columns use generic JSON (Postgres auto-promotes to JSONB; sqlite falls
back to TEXT). Large nested Pydantic models (Profile, Constraints,
OpportunityMatrix payload, Projects content) are stored as JSON; only fields
the SPA filters/groups on (saved_job.status, matrix_feedback_action.timestamp)
are first-class columns with indexes.

Revision ID: 0002_m3_user_data
Revises: 0001_create_user
Create Date: 2026-07-19
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from fastapi_users_db_sqlalchemy.generics import GUID

revision = "0002_m3_user_data"
down_revision = "0001_create_user"
branch_labels = None
depends_on = None


def _bigint_pk() -> sa.types.TypeEngine:
    """BigInteger that renders as INTEGER on sqlite (for autoincrement) and
    BIGINT on Postgres. Using Integer() universally would lose range on
    Postgres; using BigInteger() universally breaks autoincrement on sqlite.
    """
    return sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    # profile (one row per user)
    op.create_table(
        "profile",
        sa.Column("user_id", GUID(), sa.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("content", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # constraints (one row per user)
    op.create_table(
        "constraints",
        sa.Column("user_id", GUID(), sa.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("content", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # narrative (one row per user)
    op.create_table(
        "narrative",
        sa.Column("user_id", GUID(), sa.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # saved_job (many per user)
    op.create_table(
        "saved_job",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company", sa.String(length=256), nullable=False),
        sa.Column("role", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("location", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="手动添加"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="interested"),
        sa.Column("linked_direction", sa.Text(), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "saved_on",
            sa.Date(),
            server_default=sa.func.current_date(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_saved_job_user_status", "saved_job", ["user_id", "status"])
    op.create_index(
        "ix_saved_job_user_company_role",
        "saved_job",
        ["user_id", "company", "role"],
    )

    # opportunity_matrix (latest published per user; kind reserved for drafts)
    op.create_table(
        "opportunity_matrix",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="published"),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "generated_on",
            sa.Date(),
            server_default=sa.func.current_date(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_opportunity_matrix_user_kind_date",
        "opportunity_matrix",
        ["user_id", "kind", "generated_on"],
    )

    # matrix_feedback_action (append-only log)
    op.create_table(
        "matrix_feedback_action",
        sa.Column("id", _bigint_pk(), primary_key=True, autoincrement=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False, server_default=""),
        sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_matrix_feedback_user_ts",
        "matrix_feedback_action",
        ["user_id", "timestamp"],
    )

    # chat_message (intake conversation history)
    op.create_table(
        "chat_message",
        sa.Column("id", _bigint_pk(), primary_key=True, autoincrement=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", GUID(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_chat_message_user_session_created",
        "chat_message",
        ["user_id", "session_id", "created_at"],
    )

    # chat_session_state (intake engine intermediate state per session)
    op.create_table(
        "chat_session_state",
        sa.Column("user_id", GUID(), sa.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("session_id", GUID(), primary_key=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("state", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # projects (scan-projects harvested evidence)
    op.create_table(
        "projects",
        sa.Column("user_id", GUID(), sa.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("content", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("projects")
    op.drop_table("chat_session_state")
    op.drop_index("ix_chat_message_user_session_created", table_name="chat_message")
    op.drop_table("chat_message")
    op.drop_index("ix_matrix_feedback_user_ts", table_name="matrix_feedback_action")
    op.drop_table("matrix_feedback_action")
    op.drop_index(
        "ix_opportunity_matrix_user_kind_date", table_name="opportunity_matrix"
    )
    op.drop_table("opportunity_matrix")
    op.drop_index("ix_saved_job_user_company_role", table_name="saved_job")
    op.drop_index("ix_saved_job_user_status", table_name="saved_job")
    op.drop_table("saved_job")
    op.drop_table("narrative")
    op.drop_table("constraints")
    op.drop_table("profile")
