"""
Phase 1 schema migration for rubric-based scoring.

Adds new nullable columns to existing SQLite tables without dropping data.
Safe to run multiple times.

Run:
    cd backend
    .\\venv\\Scripts\\python.exe migrate_phase1_schema.py
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "database.db"


QUESTION_COLUMNS = [
    ("source_chunk_ids", "TEXT"),
    ("rubric_json", "TEXT"),
    ("pipeline_mode", "TEXT"),
    ("generation_mode", "TEXT"),
    ("rubric_version", "TEXT"),
]


SCORE_COLUMNS = [
    ("legacy_score_json", "TEXT"),
    ("grounded_score_json", "TEXT"),
    ("scoring_version", "TEXT"),
    ("scoring_mode", "TEXT"),
    ("raw_weighted_score", "FLOAT"),
    ("total_penalty", "FLOAT"),
    ("level_bonus_applied", "FLOAT"),
    ("score_band", "TEXT"),
    ("feature_breakdown_json", "TEXT"),
    ("penalties_json", "TEXT"),
    ("flags_json", "TEXT"),
    ("matched_must_concepts_json", "TEXT"),
    ("missing_must_concepts_json", "TEXT"),
    ("matched_optional_concepts_json", "TEXT"),
    ("matched_phrases_json", "TEXT"),
    ("missing_phrases_json", "TEXT"),
    ("rubric_snapshot_json", "TEXT"),
    ("feedback_summary", "TEXT"),
    ("recommendation", "TEXT"),
]


SESSION_COLUMNS = [
    ("pipeline_mode", "TEXT"),
]


def get_existing_columns(cursor: sqlite3.Cursor, table_name: str) -> set[str]:
    rows = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def add_missing_columns(cursor: sqlite3.Cursor, table_name: str, columns: list[tuple[str, str]]) -> None:
    existing = get_existing_columns(cursor, table_name)

    for col_name, col_type in columns:
        if col_name in existing:
            print(f"[skip] {table_name}.{col_name} already exists")
            continue

        sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"
        cursor.execute(sql)
        print(f"[add ] {table_name}.{col_name} ({col_type})")


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        add_missing_columns(cur, "questions", QUESTION_COLUMNS)
        add_missing_columns(cur, "scores", SCORE_COLUMNS)
        add_missing_columns(cur, "sessions", SESSION_COLUMNS)
        conn.commit()
        print("\nPhase 1 schema migration completed successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
