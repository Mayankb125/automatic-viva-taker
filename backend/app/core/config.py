from dotenv import load_dotenv
import os

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TTS_ENGINE = os.getenv("TTS_ENGINE", "pyttsx3")
DATABASE_URL = "sqlite:///./database.db"
