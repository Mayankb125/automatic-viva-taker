from fastapi import APIRouter

router = APIRouter(prefix="/api/session", tags=["session"])


@router.post("/start")
def start_session():
    return {"status": "ok"}


@router.post("/end")
def end_session():
    return {"status": "ok"}


@router.post("/switch-topic")
def switch_topic():
    return {"status": "ok"}


@router.get("/{session_id}")
def get_session(session_id: str):
    return {"status": "ok"}
