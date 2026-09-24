"""Loads the curated VIT knowledge base (data/knowledge/vit_knowledge.yaml)."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class KnowledgeEntry:
    intent: str
    title: str
    summary: str
    details: str | None = None
    sources: list[str] = field(default_factory=list)
    time_sensitive: bool = False
    as_of: str | None = None  # e.g. "NIRF 2025" or "2026 admission cycle"
    last_verified: str | None = None
    example_question: str | None = None  # offered as a "did you mean" suggestion


@dataclass(frozen=True)
class StarterQuestion:
    intent: str
    question: str


class KnowledgeBase:
    def __init__(self, path: Path) -> None:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.meta: dict = data.get("meta", {})
        self.responses: dict[str, list[str]] = data["responses"]
        self.entries: dict[str, KnowledgeEntry] = {
            intent: KnowledgeEntry(intent=intent, **spec)
            for intent, spec in data["entries"].items()
        }
        self.starter_questions = [StarterQuestion(**q) for q in data.get("starter_questions", [])]

    def entry(self, intent: str) -> KnowledgeEntry | None:
        return self.entries.get(intent)

    def response(self, key: str) -> str:
        return random.choice(self.responses[key])

    def has_response(self, key: str) -> bool:
        return key in self.responses
