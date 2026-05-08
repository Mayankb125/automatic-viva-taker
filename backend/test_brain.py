"""
test_brain.py — Adaptive Logic Test Suite
==========================================
Simulates all 7 adaptive cases using hardcoded scores.
No API calls, no database. Pure Python only.

Run:
    cd backend
    .\\venv\\Scripts\\python.exe test_brain.py

Includes Phase 4 routing and score-policy checks.
"""

import sys
import os

# Allow imports from backend/ root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.pillar2_nlp.adaptive_logic import make_session_state, process_answer
from app.services.pillar3_assessment.dual_pipeline.pipeline_router import select_active_mode_result
from app.services.pillar3_assessment.dual_pipeline.session_mode import resolve_pipeline_mode
from app.services.pillar3_assessment.grounded_pipeline.grounded_scoring import finalize_grounded_score

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
print("test_brain.py — Adaptive + Phase 4 Regression")
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
# Case 3 — First weak answer → retry_same_level
# Feed score 3.0 with checkpoint_asked = False
# Expected: decision = "retry_same_level", checkpoint_asked = False
# ─────────────────────────────────────────────────────────────────────────────
print("\nCase 3 — First weak answer → retry_same_level")
state = fresh_state()
original_topic = state["current_topic"]
original_level = state["current_level"]
process_answer(state, score=3.0)

check("decision == 'retry_same_level'",     state["decision"] == "retry_same_level")
check("checkpoint_asked is False",          state["checkpoint_asked"] is False)
check("checkpoint_original_topic saved",    state["checkpoint_original_topic"] == original_topic,
      f"got {state['checkpoint_original_topic']}")
check("checkpoint_original_level saved",    state["checkpoint_original_level"] == original_level,
      f"got {state['checkpoint_original_level']}")
check("show_topic_modal is False",          state["show_topic_modal"] is False)

# ─────────────────────────────────────────────────────────────────────────────
# Case 4 — Checkpoint question answered well → return_to_original
# First feed weak answer to trigger retry
# Then feed weak answer again to trigger checkpoint
# Then feed score 8.0 on the checkpoint question
# Expected: decision = "return_to_original", back to original topic, level + 1
# ─────────────────────────────────────────────────────────────────────────────
print("\nCase 4 — Checkpoint passed → return_to_original")
state = fresh_state()
original_topic = state["current_topic"]     # "Data Structures"
original_level = state["current_level"]     # 1

# Step 1: first weak answer triggers retry_same_level
process_answer(state, score=3.0)
assert state["decision"] == "retry_same_level", "Setup step 1 failed for Case 4"

# Step 2: repeated weak answer triggers checkpoint
process_answer(state, score=3.0)
assert state["decision"] == "checkpoint", "Setup step 2 failed for Case 4"

# Step 3: checkpoint answered well
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
# First feed weak answer to trigger retry
# Then feed weak answer again to trigger checkpoint
# Then feed score 2.0 on the checkpoint question
# Expected: decision = "topic_switch", show_topic_modal = True, topic added to switched_topics
# ─────────────────────────────────────────────────────────────────────────────
print("\nCase 5 — Checkpoint failed → topic_switch")
state = fresh_state()
original_topic = state["current_topic"]     # "Data Structures"

# Step 1: first weak answer triggers retry_same_level
process_answer(state, score=3.0)
assert state["decision"] == "retry_same_level", "Setup step 1 failed for Case 5"

# Step 2: repeated weak answer triggers checkpoint
process_answer(state, score=3.0)
assert state["decision"] == "checkpoint", "Setup step 2 failed for Case 5"

# Step 3: checkpoint answered poorly
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
# Phase 4 — Routing mode resolution and active result selection
# ─────────────────────────────────────────────────────────────────────────────
print("\nPhase 4A — Routing mode resolution")

check(
      "session mode wins when valid",
      resolve_pipeline_mode("grounded_only", "legacy_only") == "grounded_only",
)
check(
      "question mode used when session missing",
      resolve_pipeline_mode(None, "legacy_only") == "legacy_only",
)
check(
      "alias mode normalized to dual_compare",
      resolve_pipeline_mode("llm_generated", None) == "dual_compare",
)

legacy_mock = {
      "semantic_score": 0.5,
      "keyword_score": 6.2,
      "depth_score": 6.0,
      "completeness_score": 5.8,
      "confidence_score": 6.5,
      "weighted_score": 5.9,
      "level_bonus": 0.5,
      "switch_penalty": 0.0,
      "final_score": 6.4,
      "depth_reason": "legacy-depth",
      "completeness_reason": "legacy-complete",
}

