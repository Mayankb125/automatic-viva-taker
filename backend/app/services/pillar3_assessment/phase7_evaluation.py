"""Phase 7 evaluation helpers.

These utilities compute the metrics called out in the Phase 7 plan:

- mean absolute error (MAE)
- Spearman rank correlation
- band confusion matrices
- teacher preference summaries

The helpers are framework-agnostic so they can be reused by an API route,
CLI script, or notebook.
"""

from __future__ import annotations

from collections import Counter
from math import sqrt
from statistics import mean
from typing import Iterable, Sequence


DEFAULT_BAND_ORDER = ["weak", "partial", "strong"]


def compute_mae(predicted_scores: Sequence[float | None], teacher_scores: Sequence[float | None]) -> float | None:
    """Return the mean absolute error for two aligned score series."""
    pairs = [
        (float(predicted), float(teacher))
        for predicted, teacher in zip(predicted_scores, teacher_scores)
        if predicted is not None and teacher is not None
    ]
    if not pairs:
        return None
    return round(mean(abs(predicted - teacher) for predicted, teacher in pairs), 4)


def _rank(values: Sequence[float]) -> list[float]:
    """Assign average ranks while preserving ties."""
    indexed_values = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    index = 0

    while index < len(indexed_values):
        tie_end = index
        tie_value = indexed_values[index][1]
        while tie_end < len(indexed_values) and indexed_values[tie_end][1] == tie_value:
            tie_end += 1

        average_rank = (index + 1 + tie_end) / 2.0
        for tied_index in range(index, tie_end):
            original_position = indexed_values[tied_index][0]
            ranks[original_position] = average_rank

        index = tie_end

    return ranks


def compute_spearman(predicted_scores: Sequence[float | None], teacher_scores: Sequence[float | None]) -> float | None:
    """Return Spearman rank correlation for two aligned score series."""
    pairs = [
        (float(predicted), float(teacher))
        for predicted, teacher in zip(predicted_scores, teacher_scores)
        if predicted is not None and teacher is not None
    ]
    if len(pairs) < 2:
        return None

    predicted_values = [item[0] for item in pairs]
    teacher_values = [item[1] for item in pairs]
    predicted_ranks = _rank(predicted_values)
    teacher_ranks = _rank(teacher_values)

    mean_predicted = mean(predicted_ranks)
    mean_teacher = mean(teacher_ranks)
    covariance = sum(
        (predicted_rank - mean_predicted) * (teacher_rank - mean_teacher)
        for predicted_rank, teacher_rank in zip(predicted_ranks, teacher_ranks)
    )
    predicted_variance = sum((value - mean_predicted) ** 2 for value in predicted_ranks)
    teacher_variance = sum((value - mean_teacher) ** 2 for value in teacher_ranks)

    if predicted_variance == 0 or teacher_variance == 0:
        return None

    return round(covariance / sqrt(predicted_variance * teacher_variance), 4)


def build_band_confusion_matrix(
    predicted_bands: Sequence[str | None],
    teacher_bands: Sequence[str | None],
    band_order: Sequence[str] | None = None,
) -> dict:
    """Build a confusion matrix for band labels."""
    ordered_bands = [band.lower() for band in (band_order or DEFAULT_BAND_ORDER)]
    matrix = {
        actual: {predicted: 0 for predicted in ordered_bands}
        for actual in ordered_bands
    }

    for predicted_band, teacher_band in zip(predicted_bands, teacher_bands):
        if not predicted_band or not teacher_band:
            continue

        predicted_key = str(predicted_band).lower()
        teacher_key = str(teacher_band).lower()

        if teacher_key not in matrix:
            matrix[teacher_key] = {predicted: 0 for predicted in ordered_bands}
        if predicted_key not in matrix[teacher_key]:
            for row in matrix.values():
                row.setdefault(predicted_key, 0)

        matrix[teacher_key][predicted_key] += 1

    return matrix


def summarize_teacher_preferences(preferences: Iterable[str | None]) -> dict:
    """Count teacher choices across pipeline outputs."""
    cleaned_preferences = [str(choice).strip().lower() for choice in preferences if choice]
    counts = Counter(cleaned_preferences)

    return {
        "legacy": counts.get("legacy", 0),
        "grounded": counts.get("grounded", 0),
        "tie": counts.get("tie", 0),
        "other": sum(count for key, count in counts.items() if key not in {"legacy", "grounded", "tie"}),
        "total": len(cleaned_preferences),
    }


def build_evaluation_summary(records: Sequence[dict]) -> dict:
    """Build the Phase 7 evaluation summary from labeled answer records."""
    teacher_scores = [record.get("teacher_score") for record in records]
    legacy_scores = [record.get("legacy_score") for record in records]
    grounded_scores = [record.get("grounded_score") for record in records]

    teacher_bands = [record.get("teacher_band") for record in records]
    legacy_bands = [record.get("legacy_band") for record in records]
    grounded_bands = [record.get("grounded_band") for record in records]
    preferences = [record.get("teacher_preference") for record in records]

    return {
        "sample_count": len(records),
        "legacy_mae": compute_mae(legacy_scores, teacher_scores),
        "grounded_mae": compute_mae(grounded_scores, teacher_scores),
        "legacy_spearman": compute_spearman(legacy_scores, teacher_scores),
        "grounded_spearman": compute_spearman(grounded_scores, teacher_scores),
        "band_confusion": {
            "legacy": build_band_confusion_matrix(legacy_bands, teacher_bands),
            "grounded": build_band_confusion_matrix(grounded_bands, teacher_bands),
        },
        "teacher_preference_summary": summarize_teacher_preferences(preferences),
        "targets": {
            "mae": 1.5,
            "spearman": 0.75,
            "band_agreement": 0.8,
        },
    }


if __name__ == "__main__":
    demo_records = [
        {
            "teacher_score": 8.0,
            "legacy_score": 7.5,
            "grounded_score": 8.2,
            "teacher_band": "strong",
            "legacy_band": "partial",
            "grounded_band": "strong",
            "teacher_preference": "grounded",
        },
        {
            "teacher_score": 4.0,
            "legacy_score": 5.0,
            "grounded_score": 4.3,
            "teacher_band": "weak",
            "legacy_band": "partial",
            "grounded_band": "weak",
            "teacher_preference": "grounded",
        },
        {
            "teacher_score": 6.0,
            "legacy_score": 6.2,
            "grounded_score": 5.8,
            "teacher_band": "partial",
            "legacy_band": "partial",
            "grounded_band": "partial",
            "teacher_preference": "tie",
        },
    ]

    print(build_evaluation_summary(demo_records))