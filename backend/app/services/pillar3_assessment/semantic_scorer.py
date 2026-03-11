"""
pillar3_assessment/semantic_scorer.py — Semantic Similarity Scorer
====================================================================
Measures how closely the student's answer MEANS the same as the expected answer,
using sentence embeddings and cosine similarity.

This scorer catches good answers that use different words than the expected answer.
For example: "A stack uses LIFO" and "A stack processes the last item added first"
mean the same thing but share no keywords — semantic scoring catches this.

Anti-stuffing protection — 3 layers run BEFORE the model:
  Layer 1 — Relative Length Gate:
    If the student wrote less than 30% of the expected word count → score = 0.0
    Catches: "BST BST BST" against a 20-word expected answer
    Guard: max(1, expected_word_count) prevents division by zero

  Layer 2 — Unique Word Gate (only when expected answer > 5 words):
    After removing stopwords, if unique content words <= 3 → score = 0.0
    Catches: "BST left right BST left right" (only 3 unique content words)
    Skipped for short expected answers like "BST" or "LIFO"

  Layer 3 — TTR Diversity Penalty:
    TTR = unique content words / total content words (stopwords removed)
    diversity_factor = min(1.0, TTR × 2)   → no penalty above TTR 0.5
    final_semantic = raw_model_score × diversity_factor
    Catches: soft repetition that sneaks past Layers 1 and 2

Model: all-MiniLM-L6-v2 (from sentence-transformers)
  - Downloads ~90MB on first run, cached locally after that
  - Fast inference (~5ms per pair on CPU)
  - Good balance of speed and accuracy for sentence similarity

Score range: 0.0 to 1.0
  - 1.0 = identical meaning
  - 0.85+ = very strong answer
  - 0.60–0.84 = good partial answer
  - 0.30–0.59 = some relevant content but incomplete
  - 0.0–0.29 = wrong or completely off-topic

Usage:
    from app.services.pillar3_assessment.semantic_scorer import score_semantic
    score = score_semantic(expected_answer, student_answer)
"""

import re
from sentence_transformers import SentenceTransformer, util

# Stopwords removed before TTR calculation so common grammatical words
# (a, is, the, and ...) don't artificially inflate or deflate the ratio.
_STOPWORDS = {
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "of",
    "and", "or", "but", "for", "with", "as", "by", "from",
    "that", "this", "was", "are", "be", "been", "have", "has",
    "i", "we", "you", "he", "she", "they", "its", "do", "does",
}

# Load the model once at module import time (not on every function call).
# This avoids reloading ~90MB model on every answer submission.
# all-MiniLM-L6-v2 is the recommended model for semantic similarity tasks.
_model = SentenceTransformer("all-MiniLM-L6-v2")


def _content_words(text: str) -> list:
    """
    Return all words from text with stopwords removed and lowercased.
    Used by Layers 2 and 3 for TTR calculation.
    """
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in _STOPWORDS]


