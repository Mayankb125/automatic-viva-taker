"""
pillar2_nlp/question_generator.py — AI Question Generator
===========================================================
Uses the xAI Grok API to generate exam questions for the viva.

Inputs:
    topic (str)  — The subject topic, e.g. "Data Structures"
    level (int)  — Difficulty level 1–5 (see LEVEL_DESCRIPTORS below)

Output:
    A Python dict with 4 keys:
    {
        "question":        "What is a binary search tree?",
        "expected_answer": "A BST is a tree where...",
        "key_keywords":    ["BST", "left subtree", "right subtree", "inorder"],
        "key_points":      ["define BST", "explain ordering property", "give example"]
    }

Difficulty levels:
    1 — Define/recall        (What is X?)
    2 — Explain/understand   (How does X work?)
    3 — Apply/example        (Use X to solve Y)
    4 — Analyse/compare      (Compare X and Y, explain tradeoffs)
    5 — Evaluate/design      (Design a system using X, justify your choices)

Usage (standalone test):
    python question_generator.py
"""

import json
import re
import time
from difflib import SequenceMatcher
from openai import OpenAI

from app.core.config import GROK_API_KEY, GROK_MODEL, XAI_BASE_URL

# Map difficulty level numbers to natural language descriptors used in the prompt.
# These are sent directly to Grok so the wording matters — be specific.
LEVEL_DESCRIPTORS = {
    1: "basic recall and definition (What is X? Define X.)",
    2: "conceptual understanding and explanation (How does X work? Why is X used?)",
    3: "application and examples (Apply X to solve a problem, give a real example)",
    4: "analysis and comparison (Compare X vs Y, explain tradeoffs, discuss limitations)",
    5: "synthesis and design (Design a system using X, evaluate approaches, justify choices)",
}

FALLBACK_LEVEL_PROMPTS = {
    1: [
        "What is {topic}? Give a simple definition and one example.",
        "Define {topic} in your own words and mention one practical use.",
        "Explain the core idea of {topic} with a short example scenario.",
    ],
    2: [
        "How does {topic} work? Explain the main idea step by step.",
        "Describe the workflow of {topic} and why each step matters.",
        "When would you use {topic}, and how does it operate in practice?",
    ],
    3: [
        "Why is {topic} useful? Compare it with a basic alternative.",
        "Apply {topic} to a small problem and explain your approach.",
        "Give a concrete use case for {topic} and justify why it fits.",
    ],
    4: [
        "Describe a real-world use case of {topic} and discuss trade-offs.",
        "Compare {topic} with a similar approach and explain key trade-offs.",
        "Analyse limitations of {topic} and suggest where it still performs well.",
    ],
    5: [
        "Design an advanced approach using {topic} and discuss edge cases.",
        "Propose a robust design using {topic} and justify major decisions.",
        "How would you optimise a system built on {topic} for scale and reliability?",
    ],
}


def _normalize_question_text(text: str) -> str:
    """Normalize question text for robust near-duplicate checks."""
    lowered = (text or "").strip().lower()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def is_question_too_similar(
    question_text: str,
    recent_questions: list[str] | None = None,
    similarity_threshold: float = 0.88,
) -> bool:
    """Return True when a candidate question is too close to recent questions."""
    if not question_text or not recent_questions:
        return False

    candidate = _normalize_question_text(question_text)
    if not candidate:
        return False

    for recent in recent_questions:
        normalized_recent = _normalize_question_text(recent)
        if not normalized_recent:
            continue

        if candidate == normalized_recent:
            return True

        if len(candidate) > 24 and (candidate in normalized_recent or normalized_recent in candidate):
            return True

        if SequenceMatcher(None, candidate, normalized_recent).ratio() >= similarity_threshold:
            return True

    return False


def _topic_keywords(topic: str) -> list[str]:
    """Create a small keyword list from topic words plus core viva terms."""
    tokens = [word.strip() for word in re.split(r"[^A-Za-z0-9]+", topic) if word.strip()]
    deduped = []
    for token in tokens:
        lower = token.lower()
        if lower not in deduped:
            deduped.append(lower)

    base = deduped[:4]
    extras = ["definition", "working", "example", "limitations"]
    for item in extras:
        if item not in base:
            base.append(item)

    return base[:6]


def generate_fallback_question(
    topic: str,
    level: int,
    recent_questions: list[str] | None = None,
) -> dict:
    """
    Build a deterministic local question payload when Grok is unavailable.

    This keeps the viva session moving during temporary LLM outages.
    """
    level = max(1, min(5, level))
    templates = FALLBACK_LEVEL_PROMPTS[level]

    # Rotate candidate order so fallback does not keep repeating a single phrase.
    offset = (len(recent_questions or []) + len(topic)) % len(templates)
    ordered_templates = templates[offset:] + templates[:offset]

    question = ordered_templates[0].format(topic=topic)
    for template in ordered_templates:
        candidate_question = template.format(topic=topic)
        if not is_question_too_similar(candidate_question, recent_questions):
            question = candidate_question
            break

    expected_answer = (
        f"A strong answer should define {topic}, explain how it works, "
        "cover key concepts clearly, and include at least one practical example "
        "with limitations or trade-offs where relevant."
    )

    key_points = [
        f"Clear definition of {topic}",
        f"Core mechanism or workflow of {topic}",
        f"Practical example or application of {topic}",
    ]
    if level >= 4:
        key_points.append(f"Trade-offs and limitations of {topic}")

    return {
        "question": question,
        "expected_answer": expected_answer,
        "key_keywords": _topic_keywords(topic),
        "key_points": key_points,
    }


