"""Fair head-to-head comparison of the two v2 finalists (DistilBERT vs bge-small).

Every seed checkpoint from `compare_models.py` (artifacts/candidates/<model>-seed<n>)
is evaluated with the same code, at the arg-max operating point AND at the
deployed confidence threshold (0.35). Memory is measured in a fresh process per
checkpoint so models do not inflate each other's numbers.

Decision rule (fixed before the comparison was run):
  1. Primary: mean validation macro-F1 at the deployed threshold.
  2. Guardrails (validation): out-of-scope recall and in-scope rejection at the threshold.
  3. If the primary gap is smaller than the larger seed standard deviation, it is
     treated as noise and the guardrails decide, then latency and resources.
  Held-out test / spoken / OOS-eval sets are reported for every seed but never
  used for the decision.

Usage:  python -m training.final_comparison
"""

from __future__ import annotations

import json
import statistics
import subprocess
import sys
from pathlib import Path

from backend.app.config import get_settings
from backend.app.ml.intent_classifier import IntentClassifier
from training.common import apply_threshold, classification_metrics, load_split, write_json
from training.evaluate import measure_latency, predict
from training.paths import ARTIFACTS_DIR, RESULTS_DIR, ROOT

FINALISTS = {"distilbert": "DistilBERT (distilbert-base-uncased)", "bge-small": "bge-small (BAAI/bge-small-en-v1.5)"}
SEEDS = (42, 7, 13)

MEMORY_PROBE = """
import sys, psutil
from pathlib import Path
from backend.app.ml.intent_classifier import IntentClassifier
before = psutil.Process().memory_info().rss
c = IntentClassifier(Path(sys.argv[1]))
c.predict_batch(["what is ffcs"] * 32)
for _ in range(20):
    c.predict("what are the hostel facilities at vit")
print(psutil.Process().memory_info().rss / 1e6, (psutil.Process().memory_info().rss - before) / 1e6)
"""


def oos_recall(gold: list[str], pred: list[str]) -> float:
    oos = [p for g, p in zip(gold, pred) if g == "out_of_scope"]
    return round(sum(p == "out_of_scope" for p in oos) / len(oos), 4)


def in_scope_rejection(gold: list[str], pred: list[str], confident: list[bool]) -> float:
    rows = [not c for g, c in zip(gold, confident) if g != "out_of_scope"]
    return round(sum(rows) / len(rows), 4)


def evaluate_checkpoint(model_dir: Path, threshold: float) -> dict:
    classifier = IntentClassifier(model_dir)
    result: dict = {}
    for split in ("val", "test", "spoken_test"):
        texts, gold = load_split(split)
        intents, conf = predict(classifier, texts)
        thresholded = apply_threshold(intents, conf, threshold)
        result[split] = {
            "argmax": classification_metrics(gold, intents),
            "thresholded": classification_metrics(gold, thresholded),
            "in_scope_rejection": in_scope_rejection(gold, intents, [c >= threshold for c in conf]),
        }
        if split == "val":
            result[split]["oos_recall_argmax"] = oos_recall(gold, intents)
            result[split]["oos_recall_thresholded"] = oos_recall(gold, thresholded)
    oos_texts, _ = load_split("oos_eval")
    intents, conf = predict(classifier, oos_texts)
    result["oos_eval"] = {
        "recall_argmax": round(sum(i == "out_of_scope" for i in intents) / len(intents), 4),
        "recall_thresholded": round(
            sum(i == "out_of_scope" for i in apply_threshold(intents, conf, threshold)) / len(intents), 4),
    }
    result["latency"] = measure_latency(classifier, load_split("test")[0][:200])
    rss, delta = subprocess.run([sys.executable, "-c", MEMORY_PROBE, str(model_dir)], cwd=ROOT, check=True,
                                capture_output=True, text=True).stdout.split()
    result["memory"] = {"process_rss_mb": round(float(rss), 1), "model_rss_delta_mb": round(float(delta), 1)}
    weights = sum(f.stat().st_size for f in model_dir.glob("*.safetensors"))
    result["size"] = {"parameters_millions": round(sum(p.numel() for p in classifier.model.parameters()) / 1e6, 1),
                      "fp32_mb": round(weights / 1e6, 1), "fp16_mb": round(weights / 2e6, 1)}
    return result


def get(run: dict, path: str) -> float:
    value = run
    for key in path.split("."):
        value = value[key]
    return value


def summarise(runs: list[dict], path: str) -> dict:
    values = [get(r, path) for r in runs]
    return {"mean": round(statistics.mean(values), 4), "sd": round(statistics.stdev(values), 4),
            "values": [round(v, 4) for v in values]}


