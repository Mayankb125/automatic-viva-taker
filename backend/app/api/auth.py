"""api/auth.py — Deferred auth routes.

Auth is intentionally out of scope for the current build.
The router remains so main.py imports stay valid, but no endpoints are exposed.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/auth", tags=["auth"])
