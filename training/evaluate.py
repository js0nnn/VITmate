"""Evaluate the deployed VITmate intent model (backend/trained_model/).

Reports
-------
* accuracy, macro/weighted precision, recall and F1 on the test and spoken-style sets
* per-intent precision/recall/F1 and a confusion matrix for the test set
* a confidence-threshold sweep on the *validation* set (used to pick the threshold)
* out-of-scope recall on 983 held-out CLINC150 out-of-scope queries
* model load time, single-query latency and process memory on CPU

Everything is written to docs/results/ (or --output-dir).

Usage:  python -m training.evaluate [--threshold 0.5]
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
from pathlib import Path
import statistics
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import psutil
from sklearn.metrics import classification_report, confusion_matrix

from backend.app.ml.intent_classifier import IntentClassifier
from training.common import apply_threshold, classification_metrics, load_labels, load_split, write_json
from training.paths import MODEL_DIR, RESULTS_DIR

logger = logging.getLogger("evaluate")
THRESHOLDS = [round(t, 2) for t in np.arange(0.0, 0.96, 0.05)]


def predict(classifier: IntentClassifier, texts: list[str]) -> tuple[list[str], list[float]]:
    intents, confidences = [], []
    for start in range(0, len(texts), 64):
        for p in classifier.predict_batch(texts[start:start + 64]):
            intents.append(p.intent)
            confidences.append(p.confidence)
    return intents, confidences


def threshold_sweep(gold: list[str], intents: list[str], confidences: list[float]) -> list[dict]:
    """Effect of treating low-confidence predictions as out-of-scope."""
    rows = []
    in_scope = [g != "out_of_scope" for g in gold]
    for threshold in THRESHOLDS:
        pred = apply_threshold(intents, confidences, threshold)
        metrics = classification_metrics(gold, pred)
        rejected = [p == "out_of_scope" for p, keep in zip(pred, in_scope) if keep]
        rows.append({"threshold": threshold, "accuracy": metrics["accuracy"], "macro_f1": metrics["macro_f1"],
                     "in_scope_rejection_rate": round(sum(rejected) / len(rejected), 4)})
    return rows


def measure_latency(classifier: IntentClassifier, texts: list[str]) -> dict:
    classifier.predict("warm up")
    timings = []
    for text in texts:
        started = time.perf_counter()
        classifier.predict(text)
        timings.append((time.perf_counter() - started) * 1000)
    timings.sort()
    return {
        "queries": len(timings),
        "mean_ms": round(statistics.mean(timings), 2),
        "median_ms": round(statistics.median(timings), 2),
        "p95_ms": round(timings[int(0.95 * len(timings)) - 1], 2),
    }


def plot_confusion_matrix(gold: list[str], pred: list[str], labels: list[str], out_dir: Path) -> None:
    matrix = confusion_matrix(gold, pred, labels=labels, normalize="true")
    fig, ax = plt.subplots(figsize=(14, 12))
    image = ax.imshow(matrix, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(labels)), labels, rotation=90, fontsize=8)
    ax.set_yticks(range(len(labels)), labels, fontsize=8)
    ax.set_xlabel("Predicted intent")
    ax.set_ylabel("True intent")
    ax.set_title("VITmate intent classifier — normalised confusion matrix (test set)")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(out_dir / "confusion_matrix.png", dpi=150)
    plt.close(fig)


def plot_threshold_sweep(rows: list[dict], chosen: float, out_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    thresholds = [r["threshold"] for r in rows]
    ax.plot(thresholds, [r["macro_f1"] for r in rows], marker="o", label="Validation macro-F1")
    ax.plot(thresholds, [r["in_scope_rejection_rate"] for r in rows], marker="s",
            label="In-scope queries rejected")
    ax.axvline(chosen, color="grey", linestyle="--", label=f"Chosen threshold = {chosen}")
    ax.set_xlabel("Confidence threshold")
    ax.set_ylim(0, 1)
    ax.legend()
    ax.set_title("Confidence threshold sweep (validation set)")
    fig.tight_layout()
    fig.savefig(out_dir / "threshold_sweep.png", dpi=150)
    plt.close(fig)


def write_per_intent(report: dict, labels: list[str], out_dir: Path) -> None:
    with (out_dir / "per_intent_metrics.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["intent", "precision", "recall", "f1", "support"])
        for label in labels:
            r = report[label]
            writer.writerow([label, f"{r['precision']:.4f}", f"{r['recall']:.4f}", f"{r['f1-score']:.4f}",
                             int(r["support"])])


def write_markdown(results: dict, report: dict, labels: list[str], errors: list[tuple[str, str, str, float]],
                   out_dir: Path) -> None:
    def metric_row(name: str, m: dict) -> str:
        return (f"| {name} | {m['accuracy']:.4f} | {m['macro_precision']:.4f} | {m['macro_recall']:.4f} "
                f"| {m['macro_f1']:.4f} | {m['weighted_precision']:.4f} | {m['weighted_recall']:.4f} "
                f"| {m['weighted_f1']:.4f} |")

    t = results["threshold"]
    lines = [
        "# VITmate intent model — evaluation",
        "",
        f"Generated by `python -m training.evaluate`. Model: `{results['model']['base_model']}` "
        f"({results['model']['parameters_millions']}M parameters, {results['model']['num_intents']} intents).",
        "",
        "## Classification metrics (arg-max prediction, no threshold)",
        "",
        "| Set | Accuracy | Macro P | Macro R | Macro F1 | Weighted P | Weighted R | Weighted F1 |",
        "|---|---|---|---|---|---|---|---|",
        metric_row(f"Test (n={results['sizes']['test']})", results["test"]),
        metric_row(f"Spoken-style challenge (n={results['sizes']['spoken_test']})", results["spoken_test"]),
        "",
        f"## With the confidence threshold ({t['value']})",
        "",
        "Predictions below the threshold are answered with a \"please rephrase\" fallback and counted as "
        "`out_of_scope` here. The threshold was chosen on the validation set.",
        "",
        "| Set | Accuracy | Macro P | Macro R | Macro F1 | Weighted P | Weighted R | Weighted F1 |",
        "|---|---|---|---|---|---|---|---|",
        metric_row("Test", results["test_thresholded"]),
        metric_row("Spoken-style challenge", results["spoken_test_thresholded"]),
        "",
        f"- In-scope test queries rejected as low-confidence: {t['test_in_scope_rejection_rate']:.2%}",
        f"- **Out-of-scope recall** on {results['sizes']['oos_eval']} held-out CLINC150 out-of-scope queries: "
        f"{results['oos_eval']['recall_argmax']:.2%} (arg-max) / {results['oos_eval']['recall_thresholded']:.2%} "
        "(with threshold)",
        "",
        "## Efficiency (CPU)",
        "",
        f"- Model load time: {results['efficiency']['load_seconds']} s",
        f"- Single-query latency: median {results['efficiency']['latency']['median_ms']} ms, "
        f"mean {results['efficiency']['latency']['mean_ms']} ms, p95 {results['efficiency']['latency']['p95_ms']} ms",
        f"- Process memory (RSS) after loading and inference: {results['efficiency']['rss_mb']} MB",
        f"- Model size on disk: {results['model']['size_mb']} MB",
        "",
        "## Per-intent results (test set)",
        "",
        "| Intent | Precision | Recall | F1 | Support |",
        "|---|---|---|---|---|",
        *[f"| {label} | {report[label]['precision']:.3f} | {report[label]['recall']:.3f} "
          f"| {report[label]['f1-score']:.3f} | {int(report[label]['support'])} |" for label in labels],
        "",
        "![Confusion matrix](confusion_matrix.png)",
        "",
        "![Threshold sweep](threshold_sweep.png)",
        "",
        "## Misclassified test examples",
        "",
        "| Text | True | Predicted | Confidence |",
        "|---|---|---|---|",
        *[f"| {text} | {gold} | {pred} | {conf:.2f} |" for text, gold, pred, conf in errors],
    ]
    (out_dir / "evaluation.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float,
                        help="Confidence threshold to report (default: best validation macro-F1)")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    args = parser.parse_args()
    out_dir: Path = args.output_dir

    labels = load_labels()
    classifier = IntentClassifier(MODEL_DIR)
    results: dict = {"sizes": {}}

    val_texts, val_gold = load_split("val")
    val_intents, val_conf = predict(classifier, val_texts)
    sweep = threshold_sweep(val_gold, val_intents, val_conf)
    best = max(sweep, key=lambda r: (r["macro_f1"], -r["threshold"]))
    threshold = args.threshold if args.threshold is not None else best["threshold"]

    predictions = {}
    for split in ("test", "spoken_test"):
        texts, gold = load_split(split)
        intents, conf = predict(classifier, texts)
        predictions[split] = (texts, gold, intents, conf)
        results["sizes"][split] = len(texts)
        results[split] = classification_metrics(gold, intents)
        results[f"{split}_thresholded"] = classification_metrics(gold, apply_threshold(intents, conf, threshold))

    test_texts, test_gold, test_intents, test_conf = predictions["test"]
    thresholded = apply_threshold(test_intents, test_conf, threshold)
    in_scope = [(g, p) for g, p in zip(test_gold, thresholded) if g != "out_of_scope"]

    oos_texts, _ = load_split("oos_eval")
    oos_intents, oos_conf = predict(classifier, oos_texts)
    results["sizes"]["oos_eval"] = len(oos_texts)
    results["oos_eval"] = {
        "recall_argmax": round(sum(i == "out_of_scope" for i in oos_intents) / len(oos_intents), 4),
        "recall_thresholded": round(
            sum(i == "out_of_scope" for i in apply_threshold(oos_intents, oos_conf, threshold)) / len(oos_intents), 4),
    }
    results["threshold"] = {
        "value": threshold,
        "selected_on": "validation macro-F1" if args.threshold is None else "command line",
        "test_in_scope_rejection_rate": round(sum(p == "out_of_scope" for _, p in in_scope) / len(in_scope), 4),
        "validation_sweep": sweep,
    }

    results["efficiency"] = {
        "load_seconds": round(classifier.load_seconds, 2),
        "latency": measure_latency(classifier, test_texts[:200]),
        "rss_mb": round(psutil.Process().memory_info().rss / 1e6, 1),
    }
    results["model"] = {
        "base_model": json.loads((MODEL_DIR / "training_summary.json").read_text())["config"]["model_name"],
        "num_intents": len(classifier.labels),
        "parameters_millions": round(sum(p.numel() for p in classifier.model.parameters()) / 1e6, 1),
        "size_mb": round(sum(f.stat().st_size for f in MODEL_DIR.rglob("*") if f.is_file()) / 1e6, 1),
    }

    report = classification_report(test_gold, test_intents, labels=labels, output_dict=True, zero_division=0)
    errors = sorted(
        [(t, g, p, c) for t, g, p, c in zip(test_texts, test_gold, test_intents, test_conf) if g != p],
        key=lambda e: -e[3],
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "evaluation.json", {**results, "per_intent": {l: report[l] for l in labels}})
    write_per_intent(report, labels, out_dir)
    plot_confusion_matrix(test_gold, test_intents, labels, out_dir)
    plot_threshold_sweep(sweep, threshold, out_dir)
    write_markdown(results, report, labels, errors, out_dir)

    logger.info("Test accuracy %.4f | macro-F1 %.4f | weighted-F1 %.4f", results["test"]["accuracy"],
                results["test"]["macro_f1"], results["test"]["weighted_f1"])
    logger.info("Spoken-style accuracy %.4f | macro-F1 %.4f", results["spoken_test"]["accuracy"],
                results["spoken_test"]["macro_f1"])
    logger.info("OOS recall %.2f%% (threshold %.2f) | median latency %.1f ms", 100 * results["oos_eval"]["recall_thresholded"],
                threshold, results["efficiency"]["latency"]["median_ms"])
    logger.info("Results written to %s", out_dir)


if __name__ == "__main__":
    main()
