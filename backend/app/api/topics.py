from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

router = APIRouter(prefix="/api", tags=["topics"])

TOPICS_FILE = Path(__file__).resolve().parent.parent.parent / "topics.json"


@router.get("/topics")
def get_topics():
    try:
        with open(TOPICS_FILE, "r") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="topics.json not found")
