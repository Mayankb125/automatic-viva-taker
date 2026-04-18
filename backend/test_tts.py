"""
test_tts.py — Quick local test for Phase 4 text-to-speech
=========================================================
Usage:
    .\\venv\\Scripts\\python.exe test_tts.py --text "What is a binary search tree?"
"""

import argparse

from app.services.pillar2_nlp.text_to_speech import synthesize_question_audio


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate base64 question audio with configured TTS engine.")
    parser.add_argument("--text", required=True, help="Question text to synthesize")
    args = parser.parse_args()

    audio_b64, mime_type = synthesize_question_audio(args.text)

    print("=" * 60)
    print(f"Engine output MIME: {mime_type}")
    print(f"Base64 length: {len(audio_b64)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
