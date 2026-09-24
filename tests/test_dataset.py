"""Processed dataset integrity (run `python -m training.build_dataset` first)."""

import re
from collections import Counter

from training.common import load_labels, load_split


def key(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def test_splits_use_known_labels():
    labels = set(load_labels())
    for split in ("train", "val", "test", "spoken_test", "oos_eval"):
        _, intents = load_split(split)
        assert intents and set(intents) <= labels, split


def test_no_leakage_between_splits():
    train = {key(t) for t in load_split("train")[0]}
    for split in ("val", "test", "spoken_test", "oos_eval"):
        overlap = train & {key(t) for t in load_split(split)[0]}
        assert not overlap, f"{split} overlaps train: {sorted(overlap)[:5]}"


def test_every_intent_is_represented_in_every_split():
    labels = set(load_labels())
    for split in ("train", "val", "test"):
        assert set(load_split(split)[1]) == labels, split


def test_classes_are_reasonably_balanced():
    counts = Counter(load_split("train")[1])
    in_scope = [n for label, n in counts.items() if label != "out_of_scope"]
    assert min(in_scope) >= 15
    assert max(in_scope) / min(in_scope) < 6
