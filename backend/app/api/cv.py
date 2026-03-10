"""
api/cv.py — Computer Vision (Proctoring) Route
================================================
Receives webcam frames from the frontend and checks for integrity violations.

This route is called continuously during the viva (e.g. every 2 seconds) by
the frontend's proctoring component, which sends base64-encoded frames.

All routes are prefixed with /api/cv.
This is currently a STUB. Real CV logic (YOLOv8 + face detection) will be
added in Phase 4 (Proctoring Pillar).

Endpoint:
    POST /api/cv/analyze   — Analyse a webcam frame for integrity violations
"""

from fastapi import APIRouter

# All routes in this file get the /api/cv prefix automatically
router = APIRouter(prefix="/api/cv", tags=["cv"])


@router.post("/analyze")
def analyze_frame():
    """
    Analyse a single webcam frame for proctoring violations.
    TODO (Phase 4): Accept session_id + base64-encoded frame image.
    Run YOLOv8 object detection to find phones, books, extra people.
    Run face landmark detection to check gaze direction and head pose.
    If a violation is detected, save an IntegrityFlag row and return the flag type.
    """
    return {"status": "ok"}
