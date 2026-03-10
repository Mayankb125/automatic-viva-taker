from fastapi import APIRouter

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
def register():
    return {"status": "ok"}


@router.post("/login")
def login():
    return {"status": "ok"}


@router.post("/verify-face")
def verify_face():
    return {"status": "ok"}
