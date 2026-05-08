"""
test_phase2_pipeline.py — Phase 2 Deterministic Pipeline Checks
================================================================
Validates critical deterministic Phase 2 behaviors:
  1) source_page_range estimation for PDF-style pages
  2) concept alias extraction from parenthetical forms
  3) rubric generation from source chunks

Run:
    cd backend
    .\\venv\\Scripts\\python.exe test_phase2_pipeline.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.pillar2_nlp.knowledge_concepts import build_concept_bank
from app.services.pillar2_nlp.phase2_pipeline import assign_source_page_ranges
from app.services.pillar2_nlp.rubric_builder import build_rubric

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


print("=" * 60)
print("test_phase2_pipeline.py — Deterministic Phase 2 checks")
print("=" * 60)

# -----------------------------------------------------------------
# Case 1: page-range estimation produces stable page labels
# -----------------------------------------------------------------
print("\nCase 1 — source_page_range mapping")
chunks = [
    {
        "chunk_id": "chunk_1",
        "subject": "Computer Science",
        "topic": "Data Structures",
        "heading": "BST",
        "text": "A binary search tree stores nodes with ordering constraints in left and right subtrees.",
        "word_count": 14,
        "source_page_range": "unknown",
    }
]
pdf_pages = [
    "intro basics and overview of algorithms",
    "binary search tree ordering left subtree right subtree and node placement",
    "hash maps and graph traversals",
]
assign_source_page_ranges(chunks, pdf_pages)
check(
    "chunk_1 page range set to page 2",
    chunks[0]["source_page_range"] == "p2",
    f"got {chunks[0]['source_page_range']}",
)

# -----------------------------------------------------------------
# Case 2: concept aliases capture parenthetical acronym forms
# -----------------------------------------------------------------
print("\nCase 2 — concept aliases")
concept_chunks = [
    {
        "chunk_id": "chunk_1",
        "text": "A Binary Search Tree (BST) maintains ordered keys in a rooted structure.",
    },
    {
        "chunk_id": "chunk_2",
        "text": "In a binary search tree, insert and lookup follow ordering rules.",
    },
]
concept_bank, reverse_index = build_concept_bank(concept_chunks, topic="Data Structures")

bst_entry = None
for concept in concept_bank.get("concepts", []):
    if concept.get("name") == "binary search tree":
        bst_entry = concept
        break

check("binary search tree concept exists", bst_entry is not None)
check(
    "BST alias captured",
    bst_entry is not None and "BST" in bst_entry.get("aliases", []),
    f"aliases={bst_entry.get('aliases', []) if bst_entry else []}",
)
check(
    "reverse index contains binary search tree",
    "binary search tree" in reverse_index,
)

# -----------------------------------------------------------------
# Case 3: rubric generation from selected chunk IDs
# -----------------------------------------------------------------
print("\nCase 3 — rubric generation")
rubric_chunks = [
    {
        "chunk_id": "chunk_1",
        "text": "Binary search trees keep smaller keys on the left and larger keys on the right.",
    },
    {
        "chunk_id": "chunk_2",
        "text": "Balanced trees improve lookup performance and reduce worst-case depth.",
    },
]
phrase_index = {
    "binary search": {"weight": 4.0, "chunk_ids": ["chunk_1"]},
    "balanced trees": {"weight": 3.0, "chunk_ids": ["chunk_2"]},
}
rubric = build_rubric(
    source_chunk_ids=["chunk_1", "chunk_2"],
    chunks=rubric_chunks,
    concept_bank=concept_bank,
    phrase_index=phrase_index,
    evidence_count=2,
)

check("rubric has must_concepts", isinstance(rubric.get("must_concepts"), list))
check("rubric has key_phrases", len(rubric.get("key_phrases", [])) >= 1)
check("rubric has evidence sentences", len(rubric.get("evidence_sentences", [])) >= 1)
check("rubric source_chunk_ids set", rubric.get("source_chunk_ids") == ["chunk_1", "chunk_2"])

print("\n" + "=" * 60)
total = PASS_COUNT + FAIL_COUNT
print(f"  Results: {PASS_COUNT}/{total} checks passed")
if FAIL_COUNT == 0:
    print("  Phase 2 deterministic checks PASS ✓")
    print("=" * 60)
    raise SystemExit(0)

print(f"  {FAIL_COUNT} check(s) failed ✗")
print("=" * 60)
raise SystemExit(1)
