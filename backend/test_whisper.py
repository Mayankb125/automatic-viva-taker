"""
test_whisper.py — Quick local test for Phase 4 speech-to-text
==============================================================
Usage:
    .\\venv\\Scripts\\python.exe test_whisper.py --file .\\sample.wav
"""

import argparse
import base64
from pathlib import Path

from app.services.pillar2_nlp.speech_to_text import transcribe_audio_blob


def main() -> None:
    parser = argparse.ArgumentParser(description="Test Faster-Whisper transcription with a local audio file.")
    parser.add_argument("--file", required=True, help="Path to an audio file (.wav/.webm/.ogg/.mp3/.m4a).")
    args = parser.parse_args()

    audio_path = Path(args.file)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    audio_bytes = audio_path.read_bytes()
    audio_blob = base64.b64encode(audio_bytes).decode("utf-8")

    transcript = transcribe_audio_blob(audio_blob)

    print("=" * 60)
    print(f"Input file : {audio_path}")
    print(f"Transcript : {transcript}")
    print("=" * 60)


if __name__ == "__main__":
    main()
