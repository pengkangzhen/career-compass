"""Per-user data directory mapping for the SaaS layer.

Each registered user gets an isolated data directory under ``data/users/<id>/``,
reusing the file-based data layer (``view_data`` / ``jobs`` / ``matrix_feedback``
/ ``intake``) that the single-user desktop mode was built on. This delivers
per-user isolation *without* a Postgres migration during the internal-testing
phase — the SaaS routers only depend on ``user_data_dir`` /
``ensure_user_data_dir``, so a future swap to a DB-backed Repository
(docs/saas-migration-plan.md §3) stays localised to this file.
"""
from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

from career_compass.gui.app import _REPO_ROOT


def users_data_root() -> Path:
    """Root directory holding every user's data folder.

    Override with ``CC_USERS_DATA_DIR`` for deployments / tests; defaults to
    ``<repo>/data/users/`` so local dev needs no extra config.
    """
    override = os.getenv("CC_USERS_DATA_DIR")
    if override:
        return Path(override).resolve()
    return _REPO_ROOT / "data" / "users"


def user_data_dir(user_id: UUID | str) -> Path:
    """Absolute path of one user's data directory (may not exist yet)."""
    return users_data_root() / str(user_id)


def ensure_user_data_dir(user_id: UUID | str) -> Path:
    """Return the user's data dir, creating it on first access.

    New users start empty and build their own profile via intake. We do NOT
    seed from the repo's top-level ``data/`` — that is a real person's
    profile with PII (see docs/saas-migration-plan.md §9 q9).
    """
    path = user_data_dir(user_id)
    path.mkdir(parents=True, exist_ok=True)
    return path
