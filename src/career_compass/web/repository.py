"""Per-user data repository backed by Postgres (M3).

Strategy: keep every existing file-based view builder / engine / pipeline
function unchanged (they all accept `data_dir: Path`). The Repository:

1. Exports the user's DB state into a temporary per-request directory at the
   start of each mutating call.
2. Delegates to the legacy file-based logic (IntakeEngine, build_all_views,
   matrix_feedback, jobs) which write into the same directory.
3. Reads the directory back and upserts changed files into the DB.

This trades one extra disk round-trip per request for a massive surface area
reduction — M3 ships without rewriting IntakeEngine / pipeline / render.
A future M4 may swap specific hot paths (e.g. load_all) to pure DB reads.

Concurrency: each request gets its own tmpdir keyed by user_id + uuid4, so
two concurrent requests for the same user do not stomp on each other's
files. Last-writer-wins on DB upsert; the SPA serialises writes per tab.
"""
from __future__ import annotations

import json
import logging
import shutil
import tempfile
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, AsyncIterator
from uuid import UUID

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from career_compass.gui.app import _templates_dir, _run_cli
from career_compass.gui.view_data import build_all_views
from career_compass.intake import IntakeEngine, get_llm_config
from career_compass.intake.preview import build_intake_status
from career_compass.journey import build_journey_status
from career_compass.pipeline import detect_stage
from career_compass.schema import (
    Constraints as ConstraintsModel,
    MatrixFeedbackAction,
    MatrixFeedbackFile,
    OpportunityMatrix,
    Profile as ProfileModel,
    ProjectsFile,
    SavedJob,
    SavedJobStatus,
    SavedJobsFile,
    load_constraints,
    load_matrix_feedback,
    load_opportunities,
    load_profile,
    load_saved_jobs,
    save_matrix_feedback,
    save_opportunities,
    save_saved_jobs,
)

from .models import (
    ChatMessage,
    ChatSessionState,
    Constraints,
    MatrixFeedbackAction as MatrixFeedbackActionModel,
    Narrative,
    OpportunityMatrix as OpportunityMatrixModel,
    Profile,
    Projects,
    SavedJob as SavedJobModel,
)

log = logging.getLogger(__name__)


# Files the repository round-trips between DB and tmpdir.
# Anything else in the tmpdir (signals/, sectors.yaml, shared knowledge) is
# read-only and sourced from the repo's `data/` or `templates/` directories.
_PROFILE_FILES = ("profile.yaml", "constraints.yaml", "narrative.md")
_MATRIX_FILES = ("opportunities.yaml", "opportunities.md")
_FEEDBACK_FILE = "matrix_feedback.yaml"
_JOBS_FILE = "saved_jobs.yaml"
_PROJECTS_FILE = "projects.yaml"
_SESSION_FILE = "intake_session.json"


