"""Evaluation metrics for an imbalanced binary classifier, in plain numpy.

Fraud is rare, so ROC AUC flatters a model; average precision (area under the
precision-recall curve) and recall at a fixed precision are the numbers that
decide promotion. No scikit-learn, to keep the container small.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.floating[Any]]


def _sorted(labels: FloatArray, scores: FloatArray) -> tuple[FloatArray, FloatArray]:
    order = np.argsort(-scores, kind="mergesort")
    return labels[order], scores[order]


def roc_auc(labels: FloatArray, scores: FloatArray) -> float:
    """Probability a random positive outscores a random negative (ties count half)."""
    positives = float(labels.sum())
    negatives = float(len(labels) - positives)
    if positives == 0 or negatives == 0:
        return float("nan")
    ranks = _average_ranks(scores)
    positive_rank_sum = ranks[labels == 1].sum()
    return float((positive_rank_sum - positives * (positives + 1) / 2) / (positives * negatives))


def _average_ranks(values: FloatArray) -> FloatArray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=np.float64)
    sorted_values = values[order]
    start = 0
    while start < len(values):
        end = start
        while end + 1 < len(values) and sorted_values[end + 1] == sorted_values[start]:
            end += 1
        ranks[order[start : end + 1]] = (start + end) / 2 + 1
        start = end + 1
    return ranks


def precision_recall_curve(
    labels: FloatArray, scores: FloatArray
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Precision, recall and threshold at each distinct score, highest threshold first."""
    y, s = _sorted(labels, scores)
    true_positives = np.cumsum(y)
    flagged = np.arange(1, len(y) + 1)
    # Keep the last index of each run of equal scores.
    distinct = np.r_[np.where(np.diff(s) != 0)[0], len(s) - 1]
    total_positives = max(float(y.sum()), 1.0)
    precision = true_positives[distinct] / flagged[distinct]
    recall = true_positives[distinct] / total_positives
    return precision, recall, s[distinct]


def average_precision(labels: FloatArray, scores: FloatArray) -> float:
    if labels.sum() == 0:
        return float("nan")
    precision, recall, _ = precision_recall_curve(labels, scores)
    previous_recall = np.r_[0.0, recall[:-1]]
    return float(np.sum((recall - previous_recall) * precision))


def threshold_for_precision(
    labels: FloatArray, scores: FloatArray, target: float
) -> dict[str, float] | None:
    """Lowest threshold whose precision meets the target, with the recall it gives."""
    precision, recall, thresholds = precision_recall_curve(labels, scores)
    meets = np.where(precision >= target)[0]
    if len(meets) == 0:
        return None
    best = meets[np.argmax(recall[meets])]
    return {
        "threshold": float(thresholds[best]),
        "precision": float(precision[best]),
        "recall": float(recall[best]),
    }


def evaluate(labels: FloatArray, scores: FloatArray, prefix: str) -> dict[str, float]:
    """Flat metric dict, ready for MLflow: {prefix}_auc_pr, {prefix}_recall_at_p90, ..."""
    result = {
        f"{prefix}_rows": float(len(labels)),
        f"{prefix}_positives": float(labels.sum()),
        f"{prefix}_auc_roc": roc_auc(labels, scores),
        f"{prefix}_auc_pr": average_precision(labels, scores),
    }
    for target in (0.9, 0.5):
        point = threshold_for_precision(labels, scores, target)
        key = f"{prefix}_p{int(target * 100)}"
        result[f"{key}_recall"] = point["recall"] if point else 0.0
        result[f"{key}_threshold"] = point["threshold"] if point else 1.0
    return result
