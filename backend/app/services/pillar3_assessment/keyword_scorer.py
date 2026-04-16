"""
pillar3_assessment/keyword_scorer.py — Keyword Coverage Scorer
================================================================
Measures what fraction of the expected domain keywords appear in the student's answer.

This scorer is fast (pure string matching, no model) and directly checks whether
the student used the correct technical vocabulary. It complements semantic scoring:
semantic catches meaning similarity, keyword scoring catches vocabulary precision.

Matching strategy:
    - Case-insensitive normalized tokens (punctuation-insensitive)
    - Full phrase match gets full credit per keyword
    - Multi-word keyword token-overlap gets partial credit (0.25 / 0.5 / 0.75)
    - Single-word keywords still require exact token presence

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

    answer_tokens = re.findall(r"[a-z0-9]+", student_answer.lower())
    if not answer_tokens:
        return 0.0

    answer_token_set = set(answer_tokens)
    answer_normalized = f" {' '.join(answer_tokens)} "

    total_credit = 0.0
    valid_keyword_count = 0

    for keyword in key_keywords:
        keyword_tokens = re.findall(r"[a-z0-9]+", str(keyword).lower())
        if not keyword_tokens:
            continue

        valid_keyword_count += 1
        keyword_phrase = " ".join(keyword_tokens)
        phrase_hit = f" {keyword_phrase} " in answer_normalized

        if len(keyword_tokens) == 1:
            total_credit += 1.0 if phrase_hit else 0.0
            continue

        if phrase_hit:
            total_credit += 1.0
            continue

        keyword_token_set = set(keyword_tokens)
        overlap_ratio = len(keyword_token_set & answer_token_set) / len(keyword_token_set)

        if overlap_ratio >= 0.75:
            total_credit += 0.75
        elif overlap_ratio >= 0.50:
            total_credit += 0.50
        elif overlap_ratio >= 0.34:
            total_credit += 0.25

    if valid_keyword_count == 0:
        return 10.0

    score = (total_credit / valid_keyword_count) * 10.0
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
