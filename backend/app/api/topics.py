from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["topics"])


@router.get("/topics")
def get_topics():
    return {"status": "ok"}
