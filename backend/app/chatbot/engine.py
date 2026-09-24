"""The VITmate response engine: intent classification + knowledge base + context.

Typed and spoken messages both arrive here as text; there is a single pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from backend.app.chatbot import context as ctx
from backend.app.knowledge.knowledge_base import KnowledgeBase, KnowledgeEntry, StarterQuestion
from backend.app.ml.intent_classifier import IntentClassifier, IntentPrediction

logger = logging.getLogger(__name__)

# Intents never offered as "did you mean" suggestions.
NOT_SUGGESTED = {"bot_identity", "capabilities"}
MAX_SUGGESTIONS = 3
MIN_SUGGESTION_CONFIDENCE = 0.05


def time_sensitive_note(entry: KnowledgeEntry) -> str:
    """Short freshness note, shown once per topic for genuinely time-sensitive answers."""
    as_of = f" As of: {entry.as_of}." if entry.as_of else ""
    return f"🕒 _Time-sensitive information.{as_of} Please confirm on the official source before relying on it._"


@dataclass
class ConversationContext:
    """State the client sends back with each message (the server stays stateless)."""

    previous_intent: str | None = None
    depth: int = 0  # 0 = summary shown, 1 = details shown


@dataclass
class ChatResult:
    reply: str
    intent: str
    confidence: float
    is_fallback: bool = False
    is_follow_up: bool = False
    topic: str | None = None
    sources: list[str] = field(default_factory=list)
    time_sensitive: bool = False
    context: ConversationContext = field(default_factory=ConversationContext)
    suggestions: list[StarterQuestion] = field(default_factory=list)  # "did you mean" topics


class ChatEngine:
    def __init__(self, classifier: IntentClassifier, knowledge: KnowledgeBase, confidence_threshold: float) -> None:
        self.classifier = classifier
        self.knowledge = knowledge
        self.threshold = confidence_threshold
        missing = [i for i in classifier.labels if not knowledge.entry(i) and not knowledge.has_response(i)]
        if missing:
            logger.warning("Intents without knowledge-base content: %s", ", ".join(missing))
        self.starter_questions = self._verified_starters(knowledge.starter_questions)

    def _verified_starters(self, starters: list[StarterQuestion]) -> list[StarterQuestion]:
        """Keep only starter prompts that the model actually routes to their intent."""
        if not starters:
            return []
        predictions = self.classifier.predict_batch([s.question for s in starters])
        verified = [s for s, p in zip(starters, predictions) if p.intent == s.intent and p.confidence >= self.threshold]
        dropped = len(starters) - len(verified)
        if dropped:
            logger.warning("Dropped %d starter question(s) the model does not classify correctly", dropped)
        return verified

    # ------------------------------------------------------------------ public
    def respond(self, message: str, context: ConversationContext | None = None) -> ChatResult:
        context = context or ConversationContext()
        topic = self.knowledge.entry(context.previous_intent) if context.previous_intent else None

        if topic and ctx.is_continuation(message):
            return self._follow_up(topic, context, confidence=1.0)

        prediction = self.classifier.predict(message)
        if topic and ctx.is_pronoun_follow_up(message):
            result = self._resolve_pronoun_follow_up(message, topic, context, prediction)
            if result:
                return result

        if prediction.confidence < self.threshold:
            return self._unsure(prediction, context)

        entry = self.knowledge.entry(prediction.intent)
        if entry is None:  # conversational intent (greeting, thanks, out_of_scope, ...)
            key = prediction.intent if self.knowledge.has_response(prediction.intent) else "unavailable"
            return ChatResult(
                reply=self.knowledge.response(key),
                intent=prediction.intent,
                confidence=prediction.confidence,
                is_fallback=prediction.intent == "out_of_scope",
                context=context,  # keep the current topic for later follow-ups
            )

        if topic and entry.intent == topic.intent:  # asking again about the same topic
            return self._follow_up(topic, context, confidence=prediction.confidence)
        return self._answer(entry, prediction.confidence)

    # ----------------------------------------------------------------- helpers
    def _resolve_pronoun_follow_up(
        self, message: str, topic: KnowledgeEntry, context: ConversationContext, prediction: IntentPrediction
    ) -> ChatResult | None:
        rewritten = self.classifier.predict(ctx.rewrite_with_topic(message, topic.title))
        if rewritten.intent == topic.intent and rewritten.confidence >= self.threshold:
            return self._follow_up(topic, context, confidence=rewritten.confidence)

        # The message names a different topic with confidence: treat it as a topic change.
        if prediction.confidence >= self.threshold and prediction.intent != "out_of_scope":
            return None
        current_topic = [StarterQuestion(topic.intent, topic.example_question)] if topic.example_question else []
        return ChatResult(
            reply=self.knowledge.response("clarify_follow_up"),
            intent=prediction.intent,
            confidence=prediction.confidence,
            is_fallback=True,
            is_follow_up=True,
            context=context,
            suggestions=self._suggestions(prediction, first=current_topic),
        )

    def _answer(self, entry: KnowledgeEntry, confidence: float) -> ChatResult:
        return self._result(entry, entry.summary, confidence, depth=0, is_follow_up=False)

    def _follow_up(self, entry: KnowledgeEntry, context: ConversationContext, confidence: float) -> ChatResult:
        if context.depth == 0 and entry.details:
            return self._result(entry, entry.details, confidence, depth=1, is_follow_up=True)
        reply = f"That's all the verified information I have about **{entry.title}**."
        if entry.sources:
            reply += " For more, see the official page" + ("s" if len(entry.sources) > 1 else "") + " below."
        return self._result(entry, reply, confidence, depth=context.depth, is_follow_up=True, add_note=False)

    def _result(
        self, entry: KnowledgeEntry, text: str, confidence: float, depth: int, is_follow_up: bool, add_note: bool = True
    ) -> ChatResult:
        # The freshness note is shown with the first answer about a topic, not on every follow-up.
        show_note = entry.time_sensitive and add_note and not is_follow_up
        reply = f"{text.strip()}\n\n{time_sensitive_note(entry)}" if show_note else text.strip()
        return ChatResult(
            reply=reply,
            intent=entry.intent,
            confidence=confidence,
            is_follow_up=is_follow_up,
            topic=entry.title,
            sources=entry.sources,
            time_sensitive=entry.time_sensitive,
            context=ConversationContext(previous_intent=entry.intent, depth=depth),
        )

    def _suggestions(self, prediction: IntentPrediction, first: list[StarterQuestion] | None = None) -> list[StarterQuestion]:
        """The classifier's most likely VIT topics, phrased as questions the user can pick."""
        suggestions = list(first or [])
        ranked = [(prediction.intent, prediction.confidence), *prediction.alternatives]
        for intent, confidence in ranked:
            entry = self.knowledge.entry(intent)
            if (
                confidence < MIN_SUGGESTION_CONFIDENCE
                or entry is None
                or not entry.example_question
                or intent in NOT_SUGGESTED
                or any(s.intent == intent for s in suggestions)
            ):
                continue
            suggestions.append(StarterQuestion(intent, entry.example_question))
        return suggestions[:MAX_SUGGESTIONS]

    def _unsure(self, prediction: IntentPrediction, context: ConversationContext) -> ChatResult:
        """Low confidence: never guess an answer, but offer the most likely topics."""
        suggestions = self._suggestions(prediction)
        return ChatResult(
            reply=self.knowledge.response("low_confidence_suggest" if suggestions else "low_confidence"),
            intent=prediction.intent,
            confidence=prediction.confidence,
            is_fallback=True,
            context=context,
            suggestions=suggestions,
        )
