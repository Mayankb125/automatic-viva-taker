"""
pillar2_nlp/adaptive_logic.py — Adaptive Viva Logic Engine
===========================================================
Decides what happens after every answer the student gives.
This is the brain of the entire viva system.

Session State (dict passed in and returned updated):
  session_id                 : str   — unique session identifier
  student_id                 : str   — student identifier
  subject                    : str   — e.g. "Computer Science"
  topic_list                 : list  — all topics selected e.g. ["Data Structures", "Algorithms"]
  current_topic              : str   — topic currently being questioned
  current_level              : int   — difficulty level 1–5
  checkpoint_asked           : bool  — True if a checkpoint question is currently active
  checkpoint_original_topic  : str   — topic to return to after checkpoint resolves
  checkpoint_original_level  : int   — level to resume from after checkpoint resolves
  questions_on_current_topic : int   — count of questions asked on current_topic
  switched_topics            : list  — topics the student has already switched away from
  total_questions_asked      : int   — total across all topics (hard limit = 15)
  state                      : str   — "active" | "completed"
  topic_scores               : dict  — { topic: [score1, score2, ...] }
  question_history           : list  — list of past question identifiers
    weak_attempt_streak        : int   — consecutive weak answers at current topic/level

Decision Logic (evaluated in this strict order every time):
  1. total_questions_asked >= 15              → session_end
  2. checkpoint_asked AND score >= 7.0        → return_to_original (level up)
  3. checkpoint_asked AND score <  7.0        → topic_switch (show modal)
  4. current_level == 5 AND score >= 7.0      → topic_complete
  5. score >= 7.0                             → level_up
  6. score >= 5.0                             → follow_up
    7. first weak answer                         → retry_same_level
    8. repeated weak answer                      → checkpoint

Score thresholds:
    >= 6.5 = strong  → advance
    4.5–6.49 = partial → follow up same level
    < 4.5  = weak   → retry same level once, then checkpoint
"""

# ── Score thresholds ──────────────────────────────────────────────────────────
STRONG_THRESHOLD   = 6.5   # score >= this → level up or complete
PARTIAL_THRESHOLD  = 4.5   # score >= this → follow-up question
CHECKPOINT_PASS    = 6.5   # checkpoint score >= this → return to original topic
MAX_QUESTIONS      = 15    # hard session limit — session ends at this count


def make_session_state(
    session_id: str,
    student_id: str,
    subject: str,
    topic_list: list,
) -> dict:
    """
    Create a fresh session state dict for a new viva session.

    Args:
        session_id: Unique ID for this session.
        student_id: Student's ID.
        subject:    The broad subject (e.g. "Computer Science").
        topic_list: All topics the student selected. First topic is used to start.

    Returns:
        A fully initialised session_state dict ready for the first question.
    """
    first_topic = topic_list[0]
    return {
        "session_id":                 session_id,
        "student_id":                 student_id,
        "subject":                    subject,
        "topic_list":                 list(topic_list),
        "current_topic":              first_topic,
        "current_level":              1,
        "checkpoint_asked":           False,
        "checkpoint_original_topic":  first_topic,
        "checkpoint_original_level":  1,
        "questions_on_current_topic": 0,
        "switched_topics":            [],
        "total_questions_asked":      0,
        "state":                      "active",
        "topic_scores":               {first_topic: []},
        "question_history":           [],
        "weak_attempt_streak":        0,
        "show_topic_modal":           False,
        "decision":                   None,
    }


