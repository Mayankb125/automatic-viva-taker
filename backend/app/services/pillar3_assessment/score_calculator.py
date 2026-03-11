"""
pillar3_assessment/score_calculator.py — Session Score Calculator
==================================================================
Aggregates all individual question scores from a session into:

  1. Per-topic score  — average final_score across all questions on that topic
  2. Overall score    — weighted average across all topics, where topics with
                        more questions carry more weight

This module works on plain dicts (not SQLAlchemy objects) so it can be tested
in pure Python without a database. In Step 2.6 the API route will query the
database, build the list of score dicts, and pass them here.

Input format — list of score records, one per question answered:
    [
        {"topic": "Data Structures", "final_score": 8.5},
        {"topic": "Data Structures", "final_score": 7.2},
        {"topic": "Algorithms",      "final_score": 6.0},
        ...
    ]
    Each dict must have "topic" (str) and "final_score" (float 0–10).

Output format:
    {
        "topic_scores": {
            "Data Structures": 7.85,   # average of all scores on that topic
            "Algorithms":      6.0,
            ...
        },
        "topic_question_counts": {
            "Data Structures": 2,      # how many questions were asked per topic
            "Algorithms":      1,
        },
        "overall_score": 7.23,         # weighted average (more questions = more weight)
        "total_questions": 3,
    }

Usage:
    from app.services.pillar3_assessment.score_calculator import calculate_session_scores
    result = calculate_session_scores(score_records)
"""


