"""
pillar2_nlp/speech_to_text.py — Faster-Whisper Speech-to-Text Service
======================================================================
Transcribes base64 audio input into plain text for viva answer scoring.

Design goals:
  - Load Whisper model once per process (not per request)
  - Accept data URL and plain base64 audio payloads
  - Return clean transcribed text for the existing evaluator pipeline
"""

import base64
import binascii
import os
import re
import tempfile
from typing import Iterable, Tuple

from faster_whisper import WhisperModel

from app.core.config import WHISPER_MODEL_SIZE


_model: WhisperModel | None = None

_COMMON_SILENCE_HALLUCINATIONS = {
    "thank you",
    "thanks for watching",
    "you",
    "bye",
}


def _mime_to_extension(mime_type: str) -> str:
    """Map audio MIME type to a safe temporary-file extension."""
    mapping = {
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/mp3": ".mp3",
        "audio/mpeg": ".mp3",
        "audio/mp4": ".m4a",
        "audio/aac": ".aac",
    }
    return mapping.get(mime_type.lower(), ".wav")


def _get_model() -> WhisperModel:
    """Lazy-load and cache a single Whisper model instance for the process."""
    global _model
    if _model is None:
        _model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def _build_bias_prompt(topic: str | None = None, keywords: Iterable[str] | None = None) -> str | None:
    """
    Build a short prompt to bias decoding toward topic-specific vocabulary.

    Whisper does not support strict dictionaries, but an initial prompt helps
    preserve technical terms in transcription.
    """
    parts = []

    cleaned_topic = (topic or "").strip()
    if cleaned_topic:
        parts.append(f"Topic: {cleaned_topic}.")

    cleaned_keywords = []
    if keywords:
        for keyword in keywords:
            value = (keyword or "").strip()
            if value and value.lower() not in {k.lower() for k in cleaned_keywords}:
                cleaned_keywords.append(value)

    if cleaned_keywords:
        parts.append("Technical terms: " + ", ".join(cleaned_keywords[:12]) + ".")

    if not parts:
        return None

    return " ".join(parts)


def _normalize_transcript(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", (text or "").lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _is_low_signal_transcript(transcript: str, avg_no_speech_prob: float) -> bool:
    """
    Reject transcripts likely produced from silence/noise.

    This keeps the scoring pipeline from evaluating hallucinated one-word output
    when the user did not speak.
    """
    normalized = _normalize_transcript(transcript)
    if not normalized:
        return True

    if normalized in _COMMON_SILENCE_HALLUCINATIONS:
        return True

    tokens = normalized.split()
    # Very short transcripts with high no-speech probability are usually silence artifacts.
    if len(tokens) <= 2 and avg_no_speech_prob >= 0.55:
        return True

    return False


def decode_audio_blob(audio_blob: str) -> Tuple[bytes, str]:
    """
    Decode incoming base64 audio payload.

    Supports both:
      - data URL: data:audio/webm;base64,AAAA...
      - plain base64 payload: AAAA...
    """
    if not audio_blob or not audio_blob.strip():
        raise ValueError("audio_blob is empty")

    payload = audio_blob.strip()
    file_extension = ".wav"

    if payload.startswith("data:"):
        header, separator, encoded_data = payload.partition(",")
        if not separator or not encoded_data:
            raise ValueError("audio_blob data URL is malformed")

        mime_type = header[5:].split(";")[0] if ";" in header else "audio/wav"
        file_extension = _mime_to_extension(mime_type)
        payload = encoded_data

    try:
        audio_bytes = base64.b64decode(payload, validate=True)
    except binascii.Error as exc:
        raise ValueError("audio_blob is not valid base64") from exc

    if not audio_bytes:
        raise ValueError("decoded audio is empty")

    return audio_bytes, file_extension


def transcribe_audio_bytes(
    audio_bytes: bytes,
    file_extension: str = ".wav",
    topic: str | None = None,
    keywords: Iterable[str] | None = None,
) -> str:
    """Transcribe raw audio bytes to text via faster-whisper."""
    if not audio_bytes:
        raise ValueError("audio bytes are empty")

    model = _get_model()
    temp_file_path = ""
    bias_prompt = _build_bias_prompt(topic=topic, keywords=keywords)

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(audio_bytes)
            temp_file_path = temp_file.name

        segments, _ = model.transcribe(
            temp_file_path,
            language="en",
            initial_prompt=bias_prompt,
            vad_filter=True,
        )

        segment_list = list(segments)
        transcript = " ".join(segment.text.strip() for segment in segment_list if segment.text).strip()

        no_speech_scores = [
            float(getattr(segment, "no_speech_prob", 0.0))
            for segment in segment_list
            if getattr(segment, "text", "").strip()
        ]
        avg_no_speech_prob = (
            sum(no_speech_scores) / len(no_speech_scores)
            if no_speech_scores
            else 1.0
        )

        if not transcript or _is_low_signal_transcript(transcript, avg_no_speech_prob):
            raise ValueError("no speech detected in audio")

        return transcript
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)


def transcribe_audio_blob(
    audio_blob: str,
    topic: str | None = None,
    keywords: Iterable[str] | None = None,
) -> str:
    """Decode base64 input and return transcribed answer text."""
    audio_bytes, file_extension = decode_audio_blob(audio_blob)
    return transcribe_audio_bytes(
        audio_bytes,
        file_extension,
        topic=topic,
        keywords=keywords,
    )