grounded_mock = {
      "semantic_score": 6.8,
      "keyword_score": 6.4,
      "depth_score": 6.1,
      "completeness_score": 6.6,
      "confidence_score": 6.2,
      "weighted_score": 6.3,
      "level_bonus": 0.5,
      "switch_penalty": 0.0,
      "final_score": 6.8,
      "score_band": "partial",
      "depth_reason": "grounded-depth",
      "completeness_reason": "grounded-complete",
      "feedback_summary": "grounded-summary",
      "recommendation": "grounded-rec",
}

active_legacy = select_active_mode_result(
      pipeline_mode="legacy_only",
      legacy_result=legacy_mock,
      grounded_result=grounded_mock,
)
check("legacy_only selects legacy", active_legacy["mode"] == "legacy_only")
check("legacy_only final score propagated", active_legacy["final_score"] == legacy_mock["final_score"])

active_grounded = select_active_mode_result(
      pipeline_mode="grounded_only",
      legacy_result=legacy_mock,
      grounded_result=grounded_mock,
)
check("grounded_only selects grounded", active_grounded["mode"] == "grounded_only")
check("grounded_only final score propagated", active_grounded["final_score"] == grounded_mock["final_score"])

active_compare = select_active_mode_result(
      pipeline_mode="dual_compare",
      legacy_result=legacy_mock,
      grounded_result=grounded_mock,
      dual_compare_policy="score_max",
)
check("dual_compare score_max picks higher score", active_compare["mode"] == "grounded_only")

# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — Score policy checks: level bonus, switch penalty, score band
# ─────────────────────────────────────────────────────────────────────────────
print("\nPhase 4B — Score policy checks")

base_components = {
      "semantic_score": 6.0,
      "keyword_score": 6.0,
      "completeness_score": 6.0,
      "depth_score": 6.0,
      "confidence_score": 6.0,
}

level_1 = finalize_grounded_score(base_components, total_penalty=0.0, current_level=1, switched=False)
level_3 = finalize_grounded_score(base_components, total_penalty=0.0, current_level=3, switched=False)

check("level bonus at level 1 is 0.0", level_1["level_bonus"] == 0.0)
check("level bonus at level 3 is +1.0", level_3["level_bonus"] == 1.0)
check(
      "higher level increases final score",
      level_3["final_score"] > level_1["final_score"],
      f"level1={level_1['final_score']} level3={level_3['final_score']}",
)

switch_off = finalize_grounded_score(base_components, total_penalty=0.0, current_level=2, switched=False)
switch_on = finalize_grounded_score(base_components, total_penalty=0.0, current_level=2, switched=True)
check("switch penalty applied is 1.0", switch_on["switch_penalty"] == 1.0)
check(
      "switch penalty lowers final score",
      switch_on["final_score"] < switch_off["final_score"],
      f"off={switch_off['final_score']} on={switch_on['final_score']}",
)

strong_band = finalize_grounded_score(
      {
            "semantic_score": 8.0,
            "keyword_score": 8.0,
            "completeness_score": 8.0,
            "depth_score": 8.0,
            "confidence_score": 8.0,
      },
      total_penalty=0.0,
      current_level=1,
      switched=False,
)
weak_band = finalize_grounded_score(
      {
            "semantic_score": 2.0,
            "keyword_score": 2.0,
            "completeness_score": 2.0,
            "depth_score": 2.0,
            "confidence_score": 2.0,
      },
      total_penalty=0.0,
      current_level=1,
      switched=False,
)
check("strong band threshold works", strong_band["score_band"] == "strong")
check("weak band threshold works", weak_band["score_band"] == "weak")

# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — Legacy vs grounded comparison checks
# ─────────────────────────────────────────────────────────────────────────────
print("\nPhase 4C — Legacy vs grounded comparison")

legacy_higher = {**legacy_mock, "final_score": 7.1}
grounded_lower = {**grounded_mock, "final_score": 6.0}
active_compare_2 = select_active_mode_result(
      pipeline_mode="dual_compare",
      legacy_result=legacy_higher,
      grounded_result=grounded_lower,
      dual_compare_policy="score_max",
)
check("dual_compare can pick legacy when higher", active_compare_2["mode"] == "legacy_only")
check("picked score equals highest candidate", active_compare_2["final_score"] == 7.1)

# ─────────────────────────────────────────────────────────────────────────────
# Final result
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
total = PASS_COUNT + FAIL_COUNT
print(f"  Results: {PASS_COUNT}/{total} checks passed")
if FAIL_COUNT == 0:
      print("  Adaptive + Phase 4 regression checks PASS")
      print("=" * 60)
      sys.exit(0)
else:
      print(f"  {FAIL_COUNT} CHECK(S) FAILED - Fix before proceeding")
      print("=" * 60)
      sys.exit(1)
