"""
config.py — Application Configuration
=======================================
Reads settings from the .env file in the backend/ directory and exposes them
as module-level variables so any other file can import them cleanly.

Required .env keys:
    GEMINI_API_KEY  — Google Gemini API key used by the NLP question generator (Phase 2)
    TTS_ENGINE      — Text-to-speech engine name (default: "pyttsx3")

The database URL is hardcoded here (SQLite file in the backend/ folder)
because it never needs to change between environments for this project.

Usage in other files:
    from app.core.config import GEMINI_API_KEY, DATABASE_URL
"""

from dotenv import load_dotenv
import os

# Load all key=value pairs from backend/.env into os environment variables.
# If .env doesn't exist, no error is raised — os.getenv() will return the defaults below.
load_dotenv()

# Google Gemini API key — required for AI question generation in Phase 2.
# If not set, the NLP services will fail when they try to call the Gemini API.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Text-to-speech engine to use when reading questions aloud to the student.
# Default is "pyttsx3" (works offline, no API key needed).
TTS_ENGINE = os.getenv("TTS_ENGINE", "pyttsx3")

# SQLite database file path (relative to the backend/ directory).
# SQLAlchemy will create 'database.db' automatically if it doesn't exist.
DATABASE_URL = "sqlite:///./database.db"
