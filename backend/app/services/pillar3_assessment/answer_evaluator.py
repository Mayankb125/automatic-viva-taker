"""
pillar3_assessment/answer_evaluator.py — Main Answer Evaluator
==============================================================
Orchestrates all 5 scorers and combines them into a single final score
using a weighted formula with level bonuses and switch penalties.

Scoring pipeline:
  1. Run all 5 scorers in order
  2. Normalise semantic score (0–1) → (0–10) before weighting
  3. Apply weighted formula:
       semantic      × 0.35   (meaning and understanding)
       keyword       × 0.20   (technical vocabulary)
       completeness  × 0.20   (coverage of key points)
       depth         × 0.15   (thoroughness of explanation)
       confidence    × 0.10   (certainty and fluency)
  4. Add level bonus:   (current_level - 1) × 0.5
       Harder questions are worth more — level 5 gives +2.0 bonus
  5. Apply switch penalty: -2.0 if the student switched topics
       Switching costs points — answers on the original topic matter more
  6. Clamp final score to [0.0, 10.0]

Return dict contains every individual score + reasons so the API can
send them all back to the frontend for display.

Usage:
    from app.services.pillar3_assessment.answer_evaluator import evaluate_answer
    result = evaluate_answer(
        question, expected_answer, student_answer,
        key_keywords, key_points, current_level, switched
    )
"""

from app.services.pillar3_assessment.semantic_scorer import score_semantic
from app.services.pillar3_assessment.keyword_scorer import score_keywords
from app.services.pillar3_assessment.confidence_scorer import score_confidence
from app.services.pillar3_assessment.depth_scorer import score_depth_completeness

# Weights for each scoring dimension — must sum to 1.0
WEIGHTS = {
    "semantic":      0.35,
    "keyword":       0.20,
    "completeness":  0.20,
    "depth":         0.15,
    "confidence":    0.10,
}

# Bonus per difficulty level above 1 (level 1 = no bonus, level 5 = +2.0)
LEVEL_BONUS_PER_LEVEL = 0.5

# Penalty applied when the student has switched topics in this session
SWITCH_PENALTY = 2.0


