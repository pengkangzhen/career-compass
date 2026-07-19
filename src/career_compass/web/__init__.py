"""北斗星 SaaS web layer (FastAPI + FastAPI Users).

Sibling of the legacy `gui/` package: the desktop / CLI app stays untouched.
M1 only ships auth + health endpoints; business data migrations land in M2/M3.
"""
from __future__ import annotations

__all__ = ["app"]
