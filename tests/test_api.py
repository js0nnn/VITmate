"""HTTP API behaviour (with the deterministic fake classifier)."""

from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_health_reports_loaded_model(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert body["num_intents"] > 0


def test_valid_chat_request_returns_structured_answer(client):
    response = client.post("/api/chat", json={"message": "What is FFCS?"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "ffcs"
    assert 0 <= body["confidence"] <= 1
    assert "Fully Flexible Credit System" in body["reply"]
    assert body["sources"] and all(url.startswith("https://") for url in body["sources"])
    assert body["context"] == {"previous_intent": "ffcs", "depth": 0}
    assert body["is_fallback"] is False


def test_voice_and_text_use_the_same_pipeline(client):
    text = client.post("/api/chat", json={"message": "What is FFCS?", "input_mode": "text"}).json()
    voice = client.post("/api/chat", json={"message": "What is FFCS?", "input_mode": "voice"}).json()
    assert text["intent"] == voice["intent"] and text["reply"] == voice["reply"]


def test_empty_message_is_rejected(client):
    for message in ["", "   ", "\n\t"]:
        response = client.post("/api/chat", json={"message": message})
        assert response.status_code == 422
        assert response.json()["detail"] == "Message must not be empty"


def test_overlong_message_is_rejected(client):
    response = client.post("/api/chat", json={"message": "a" * 501})
    assert response.status_code == 422


def test_malformed_requests_are_rejected(client):
    assert client.post("/api/chat", json={}).status_code == 422
    assert client.post("/api/chat", json={"message": 42}).status_code == 422
    assert client.post("/api/chat", content="not json", headers={"Content-Type": "application/json"}).status_code == 422
    assert client.post("/api/chat", json={"message": "hi", "input_mode": "telepathy"}).status_code == 422
    assert client.post("/api/chat", json={"message": "hi", "context": {"depth": 7}}).status_code == 422


def test_unknown_context_intent_is_ignored(client):
    response = client.post("/api/chat", json={"message": "hello", "context": {"previous_intent": "../../etc/passwd"}})
    assert response.status_code == 200
    assert response.json()["context"]["previous_intent"] is None


def test_out_of_scope_question(client):
    body = client.post("/api/chat", json={"message": "What is the capital of France?"}).json()
    assert body["intent"] == "out_of_scope"
    assert body["is_fallback"] is True
    assert "VIT" in body["reply"]


def test_low_confidence_question_offers_suggestions(client):
    body = client.post("/api/chat", json={"message": "some vague thing"}).json()
    assert body["is_fallback"] is True
    assert body["suggestions"] == [{"intent": "library", "question": "What facilities does the library provide?"}]


def test_low_confidence_without_candidates_asks_to_rephrase(client):
    body = client.post("/api/chat", json={"message": "completely unknown words"}).json()
    assert body["is_fallback"] is True and body["suggestions"] == []
    assert "rephrase" in body["reply"].lower()


def test_suggestions_are_served(client):
    response = client.get("/api/suggestions")
    assert response.status_code == 200
    assert all({"intent", "question"} <= set(s) for s in response.json())


def test_engine_failure_returns_friendly_error(client):
    def explode(*_args, **_kwargs):
        raise RuntimeError("secret internal detail /home/user/model.bin")

    client.app.state.engine.respond = explode
    response = client.post("/api/chat", json={"message": "What is FFCS?"})
    assert response.status_code == 503
    assert "secret" not in response.text and "/home" not in response.text


def test_missing_model_degrades_gracefully():
    app = create_app()
    app.state.engine = None  # what build_engine() leaves behind when loading fails
    test_client = TestClient(app)
    assert test_client.get("/api/health").json()["model_loaded"] is False
    response = test_client.post("/api/chat", json={"message": "What is FFCS?"})
    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]
