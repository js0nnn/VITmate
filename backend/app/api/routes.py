"""HTTP endpoints."""

from __future__ import annotations

import logging
import time
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request

from backend.app.api.schemas import ChatContext, ChatRequest, ChatResponse, HealthResponse, Suggestion
from backend.app.chatbot.engine import ChatEngine, ConversationContext

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

UNAVAILABLE = "The assistant is temporarily unavailable. Please try again shortly."


def get_engine(request: Request) -> ChatEngine:
    engine: ChatEngine | None = getattr(request.app.state, "engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail=UNAVAILABLE)
    return engine


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    engine: ChatEngine | None = getattr(request.app.state, "engine", None)
    return HealthResponse(
        status="ok" if engine else "degraded",
        model_loaded=engine is not None,
        num_intents=len(engine.classifier.labels) if engine else 0,
        knowledge_retrieved_on=engine.knowledge.meta.get("retrieved_on") if engine else None,
    )


@router.get("/suggestions", response_model=list[Suggestion])
def suggestions(request: Request) -> list[Suggestion]:
    return [Suggestion(**asdict(s)) for s in get_engine(request).starter_questions]


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    engine = get_engine(request)
    previous = payload.context.previous_intent
    context = ConversationContext(
        previous_intent=previous if engine.knowledge.entry(previous or "") else None,
        depth=payload.context.depth,
    )
    started = time.perf_counter()
    try:
        result = engine.respond(payload.message, context)
    except Exception:  # never leak internals to the client
        logger.exception("Failed to answer a chat message")
        raise HTTPException(status_code=503, detail=UNAVAILABLE) from None
    latency_ms = round((time.perf_counter() - started) * 1000, 1)
    logger.info("intent=%s confidence=%.3f mode=%s latency=%.1fms",
                result.intent, result.confidence, payload.input_mode, latency_ms)

    data = asdict(result)
    data["context"] = ChatContext(**data["context"])
    return ChatResponse(**data, latency_ms=latency_ms)