def evaluate_answer(
    question: str,
    expected_answer: str,
    student_answer: str,
    key_keywords: list,
    key_points: list,
    current_level: int = 1,
    switched: bool = False,
) -> dict:
    """
    Evaluate a student's answer using all 5 scorers and return a full breakdown.

    Args:
        question:        The question that was asked.
        expected_answer: The ideal answer from the question generator.
        student_answer:  The raw text of what the student said/typed.
        key_keywords:    List of important domain terms (from question generator).
        key_points:      List of core concepts to cover (from question generator).
        current_level:   Difficulty level 1–5. Higher level = more bonus points.
        switched:        True if the student previously switched topics this session.

    Returns:
        Dict with all individual scores, reasons, bonuses, penalties, and final score:
        {
            semantic_score      : float  0.0–1.0  (raw model output)
            keyword_score       : float  0.0–10.0
            depth_score         : float  0.0–10.0
            completeness_score  : float  0.0–10.0
            confidence_score    : float  0.0–10.0
            depth_reason        : str
            completeness_reason : str
            weighted_score      : float  0.0–10.0  (before bonuses/penalties)
            level_bonus         : float  0.0+
            switch_penalty      : float  0.0 or 2.0
            final_score         : float  0.0–10.0  (clamped)
        }
    """
    # ── Step 1: Run all 5 scorers ─────────────────────────────────────────────

    semantic_score = score_semantic(expected_answer, student_answer)
    keyword_score = score_keywords(key_keywords, student_answer)
    confidence_score = score_confidence(student_answer)
    depth_result = score_depth_completeness(
        question, expected_answer, student_answer, key_points
    )
    depth_score = depth_result["depth_score"]
    completeness_score = depth_result["completeness_score"]
    depth_reason = depth_result["depth_reason"]
    completeness_reason = depth_result["completeness_reason"]

    # ── Step 2: Normalise semantic to 0–10 scale before weighting ────────────
    # All other scorers already return 0–10.
    # Semantic returns 0–1 so multiply by 10 to put it on the same scale.
    semantic_normalised = semantic_score * 10.0

    # ── Step 3: Apply weighted formula ───────────────────────────────────────
    weighted_score = (
        semantic_normalised * WEIGHTS["semantic"]
        + keyword_score     * WEIGHTS["keyword"]
        + completeness_score * WEIGHTS["completeness"]
        + depth_score       * WEIGHTS["depth"]
        + confidence_score  * WEIGHTS["confidence"]
    )
    weighted_score = round(weighted_score, 4)

    # ── Step 4: Level bonus ───────────────────────────────────────────────────
    # Level 1 → +0.0,  Level 2 → +0.5,  Level 3 → +1.0,  Level 5 → +2.0
    level_bonus = (current_level - 1) * LEVEL_BONUS_PER_LEVEL

    # ── Step 5: Switch penalty ────────────────────────────────────────────────
    # Applied once per answer during the session where switching occurred.
    switch_penalty = SWITCH_PENALTY if switched else 0.0

    # ── Step 6: Compute and clamp final score ─────────────────────────────────
    raw_final = weighted_score + level_bonus - switch_penalty
    final_score = round(max(0.0, min(10.0, raw_final)), 4)

    return {
        "semantic_score":      semantic_score,
        "keyword_score":       keyword_score,
        "depth_score":         depth_score,
        "completeness_score":  completeness_score,
        "confidence_score":    confidence_score,
        "depth_reason":        depth_reason,
        "completeness_reason": completeness_reason,
        "weighted_score":      weighted_score,
        "level_bonus":         level_bonus,
        "switch_penalty":      switch_penalty,
        "final_score":         final_score,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Standalone test:
#   cd backend
#   .\venv\Scripts\python.exe app/services/pillar3_assessment/answer_evaluator.py
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import time

    QUESTION = "What is a binary search tree and why is it efficient for searching?"
    EXPECTED = (
        "A binary search tree (BST) is a tree data structure where each node has "
        "at most two children. For every node, all values in its left subtree are "
        "smaller, and all values in its right subtree are larger. This ordering "
        "property enables efficient search, insertion, and deletion in O(log n) "
        "average time by halving the search space at each step."
    )
    KEYWORDS = ["binary search tree", "left subtree", "right subtree", "O(log n)", "node"]
    KEY_POINTS = [
        "Each node has at most two children",
        "Left subtree contains values smaller than the node",
        "Right subtree contains values larger than the node",
        "Search time is O(log n) on average",
    ]

    test_cases = [
        {
            "label": "STRONG",
            "answer": (
                "A BST is a binary tree where the left subtree of every node holds "
                "values smaller than the node and the right subtree holds larger values. "
                "This property allows O(log n) search time on average because at each node "
                "we eliminate half the remaining values. It is widely used in databases "
                "and symbol tables for efficient lookup and insertion."
            ),
            "level": 1,
            "switched": False,
            "expected_range": (8.0, 10.0),
        },
        {
            "label": "PARTIAL",
            "answer": (
                "A binary search tree is a tree where nodes are arranged in order. "
                "Left side has smaller values and right side has bigger values. "
                "It helps search data faster than scanning everything one by one."
            ),
            "level": 1,
            "switched": False,
            "expected_range": (4.5, 7.0),
        },
        {
            "label": "WRONG",
            "answer": (
                "I think it is basically like an array but maybe sorted somehow. "
                "Um, I'm not sure exactly how it works. Perhaps it stores elements "
                "in some kind of order but I don't really know the details."
            ),
            "level": 1,
            "switched": False,
            "expected_range": (0.0, 4.0),
        },
    ]

    print("=" * 65)
    print("Testing answer_evaluator.py")
    print("=" * 65)

    for i, tc in enumerate(test_cases):
        if i > 0:
            # Pause between Gemini calls to avoid rate limiting
            print("\n  (waiting 8s before next Gemini call...)")
            time.sleep(8)

        print(f"\n  [{tc['label']}]")
        result = evaluate_answer(
            QUESTION, EXPECTED, tc["answer"],
            KEYWORDS, KEY_POINTS,
            current_level=tc["level"],
            switched=tc["switched"],
        )

        print(f"  semantic_score    : {result['semantic_score']} (raw 0–1)")
        print(f"  keyword_score     : {result['keyword_score']}")
        print(f"  depth_score       : {result['depth_score']}")
        print(f"  completeness_score: {result['completeness_score']}")
        print(f"  confidence_score  : {result['confidence_score']}")
        print(f"  weighted_score    : {result['weighted_score']}")
        print(f"  level_bonus       : +{result['level_bonus']}")
        print(f"  switch_penalty    : -{result['switch_penalty']}")
        print(f"  FINAL SCORE       : {result['final_score']}")
        print(f"  depth_reason      : {result['depth_reason']}")
        print(f"  completeness_reason: {result['completeness_reason']}")

        lo, hi = tc["expected_range"]
        if lo <= result["final_score"] <= hi:
            print(f"  STATUS: PASS ✓ (final score {result['final_score']} in [{lo}, {hi}])")
        else:
            print(f"  STATUS: FAIL ✗ (final score {result['final_score']} NOT in [{lo}, {hi}])")

    print("\n" + "=" * 65)
