"""Transformer-based intent classifier used by the API and the evaluation scripts."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IntentPrediction:
    intent: str
    confidence: float
    alternatives: list[tuple[str, float]]  # next most likely intents


class IntentClassifier:
    """Loads a fine-tuned sequence-classification model once and serves predictions."""

    def __init__(self, model_dir: Path, max_length: int = 64, top_k: int = 3) -> None:
        if not (model_dir / "config.json").exists():
            raise FileNotFoundError(
                "Trained model not found. Run `python -m training.train` first."
            )
        started = time.perf_counter()
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        # Checkpoints may be stored in fp16 to save space; CPU inference runs in fp32.
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir, dtype=torch.float32)
        self.model.eval()
        self.labels: list[str] = [
            self.model.config.id2label[i] for i in range(self.model.config.num_labels)
        ]
        self.max_length = max_length
        self.top_k = top_k
        self.load_seconds = time.perf_counter() - started
        logger.info("Loaded intent model with %d labels in %.2fs", len(self.labels), self.load_seconds)

    @torch.inference_mode()
    def predict_batch(self, texts: list[str]) -> list[IntentPrediction]:
        encoded = self.tokenizer(
            texts, padding=True, truncation=True, max_length=self.max_length, return_tensors="pt"
        )
        probabilities = torch.softmax(self.model(**encoded).logits, dim=-1)
        top = torch.topk(probabilities, k=min(self.top_k + 1, len(self.labels)), dim=-1)

        predictions = []
        for scores, indices in zip(top.values.tolist(), top.indices.tolist()):
            ranked = [(self.labels[i], round(s, 4)) for i, s in zip(indices, scores)]
            predictions.append(IntentPrediction(ranked[0][0], ranked[0][1], ranked[1:]))
        return predictions

    def predict(self, text: str) -> IntentPrediction:
        return self.predict_batch([text])[0]
