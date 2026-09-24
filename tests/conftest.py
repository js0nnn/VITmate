"""Shared fixtures.

Unit tests use `FakeClassifier`, a deterministic stand-in for the neural model,
so the chat logic can be tested exactly. Tests marked `model` load the real
trained model from backend/trained_model/ and are skipped if it is missing.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.chatbot.engine import ChatEngine
from backend.app.config import get_settings
from backend.app.knowledge.knowledge_base import KnowledgeBase
from backend.app.main import create_app
from backend.app.ml.intent_classifier import IntentPrediction

SETTINGS = get_settings()
MODEL_AVAILABLE = (SETTINGS.model_dir / "config.json").exists()


class FakeClassifier:
    """Maps known texts to fixed predictions; everything else is low-confidence."""

    def __init__(self, labels: list[str], table: dict[str, tuple[str, float]]) -> None:
        self.labels = labels
        self.table = {k.lower(): v for k, v in table.items()}

    def predict(self, text: str) -> IntentPrediction:
        intent, confidence = self.table.get(text.lower().strip(), ("out_of_scope", 0.2))
        return IntentPrediction(intent, confidence, [])

    def predict_batch(self, texts: list[str]) -> list[IntentPrediction]:
        return [self.predict(t) for t in texts]


FAKE_TABLE = {
    "what is ffcs?": ("ffcs", 0.97),
    "how does ffcs work?": ("ffcs", 0.93),
    "what are the hostel facilities?": ("hostel", 0.95),
    "hello": ("greeting", 0.99),
    "thanks": ("thanks", 0.98),
    "what is the capital of france?": ("out_of_scope", 0.96),
    "what about the hostel fee?": ("fees", 0.9),
    "is it good?": ("out_of_scope", 0.3),
    "tell me about vit placements.": ("placements", 0.94),
    "some vague thing": ("library", 0.31),
}


@pytest.fixture(scope="session")
def knowledge() -> KnowledgeBase:
    return KnowledgeBase(SETTINGS.knowledge_file)


@pytest.fixture
def engine(knowledge: KnowledgeBase) -> ChatEngine:
    labels = sorted({i for i, _ in FAKE_TABLE.values()} | set(knowledge.entries))
    return ChatEngine(FakeClassifier(labels, FAKE_TABLE), knowledge, confidence_threshold=0.5)


@pytest.fixture
def client(engine: ChatEngine) -> TestClient:
    app = create_app()
    app.state.engine = engine  # no lifespan run: the real model is never loaded
    return TestClient(app)


@pytest.fixture(scope="session")
def real_engine(knowledge: KnowledgeBase) -> ChatEngine:
    if not MODEL_AVAILABLE:
        pytest.skip("trained model not found; run `python -m training.train`")
    from backend.app.ml.intent_classifier import IntentClassifier

    return ChatEngine(IntentClassifier(SETTINGS.model_dir), knowledge, SETTINGS.confidence_threshold)