def generate_question(
    topic: str,
    level: int,
    recent_questions: list[str] | None = None,
) -> dict:
    """
    Generate one exam question for the given topic at the given difficulty level.

    Args:
        topic: Subject topic string, e.g. "Data Structures", "Operating Systems"
        level: Integer 1–5. Controls how deep/complex the question is.

    Returns:
        Dict with keys: question, expected_answer, key_keywords, key_points
        All values are strings or lists of strings.

    Raises:
        ValueError: If the Grok response is not valid JSON.
        RuntimeError: If GROK_API_KEY is missing from .env.
    """
    api_key = GROK_API_KEY.strip()
    if not api_key:
        raise RuntimeError(
            "GROK_API_KEY is not set. Add it to backend/.env file.\n"
            "Example: GROK_API_KEY=xai-..."
        )

    # Create the Grok client using xAI's OpenAI-compatible endpoint.
    client = OpenAI(api_key=api_key, base_url=XAI_BASE_URL)

    # Clamp level to valid range just in case adaptive logic sends an out-of-range value
    level = max(1, min(5, level))
    level_description = LEVEL_DESCRIPTORS[level]

    recent_constraints = ""
    if recent_questions:
        trimmed_recent = [q.strip() for q in recent_questions if q and q.strip()][:5]
        if trimmed_recent:
            recent_constraints = "\nAvoid repeating or lightly rephrasing these recent questions:\n"
            recent_constraints += "\n".join(f"- {q}" for q in trimmed_recent)

    # The prompt asks Grok to return ONLY a JSON object — no markdown, no extra text.
    # This makes it safe to call json.loads() directly on the response.
    prompt = f"""You are an examiner conducting an oral exam on the topic: "{topic}".

Generate ONE exam question at difficulty level {level} ({level_description}).
{recent_constraints}

Respond with ONLY a JSON object (no markdown, no code blocks, no extra text):
{{
    "question": "The exam question to ask the student",
    "expected_answer": "A detailed ideal answer (3-5 sentences)",
    "key_keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
    "key_points": ["key point 1", "key point 2", "key point 3"]
}}

Rules:
- question must be a single clear sentence ending with ?
- expected_answer must be 3-5 complete sentences
- key_keywords: 4-6 important domain terms the student should mention
- key_points: 3-5 core concepts that a good answer must cover
- All values must be in English
- Do NOT include any text outside the JSON object"""

    # Use configured Grok model via chat completions endpoint.
    response = client.chat.completions.create(
        model=GROK_MODEL,
        messages=[
            {"role": "system", "content": "You are a strict JSON-only assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    raw_text = (response.choices[0].message.content or "").strip()

    # Strip markdown code fences if Grok wraps the JSON anyway (defensive)
    # e.g. ```json { ... } ``` -> { ... }
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Grok returned non-JSON response.\n"
            f"Raw response: {raw_text}\n"
            f"JSON error: {e}"
        )

    # Validate all 4 required keys are present before returning
    required_keys = {"question", "expected_answer", "key_keywords", "key_points"}
    missing = required_keys - set(result.keys())
    if missing:
        raise ValueError(f"Grok response is missing keys: {missing}. Got: {result}")

    if is_question_too_similar(result.get("question", ""), recent_questions):
        raise ValueError("Generated question is too similar to a recently asked question")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Standalone test — run this file directly to verify the generator works:
#   cd backend
#   .\venv\Scripts\python.exe app/services/pillar2_nlp/question_generator.py
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    TEST_TOPIC = "Data Structures"

    print("=" * 60)
    print(f"Testing question_generator.py — topic: {TEST_TOPIC}")
    print("=" * 60)

    for level in range(1, 6):
        print(f"\n--- Level {level} ---")
        try:
            result = generate_question(TEST_TOPIC, level)
            print(f"  Question    : {result['question']}")
            print(f"  Keywords    : {result['key_keywords']}")
            print(f"  Key Points  : {result['key_points']}")
            print(f"  Exp. Answer : {result['expected_answer'][:80]}...")
            print(f"  STATUS: PASS ✓")
        except Exception as e:
            print(f"  STATUS: FAIL ✗ — {e}")

        # Wait 5 seconds between requests to stay within free tier rate limit (15 RPM)
        if level < 5:
            time.sleep(5)

    print("\n" + "=" * 60)
    print("All 5 levels tested.")
