"""Knowledge-base integrity: every intent is answerable and facts are sourced."""

from urllib.parse import urlparse

from training.common import load_labels

OFFICIAL_HOSTS = {"vit.ac.in", "viteee.vit.ac.in", "vtop.vit.ac.in", "admissions.vit.ac.in"}
CONVERSATIONAL = {"greeting", "goodbye", "thanks", "profanity", "out_of_scope"}


def test_every_intent_has_an_answer(knowledge):
    for label in load_labels():
        assert knowledge.entry(label) or knowledge.has_response(label), label


def test_fallback_responses_exist(knowledge):
    for key in ("low_confidence", "clarify_follow_up", "unavailable", "out_of_scope"):
        assert knowledge.has_response(key)


def test_vit_facts_cite_official_sources(knowledge):
    for intent, entry in knowledge.entries.items():
        if intent in {"bot_identity", "capabilities"}:
            continue
        assert entry.sources, f"{intent} has no source"
        assert entry.last_verified, f"{intent} has no verification date"
        for url in entry.sources:
            assert urlparse(url).scheme == "https"
            assert urlparse(url).hostname in OFFICIAL_HOSTS, url


def test_entries_have_follow_up_details(knowledge):
    for intent, entry in knowledge.entries.items():
        assert entry.title and entry.summary.strip(), intent
        assert entry.details and entry.details.strip(), intent


def test_starter_questions_reference_real_intents(knowledge):
    labels = set(load_labels())
    assert knowledge.starter_questions
    assert all(q.intent in labels and q.intent not in CONVERSATIONAL for q in knowledge.starter_questions)