METRICS = [
    ("Validation macro-F1 @0.35 (PRIMARY)", "val.thresholded.macro_f1"),
    ("Validation macro-F1 (arg-max)", "val.argmax.macro_f1"),
    ("Validation accuracy @0.35", "val.thresholded.accuracy"),
    ("Validation OOS recall @0.35 (guardrail)", "val.oos_recall_thresholded"),
    ("Validation in-scope rejection @0.35 (guardrail, lower is better)", "val.in_scope_rejection"),
    ("Test macro-F1 @0.35", "test.thresholded.macro_f1"),
    ("Test macro-F1 (arg-max)", "test.argmax.macro_f1"),
    ("Test accuracy @0.35", "test.thresholded.accuracy"),
    ("Test in-scope rejection @0.35", "test.in_scope_rejection"),
    ("Spoken macro-F1 @0.35", "spoken_test.thresholded.macro_f1"),
    ("Spoken accuracy @0.35", "spoken_test.thresholded.accuracy"),
    ("OOS-eval recall @0.35 (977 unseen)", "oos_eval.recall_thresholded"),
    ("OOS-eval recall (arg-max)", "oos_eval.recall_argmax"),
    ("Median latency (ms)", "latency.median_ms"),
    ("p95 latency (ms)", "latency.p95_ms"),
    ("Process RSS after load + inference (MB)", "memory.process_rss_mb"),
    ("Model RSS increase (MB)", "memory.model_rss_delta_mb"),
]


def decide(summary: dict, names: list[str]) -> tuple[str, str]:
    a, b = names
    primary = {n: summary[n]["val.thresholded.macro_f1"] for n in names}
    gap = primary[a]["mean"] - primary[b]["mean"]
    noise = max(primary[a]["sd"], primary[b]["sd"])
    if abs(gap) >= noise:
        winner = a if gap > 0 else b
        return winner, (f"Primary metric decides: {winner} leads validation macro-F1 @0.35 by {abs(gap):.4f}, "
                        f"which is at least the larger seed SD ({noise:.4f}).")
    reasons = [f"Primary gap {abs(gap):.4f} is smaller than the larger seed SD {noise:.4f}, so it is treated as noise."]
    score = {n: 0 for n in names}
    for path, higher_is_better in (("val.oos_recall_thresholded", True), ("val.in_scope_rejection", False)):
        x, y = summary[a][path]["mean"], summary[b][path]["mean"]
        if x != y:
            better = a if (x > y) == higher_is_better else b
            score[better] += 1
            reasons.append(f"Guardrail {path}: {better} is better ({x:.4f} vs {y:.4f}).")
    if score[a] != score[b]:
        winner = max(score, key=score.get)
        return winner, " ".join(reasons + [f"Guardrails favour {winner}."])
    lat = {n: summary[n]["latency.median_ms"]["mean"] for n in names}
    winner = min(lat, key=lat.get)
    return winner, " ".join(reasons + [f"Guardrails tie; the lower-latency model ({winner}) is preferred."])


def main() -> None:
    threshold = get_settings().confidence_threshold
    runs: dict[str, list[dict]] = {}
    for name in FINALISTS:
        runs[name] = []
        for seed in SEEDS:
            model_dir = ARTIFACTS_DIR / "candidates" / f"{name}-seed{seed}"
            print(f"evaluating {model_dir.relative_to(ROOT)}", flush=True)
            runs[name].append({"seed": seed, **evaluate_checkpoint(model_dir, threshold)})

    summary = {n: {path: summarise(runs[n], path) for _, path in METRICS} for n in FINALISTS}
    for n in FINALISTS:
        summary[n]["size"] = runs[n][0]["size"]
    winner, reason = decide(summary, list(FINALISTS))
    write_json(RESULTS_DIR / "final_comparison.json",
               {"threshold": threshold, "seeds": SEEDS, "decision": {"winner": winner, "reason": reason},
                "summary": summary, "runs": runs})

    names = list(FINALISTS)
    lines = [
        "# Final comparison: DistilBERT vs bge-small (dataset v2)",
        "",
        f"Generated by `python -m training.final_comparison`. Each value is the mean ± SD over seeds {SEEDS} "
        f"(checkpoints from `compare_models.py`), evaluated with identical code at the deployed confidence "
        f"threshold **{threshold}** and at arg-max. Held-out rows (test, spoken, OOS-eval) are reported but not "
        "used for the decision.",
        "",
        f"| Metric | {FINALISTS[names[0]]} | {FINALISTS[names[1]]} |",
        "|---|---|---|",
    ]
    for label, path in METRICS:
        cells = [f"{summary[n][path]['mean']:.4f} ± {summary[n][path]['sd']:.4f}" for n in names]
        lines.append(f"| {label} | {cells[0]} | {cells[1]} |")
    for label, key in (("Parameters (M)", "parameters_millions"), ("Checkpoint fp32 (MB)", "fp32_mb"),
                       ("Deployed fp16 checkpoint (MB)", "fp16_mb")):
        lines.append(f"| {label} | {summary[names[0]]['size'][key]} | {summary[names[1]]['size'][key]} |")
    lines += ["", "## Decision", "", f"**{FINALISTS[winner]}** — {reason}", "",
              "Decision rule (fixed before running): primary = mean validation macro-F1 at the deployed threshold; "
              "if the gap is below the larger seed SD it is noise, and validation guardrails (OOS recall, in-scope "
              "rejection) decide, then latency/resources."]
    (RESULTS_DIR / "final_comparison.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
