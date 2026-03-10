from fastapi import APIRouter

router = APIRouter(prefix="/api/viva", tags=["viva"])


@router.get("/question")
def get_question():
    return {"status": "ok"}


@router.post("/answer")
def submit_answer():
    return {"status": "ok"}
