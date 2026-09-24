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

VERIFY_NOTE = "_This information can change — please check the latest details on the official VIT website._"


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
            return self._fallback("low_confidence", prediction, context)

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
        return ChatResult(
            reply=self.knowledge.response("clarify_follow_up"),
            intent=prediction.intent,
            confidence=prediction.confidence,
            is_fallback=True,
            is_follow_up=True,
            context=context,
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
        reply = f"{text.strip()}\n\n{VERIFY_NOTE}" if entry.time_sensitive and add_note else text.strip()
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

    def _fallback(self, key: str, prediction: IntentPrediction, context: ConversationContext) -> ChatResult:
        return ChatResult(
            reply=self.knowledge.response(key),
            intent=prediction.intent,
            confidence=prediction.confidence,
            is_fallback=True,
            context=context,
        )
