from fastapi import APIRouter

router = APIRouter(prefix="/api/report", tags=["report"])


@router.get("/{session_id}")
def get_report(session_id: str):
    return {"status": "ok"}


@router.get("/{session_id}/pdf")
def get_report_pdf(session_id: str):
    return {"status": "ok"}
