"""Build the VITmate intent dataset.

Sources
-------
1. Kaggle "University Chatbot Dataset" (Tushar Paul, Apache-2.0), remapped to the
   VITmate taxonomy via data/taxonomy.yaml.
2. Utterances authored for VITmate (data/authored/*.yaml).
3. CLINC150 (Larson et al., 2019, CC BY 3.0): extra paraphrases for the
   conversational intents and out-of-domain queries for `out_of_scope`.

Outputs (data/processed/)
-------------------------
train.jsonl, val.jsonl, test.jsonl  stratified, leakage-free splits
spoken_test.jsonl                   held-out spoken-style challenge set
oos_eval.jsonl                      held-out CLINC150 out-of-scope test queries
labels.json                         ordered label list
dataset_report.json                 statistics for the report

Usage:  python -m training.build_dataset
"""

from __future__ import annotations

import json
import random
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from training.paths import AUTHORED_DIR, PROCESSED_DIR, RAW_DIR, TAXONOMY_FILE

SEED = 42
SPLIT_RATIOS = (0.70, 0.15, 0.15)  # train / val / test
CLINC_PER_VITMATE_INTENT = 30  # spread across the mapped CLINC intents
CLINC_OOS_PER_DOMAIN_INTENT = 1

# CLINC intents that are *not* out-of-scope for VITmate or are too ambiguous
# to be used as negatives (they overlap with VITmate intents).
CLINC_NOT_NEGATIVE = {
    "greeting", "goodbye", "thank_you", "what_is_your_name", "who_made_you",
    "are_you_a_bot", "what_can_i_ask_you", "who_do_you_work_for", "yes", "no",
    "maybe", "repeat", "cancel", "next_holiday", "calendar", "calendar_update",
    "application_status", "user_name", "change_user_name", "change_ai_name",
    "directions", "distance", "current_location", "share_location",
    "restaurant_suggestion", "meal_suggestion", "insurance",
}
# CLINC utterances mentioning these words could be genuine campus questions.
CAMPUS_WORDS = re.compile(
    r"\b(college|university|school|exam|class|semester|hostel|library|fee|fees|"
    r"tuition|scholarship|campus|student|course|admission|professor|vit)\b",
    re.IGNORECASE,
)
# Words ignored when detecting near-duplicate paraphrases.
FILLERS = {
    "uh", "um", "hey", "hi", "so", "please", "can", "you", "tell", "me", "the",
    "a", "an", "is", "are", "at", "in", "of", "to", "what", "about", "okay", "ok",
    "i", "do", "does", "vit", "vits", "there", "any", "my",
}


def clean(text: str) -> str:
    """Normalise unicode and whitespace while keeping the natural casing."""
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text).strip()


