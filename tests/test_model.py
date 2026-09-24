"""Real trained model: loading, inference and the documented demo scenarios."""

import subprocess
import sys

import pytest

from training.common import load_labels
from training.paths import ROOT

pytestmark = pytest.mark.model

DEMO_QUERIES = {
    "What is FFCS?": "ffcs",
    "What are the hostel facilities at VIT?": "hostel",
    "Tell me about VIT placements.": "placements",
    "What programmes does VIT offer?": "programmes",
    "How can I find information about admissions?": "admissions",
    "What facilities does the library provide?": "library",
    "What is the capital of France?": "out_of_scope",
    "Write me a Python program.": "out_of_scope",
    "Hey, can you tell me what FFCS is?": "ffcs",
    "Uh, what are the hostel facilities at VIT?": "hostel",
}


def test_model_loads_with_expected_labels(real_engine):
    assert real_engine.classifier.labels == load_labels()


def test_inference_returns_valid_intent_and_confidence(real_engine):
    prediction = real_engine.classifier.predict("When is VITEEE?")
    assert prediction.intent in real_engine.classifier.labels
    assert 0.0 <= prediction.confidence <= 1.0
    assert all(0.0 <= c <= prediction.confidence for _, c in prediction.alternatives)


@pytest.mark.parametrize("query,expected", DEMO_QUERIES.items())
def test_demo_queries(real_engine, query, expected):
    result = real_engine.respond(query)
    assert result.intent == expected


def test_follow_up_with_real_model(real_engine):
    first = real_engine.respond("What is FFCS?")
    follow_up = real_engine.respond("How does it work?", first.context)
    assert follow_up.intent == "ffcs" and follow_up.is_follow_up


def test_all_starter_questions_survive_verification(real_engine):
    assert len(real_engine.starter_questions) == len(real_engine.knowledge.starter_questions)


def test_evaluation_script_runs(tmp_path):
    completed = subprocess.run(
        [sys.executable, "-m", "training.evaluate", "--output-dir", str(tmp_path)],
        cwd=ROOT, capture_output=True, text=True, timeout=600,
    )
    assert completed.returncode == 0, completed.stderr[-2000:]
    for name in ("evaluation.json", "evaluation.md", "confusion_matrix.png", "per_intent_metrics.csv"):
        assert (tmp_path / name).exists(), name
