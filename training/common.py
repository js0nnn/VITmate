"""Helpers shared by the training, comparison and evaluation scripts."""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from training.paths import PROCESSED_DIR


def set_seed(seed: int) -> None:
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def load_split(name: str) -> tuple[list[str], list[str]]:
    """Return (texts, intents) for a processed split such as 'train' or 'spoken_test'."""
    rows = [json.loads(line) for line in (PROCESSED_DIR / f"{name}.jsonl").read_text().splitlines()]
    return [r["text"] for r in rows], [r["intent"] for r in rows]


def load_labels() -> list[str]:
    return json.loads((PROCESSED_DIR / "labels.json").read_text())


def classification_metrics(y_true: list[str], y_pred: list[str]) -> dict[str, float]:
    """Accuracy plus macro- and weighted-averaged precision/recall/F1."""
    metrics = {"accuracy": accuracy_score(y_true, y_pred)}
    for average in ("macro", "weighted"):
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average=average, zero_division=0
        )
        metrics.update(
            {f"{average}_precision": precision, f"{average}_recall": recall, f"{average}_f1": f1}
        )
    return {k: round(float(v), 4) for k, v in metrics.items()}


def apply_threshold(
    intents: list[str], confidences: list[float], threshold: float, fallback: str = "out_of_scope"
) -> list[str]:
    """Replace predictions below the confidence threshold with the fallback intent."""
    return [i if c >= threshold else fallback for i, c in zip(intents, confidences)]


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
