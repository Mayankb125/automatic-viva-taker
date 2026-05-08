"""
pillar3_assessment/confidence_scorer.py — Confidence / Fluency Scorer
========================================================================
Estimates how confidently the student answered based on their word choice.
Detects hesitation markers, filler words, and uncertainty phrases.

In a real viva, confidence is measured from voice analysis (speech rate,
pauses, pitch). In Phase 4 (Speech), this scorer will be upgraded to use
audio features. For now (Phase 2), it works on the TEXT of the transcribed
answer — so it catches written hesitations like "I think", "maybe", "um".

How it works:
  1. Count how many hesitation markers appear in the answer
  2. Compute: penalty = hesitation_count / word_count
  3. Score = 10.0 - (penalty * 50), clamped to 0.0–10.0

Score range: 0.0 to 10.0
  - 9.0–10.0 = very confident, no filler words
  - 6.0–8.9  = mostly confident, 1–2 filler words
  - 3.0–5.9  = somewhat hesitant, several filler words
  - 0.0–2.9  = very hesitant, many uncertainty markers

Usage:
    from app.services.pillar3_assessment.confidence_scorer import score_confidence
    score = score_confidence(student_answer)
"""

import re


STOPWORDS = {
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "of",
    "and", "or", "but", "for", "with", "as", "by", "from",
    "that", "this", "was", "are", "be", "been", "have", "has",
    "i", "we", "you", "he", "she", "they", "its", "do", "does",
}

# List of hesitation markers and uncertainty phrases.
# All matched using regex word boundaries (\b) so "um" matches in "Um," and at
# sentence start, not just when surrounded by spaces.
HESITATION_MARKERS = [
    # Multi-word phrases — checked first so they aren't double-counted
    "i'm not sure",
    "i am not sure",
    "i don't know",
    "i do not know",
    "i'm not certain",
    "i think that",
    "i believe that",
    "sort of like",
    "kind of like",
    "you know",
    "i feel like",
    "not sure",
    "kind of",
    "sort of",
    # Single-word hesitations and uncertainty markers
    "i guess",
    "i think",
    "i believe",
    "maybe",
    "perhaps",
    "probably",
    "possibly",
    "basically",
    "actually",
    "literally",
    # Spoken filler words (from speech-to-text transcription)
    "um",
    "uh",
    "er",
    "hmm",
    "umm",
    "uhh",
]


def score_confidence(student_answer: str) -> float:
    """
    Score the student's answer based on hesitation and uncertainty markers.

    Args:
        student_answer: The raw text of what the student said/typed.

    Returns:
        Float in range 0.0–10.0.
        Higher = more confident delivery with fewer filler words.
    """
    if not student_answer or not student_answer.strip():
        return 0.0  # Empty answer = zero confidence

    answer_lower = student_answer.lower().strip()

    # Tokenize into word-like units so punctuation-only inputs do not score high.
    tokens = re.findall(r"[a-z0-9]+", answer_lower)
    word_count = len(tokens)
    if word_count == 0:
        return 0.0

    # Count each hesitation marker that appears in the answer.
    # Use word-boundary regex so "um" catches "Um," at sentence start,
    # "um." at end, and doesn't falsely match inside other words.
    hesitation_count = 0
    for marker in HESITATION_MARKERS:
        pattern = r"\b" + re.escape(marker) + r"\b"
        occurrences = len(re.findall(pattern, answer_lower))
        hesitation_count += occurrences

    # Base hesitation penalty.
    # 1 hesitation per 10 words removes ~2.5 points.
    hesitation_penalty = (hesitation_count / word_count) * 25

    # Content-quality penalties prevent "always 10" on vague/empty-like answers.
    content_tokens = [token for token in tokens if token not in STOPWORDS]
    content_count = len(content_tokens)
    content_ratio = content_count / word_count
    diversity = (len(set(content_tokens)) / content_count) if content_count else 0.0

    quality_penalty = 0.0
    if word_count < 6:
        quality_penalty += 1.0
    if content_count < 4:
        quality_penalty += 3.0
    elif content_count < 8:
        quality_penalty += 1.5
    if content_ratio < 0.35:
        quality_penalty += 2.0
    if content_count > 0 and diversity < 0.45:
        quality_penalty += 1.5

    score = 10.0 - hesitation_penalty - quality_penalty

    return round(max(0.0, min(10.0, score)), 2)


# ─────────────────────────────────────────────────────────────────────────────
# Standalone test:
#   cd backend
#   .\venv\Scripts\python.exe app/services/pillar3_assessment/confidence_scorer.py
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_cases = [
        (
            "STRONG (confident)",
            "A binary search tree stores data in a sorted hierarchical structure. "
            "Each node has at most two children where the left subtree contains "
            "smaller values and the right subtree contains larger values. "
            "This enables O(log n) search by eliminating half the tree at each step.",
        ),
        (
            "PARTIAL (some hesitation)",
            "I think a binary search tree is a tree where elements are stored in a "
            "sorted order at each node. Basically it makes searching faster because "
            "you go left for smaller values and right for larger ones.",
        ),
        (
            "WRONG (very hesitant)",
            "Um, I'm not sure, maybe it's some kind of sorting algorithm? I guess it "
            "divides things up, probably using recursion, I think. I don't know, "
            "maybe it's related to binary search but I'm not certain.",
        ),
        (
            "EMPTY",
            "",
        ),
    ]

    print("=" * 60)
    print("Testing confidence_scorer.py")
    print("=" * 60)

    for label, student_answer in test_cases:
        score = score_confidence(student_answer)
        print(f"\n  [{label}]")
        print(f"  Score : {score} / 10.0")
        if "STRONG" in label and score >= 9.0:
            print("  STATUS: PASS ✓ (score >= 9.0 for confident answer)")
        elif "PARTIAL" in label and 3.0 <= score < 9.0:
            print("  STATUS: PASS ✓ (score in 3.0–9.0 for hesitant answer)")
        elif "WRONG" in label and score < 6.0:
            print("  STATUS: PASS ✓ (score < 6.0 for very hesitant answer)")
        elif "EMPTY" in label and score == 0.0:
            print("  STATUS: PASS ✓ (score = 0.0 for empty answer)")
        else:
            print("  STATUS: FAIL ✗ (score outside expected range)")

    print("\n" + "=" * 60)
