"""VITmate FastAPI application.

Run from the project root:
    uvicorn backend.app.main:app --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import torch
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes import router
from backend.app.chatbot.engine import ChatEngine
from backend.app.config import Settings, get_settings
from backend.app.knowledge.knowledge_base import KnowledgeBase
from backend.app.ml.intent_classifier import IntentClassifier

logger = logging.getLogger("vitmate")


def build_engine(settings: Settings) -> ChatEngine | None:
    """Load the model and knowledge base once. Returns None if loading fails."""
    try:
        if settings.torch_threads:
            torch.set_num_threads(settings.torch_threads)
        classifier = IntentClassifier(settings.model_dir)
        knowledge = KnowledgeBase(settings.knowledge_file)
        return ChatEngine(classifier, knowledge, settings.confidence_threshold)
    except Exception:
        logger.exception("VITmate could not load its model or knowledge base")
        return None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.engine = build_engine(settings)
        yield

    app = FastAPI(
        title="VITmate API",
        description="VITmate — Your VIT Campus Companion",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        message = str(first.get("msg", "Invalid request")).removeprefix("Value error, ")
        return JSONResponse(status_code=422, content={"detail": message})

    @app.exception_handler(Exception)
    async def unhandled_error(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error", exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})

    app.include_router(router)

    # In a single-service deployment the built frontend is served by the API.
    if settings.frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=settings.frontend_dist, html=True), name="frontend")
    return app


app = create_app()
