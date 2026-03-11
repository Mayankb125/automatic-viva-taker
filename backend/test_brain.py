"""
test_brain.py — Adaptive Logic Test Suite
==========================================
Simulates all 7 adaptive cases using hardcoded scores.
No API calls, no database. Pure Python only.

Run:
    cd backend
    .\\venv\\Scripts\\python.exe test_brain.py

All 7 cases must print PASS before Phase 3 can begin.
"""

import sys
import os

# Allow imports from backend/ root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.pillar2_nlp.adaptive_logic import make_session_state, process_answer

PASS_COUNT = 0
FAIL_COUNT = 0


def check(label: str, condition: bool, detail: str = ""):
    global PASS_COUNT, FAIL_COUNT
    if condition:
        PASS_COUNT += 1
        print(f"  PASS ✓  {label}")
    else:
        FAIL_COUNT += 1
        print(f"  FAIL ✗  {label}  {detail}")


def fresh_state():
    """Return a clean session state for each test case."""
    return make_session_state(
        session_id="test-session-001",
        student_id="student-001",
        subject="Computer Science",
        topic_list=["Data Structures", "Algorithms", "Operating Systems"],
    )


print("=" * 60)
print("test_brain.py — All 7 Adaptive Cases")
print("=" * 60)

# ─────────────────────────────────────────────────────────────────────────────
# Case 1 — Strong answer → level_up
# Feed score 8.0 on a level 1 question
# Expected: decision = "level_up", current_level = 2
# ─────────────────────────────────────────────────────────────────────────────
print("\nCase 1 — Strong answer → level_up")
state = fresh_state()
level_before = state["current_level"]   # 1
process_answer(state, score=8.0)

check("decision == 'level_up'",    state["decision"] == "level_up")
check("current_level increased",   state["current_level"] == level_before + 1,
      f"got {state['current_level']}, expected {level_before + 1}")
check("state still active",        state["state"] == "active")
check("show_topic_modal is False", state["show_topic_modal"] is False)

# ─────────────────────────────────────────────────────────────────────────────
# Case 2 — Partial answer → follow_up
# Feed score 6.0 on a level 1 question
# Expected: decision = "follow_up", level stays the same
# ─────────────────────────────────────────────────────────────────────────────
print("\nCase 2 — Partial answer → follow_up")
state = fresh_state()
level_before = state["current_level"]   # 1
process_answer(state, score=6.0)

check("decision == 'follow_up'",   state["decision"] == "follow_up")
check("current_level unchanged",   state["current_level"] == level_before,
      f"got {state['current_level']}, expected {level_before}")
check("state still active",        state["state"] == "active")
check("show_topic_modal is False", state["show_topic_modal"] is False)

# ─────────────────────────────────────────────────────────────────────────────
# Case 3 — Weak answer, no checkpoint active → checkpoint
# Feed score 3.0 with checkpoint_asked = False
# Expected: decision = "checkpoint", checkpoint_asked = True
# ─────────────────────────────────────────────────────────────────────────────
print("\nCase 3 — Weak answer → checkpoint")
state = fresh_state()
original_topic = state["current_topic"]
original_level = state["current_level"]
process_answer(state, score=3.0)

check("decision == 'checkpoint'",           state["decision"] == "checkpoint")
check("checkpoint_asked is True",           state["checkpoint_asked"] is True)
check("checkpoint_original_topic saved",    state["checkpoint_original_topic"] == original_topic,
      f"got {state['checkpoint_original_topic']}")
check("checkpoint_original_level saved",    state["checkpoint_original_level"] == original_level,
      f"got {state['checkpoint_original_level']}")
check("show_topic_modal is False",          state["show_topic_modal"] is False)