def calculate_session_scores(score_records: list) -> dict:
    """
    Calculate per-topic and overall scores for a completed session.

    Args:
        score_records: List of dicts, each with "topic" (str) and
                       "final_score" (float 0–10). One dict per question answered.

    Returns:
        Dict with keys:
            topic_scores          (dict: topic → average score)
            topic_question_counts (dict: topic → question count)
            overall_score         (float 0–10, weighted by question count)
            total_questions       (int)

    Raises:
        ValueError: If score_records is empty or contains invalid entries.
    """
    if not score_records:
        raise ValueError("score_records is empty — no answers to calculate scores from")

    # ── Step 1: Group final scores by topic ───────────────────────────────────
    # topic_buckets: { "Data Structures": [8.5, 7.2], "Algorithms": [6.0] }
    topic_buckets: dict = {}
    for record in score_records:
        topic = record.get("topic")
        final_score = record.get("final_score")

        if topic is None or final_score is None:
            raise ValueError(
                f"Each score record must have 'topic' and 'final_score'. Got: {record}"
            )

        if topic not in topic_buckets:
            topic_buckets[topic] = []
        topic_buckets[topic].append(float(final_score))

    # ── Step 2: Per-topic average score ───────────────────────────────────────
    # Round to 2 decimal places for clean display
    topic_scores = {}
    topic_question_counts = {}
    for topic, scores in topic_buckets.items():
        topic_scores[topic] = round(sum(scores) / len(scores), 2)
        topic_question_counts[topic] = len(scores)

    # ── Step 3: Overall score — weighted average across topics ────────────────
    # A topic with 5 questions contributes more than a topic with 1 question.
    # Formula: sum(topic_avg × question_count) / total_questions
    #
    # Example:
    #   Data Structures: avg=7.85, count=2  → contributes 7.85×2 = 15.70
    #   Algorithms:      avg=6.00, count=1  → contributes 6.00×1 = 6.00
    #   total_questions = 3
    #   overall = (15.70 + 6.00) / 3 = 7.23
    total_questions = len(score_records)
    weighted_sum = sum(
        topic_scores[topic] * topic_question_counts[topic]
        for topic in topic_scores
    )
    overall_score = round(weighted_sum / total_questions, 2)

    return {
        "topic_scores":           topic_scores,
        "topic_question_counts":  topic_question_counts,
        "overall_score":          overall_score,
        "total_questions":        total_questions,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Standalone test:
#   cd backend
#   .\venv\Scripts\python.exe app/services/pillar3_assessment/score_calculator.py
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    # Simulated session: student answered 7 questions across 3 topics
    # This mirrors what the database query will return in Step 2.6
    simulated_scores = [
        # Topic 1 — Data Structures: 3 questions, doing well
        {"topic": "Data Structures", "final_score": 8.81},  # strong BST answer
        {"topic": "Data Structures", "final_score": 7.50},  # decent answer
        {"topic": "Data Structures", "final_score": 6.20},  # partial answer
        # Topic 2 — Algorithms: 2 questions, average performance
        {"topic": "Algorithms",      "final_score": 5.76},  # partial answer
        {"topic": "Algorithms",      "final_score": 6.40},  # decent answer
        # Topic 3 — Operating Systems: 2 questions, struggling
        {"topic": "Operating Systems", "final_score": 3.10},  # weak answer
        {"topic": "Operating Systems", "final_score": 1.74},  # wrong answer
    ]

    print("=" * 60)
    print("Testing score_calculator.py")
    print("=" * 60)
    print(f"\n  Input: {len(simulated_scores)} score records across 3 topics")

    result = calculate_session_scores(simulated_scores)

    print("\n  ── Per-Topic Scores ──")
    for topic, score in result["topic_scores"].items():
        count = result["topic_question_counts"][topic]
        print(f"  {topic:<22} avg={score}  ({count} questions)")

    print(f"\n  ── Overall Score ──")
    print(f"  overall_score    : {result['overall_score']}")
    print(f"  total_questions  : {result['total_questions']}")

    # ── Validation ────────────────────────────────────────────────────────────
    print("\n  ── Validation ──")
    all_pass = True

    # Data Structures: (8.81 + 7.50 + 6.20) / 3 = 7.50
    expected_ds = round((8.81 + 7.50 + 6.20) / 3, 2)
    actual_ds = result["topic_scores"]["Data Structures"]
    if actual_ds == expected_ds:
        print(f"  Data Structures avg : PASS ✓ ({actual_ds})")
    else:
        print(f"  Data Structures avg : FAIL ✗ (got {actual_ds}, expected {expected_ds})")
        all_pass = False

    # Algorithms: (5.76 + 6.40) / 2 = 6.08
    expected_alg = round((5.76 + 6.40) / 2, 2)
    actual_alg = result["topic_scores"]["Algorithms"]
    if actual_alg == expected_alg:
        print(f"  Algorithms avg      : PASS ✓ ({actual_alg})")
    else:
        print(f"  Algorithms avg      : FAIL ✗ (got {actual_alg}, expected {expected_alg})")
        all_pass = False

    # Operating Systems: (3.10 + 1.74) / 2 = 2.42
    expected_os = round((3.10 + 1.74) / 2, 2)
    actual_os = result["topic_scores"]["Operating Systems"]
    if actual_os == expected_os:
        print(f"  Operating Systems avg: PASS ✓ ({actual_os})")
    else:
        print(f"  Operating Systems avg: FAIL ✗ (got {actual_os}, expected {expected_os})")
        all_pass = False

    # Overall: weighted sum / 7 = (7.50×3 + 6.08×2 + 2.42×2) / 7
    expected_overall = round(
        (expected_ds * 3 + expected_alg * 2 + expected_os * 2) / 7, 2
    )
    actual_overall = result["overall_score"]
    if actual_overall == expected_overall:
        print(f"  Overall score       : PASS ✓ ({actual_overall})")
    else:
        print(f"  Overall score       : FAIL ✗ (got {actual_overall}, expected {expected_overall})")
        all_pass = False

    # Edge case — single topic, single question
    single = calculate_session_scores([{"topic": "Networks", "final_score": 9.0}])
    if single["overall_score"] == 9.0 and single["topic_scores"]["Networks"] == 9.0:
        print(f"  Single-question     : PASS ✓ (overall=9.0)")
    else:
        print(f"  Single-question     : FAIL ✗")
        all_pass = False

    print("\n" + "=" * 60)
    print("  ALL PASS ✓" if all_pass else "  SOME TESTS FAILED ✗")
    print("=" * 60)
