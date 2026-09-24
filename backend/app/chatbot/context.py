"""Lightweight follow-up detection for multi-turn conversations.

A follow-up such as "How does it work?" carries no topic of its own. When the
conversation already has a topic (e.g. FFCS), the pronoun is replaced with the
topic title ("How does FFCS work?") so the classifier can check that the
rewritten question really belongs to that topic.
"""

from __future__ import annotations

import re

PRONOUN = re.compile(r"\b(it|its|it's|that|this|they|them|their|there|those|these)\b", re.IGNORECASE)
CONTINUATION = re.compile(
    r"^\s*(and\s+)?(tell me more|more( details| info(rmation)?)?|go on|continue|elaborate|"
    r"explain (more|further|that|it)|can you elaborate|what else|anything else about (it|that)|"
    r"more about (it|that|this)|details( please)?)\s*[?.!]*\s*$",
    re.IGNORECASE,
)
MAX_FOLLOW_UP_WORDS = 10


def is_continuation(message: str) -> bool:
    """Pure requests for more information, e.g. "tell me more"."""
    return bool(CONTINUATION.match(message))


def is_pronoun_follow_up(message: str) -> bool:
    """Short questions that refer back to an earlier topic, e.g. "how does it work?"."""
    return len(message.split()) <= MAX_FOLLOW_UP_WORDS and bool(PRONOUN.search(message))


def rewrite_with_topic(message: str, topic_title: str) -> str:
    """Replace the first referring pronoun with the topic title."""
    return PRONOUN.sub(topic_title, message, count=1)
