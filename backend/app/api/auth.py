"""
api/auth.py — Authentication Routes
=====================================
Handles student registration, login, and face verification.

All routes are prefixed with /api/auth (defined by the router prefix below).
These are currently STUB implementations that return {"status": "ok"}.
Real logic will be added in Phase 3 when we integrate face_recognition
and JWT token authentication.

Endpoints:
    POST /api/auth/register      — Create a new student account + save face encoding
    POST /api/auth/login         — Verify email/password, return session token
    POST /api/auth/verify-face   — Compare live webcam face to stored encoding
"""

from fastapi import APIRouter

# All routes in this file get the /api/auth prefix automatically
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
def register():
    """
    Register a new student.
    TODO (Phase 3): Accept name, email, password, and a face photo.
    Save a new Student row. Encode the face photo and store as BLOB.
    """
    return {"status": "ok"}


@router.post("/login")
def login():
    """
    Log in an existing student.
    TODO (Phase 3): Verify email + password. Return a JWT access token
    that the frontend stores and sends with every subsequent request.
    """
    return {"status": "ok"}


@router.post("/verify-face")
def verify_face():
    """
    Verify the live webcam face matches the registered face.
    Called at the start of every viva session before questions begin.
    TODO (Phase 3): Compare face_recognition encoding of the live frame
    against the stored face_encoding BLOB in the students table.
    """
    return {"status": "ok"}
