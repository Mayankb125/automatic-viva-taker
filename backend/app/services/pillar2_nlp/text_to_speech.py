"""
pillar2_nlp/text_to_speech.py — Question Text-to-Speech Service
===============================================================
Converts question text to base64 audio for frontend playback.
"""

import base64
import os
import tempfile
import threading
from typing import Tuple

import pyttsx3

from app.core.config import TTS_ENGINE, TTS_RATE, TTS_VOLUME


_engine_lock = threading.Lock()


def _clamp_volume(volume: float) -> float:
    return max(0.0, min(1.0, volume))


def _synthesize_with_pyttsx3(text: str) -> Tuple[bytes, str]:
    temp_path = ""

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_path = temp_file.name

        with _engine_lock:
            # Recreate engine per call: shared instances can deadlock on Windows
            # after the first save_to_file/runAndWait cycle.
            engine = pyttsx3.init()
            try:
                engine.setProperty("rate", TTS_RATE)
                engine.setProperty("volume", _clamp_volume(TTS_VOLUME))
                engine.save_to_file(text, temp_path)
                engine.runAndWait()
            finally:
                engine.stop()

        if not os.path.exists(temp_path):
            raise RuntimeError("TTS output file was not created")

        with open(temp_path, "rb") as audio_file:
            audio_bytes = audio_file.read()
        if not audio_bytes:
            raise RuntimeError("TTS output audio is empty")

        return audio_bytes, "audio/wav"
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def synthesize_question_audio(text: str) -> Tuple[str, str]:
    """
    Return question audio as base64 and MIME type.

    Returns:
      (audio_base64, mime_type)
    """
    if not text or not text.strip():
        raise ValueError("question text is empty")

    engine_name = (TTS_ENGINE or "pyttsx3").strip().lower()
    if engine_name != "pyttsx3":
        raise ValueError("Unsupported TTS_ENGINE. Supported value for this phase: pyttsx3")

    audio_bytes, mime_type = _synthesize_with_pyttsx3(text.strip())
    return base64.b64encode(audio_bytes).decode("utf-8"), mime_type