def score_semantic(expected_answer: str, student_answer: str) -> float:
    """
    Compute cosine similarity between expected and student answer embeddings,
    with 3-layer anti-stuffing protection applied first.

    Args:
        expected_answer: The ideal answer generated alongside the question.
        student_answer:  The raw text of what the student said/typed.

    Returns:
        Float in range 0.0–1.0.
        Higher = student answer is more semantically similar to expected.
    """
    if not student_answer or not student_answer.strip():
        return 0.0  # Empty answer scores 0 immediately

    student_words = student_answer.split()
    student_word_count = len(student_words)

    # ── Layer 1: Relative Length Gate ────────────────────────────────────────
    # Student must write at least 30% as many words as the expected answer.
    # max(1, ...) prevents division by zero if expected_answer is empty.
    expected_word_count = max(1, len(expected_answer.split()))
    ratio = student_word_count / expected_word_count
    if ratio < 0.3:
        return 0.0  # Too short relative to what the question demands

    # ── Layer 2: Unique Word Gate ─────────────────────────────────────────────
    # Only applied when the expected answer itself requires a real explanation.
    # Short expected answers like "BST" or "LIFO" bypass this gate entirely.
    if expected_word_count > 5:
        content = _content_words(student_answer)
        unique_content = set(content)
        if len(unique_content) <= 3:
            return 0.0  # Answer is pure keyword repetition

    # ── Layer 3: TTR Diversity Penalty ────────────────────────────────────────
    # Type-Token Ratio measures vocabulary variety on content words only.
    # diversity_factor = 1.0 when TTR >= 0.5 (no penalty for varied answers).
    # diversity_factor scales down to 0.0 as TTR approaches 0 (full repetition).
    content_all = _content_words(student_answer)
    if content_all:
        ttr = len(set(content_all)) / len(content_all)
        diversity_factor = min(1.0, ttr * 2)
    else:
        diversity_factor = 0.0

    # ── Semantic Model Scoring ────────────────────────────────────────────────
    # Encode both answers into 384-dimensional embedding vectors
    embeddings = _model.encode(
        [expected_answer, student_answer],
        convert_to_tensor=True,
    )

    # Cosine similarity: dot product of unit vectors → range [-1, 1]
    # clamp to [0, 1] since negative similarity has no meaning here
    similarity = util.cos_sim(embeddings[0], embeddings[1]).item()
    raw_score = max(0.0, min(1.0, similarity))

    # Apply TTR diversity factor — penalises repetitive answers proportionally
    final_score = raw_score * diversity_factor
    return round(final_score, 4)


# ─────────────────────────────────────────────────────────────────────────────
# Standalone test:
#   cd backend
#   .\venv\Scripts\python.exe app/services/pillar3_assessment/semantic_scorer.py
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    QUESTION = "What is a binary search tree?"
    EXPECTED = (
        "A binary search tree (BST) is a tree data structure where each node has "
        "at most two children. For every node, all values in its left subtree are "
        "smaller, and all values in its right subtree are larger. This ordering "
        "property enables efficient search, insertion, and deletion in O(log n) "
        "average time. BSTs are widely used in databases and search algorithms."
    )

    test_cases = [
        (
            "STRONG",
            "A BST is a binary tree where the left child contains values smaller "
            "than the root and the right child contains values greater than the root. "
            "This property allows O(log n) search time on average, making it efficient "
            "for lookup operations. It's used in databases and symbol tables.",
        ),
        (
            "PARTIAL",
            "A binary search tree is a type of tree where nodes are arranged in order. "
            "It helps to search data faster than a normal array.",
        ),
        (
            "WRONG",
            "A linked list is a linear data structure where each element points to "
            "the next one in memory. There is no hierarchical ordering, and finding "
            "an element requires scanning from the head node sequentially, giving O(n) time.",
        ),
        (
            "EMPTY",
            "",
        ),
        (
            "STUFFED",
            # Repeating one keyword many times — should be caught by Layer 2
            "BST BST BST BST BST BST BST BST BST BST BST BST BST BST BST BST BST BST",
        ),
    ]

    print("=" * 60)
    print("Testing semantic_scorer.py")
    print("=" * 60)

    for label, student_answer in test_cases:
        score = score_semantic(EXPECTED, student_answer)
        print(f"\n  [{label}]")
        print(f"  Score : {score}")
        # Validate expected ranges
        if label == "STRONG" and score >= 0.75:
            print("  STATUS: PASS ✓ (score >= 0.75 for strong answer)")
        elif label == "PARTIAL" and 0.30 <= score < 0.80:
            print("  STATUS: PASS ✓ (score in 0.30–0.80 for partial answer)")
        elif label == "WRONG" and score < 0.55:
            print("  STATUS: PASS ✓ (score < 0.55 for wrong answer)")
        elif label == "EMPTY" and score == 0.0:
            print("  STATUS: PASS ✓ (score = 0.0 for empty answer)")
        elif label == "STUFFED" and score == 0.0:
            print("  STATUS: PASS ✓ (score = 0.0 for keyword-stuffed answer)")
        else:
            print("  STATUS: FAIL ✗ (score outside expected range)")

    print("\n" + "=" * 60)
