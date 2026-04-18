"""
config.py — Application Configuration
=======================================
Reads settings from the .env file in the backend/ directory and exposes them
as module-level variables so any other file can import them cleanly.

Required .env keys:
    GEMINI_API_KEY  — Google Gemini API key used by the NLP question generator (Phase 2)
    TTS_ENGINE      — Text-to-speech engine name (default: "pyttsx3")
    TTS_RATE        — Text-to-speech voice rate in words-per-minute style units
    TTS_VOLUME      — Text-to-speech output volume in range 0.0–1.0
    WHISPER_MODEL_SIZE — Faster-Whisper model size (default: "base")

The database URL is hardcoded here (SQLite file in the backend/ folder)
because it never needs to change between environments for this project.

Usage in other files:
    from app.core.config import GEMINI_API_KEY, DATABASE_URL
"""

from pathlib import Path

from dotenv import load_dotenv
import os

# Resolve backend/.env with an absolute path so loading works from any cwd.
BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BACKEND_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False)

# Google Gemini API key — required for AI question generation in Phase 2.
# If not set, the NLP services will fail when they try to call the Gemini API.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Text-to-speech engine to use when reading questions aloud to the student.
# Default is "pyttsx3" (works offline, no API key needed).
TTS_ENGINE = os.getenv("TTS_ENGINE", "pyttsx3")

# Voice rate and volume for TTS output.
TTS_RATE = int(os.getenv("TTS_RATE", "170"))
TTS_VOLUME = float(os.getenv("TTS_VOLUME", "1.0"))

# Faster-Whisper model size used for speech-to-text in Phase 4.
# Valid values include: tiny, base, small, medium, large-v3.
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")

# SQLite database file path (relative to the backend/ directory).
# SQLAlchemy will create 'database.db' automatically if it doesn't exist.
DATABASE_URL = "sqlite:///./database.db"