# ─────────────────────────────────────────────────────────────────────────────
# Case 4 — Checkpoint question answered well → return_to_original
# First feed a weak answer to trigger checkpoint (Case 3)
# Then feed score 8.0 on the checkpoint question
# Expected: decision = "return_to_original", back to original topic, level + 1
# ─────────────────────────────────────────────────────────────────────────────
print("\nCase 4 — Checkpoint passed → return_to_original")
state = fresh_state()
original_topic = state["current_topic"]     # "Data Structures"
original_level = state["current_level"]     # 1

# Step 1: weak answer triggers checkpoint
process_answer(state, score=3.0)
assert state["decision"] == "checkpoint", "Setup failed for Case 4"

# Step 2: checkpoint answered well
process_answer(state, score=8.0)

check("decision == 'return_to_original'",   state["decision"] == "return_to_original")
check("back to original topic",             state["current_topic"] == original_topic,
      f"got '{state['current_topic']}', expected '{original_topic}'")
check("level incremented",                  state["current_level"] == original_level + 1,
      f"got {state['current_level']}, expected {original_level + 1}")
check("checkpoint_asked reset to False",    state["checkpoint_asked"] is False)
check("show_topic_modal is False",          state["show_topic_modal"] is False)

# ─────────────────────────────────────────────────────────────────────────────
# Case 5 — Checkpoint question answered poorly → topic_switch
# First feed weak answer to trigger checkpoint (Case 3)
# Then feed score 2.0 on the checkpoint question
# Expected: decision = "topic_switch", show_topic_modal = True, topic added to switched_topics
# ─────────────────────────────────────────────────────────────────────────────
print("\nCase 5 — Checkpoint failed → topic_switch")
state = fresh_state()
original_topic = state["current_topic"]     # "Data Structures"

# Step 1: weak answer triggers checkpoint
process_answer(state, score=3.0)
assert state["decision"] == "checkpoint", "Setup failed for Case 5"

# Step 2: checkpoint answered poorly
process_answer(state, score=2.0)

check("decision == 'topic_switch'",         state["decision"] == "topic_switch")
check("show_topic_modal is True",           state["show_topic_modal"] is True)
check("original topic in switched_topics",  original_topic in state["switched_topics"],
      f"switched_topics = {state['switched_topics']}")
check("checkpoint_asked reset to False",    state["checkpoint_asked"] is False)

# ─────────────────────────────────────────────────────────────────────────────
# Case 6 — At level 5, strong answer → topic_complete
# Set current_level = 5 manually, then feed score 8.0
# Expected: decision = "topic_complete", state = "completed"
# ─────────────────────────────────────────────────────────────────────────────
print("\nCase 6 — Level 5 strong answer → topic_complete")
state = fresh_state()
state["current_level"] = 5   # manually set to max level
process_answer(state, score=8.0)

check("decision == 'topic_complete'",  state["decision"] == "topic_complete")
check("state == 'completed'",          state["state"] == "completed")
check("show_topic_modal is False",     state["show_topic_modal"] is False)

# ─────────────────────────────────────────────────────────────────────────────
# Case 7 — 15 questions already asked → session_end
# Set total_questions_asked = 14, then feed one more answer
# Expected: decision = "session_end" immediately (limit check runs first)
# ─────────────────────────────────────────────────────────────────────────────
print("\nCase 7 — 15 questions reached → session_end")
state = fresh_state()
state["total_questions_asked"] = 14   # one away from the limit

# Feed any score — session_end should trigger regardless of score
process_answer(state, score=9.0)

check("decision == 'session_end'",  state["decision"] == "session_end")
check("state == 'completed'",       state["state"] == "completed")
check("total_questions == 15",      state["total_questions_asked"] == 15,
      f"got {state['total_questions_asked']}")

# ─────────────────────────────────────────────────────────────────────────────
# Final result
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
total = PASS_COUNT + FAIL_COUNT
print(f"  Results: {PASS_COUNT}/{total} checks passed")
if FAIL_COUNT == 0:
    print("  ALL 7 CASES PASS ✓ — Ready for Phase 3")
else:
    print(f"  {FAIL_COUNT} CHECK(S) FAILED ✗ — Fix before proceeding")
print("=" * 60)
