"""Response-engine logic: knowledge retrieval, fallbacks and conversational context."""

from backend.app.chatbot import context as ctx
from backend.app.chatbot.engine import ConversationContext, time_sensitive_note


def test_high_confidence_intent_uses_knowledge_base(engine, knowledge):
    result = engine.respond("What are the hostel facilities?")
    assert result.intent == "hostel"
    assert result.reply.startswith(knowledge.entry("hostel").summary.strip())
    assert result.sources == knowledge.entry("hostel").sources


def test_time_sensitive_answers_carry_a_dated_note_once(engine, knowledge):
    placements = knowledge.entry("placements")
    assert placements.time_sensitive and placements.as_of
    first = engine.respond("Tell me about VIT placements.")
    assert time_sensitive_note(placements) in first.reply
    assert placements.as_of in first.reply
    # Follow-ups on the same topic do not repeat the note.
    assert "Time-sensitive" not in engine.respond("tell me more", first.context).reply


def test_stable_answers_have_no_freshness_note(engine, knowledge):
    assert not knowledge.entry("ffcs").time_sensitive
    assert "Time-sensitive" not in engine.respond("What is FFCS?").reply
    assert "Time-sensitive" not in engine.respond("What are the hostel facilities?").reply


def test_conversational_intents_keep_the_current_topic(engine):
    topic = ConversationContext(previous_intent="ffcs", depth=0)
    result = engine.respond("thanks", topic)
    assert result.intent == "thanks"
    assert result.context == topic


def test_pronoun_follow_up_is_resolved_to_previous_topic(engine, knowledge):
    first = engine.respond("What is FFCS?")
    # "How does it work?" is rewritten to "How does FFCS work?" before classification.
    follow_up = engine.respond("How does it work?", first.context)
    assert follow_up.intent == "ffcs"
    assert follow_up.is_follow_up
    assert follow_up.reply.startswith(knowledge.entry("ffcs").details.strip())
    assert follow_up.context.depth == 1


def test_continuation_phrase_returns_details_then_stops(engine):
    first = engine.respond("What are the hostel facilities?")
    more = engine.respond("tell me more", first.context)
    assert more.is_follow_up and more.context.depth == 1
    again = engine.respond("tell me more", more.context)
    assert "all the verified information" in again.reply


def test_repeating_the_topic_gives_details(engine, knowledge):
    first = engine.respond("What is FFCS?")
    second = engine.respond("How does FFCS work?", first.context)
    assert second.reply.startswith(knowledge.entry("ffcs").details.strip())


def test_follow_up_with_new_explicit_topic_switches_topic(engine):
    first = engine.respond("What is FFCS?")
    switched = engine.respond("What about the hostel fee?", first.context)
    assert switched.intent == "fees"
    assert switched.context.previous_intent == "fees"


def test_unresolvable_follow_up_asks_for_clarification(engine):
    first = engine.respond("What is FFCS?")
    unclear = engine.respond("Is it good?", first.context)
    assert unclear.is_fallback
    assert "which VIT topic" in unclear.reply


def test_follow_up_without_history_is_not_guessed(engine):
    result = engine.respond("tell me more")
    assert result.is_fallback


def test_low_confidence_prediction_is_not_answered(engine, knowledge):
    result = engine.respond("some vague thing")  # fake model: library @ 0.31
    assert result.is_fallback
    assert knowledge.entry("library").summary.strip() not in result.reply


def test_low_confidence_offers_the_most_likely_topics(engine, knowledge):
    result = engine.respond("some vague thing")  # fake model: library @ 0.31
    assert [s.intent for s in result.suggestions] == ["library"]
    assert result.suggestions[0].question == knowledge.entry("library").example_question
    assert "not completely sure" in result.reply


def test_low_confidence_without_vit_candidates_just_asks_to_rephrase(engine):
    result = engine.respond("completely unknown words")  # fake model: out_of_scope @ 0.2
    assert result.suggestions == []
    assert "rephrase" in result.reply.lower()


def test_unclear_follow_up_offers_current_topic_first(engine):
    first = engine.respond("What is FFCS?")
    unclear = engine.respond("Is it good?", first.context)
    assert unclear.suggestions and unclear.suggestions[0].intent == "ffcs"


def test_starter_questions_are_verified_against_the_model(engine):
    # The fake model only recognises the FFCS and hostel starters; the rest are dropped.
    assert {s.intent for s in engine.starter_questions} == {"ffcs", "hostel"}


def test_context_helpers():
    assert ctx.is_continuation("Tell me more")
    assert ctx.is_continuation("can you elaborate?")
    assert not ctx.is_continuation("tell me more about hostels")
    assert ctx.is_pronoun_follow_up("how does it work?")
    assert not ctx.is_pronoun_follow_up("what is ffcs")
    assert ctx.rewrite_with_topic("how does it work?", "FFCS") == "how does FFCS work?"
