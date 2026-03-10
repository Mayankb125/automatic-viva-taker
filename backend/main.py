from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base

# Import all models so SQLAlchemy knows about them before creating tables
from app.models import student, session, question, score, integrity_flag

app = FastAPI(title="Automatic Viva Taker API")

# CORS — allow React frontend on port 5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create all tables on startup
Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"status": "Automatic Viva Taker API is running"}
