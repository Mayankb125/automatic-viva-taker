"""
api/topics.py — Topics Route
==============================
Returns the full list of available exam subjects and their topics.
This is the only REAL (non-stub) route implemented in Phase 1.

The data is read from topics.json in the backend/ directory.
That file has a "subjects" wrapper with named subject objects,
each containing a "topics" list.

Endpoint:
    GET /api/topics   — Returns the full subjects object from topics.json

Why pathlib?
    __file__ gives the absolute path of this source file.
    .resolve() converts it to a real path (no symlink issues).
    .parent.parent.parent goes up 3 levels:
        api/ → app/ → backend/
    Then we append "topics.json" to get the correct absolute path.
    This works regardless of which directory uvicorn is started from.
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

router = APIRouter(prefix="/api", tags=["topics"])

# Build the absolute path to topics.json at startup time (not per-request).
# Path chain: this file → api/ → app/ → backend/ → topics.json
TOPICS_FILE = Path(__file__).resolve().parent.parent.parent / "topics.json"


@router.get("/topics")
def get_topics():
    """
    Load and return all subjects + topics from topics.json.

    Returns the full JSON object, which the frontend uses to populate
    the subject dropdown and topic checkboxes on the Topic Selection page.

    Raises HTTP 500 if topics.json is missing (should never happen in normal use).
    """
    try:
        with open(TOPICS_FILE, "r") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        # This would mean topics.json was deleted from the backend/ directory.
        # Return a 500 rather than a 404 because this is a server config problem.
        raise HTTPException(status_code=500, detail="topics.json not found")