class Repository:
    """DB-backed per-user career data access.

    All public methods are async; file I/O is done in-thread but kept short
    (single tmpdir per request, ~few KB of YAML).
    """

    def __init__(self, session: AsyncSession, user_id: UUID) -> None:
        self.session = session
        self.user_id = user_id

    # ------------------------------------------------------------------
    # tmpdir round-trip
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def with_tmpdir(self) -> AsyncIterator[Path]:
        """Yield a tmpdir populated with the user's DB state; sync on exit.

        On exit, any files written/modified in the tmpdir are upserted back
        into the DB. Files that weren't touched are skipped.
        """
        tmpdir = Path(tempfile.mkdtemp(prefix=f"cc-{self.user_id}-"))
        try:
            await self._export_into(tmpdir)
            mtime_before = {p: p.stat().st_mtime_ns for p in tmpdir.rglob("*") if p.is_file()}
            yield tmpdir
            mtime_after = {p: p.stat().st_mtime_ns for p in tmpdir.rglob("*") if p.is_file()}
            changed = {p for p, t in mtime_after.items() if mtime_before.get(p, 0) != t}
            # New files created during the request (not in mtime_before).
            changed |= set(mtime_after) - set(mtime_before)
            if changed:
                await self._import_from(tmpdir, changed)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    async def _export_into(self, target: Path) -> None:
        """Write the user's DB state into target/ as YAML/MD files."""
        target.mkdir(parents=True, exist_ok=True)

        # profile.yaml
        p_row = await self.session.get(Profile, self.user_id)
        if p_row and p_row.content:
            (target / "profile.yaml").write_text(
                yaml.safe_dump(p_row.content, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

        # constraints.yaml
        c_row = await self.session.get(Constraints, self.user_id)
        if c_row and c_row.content:
            (target / "constraints.yaml").write_text(
                yaml.safe_dump(c_row.content, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

        # narrative.md
        n_row = await self.session.get(Narrative, self.user_id)
        if n_row and n_row.content:
            (target / "narrative.md").write_text(n_row.content, encoding="utf-8")

        # opportunities.yaml / .md
        result = await self.session.execute(
            select(OpportunityMatrixModel)
            .where(OpportunityMatrixModel.user_id == self.user_id)
            .order_by(OpportunityMatrixModel.generated_on.desc())
            .limit(1)
        )
        om_row = result.scalars().first()
        if om_row and om_row.payload:
            (target / "opportunities.yaml").write_text(
                yaml.safe_dump(om_row.payload, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

        # saved_jobs.yaml (aggregate)
        jobs_result = await self.session.execute(
            select(SavedJobModel)
            .where(SavedJobModel.user_id == self.user_id)
            .order_by(SavedJobModel.saved_on.desc(), SavedJobModel.created_at.desc())
        )
        jobs = jobs_result.scalars().all()
        if jobs:
            payload = {
                "updated_on": max(j.saved_on for j in jobs),
                "jobs": [_saved_job_to_dict(j) for j in jobs],
            }
            (target / "saved_jobs.yaml").write_text(
                yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

        # matrix_feedback.yaml
        fb_result = await self.session.execute(
            select(MatrixFeedbackActionModel)
            .where(MatrixFeedbackActionModel.user_id == self.user_id)
            .order_by(MatrixFeedbackActionModel.timestamp.asc(), MatrixFeedbackActionModel.id.asc())
        )
        actions = fb_result.scalars().all()
        if actions:
            payload = {
                "updated_on": actions[-1].timestamp.date() if actions else date.today(),
                "actions": [_feedback_action_to_dict(a) for a in actions],
            }
            (target / _FEEDBACK_FILE).write_text(
                yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

        # projects.yaml
        pr_row = await self.session.get(Projects, self.user_id)
        if pr_row and pr_row.content:
            (target / "projects.yaml").write_text(
                yaml.safe_dump(pr_row.content, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

        # intake_session.json — reconstruct from chat_message + chat_session_state
        await self._export_chat_session(target)

    async def _export_chat_session(self, target: Path) -> None:
        """Reconstruct intake_session.json from chat_message + chat_session_state.

        IntakeEngine stores its full state (messages, draft profile, stage, etc.)
        as JSON. We persist that blob verbatim in `chat_session_state.state`,
        keyed by session_id; messages are also normalised into `chat_message`
        for future query-ability but the JSON blob is the authoritative
        IntakeEngine input.
        """
        # Find the active session for this user
        state_result = await self.session.execute(
            select(ChatSessionState)
            .where(
                ChatSessionState.user_id == self.user_id,
                ChatSessionState.active.is_(True),
            )
            .order_by(ChatSessionState.updated_at.desc())
            .limit(1)
        )
        state_row = state_result.scalars().first()
        if state_row and state_row.state:
            (target / _SESSION_FILE).write_text(
                json.dumps(state_row.state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    async def _import_from(self, tmpdir: Path, changed: set[Path]) -> None:
        """Upsert changed files back into DB."""
        names = {p.name for p in changed}

        if "profile.yaml" in names and (tmpdir / "profile.yaml").exists():
            content = _safe_yaml_load(tmpdir / "profile.yaml")
            if content is not None:
                await self._upsert_single(Profile, {"content": content})

        if "constraints.yaml" in names and (tmpdir / "constraints.yaml").exists():
            content = _safe_yaml_load(tmpdir / "constraints.yaml")
            if content is not None:
                await self._upsert_single(Constraints, {"content": content})

        if "narrative.md" in names and (tmpdir / "narrative.md").exists():
            text = (tmpdir / "narrative.md").read_text(encoding="utf-8")
            await self._upsert_single(Narrative, {"content": text})

        if "opportunities.yaml" in names and (tmpdir / "opportunities.yaml").exists():
            payload = _safe_yaml_load(tmpdir / "opportunities.yaml")
            if payload is not None:
                await self._upsert_opportunity_matrix(payload)

        if "saved_jobs.yaml" in names and (tmpdir / "saved_jobs.yaml").exists():
            await self._sync_saved_jobs(tmpdir / "saved_jobs.yaml")

        if _FEEDBACK_FILE in names and (tmpdir / _FEEDBACK_FILE).exists():
            await self._sync_matrix_feedback(tmpdir / _FEEDBACK_FILE)

        if "projects.yaml" in names and (tmpdir / "projects.yaml").exists():
            content = _safe_yaml_load(tmpdir / "projects.yaml")
            if content is not None:
                await self._upsert_single(Projects, {"content": content})

        if _SESSION_FILE in names and (tmpdir / _SESSION_FILE).exists():
            await self._upsert_chat_session(tmpdir / _SESSION_FILE)

        await self.session.commit()

    async def _upsert_single(self, model_cls, values: dict[str, Any]) -> None:
        row = await self.session.get(model_cls, self.user_id)
        if row is None:
            row = model_cls(user_id=self.user_id, **values)
            self.session.add(row)
        else:
            for k, v in values.items():
                setattr(row, k, v)

    async def _upsert_opportunity_matrix(self, payload: dict) -> None:
        # Keep only the latest published row per user (M3 simplification).
        result = await self.session.execute(
            select(OpportunityMatrixModel)
            .where(
                OpportunityMatrixModel.user_id == self.user_id,
                OpportunityMatrixModel.kind == "published",
            )
            .order_by(OpportunityMatrixModel.generated_on.desc())
            .limit(1)
        )
        row = result.scalars().first()
        generated_on_str = payload.get("generated_on") or date.today().isoformat()
        try:
            generated_on = date.fromisoformat(str(generated_on_str)[:10])
        except ValueError:
            generated_on = date.today()
        if row is None:
            row = OpportunityMatrixModel(
                user_id=self.user_id,
                kind="published",
                payload=payload,
                generated_on=generated_on,
            )
            self.session.add(row)
        else:
            row.payload = payload
            row.generated_on = generated_on

    async def _sync_saved_jobs(self, path: Path) -> None:
        if not path.exists():
            return
        data = load_saved_jobs(path)
        # Pull all existing rows for this user into a dict by id.
        result = await self.session.execute(
            select(SavedJobModel).where(SavedJobModel.user_id == self.user_id)
        )
        existing = {str(j.id): j for j in result.scalars().all()}
        seen: set[str] = set()
        for job in data.jobs:
            seen.add(job.id)
            row = existing.get(job.id)
            saved_on = job.saved_on
            if row is None:
                self.session.add(
                    _saved_job_from_model(job, self.user_id)
                )
            else:
                _saved_job_update(row, job)
        # Delete rows that were removed from the file.
        for jid, row in existing.items():
            if jid not in seen:
                await self.session.delete(row)

    async def _sync_matrix_feedback(self, path: Path) -> None:
        if not path.exists():
            return
        data = load_matrix_feedback(path)
        # Wipe + rewrite — append-only log, ordering matters.
        result = await self.session.execute(
            select(MatrixFeedbackActionModel).where(
                MatrixFeedbackActionModel.user_id == self.user_id
            )
        )
        for r in result.scalars().all():
            await self.session.delete(r)
        for action in data.actions:
            try:
                ts = datetime.fromisoformat(action.timestamp)
            except (ValueError, TypeError):
                ts = datetime.utcnow()
            self.session.add(
                MatrixFeedbackActionModel(
                    user_id=self.user_id,
                    action=action.action,
                    direction=action.direction,
                    details=dict(action.details or {}),
                    timestamp=ts,
                )
            )

    async def _upsert_chat_session(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        # Find or create active session for user.
        result = await self.session.execute(
            select(ChatSessionState)
            .where(
                ChatSessionState.user_id == self.user_id,
                ChatSessionState.active.is_(True),
            )
            .order_by(ChatSessionState.updated_at.desc())
            .limit(1)
        )
        row = result.scalars().first()
        if row is None:
            row = ChatSessionState(
                user_id=self.user_id,
                session_id=uuid.uuid4(),
                active=True,
                state=state,
            )
            self.session.add(row)
        else:
            row.state = state

        # Sync messages (cheap; replace all).
        msgs_result = await self.session.execute(
            select(ChatMessage).where(ChatMessage.user_id == self.user_id)
        )
        for m in msgs_result.scalars().all():
            await self.session.delete(m)
        messages = state.get("messages") if isinstance(state, dict) else None
        if isinstance(messages, list):
            for msg in messages:
                if not isinstance(msg, dict):
                    continue
                role = str(msg.get("role") or msg.get("sender") or "user")
                content = str(msg.get("content") or msg.get("text") or "")
                if not content:
                    continue
                self.session.add(
                    ChatMessage(
                        user_id=self.user_id,
                        session_id=row.session_id,
                        role=role[:16],
                        content=content,
                    )
                )

    # ------------------------------------------------------------------
    # Public API (mirrors career_compass.gui.app.AppApi method names so the
    # router can swap `_api_for(user)` for `_repo_for(user, session)` with
    # minimal change).
    # ------------------------------------------------------------------

    async def load_all(self) -> dict[str, Any]:
        """Aggregate every view + journey + intake status into one payload."""
        async with self.with_tmpdir() as tmpdir:
            status = build_intake_status(tmpdir)
            journey = build_journey_status(tmpdir)
            views = build_all_views(tmpdir)
            return {
                "data_dir": str(tmpdir),
                "intake_complete": status["intake_complete"],
                "journey": journey.to_dict(),
                "views": views,
                "spa": True,
                # legacy HTML fields — SPA doesn't use them; keep for back-compat
                "profile_html": "",
                "trends_html": "",
                "jobs_html": "",
                "matrix_html": "",
            }

    async def chat_state(self) -> dict[str, Any]:
        async with self.with_tmpdir() as tmpdir:
            cfg = get_llm_config()
            engine = IntakeEngine(tmpdir, templates_dir=_templates_dir())
            status = build_intake_status(tmpdir)
            pipeline = detect_stage(tmpdir)
            journey = build_journey_status(tmpdir)
            return {
                "messages": engine.get_messages(),
                "llm": {
                    "provider": cfg.provider,
                    "model": cfg.model,
                    "configured": cfg.configured,
                },
                "stage": pipeline.stage.value,
                "journey": journey.to_dict(),
                **status,
            }

    async def chat_send(self, message: str) -> dict[str, Any]:
        async with self.with_tmpdir() as tmpdir:
            engine = IntakeEngine(tmpdir, templates_dir=_templates_dir())
            result = engine.chat(message)
            status = build_intake_status(tmpdir)
            journey = build_journey_status(tmpdir)
            return {
                "reply": result.reply,
                "ok": result.ok,
                "messages": engine.get_messages(),
                "files_updated": result.files_updated,
                "just_completed": result.just_completed,
                "llm": {
                    "provider": result.llm_provider,
                    "model": result.llm_model,
                    "configured": get_llm_config().configured,
                },
                "journey": journey.to_dict(),
                **status,
            }

    async def chat_reset(self) -> dict[str, Any]:
        async with self.with_tmpdir() as tmpdir:
            engine = IntakeEngine(tmpdir, templates_dir=_templates_dir())
            engine.reset()
            return {"ok": True}

    async def matrix_feedback(self) -> dict[str, Any]:
        result = await self.session.execute(
            select(MatrixFeedbackActionModel)
            .where(MatrixFeedbackActionModel.user_id == self.user_id)
            .order_by(
                MatrixFeedbackActionModel.timestamp.asc(),
                MatrixFeedbackActionModel.id.asc(),
            )
        )
        actions = result.scalars().all()
        return {
            "actions": [
                {
                    "action": a.action,
                    "direction": a.direction,
                    "details": dict(a.details or {}),
                    "timestamp": a.timestamp.isoformat() if a.timestamp else "",
                }
                for a in actions
            ]
        }

    async def matrix_feedback_add(
        self,
        action: str,
        direction: str = "",
        details: dict | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        # Validate via the schema model (raises ValueError on bad input).
        entry = MatrixFeedbackAction(
            action=action,
            direction=direction,
            timestamp=timestamp or datetime.utcnow().replace(microsecond=0).isoformat(),
            details=details or {},
        )
        # schema validation for `note`/`reset`
        if action not in ("remove", "reorder", "reset", "note"):
            return {"ok": False, "error": f"unknown feedback action: {action!r}"}
        if action != "reset" and not direction:
            return {"ok": False, "error": f"direction required for action={action!r}"}

        try:
            ts = datetime.fromisoformat(entry.timestamp)
        except ValueError:
            ts = datetime.utcnow()
        row = MatrixFeedbackActionModel(
            user_id=self.user_id,
            action=action,
            direction=direction,
            details=details or {},
            timestamp=ts,
        )
        # On reset, wipe prior actions for this user (matches file-based semantics).
        if action == "reset":
            existing = await self.session.execute(
                select(MatrixFeedbackActionModel).where(
                    MatrixFeedbackActionModel.user_id == self.user_id
                )
            )
            for r in existing.scalars().all():
                await self.session.delete(r)

        self.session.add(row)
        await self.session.commit()
        return {
            "ok": True,
            "action": {
                "action": row.action,
                "direction": row.direction,
                "details": dict(row.details or {}),
                "timestamp": row.timestamp.isoformat() if row.timestamp else "",
            },
        }

    async def jobs_add(
        self,
        company: str,
        role: str,
        description: str,
        *,
        location: str = "",
        source: str = "手动添加",
        linked_direction: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        if not company.strip() or not role.strip():
            return {"ok": False, "error": "company and role are required"}
        # Upsert by (user_id, company, role) to match file-based behaviour.
        result = await self.session.execute(
            select(SavedJobModel).where(
                SavedJobModel.user_id == self.user_id,
                SavedJobModel.company == company,
                SavedJobModel.role == role,
            )
        )
        existing = result.scalars().first()
        if existing is not None:
            existing.description = description
            if location:
                existing.location = location
            if notes:
                existing.notes = notes
            if linked_direction:
                existing.linked_direction = linked_direction
            if source:
                existing.source = source
            await self.session.commit()
            return {"ok": True, "job": _saved_job_row_to_dict(existing)}

        job = SavedJobModel(
            id=uuid.uuid4(),
            user_id=self.user_id,
            company=company,
            role=role,
            description=description,
            location=location,
            source=source or "手动添加",
            linked_direction=linked_direction,
            notes=notes,
        )
        self.session.add(job)
        await self.session.commit()
        return {"ok": True, "job": _saved_job_row_to_dict(job)}

    async def jobs_update(self, job_id: str, **fields: object) -> dict[str, Any]:
        try:
            job_uuid = uuid.UUID(str(job_id))
        except ValueError:
            # Accept legacy slug-style ids by string lookup.
            job_uuid = None
        if job_uuid is not None:
            row = await self.session.get(SavedJobModel, job_uuid)
        else:
            result = await self.session.execute(
                select(SavedJobModel).where(SavedJobModel.user_id == self.user_id)
            )
            row = next(
                (j for j in result.scalars().all() if str(j.id) == str(job_id)),
                None,
            )
        if row is None or row.user_id != self.user_id:
            return {"ok": False, "error": "job not found"}

        for key in (
            "company", "role", "description", "location",
            "source", "linked_direction", "notes",
        ):
            if key in fields and fields[key] is not None:
                value = str(fields[key])
                if key in ("company", "role") and not value.strip():
                    continue
                setattr(row, key, value)
        if "status" in fields and fields["status"] is not None:
            raw_status = str(fields["status"]).strip()
            try:
                SavedJobStatus(raw_status)
            except ValueError:
                return {"ok": False, "error": f"invalid status: {raw_status}"}
            row.status = raw_status

        await self.session.commit()
        return {"ok": True, "job": _saved_job_row_to_dict(row)}

    async def jobs_remove(self, job_id: str) -> dict[str, Any]:
        try:
            job_uuid = uuid.UUID(str(job_id))
        except ValueError:
            job_uuid = None
        if job_uuid is not None:
            row = await self.session.get(SavedJobModel, job_uuid)
        else:
            result = await self.session.execute(
                select(SavedJobModel).where(SavedJobModel.user_id == self.user_id)
            )
            row = next(
                (j for j in result.scalars().all() if str(j.id) == str(job_id)),
                None,
            )
        if row is None or row.user_id != self.user_id:
            return {"ok": False, "error": "job not found"}
        await self.session.delete(row)
        await self.session.commit()
        return {"ok": True, "removed": str(row.id)}

    async def run_command(self, cmd: str) -> dict[str, Any]:
        """Spawn the legacy CLI against a tmpdir; sync changes back.

        This is the one endpoint where the file-based round-trip is
        unavoidable — the CLI reads/writes files directly. M3 keeps it as-is.
        """
        mapping = {
            "validate": ["validate"],
            "render-opportunities": ["render-opportunities"],
            "render-execution": ["render-execution"],
            "replan": ["replan", "--write"],
            "job-analyze": ["job", "analyze"],
            "refresh": [],
        }
        if cmd == "refresh":
            return {"ok": True, "code": 0, "output": ""}
        args = mapping.get(cmd, [cmd])
        async with self.with_tmpdir() as tmpdir:
            return _run_cli(args, tmpdir)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _safe_yaml_load(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError):
        return None


def _saved_job_to_dict(row: SavedJobModel) -> dict:
    return {
        "id": str(row.id),
        "company": row.company,
        "role": row.role,
        "description": row.description,
        "location": row.location,
        "source": row.source,
        "saved_on": row.saved_on.isoformat() if row.saved_on else "",
        "status": row.status,
        "linked_direction": row.linked_direction,
        "notes": row.notes,
    }


def _saved_job_row_to_dict(row: SavedJobModel) -> dict:
    return _saved_job_to_dict(row)


def _saved_job_from_model(job: SavedJob, user_id: UUID) -> SavedJobModel:
    try:
        job_uuid = uuid.UUID(str(job.id)) if job.id else uuid.uuid4()
    except ValueError:
        job_uuid = uuid.uuid4()
    return SavedJobModel(
        id=job_uuid,
        user_id=user_id,
        company=job.company,
        role=job.role,
        description=job.description,
        location=job.location,
        source=job.source,
        status=job.status.value if isinstance(job.status, SavedJobStatus) else str(job.status),
        linked_direction=job.linked_direction,
        notes=job.notes,
        saved_on=job.saved_on,
    )


def _saved_job_update(row: SavedJobModel, job: SavedJob) -> None:
    row.company = job.company
    row.role = job.role
    row.description = job.description
    row.location = job.location
    row.source = job.source
    row.status = job.status.value if isinstance(job.status, SavedJobStatus) else str(job.status)
    row.linked_direction = job.linked_direction
    row.notes = job.notes
    row.saved_on = job.saved_on


def _feedback_action_to_dict(row: MatrixFeedbackActionModel) -> dict:
    return {
        "action": row.action,
        "direction": row.direction,
        "details": dict(row.details or {}),
        "timestamp": row.timestamp.isoformat() if row.timestamp else "",
    }


__all__ = ["Repository"]
