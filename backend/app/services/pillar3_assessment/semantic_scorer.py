"""
pillar3_assessment/semantic_scorer.py — Semantic Similarity Scorer
====================================================================
Measures how closely the student's answer MEANS the same as the expected answer,
using sentence embeddings and cosine similarity.

This scorer catches good answers that use different words than the expected answer.
For example: "A stack uses LIFO" and "A stack processes the last item added first"
mean the same thing but share no keywords — semantic scoring catches this.

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

from sentence_transformers import SentenceTransformer, util

# Load the model once at module import time (not on every function call).
# This avoids reloading ~90MB model on every answer submission.
# all-MiniLM-L6-v2 is the recommended model for semantic similarity tasks.
_model = SentenceTransformer("all-MiniLM-L6-v2")


def score_semantic(expected_answer: str, student_answer: str) -> float:
    """
    Compute cosine similarity between expected and student answer embeddings.

    Args:
        expected_answer: The ideal answer generated alongside the question.
        student_answer:  The raw text of what the student said/typed.

    Returns:
        Float in range 0.0–1.0.
        Higher = student answer is more semantically similar to expected.
    """
    if not student_answer or not student_answer.strip():
        return 0.0  # Empty answer scores 0 immediately

    # Encode both answers into 384-dimensional embedding vectors
    embeddings = _model.encode(
        [expected_answer, student_answer],
        convert_to_tensor=True,
    )

    # Cosine similarity: dot product of unit vectors → range [-1, 1]
    # clamp to [0, 1] since negative similarity has no meaning here
    similarity = util.cos_sim(embeddings[0], embeddings[1]).item()
    return round(max(0.0, min(1.0, similarity)), 4)


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
        else:
            print("  STATUS: FAIL ✗ (score outside expected range)")

    print("\n" + "=" * 60)
