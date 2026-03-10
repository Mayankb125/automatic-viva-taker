"""
pillar3_assessment/keyword_scorer.py — Keyword Coverage Scorer
================================================================
Measures what fraction of the expected domain keywords appear in the student's answer.

This scorer is fast (pure string matching, no model) and directly checks whether
the student used the correct technical vocabulary. It complements semantic scoring:
semantic catches meaning similarity, keyword scoring catches vocabulary precision.

Matching strategy:
  - Case-insensitive
  - Whole-word matching (so "tree" doesn't match inside "subtree")
  - Each keyword is checked as a substring with word boundaries via regex

Score range: 0.0 to 10.0
  - 10.0 = all keywords mentioned
  - 0.0  = no keywords mentioned
  - Score = (keywords_found / total_keywords) * 10.0

Usage:
    from app.services.pillar3_assessment.keyword_scorer import score_keywords
    score = score_keywords(key_keywords, student_answer)
"""

import re


def score_keywords(key_keywords: list, student_answer: str) -> float:
    """
    Count how many of the expected keywords appear in the student's answer.

    Args:
        key_keywords:   List of important domain terms from the question generator.
                        e.g. ["BST", "left subtree", "right subtree", "inorder"]
        student_answer: The raw text of what the student said/typed.

    Returns:
        Float in range 0.0–10.0.
        (keywords_found / total_keywords) * 10.0
    """
    if not student_answer or not student_answer.strip():
        return 0.0  # Empty answer scores 0

    if not key_keywords:
        return 10.0  # No keywords to check — full marks by default

    answer_lower = student_answer.lower()
    found = 0

    for keyword in key_keywords:
        # Case-insensitive whole-word search using word boundary anchors.
        # \b matches at a word boundary so "tree" won't falsely match inside "subtree".
        # re.escape handles keywords with special characters like "O(log n)".
        pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
        if re.search(pattern, answer_lower):
            found += 1

    score = (found / len(key_keywords)) * 10.0
    return round(score, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Standalone test:
#   cd backend
#   .\venv\Scripts\python.exe app/services/pillar3_assessment/keyword_scorer.py
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    KEYWORDS = ["binary search tree", "left subtree", "right subtree", "O(log n)", "node"]

    test_cases = [
        (
            "STRONG",
            "A binary search tree is a data structure where every node has a left subtree "
            "with smaller values and a right subtree with larger values. This enables "
            "O(log n) search time by halving the search space at each node.",
        ),
        (
            "PARTIAL",
            "A binary search tree organizes data so each node has a left and right child. "
            "Values smaller than the node go left, larger ones go right. "
            "This helps find elements faster than scanning everything.",
        ),
        (
            "WRONG",
            "Quicksort divides the array around a pivot element and recursively "
            "sorts the two halves. It runs in O(n log n) average time.",
        ),
        (
            "EMPTY",
            "",
        ),
    ]

    print("=" * 60)
    print("Testing keyword_scorer.py")
    print("=" * 60)

    for label, student_answer in test_cases:
        score = score_keywords(KEYWORDS, student_answer)
        print(f"\n  [{label}]")
        print(f"  Score : {score} / 10.0")
        if label == "STRONG" and score >= 8.0:
            print("  STATUS: PASS ✓ (score >= 8.0 for strong answer)")
        elif label == "PARTIAL" and 2.0 <= score < 8.0:
            print("  STATUS: PASS ✓ (score in 2.0–8.0 for partial answer)")
        elif label == "WRONG" and score <= 2.0:
            print("  STATUS: PASS ✓ (score <= 2.0 for wrong answer)")
        elif label == "EMPTY" and score == 0.0:
            print("  STATUS: PASS ✓ (score = 0.0 for empty answer)")
        else:
            print("  STATUS: FAIL ✗ (score outside expected range)")

    print("\n" + "=" * 60)
