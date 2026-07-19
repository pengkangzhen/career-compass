#!/usr/bin/env python
"""Migrate a per-user file directory into the SaaS Postgres DB.

Usage:

    DATABASE_URL=postgresql+psycopg://user:pass@host/db \
    python scripts/migrate_files_to_db.py \\
        --user-id <uuid> \\
        --source data/users/<uuid>/

Idempotent: running twice on the same (user_id, source) upserts the same
data safely. Useful for: re-importing after schema changes, recovering
from a Render free-tier disk wipe, or seeding a dev DB from a local
single-user installation.

NOTE: By default the M3 deployment does NOT migrate existing data/users/
data — internal-test users start fresh. This script is a tool for one-off
imports after explicit operator action.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Make src/ importable when run as a standalone script.
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from career_compass.web.models import (  # noqa: E402
    Base,
    ChatMessage,
    ChatSessionState,
    Constraints,
    MatrixFeedbackAction,
    Narrative,
    OpportunityMatrix,
    Profile,
    Projects,
    SavedJob,
    User,
)
from career_compass.schema import (  # noqa: E402
    SavedJobStatus,
    load_matrix_feedback,
    load_saved_jobs,
)

log = logging.getLogger("migrate_files_to_db")


def _load_yaml(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError) as e:
        log.warning("could not parse %s: %s", path, e)
        return None


async def migrate(source: Path, user_id: uuid.UUID, database_url: str) -> dict:
    """Returns a summary of what was imported."""
    if not source.is_dir():
        raise SystemExit(f"source directory not found: {source}")

    engine = create_async_engine(database_url, future=True)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    summary: dict[str, int] = {}

    async with Session() as s:
        # Verify the user exists
        user = await s.get(User, user_id)
        if user is None:
            raise SystemExit(f"user_id {user_id} not found in DB")

        # profile.yaml
        profile_data = _load_yaml(source / "profile.yaml")
        if profile_data is not None:
            row = await s.get(Profile, user_id)
            if row is None:
                s.add(Profile(user_id=user_id, content=profile_data))
            else:
                row.content = profile_data
            summary["profile"] = 1
        else:
            summary["profile"] = 0

        # constraints.yaml
        c_data = _load_yaml(source / "constraints.yaml")
        if c_data is not None:
            row = await s.get(Constraints, user_id)
            if row is None:
                s.add(Constraints(user_id=user_id, content=c_data))
            else:
                row.content = c_data
            summary["constraints"] = 1
        else:
            summary["constraints"] = 0

        # narrative.md
        n_path = source / "narrative.md"
        if n_path.exists():
            text = n_path.read_text(encoding="utf-8")
            row = await s.get(Narrative, user_id)
            if row is None:
                s.add(Narrative(user_id=user_id, content=text))
            else:
                row.content = text
            summary["narrative"] = 1
        else:
            summary["narrative"] = 0

        # opportunities.yaml
        opp_data = _load_yaml(source / "opportunities.yaml")
        if opp_data is not None:
            from datetime import date as _date

            gen_on_str = opp_data.get("generated_on") or _date.today().isoformat()
            try:
                gen_on = _date.fromisoformat(str(gen_on_str)[:10])
            except ValueError:
                gen_on = _date.today()
            # Replace existing published row(s) for this user
            existing = await s.execute(
                select(OpportunityMatrix).where(
                    OpportunityMatrix.user_id == user_id,
                    OpportunityMatrix.kind == "published",
                )
            )
            for r in existing.scalars().all():
                await s.delete(r)
            s.add(
                OpportunityMatrix(
                    user_id=user_id,
                    kind="published",
                    payload=opp_data,
                    generated_on=gen_on,
                )
            )
            summary["opportunities"] = 1
        else:
            summary["opportunities"] = 0

        # saved_jobs.yaml → saved_job rows
        jobs_path = source / "saved_jobs.yaml"
        if jobs_path.exists():
            data = load_saved_jobs(jobs_path)
            # Replace existing
            existing = await s.execute(
                select(SavedJob).where(SavedJob.user_id == user_id)
            )
            for r in existing.scalars().all():
                await s.delete(r)
            count = 0
            for job in data.jobs:
                try:
                    job_uuid = uuid.UUID(str(job.id))
                except ValueError:
                    job_uuid = uuid.uuid4()
                s.add(
                    SavedJob(
                        id=job_uuid,
                        user_id=user_id,
                        company=job.company,
                        role=job.role,
                        description=job.description,
                        location=job.location,
                        source=job.source,
                        status=job.status.value
                        if isinstance(job.status, SavedJobStatus)
                        else str(job.status),
                        linked_direction=job.linked_direction,
                        notes=job.notes,
                        saved_on=job.saved_on,
                    )
                )
                count += 1
            summary["saved_jobs"] = count
        else:
            summary["saved_jobs"] = 0

        # matrix_feedback.yaml → matrix_feedback_action rows
        fb_path = source / "matrix_feedback.yaml"
        if fb_path.exists():
            data = load_matrix_feedback(fb_path)
            from datetime import datetime

            existing = await s.execute(
                select(MatrixFeedbackAction).where(
                    MatrixFeedbackAction.user_id == user_id
                )
            )
            for r in existing.scalars().all():
                await s.delete(r)
            count = 0
            for action in data.actions:
                try:
                    ts = datetime.fromisoformat(action.timestamp)
                except (ValueError, TypeError):
                    ts = datetime.utcnow()
                s.add(
                    MatrixFeedbackAction(
                        user_id=user_id,
                        action=action.action,
                        direction=action.direction,
                        details=dict(action.details or {}),
                        timestamp=ts,
                    )
                )
                count += 1
            summary["matrix_feedback_actions"] = count
        else:
            summary["matrix_feedback_actions"] = 0

        # projects.yaml
        pr_data = _load_yaml(source / "projects.yaml")
        if pr_data is not None:
            row = await s.get(Projects, user_id)
            if row is None:
                s.add(Projects(user_id=user_id, content=pr_data))
            else:
                row.content = pr_data
            summary["projects"] = 1
        else:
            summary["projects"] = 0

        # intake_session.json → chat_session_state + chat_message rows
        sess_path = source / "intake_session.json"
        if sess_path.exists():
            try:
                state = json.loads(sess_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                log.warning("could not parse intake_session.json: %s", e)
                state = None
            if state is not None:
                # Replace existing active session
                existing = await s.execute(
                    select(ChatSessionState).where(
                        ChatSessionState.user_id == user_id,
                        ChatSessionState.active.is_(True),
                    )
                )
                session_id = uuid.uuid4()
                for r in existing.scalars().all():
                    r.active = False
                s.add(
                    ChatSessionState(
                        user_id=user_id,
                        session_id=session_id,
                        active=True,
                        state=state,
                    )
                )
                # Sync messages
                msgs = (
                    state.get("messages") if isinstance(state, dict) else None
                )
                msg_count = 0
                if isinstance(msgs, list):
                    for msg in msgs:
                        if not isinstance(msg, dict):
                            continue
                        role = str(msg.get("role") or msg.get("sender") or "user")
                        content = str(msg.get("content") or msg.get("text") or "")
                        if not content:
                            continue
                        s.add(
                            ChatMessage(
                                user_id=user_id,
                                session_id=session_id,
                                role=role[:16],
                                content=content,
                            )
                        )
                        msg_count += 1
                summary["chat_messages"] = msg_count

        await s.commit()

    await engine.dispose()
    return summary


def main() -> None:
    import os

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", required=True, help="existing user UUID")
    parser.add_argument(
        "--source",
        required=True,
        help="path to the user's file-based data directory",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="async SQLAlchemy URL (defaults to $DATABASE_URL)",
    )
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("DATABASE_URL env var or --database-url is required")

    try:
        user_id = uuid.UUID(args.user_id)
    except ValueError:
        raise SystemExit(f"--user-id must be a valid UUID, got: {args.user_id!r}")

    source = Path(args.source).resolve()
    summary = asyncio.run(migrate(source, user_id, args.database_url))

    log.info("=== migration summary (user %s) ===", user_id)
    for k, v in summary.items():
        log.info("  %-26s %d", k, v)


if __name__ == "__main__":
    main()
