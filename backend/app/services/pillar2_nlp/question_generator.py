"""
pillar2_nlp/question_generator.py — AI Question Generator
===========================================================
Uses the Google Gemini API to generate exam questions for the viva.

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
from google import genai

from app.core.config import GEMINI_API_KEY

# Map difficulty level numbers to natural language descriptors used in the prompt.
# These are sent directly to Gemini so the wording matters — be specific.
LEVEL_DESCRIPTORS = {
    1: "basic recall and definition (What is X? Define X.)",
    2: "conceptual understanding and explanation (How does X work? Why is X used?)",
    3: "application and examples (Apply X to solve a problem, give a real example)",
    4: "analysis and comparison (Compare X vs Y, explain tradeoffs, discuss limitations)",
    5: "synthesis and design (Design a system using X, evaluate approaches, justify choices)",
}

FALLBACK_LEVEL_PROMPTS = {
    1: "What is {topic}? Give a simple definition and one example.",
    2: "How does {topic} work? Explain the main idea step by step.",
    3: "Why is {topic} useful? Compare it with a basic alternative.",
    4: "Describe a real-world use case of {topic} and discuss trade-offs.",
    5: "Design an advanced approach using {topic} and discuss edge cases.",
}


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


def generate_fallback_question(topic: str, level: int) -> dict:
    """
    Build a deterministic local question payload when Gemini is unavailable.

    This keeps the viva session moving during temporary LLM outages.
    """
    level = max(1, min(5, level))
    question = FALLBACK_LEVEL_PROMPTS[level].format(topic=topic)

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


def generate_question(topic: str, level: int) -> dict:
    """
    Generate one exam question for the given topic at the given difficulty level.

    Args:
        topic: Subject topic string, e.g. "Data Structures", "Operating Systems"
        level: Integer 1–5. Controls how deep/complex the question is.

    Returns:
        Dict with keys: question, expected_answer, key_keywords, key_points
        All values are strings or lists of strings.

    Raises:
        ValueError: If the Gemini response is not valid JSON.
        RuntimeError: If GEMINI_API_KEY is missing from .env.
    """
    api_key = GEMINI_API_KEY.strip()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to backend/.env file.\n"
            "Example: GEMINI_API_KEY=AIza..."
        )

    # Create the Gemini client with the API key from .env
    client = genai.Client(api_key=api_key)

    # Clamp level to valid range just in case adaptive logic sends an out-of-range value
    level = max(1, min(5, level))
    level_description = LEVEL_DESCRIPTORS[level]

    # The prompt asks Gemini to return ONLY a JSON object — no markdown, no extra text.
    # This makes it safe to call json.loads() directly on the response.
    prompt = f"""You are an examiner conducting an oral exam on the topic: "{topic}".

Generate ONE exam question at difficulty level {level} ({level_description}).

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

    # Use gemini-2.5-flash — latest stable model, fast, high quality structured output
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    raw_text = response.text.strip()

    # Strip markdown code fences if Gemini wraps the JSON anyway (defensive)
    # e.g. ```json { ... } ``` -> { ... }
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Gemini returned non-JSON response.\n"
            f"Raw response: {raw_text}\n"
            f"JSON error: {e}"
        )

    # Validate all 4 required keys are present before returning
    required_keys = {"question", "expected_answer", "key_keywords", "key_points"}
    missing = required_keys - set(result.keys())
    if missing:
        raise ValueError(f"Gemini response is missing keys: {missing}. Got: {result}")

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