def dedup_key(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def near_dup_key(text: str) -> str:
    """Order-insensitive content signature used to keep paraphrases together."""
    tokens = {t for t in dedup_key(text).split() if t not in FILLERS}
    return " ".join(sorted(tokens)) or dedup_key(text)


def adapt_original_pattern(text: str) -> str:
    """Replace the dataset's university placeholders with VIT."""
    text = text.replace("(your univrsity(UNI) name)", "VIT")
    return re.sub(r"\bUNI('s)?\b", "VIT", text)


def load_yaml_dir(directory: Path, skip: set[str]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = defaultdict(list)
    for path in sorted(directory.glob("*.yaml")):
        if path.name in skip:
            continue
        for intent, utterances in yaml.safe_load(path.read_text()).items():
            merged[intent].extend(utterances)
    return merged


def load_original(taxonomy: dict) -> list[dict]:
    tag_to_intent = {
        tag: intent
        for intent, spec in taxonomy["intents"].items()
        for tag in spec.get("sources", [])
    }
    overrides = taxonomy.get("pattern_overrides", {})
    raw = json.loads((RAW_DIR / "university_chatbot_intents.json").read_text())

    examples = []
    for entry in raw["intents"]:
        tag = entry["intent"]
        for pattern in entry["text"]:
            pattern = pattern.strip()
            intent = overrides[pattern] if pattern in overrides else tag_to_intent.get(tag)
            if intent is None:
                continue
            examples.append(
                {"text": clean(adapt_original_pattern(pattern)), "intent": intent,
                 "source": "kaggle_university", "original_tag": tag}
            )
    return examples


def load_clinc(taxonomy: dict, rng: random.Random) -> tuple[list[dict], list[dict]]:
    """Return (training-pool examples, held-out out-of-scope evaluation queries)."""
    clinc = json.loads((RAW_DIR / "clinc150_data_full.json").read_text())
    by_intent: dict[str, list[str]] = defaultdict(list)
    for text, label in clinc["train"]:
        by_intent[label].append(text)

    pool = []
    mapped = set()
    for intent, spec in taxonomy["intents"].items():
        clinc_intents = spec.get("clinc", [])
        for clinc_intent in clinc_intents:
            mapped.add(clinc_intent)
            per_intent = CLINC_PER_VITMATE_INTENT // len(clinc_intents)
            for text in rng.sample(by_intent[clinc_intent], per_intent):
                pool.append({"text": clean(text), "intent": intent, "source": "clinc150"})

    negatives = [t for t, _ in clinc["oos_train"] + clinc["oos_val"]]
    for clinc_intent in sorted(by_intent):
        if clinc_intent in CLINC_NOT_NEGATIVE or clinc_intent in mapped:
            continue
        negatives.extend(rng.sample(by_intent[clinc_intent], CLINC_OOS_PER_DOMAIN_INTENT))
    pool.extend(
        {"text": clean(t), "intent": "out_of_scope", "source": "clinc150"}
        for t in negatives if not CAMPUS_WORDS.search(t)
    )

    oos_eval = [
        {"text": clean(t), "intent": "out_of_scope", "source": "clinc150_oos_test"}
        for t, _ in clinc["oos_test"] if not CAMPUS_WORDS.search(t)
    ]
    return pool, oos_eval


def resolve_duplicates(examples: list[dict]) -> tuple[list[dict], list[str]]:
    """Drop exact duplicates; drop every copy of a text labelled with >1 intent."""
    labels_by_key: dict[str, set[str]] = defaultdict(set)
    for ex in examples:
        labels_by_key[dedup_key(ex["text"])].add(ex["intent"])
    conflicts = sorted(k for k, labels in labels_by_key.items() if len(labels) > 1)

    seen, unique = set(), []
    for ex in examples:
        key = dedup_key(ex["text"])
        if not key or key in conflicts or key in seen:
            continue
        seen.add(key)
        unique.append(ex)
    return unique, conflicts


def grouped_stratified_split(examples: list[dict], rng: random.Random) -> dict[str, list[dict]]:
    """Split each intent 70/15/15, keeping near-duplicate groups in one split."""
    splits: dict[str, list[dict]] = {"train": [], "val": [], "test": []}
    by_intent: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for ex in examples:
        by_intent[ex["intent"]][near_dup_key(ex["text"])].append(ex)

    for intent in sorted(by_intent):
        groups = list(by_intent[intent].values())
        rng.shuffle(groups)
        total = sum(len(g) for g in groups)
        targets = {"val": round(total * SPLIT_RATIOS[1]), "test": round(total * SPLIT_RATIOS[2])}
        counts = {"val": 0, "test": 0}
        for group in groups:
            split = next((s for s in ("test", "val") if counts[s] < targets[s]), "train")
            if split != "train":
                counts[split] += len(group)
            splits[split].extend(group)
    for split in splits.values():
        rng.shuffle(split)
    return splits


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    rng = random.Random(SEED)
    taxonomy = yaml.safe_load(TAXONOMY_FILE.read_text())
    labels = list(taxonomy["intents"])

    authored = load_yaml_dir(AUTHORED_DIR, skip={"spoken_challenge_test.yaml"})
    challenge = yaml.safe_load((AUTHORED_DIR / "spoken_challenge_test.yaml").read_text())
    for intent in list(authored) + list(challenge):
        if intent not in labels:
            raise ValueError(f"Unknown intent '{intent}' in authored data")

    pool = load_original(taxonomy)
    pool += [
        {"text": clean(t), "intent": intent, "source": "authored"}
        for intent, texts in authored.items() for t in texts
    ]
    clinc_pool, oos_eval = load_clinc(taxonomy, rng)
    pool += clinc_pool

    spoken_test = [
        {"text": clean(t), "intent": intent, "source": "authored_spoken_challenge"}
        for intent, texts in challenge.items() for t in texts
    ]
    held_out_keys = {dedup_key(r["text"]) for r in spoken_test + oos_eval}
    held_out_near = {near_dup_key(r["text"]) for r in spoken_test}
    before = len(pool)
    pool = [
        ex for ex in pool
        if dedup_key(ex["text"]) not in held_out_keys and near_dup_key(ex["text"]) not in held_out_near
    ]
    removed_for_held_out = before - len(pool)

    pool, conflicts = resolve_duplicates(pool)
    splits = grouped_stratified_split(pool, rng)

    # Leakage check: no exact duplicate may appear in two splits.
    split_keys = {name: {dedup_key(r["text"]) for r in rows} for name, rows in splits.items()}
    assert not split_keys["train"] & split_keys["test"], "train/test leakage"
    assert not split_keys["train"] & split_keys["val"], "train/val leakage"

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for name, rows in splits.items():
        write_jsonl(PROCESSED_DIR / f"{name}.jsonl", rows)
    write_jsonl(PROCESSED_DIR / "spoken_test.jsonl", spoken_test)
    write_jsonl(PROCESSED_DIR / "oos_eval.jsonl", oos_eval)
    (PROCESSED_DIR / "labels.json").write_text(json.dumps(labels, indent=2))

    report = {
        "seed": SEED,
        "num_intents": len(labels),
        "total_examples": len(pool),
        "split_sizes": {k: len(v) for k, v in splits.items()},
        "spoken_test_size": len(spoken_test),
        "oos_eval_size": len(oos_eval),
        "examples_by_source": dict(Counter(ex["source"] for ex in pool)),
        "removed_overlapping_held_out": removed_for_held_out,
        "dropped_label_conflicts": conflicts,
        "per_intent": {
            label: {name: sum(r["intent"] == label for r in rows) for name, rows in splits.items()}
            for label in labels
        },
    }
    (PROCESSED_DIR / "dataset_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "per_intent"}, indent=2))


if __name__ == "__main__":
    main()