def process_answer(session_state: dict, score: float) -> dict:
    """
    Update session state after an answer is scored and decide what to do next.

    Called AFTER every answer is evaluated by answer_evaluator.py.
    Mutates session_state in place and returns it.

    Args:
        session_state: The current session state dict.
        score:         The final_score from answer_evaluator.py (0.0–10.0).

    Returns:
        Updated session_state with:
            decision         — what to do next (string, see below)
            show_topic_modal — True only when decision is "topic_switch"

    Decision values:
        "session_end"        — 15 questions reached, session is over
        "return_to_original" — checkpoint passed, back to main topic, level up
        "topic_switch"       — checkpoint failed, student must pick new topic
        "topic_complete"     — reached level 5 with strong answer, topic done
        "level_up"           — strong answer, increase difficulty
        "follow_up"          — partial answer, ask clarifying question same level
        "retry_same_level"   — weak answer once, ask a new question at same level
        "checkpoint"         — weak answer, ask prerequisite question on related topic
    """
    current_topic = session_state["current_topic"]
    weak_attempt_streak = int(session_state.get("weak_attempt_streak", 0) or 0)
    session_state["weak_attempt_streak"] = weak_attempt_streak

    # ── Record this score ─────────────────────────────────────────────────────
    if current_topic not in session_state["topic_scores"]:
        session_state["topic_scores"][current_topic] = []
    session_state["topic_scores"][current_topic].append(score)

    # ── Increment counters ────────────────────────────────────────────────────
    session_state["total_questions_asked"] += 1
    session_state["questions_on_current_topic"] += 1
    session_state["show_topic_modal"] = False  # reset each time

    # ══ Decision tree (strict priority order) ════════════════════════════════

    # Case 7 — Hard session limit
    if session_state["total_questions_asked"] >= MAX_QUESTIONS:
        session_state["state"] = "completed"
        session_state["decision"] = "session_end"
        return session_state

    # Cases 4 & 5 — Checkpoint resolution (checkpoint was active)
    if session_state["checkpoint_asked"]:
        session_state["weak_attempt_streak"] = 0
        if score >= CHECKPOINT_PASS:
            # Case 4 — Checkpoint passed: return to original topic, level up
            session_state["checkpoint_asked"] = False
            session_state["current_topic"] = session_state["checkpoint_original_topic"]
            session_state["current_level"] = min(5, session_state["checkpoint_original_level"] + 1)
            session_state["questions_on_current_topic"] = 0
            # Ensure topic_scores has an entry for the topic we're returning to
            if session_state["current_topic"] not in session_state["topic_scores"]:
                session_state["topic_scores"][session_state["current_topic"]] = []
            session_state["decision"] = "return_to_original"
        else:
            # Case 5 — Checkpoint failed: student must switch to a different topic
            session_state["checkpoint_asked"] = False
            session_state["switched_topics"].append(current_topic)
            session_state["show_topic_modal"] = True
            session_state["decision"] = "topic_switch"
        return session_state

    # Case 6 — Topic complete (max level + strong answer)
    if session_state["current_level"] >= 5 and score >= STRONG_THRESHOLD:
        session_state["weak_attempt_streak"] = 0
        session_state["state"] = "completed"
        session_state["decision"] = "topic_complete"
        return session_state

    # Case 1 — Strong answer: level up
    if score >= STRONG_THRESHOLD:
        session_state["weak_attempt_streak"] = 0
        session_state["current_level"] = min(5, session_state["current_level"] + 1)
        session_state["decision"] = "level_up"
        return session_state

    # Case 2 — Partial answer: follow-up at same level
    if score >= PARTIAL_THRESHOLD:
        session_state["weak_attempt_streak"] = 0
        session_state["decision"] = "follow_up"
        return session_state

    # Case 3 — First weak answer: keep same level and ask a different question.
    if weak_attempt_streak < 1:
        session_state["weak_attempt_streak"] = weak_attempt_streak + 1
        session_state["decision"] = "retry_same_level"
        return session_state

    # Case 4 — Repeated weak answer: move to checkpoint flow.
    session_state["weak_attempt_streak"] = 0
    session_state["checkpoint_asked"] = True
    session_state["checkpoint_original_topic"] = current_topic
    session_state["checkpoint_original_level"] = session_state["current_level"]
    session_state["current_level"] = max(1, session_state["current_level"] - 1)
    session_state["decision"] = "checkpoint"
    return session_state
