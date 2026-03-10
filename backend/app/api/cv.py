from fastapi import APIRouter

router = APIRouter(prefix="/api/cv", tags=["cv"])


@router.post("/analyze")
def analyze_frame():
    return {"status": "ok"}
