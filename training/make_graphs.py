"""Generate report graphs from the real result files.

Inputs (all produced by the pipeline, never typed in by hand):
  docs/results/model_comparison.json    python -m training.compare_models
  docs/results/evaluation.json          python -m training.evaluate
  docs/results/confusion_matrix.png     python -m training.evaluate
  backend/trained_model/training_summary.json
  data/processed/dataset_report.json
  docs/results/v1/*                     archived results of dataset v1

Outputs: docs/graphs/*.png

Usage:  python -m training.make_graphs
"""

from __future__ import annotations

import json
import shutil
import statistics
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from training.paths import MODEL_DIR, PROCESSED_DIR, RESULTS_DIR, ROOT

GRAPHS_DIR = ROOT / "docs" / "graphs"

# Validated categorical palette (first three slots pass all-pairs CVD checks).
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"

CANDIDATE_ORDER = ["baseline", "bert-mini", "minilm-l6", "bge-small", "distilbert"]
LABELS = {
    "baseline": "TF-IDF + LogReg\n(baseline)",
    "bert-mini": "BERT-mini\n11M",
    "minilm-l6": "MiniLM-L6\n23M",
    "bge-small": "bge-small\n33M",
    "distilbert": "DistilBERT\n67M",
}

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID,
    "axes.labelcolor": INK_2,
    "axes.titlecolor": INK,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "xtick.color": INK_2,
    "ytick.color": INK_2,
    "font.size": 10,
    "legend.frameon": False,
})


def load_json(path):
    return json.loads(path.read_text())


def grouped_runs(runs: dict) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for key, run in runs.items():
        grouped[key.split("@")[0]].append(run)
    return {k: grouped[k] for k in CANDIDATE_ORDER if k in grouped}


def mean_std(runs: list[dict], split: str, metric: str) -> tuple[float, float]:
    values = [r[split][metric] for r in runs]
    return statistics.mean(values), (statistics.stdev(values) if len(values) > 1 else 0.0)


def save(fig, name: str, note: str) -> None:
    # Below the axes (bbox_inches="tight" keeps it in the image) so it never overlaps tick labels.
    fig.text(0.01, -0.03, note, fontsize=7.5, color=INK_2, ha="left", va="top")
    fig.savefig(GRAPHS_DIR / name, dpi=200, bbox_inches="tight")
    plt.close(fig)


def bar_labels(ax, bars, values, fmt="{:.3f}", errors=None):
    errors = errors or [0] * len(values)
    for bar, value, error in zip(bars, values, errors):
        ax.annotate(fmt.format(value), (bar.get_x() + bar.get_width() / 2, bar.get_height() + error),
                    xytext=(0, 3), textcoords="offset points", ha="center", fontsize=7.5, color=INK_2)


def plot_metric_by_split(groups, metric: str, title: str, name: str, ylabel: str) -> None:
    splits = [("val", "Validation", BLUE), ("test", "Test", ORANGE), ("spoken_test", "Spoken-style", AQUA)]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    width = 0.26
    keys = list(groups)
    for i, (split, label, color) in enumerate(splits):
        stats = [mean_std(groups[k], split, metric) for k in keys]
        xs = [j + (i - 1) * width for j in range(len(keys))]
        bars = ax.bar(xs, [m for m, _ in stats], width - 0.03, color=color, label=label,
                      yerr=[s for _, s in stats], capsize=3, error_kw={"ecolor": INK_2, "linewidth": 1})
        bar_labels(ax, bars, [m for m, _ in stats], errors=[sd for _, sd in stats])
    ax.set_xticks(range(len(keys)), [LABELS[k] for k in keys])
    ax.set_ylim(0.6, 1.02)
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left")
    ax.legend(ncol=3, loc="upper left")
    ax.grid(axis="x", visible=False)
    seeds = ", ".join(f"{LABELS[k].split(chr(10))[0]}: {len(groups[k])} seeds" for k in keys if len(groups[k]) > 1)
    save(fig, name, f"Source: docs/results/model_comparison.json. Error bars = std over seeds ({seeds}).")


def plot_efficiency(groups) -> None:
    keys = [k for k in groups if groups[k][0]["deep_learning"]]
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(12, 4))
    params = [groups[k][0]["parameters_millions"] for k in keys]
    sizes = [groups[k][0]["size_mb"] for k in keys]
    latency = [statistics.median(r["median_latency_ms"] for r in groups[k]) for k in keys]
    names = [LABELS[k].split("\n")[0] for k in keys]
    for ax, values, title, fmt in (
        (ax1, params, "Parameters (millions)", "{:.1f}"),
        (ax2, sizes, "Checkpoint size, fp32 (MB)", "{:.0f}"),
        (ax3, latency, "Median CPU latency per query (ms)", "{:.1f}"),
    ):
        bars = ax.bar(names, values, color=BLUE, width=0.6)
        bar_labels(ax, bars, values, fmt)
        ax.set_title(title, loc="left", fontsize=11)
        ax.grid(axis="x", visible=False)
        ax.tick_params(axis="x", rotation=20)
    save(fig, "model_efficiency.png",
         "Source: docs/results/model_comparison.json. Latency: single query, CPU, batch size 1 (median of runs).")


def plot_accuracy_vs_latency(groups) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.6))
    for k, runs in groups.items():
        if not runs[0]["deep_learning"]:
            continue
        f1, _ = mean_std(runs, "val", "macro_f1")
        latency = statistics.median(r["median_latency_ms"] for r in runs)
        ax.scatter(latency, f1, s=runs[0]["parameters_millions"] * 12, color=BLUE, alpha=0.8,
                   edgecolor=SURFACE, linewidth=2, zorder=3)
        ax.annotate(LABELS[k].replace("\n", " "), (latency, f1), xytext=(8, -3), textcoords="offset points",
                    fontsize=8.5, color=INK)
    base = groups.get("baseline")
    if base:
        ax.axhline(base[0]["val"]["macro_f1"], color=INK_2, linestyle="--", linewidth=1)
        ax.annotate("TF-IDF baseline", (ax.get_xlim()[1], base[0]["val"]["macro_f1"]), xytext=(-4, 4),
                    textcoords="offset points", ha="right", fontsize=8, color=INK_2)
    ax.set_xlabel("Median CPU latency per query (ms)")
    ax.set_ylabel("Validation macro-F1 (mean over seeds)")
    ax.set_title("Accuracy vs. speed (bubble area ∝ parameters)", loc="left")
    save(fig, "accuracy_vs_latency.png", "Source: docs/results/model_comparison.json.")


def plot_training_curve(summary: dict) -> None:
    history = summary["history"]
    epochs = [h["epoch"] for h in history]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    ax1.plot(epochs, [h["train_loss"] for h in history], color=BLUE, linewidth=2, marker="o", markersize=5)
    ax1.set_title("Training loss (weighted cross-entropy)", loc="left", fontsize=11)
    ax1.set_xlabel("Epoch")
    ax2.plot(epochs, [h["val_macro_f1"] for h in history], color=BLUE, linewidth=2, marker="o", markersize=5,
             label="Validation macro-F1")
    ax2.plot(epochs, [h["val_accuracy"] for h in history], color=ORANGE, linewidth=2, marker="s", markersize=5,
             label="Validation accuracy")
    best = summary["best_epoch"]
    ax2.axvline(best, color=INK_2, linestyle="--", linewidth=1)
    ax2.annotate(f"best epoch {best} (checkpoint kept)", (best, 0.5), xytext=(6, 0),
                 textcoords="offset points", fontsize=8, color=INK_2)
    ax2.set_title("Validation metrics (early stopping, patience 4)", loc="left", fontsize=11)
    ax2.set_xlabel("Epoch")
    ax2.legend(loc="lower right")
    ax2.set_ylim(0, 1)
    for ax in (ax1, ax2):
        ax.set_xticks(epochs)
    save(fig, "training_curve.png",
         f"Source: backend/trained_model/training_summary.json ({summary['config']['model_name']}, seed "
         f"{summary['config']['seed']}).")


def plot_per_intent(evaluation: dict) -> None:
    per_intent = evaluation["per_intent"]
    items = sorted(per_intent.items(), key=lambda kv: kv[1]["f1-score"])
    fig, ax = plt.subplots(figsize=(8, 10))
    names = [k for k, _ in items]
    f1 = [v["f1-score"] for _, v in items]
    bars = ax.barh(names, f1, color=BLUE, height=0.7)
    for bar, value, (_, v) in zip(bars, f1, items):
        ax.annotate(f"{value:.2f}  (n={int(v['support'])})", (bar.get_width(), bar.get_y() + bar.get_height() / 2),
                    xytext=(4, 0), textcoords="offset points", va="center", fontsize=7.5, color=INK_2)
    ax.axvline(evaluation["test"]["macro_f1"], color=ORANGE, linestyle="--", linewidth=1.5)
    ax.annotate(f"macro-F1 {evaluation['test']['macro_f1']:.3f}", (evaluation["test"]["macro_f1"], len(names) - 0.5),
                xytext=(-4, 0), textcoords="offset points", ha="right", fontsize=8, color=INK_2)
    ax.set_xlim(0, 1.15)
    ax.set_xlabel("F1 on the test set")
    ax.set_title("Per-intent F1 — deployed model", loc="left")
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", labelsize=8)
    save(fig, "per_intent_f1.png", "Source: docs/results/evaluation.json (test split). n = test support.")


def plot_out_of_scope(evaluation: dict) -> None:
    sweep = evaluation["threshold"]["validation_sweep"]
    chosen = evaluation["threshold"]["value"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4), gridspec_kw={"width_ratios": [1, 1.6]})
    oos = evaluation["oos_eval"]
    values = [oos["recall_argmax"], oos["recall_thresholded"]]
    bars = ax1.bar(["Arg-max only", f"With threshold {chosen}"], values, color=[BLUE, ORANGE], width=0.55)
    bar_labels(ax1, bars, values, "{:.1%}")
    ax1.set_ylim(0, 1.05)
    ax1.set_title(f"Out-of-scope recall ({evaluation['sizes']['oos_eval']} unseen queries)", loc="left", fontsize=11)
    ax1.grid(axis="x", visible=False)
    thresholds = [r["threshold"] for r in sweep]
    ax2.plot(thresholds, [r["macro_f1"] for r in sweep], color=BLUE, linewidth=2, marker="o", markersize=4,
             label="Validation macro-F1")
    ax2.plot(thresholds, [r["in_scope_rejection_rate"] for r in sweep], color=ORANGE, linewidth=2, marker="s",
             markersize=4, label="In-scope questions rejected")
    ax2.axvline(chosen, color=INK_2, linestyle="--", linewidth=1)
    best = evaluation["threshold"].get("sweep_best", {}).get("threshold")
    note = f"deployed floor {chosen}" + (f"\n(sweep optimum {best})" if best is not None and best != chosen else "")
    ax2.annotate(note, (chosen, 0.5), xytext=(5, 0), textcoords="offset points", fontsize=8, color=INK_2)
    ax2.set_xlabel("Confidence threshold")
    ax2.set_ylim(0, 1.02)
    ax2.set_title("Threshold sweep (validation set)", loc="left", fontsize=11)
    ax2.legend(loc="center left")
    save(fig, "out_of_scope_and_threshold.png", "Source: docs/results/evaluation.json.")


def plot_dataset(report: dict) -> None:
    per_intent = report["per_intent"]
    items = sorted(per_intent.items(), key=lambda kv: sum(kv[1].values()))
    names = [k for k, _ in items]
    fig, ax = plt.subplots(figsize=(8, 10))
    left = [0] * len(names)
    for split, label, color in (("train", "Train", BLUE), ("val", "Validation", ORANGE), ("test", "Test", AQUA)):
        values = [v[split] for _, v in items]
        ax.barh(names, values, left=left, color=color, label=label, height=0.7, edgecolor=SURFACE, linewidth=1)
        left = [a + b for a, b in zip(left, values)]
    for y, total in enumerate(left):
        ax.annotate(str(total), (total, y), xytext=(4, 0), textcoords="offset points", va="center", fontsize=7.5,
                    color=INK_2)
    ax.set_xlabel("Examples")
    ax.set_title(f"Dataset v2: {report['total_examples']} examples, {report['num_intents']} intents", loc="left")
    ax.legend(loc="lower right")
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", labelsize=8)
    save(fig, "dataset_distribution.png", "Source: data/processed/dataset_report.json.")


def plot_dataset_sources(report: dict) -> None:
    sources = report["examples_by_source"]
    names = {"kaggle_university": "Kaggle University\nChatbot Dataset", "authored": "Authored VITmate\nutterances",
             "clinc150": "CLINC150"}
    keys = ["kaggle_university", "authored", "clinc150"]
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    bars = ax.bar([names[k] for k in keys], [sources[k] for k in keys], color=BLUE, width=0.55)
    bar_labels(ax, bars, [sources[k] for k in keys], "{:d}")
    ax.set_ylabel("Examples in the labelled pool")
    ax.set_title("Where the training data comes from", loc="left")
    ax.grid(axis="x", visible=False)
    save(fig, "dataset_sources.png", "Source: data/processed/dataset_report.json.")


def plot_v1_vs_v2(v1: dict, v2: dict) -> None:
    rows = [("Test accuracy", "test", "accuracy"), ("Test macro-F1", "test", "macro_f1"),
            ("Test weighted-F1", "test", "weighted_f1"), ("Spoken accuracy", "spoken_test", "accuracy"),
            ("Spoken macro-F1", "spoken_test", "macro_f1")]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    width = 0.36
    for i, (data, label, color) in enumerate(((v1, "v1: bge-small, 36 intents", BLUE), (v2, "v2: DistilBERT, 38 intents", ORANGE))):
        values = [data[s][m] for _, s, m in rows] + [data["oos_eval"]["recall_thresholded"]]
        xs = [j + (i - 0.5) * width for j in range(len(values))]
        bars = ax.bar(xs, values, width - 0.03, color=color, label=label)
        bar_labels(ax, bars, values)
    ax.set_xticks(range(len(rows) + 1), [r[0] for r in rows] + ["OOS recall\n(thresholded)"], fontsize=8.5)
    ax.set_ylim(0.6, 1.05)
    ax.set_title("Deployed model: bge-small on dataset v1 → DistilBERT on dataset v2", loc="left")
    ax.legend(loc="upper left", ncol=2)
    ax.grid(axis="x", visible=False)
    save(fig, "v1_vs_v2_final_model.png",
         "Sources: docs/results/v1/evaluation.json and docs/results/evaluation.json. v2 test/spoken sets are larger "
         "(new intents), so the sets are not identical.")


def plot_finalists(final: dict) -> None:
    """Head-to-head of the two v2 finalists at the deployed threshold (mean ± SD over 3 seeds)."""
    summary = final["summary"]
    names = [("distilbert", "DistilBERT", ORANGE), ("bge-small", "bge-small", BLUE)]
    quality = [("Val macro-F1\n(selection)", "val.thresholded.macro_f1"),
               ("Val OOS recall\n(guardrail)", "val.oos_recall_thresholded"),
               ("Test\nmacro-F1", "test.thresholded.macro_f1"),
               ("Spoken\nmacro-F1", "spoken_test.thresholded.macro_f1"),
               ("OOS-eval recall\n(977 unseen)", "oos_eval.recall_thresholded")]
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(14, 4.6), gridspec_kw={"width_ratios": [2.6, 0.8, 0.8]})
    width = 0.38
    for i, (key, label, color) in enumerate(names):
        means = [summary[key][p]["mean"] for _, p in quality]
        sds = [summary[key][p]["sd"] for _, p in quality]
        xs = [j + (i - 0.5) * width for j in range(len(quality))]
        bars = ax1.bar(xs, means, width - 0.04, yerr=sds, capsize=3, color=color, label=label,
                       error_kw={"ecolor": INK_2, "linewidth": 1})
        bar_labels(ax1, bars, means, errors=sds)
    ax1.set_xticks(range(len(quality)), [q[0] for q in quality], fontsize=8.5)
    ax1.set_ylim(0.75, 1.02)
    ax1.set_title(f"Quality at the deployed threshold {final['threshold']} (mean ± SD, 3 seeds)", loc="left",
                  fontsize=11)
    ax1.legend(loc="upper left", ncol=2)
    ax1.grid(axis="x", visible=False)
    ax1.axvspan(-0.5, 1.5, color=GRID, alpha=0.35, zorder=0)
    ax1.annotate("used for the decision", (0.5, 0.765), ha="center", fontsize=8, color=INK_2)
    for ax, path, title, fmt in ((ax2, "latency.median_ms", "Median latency (ms)", "{:.1f}"),
                                 (ax3, "memory.process_rss_mb", "Process RSS (MB)", "{:.0f}")):
        values = [summary[key][path]["mean"] for key, _, _ in names]
        bars = ax.bar([n[1] for n in names], values, color=[n[2] for n in names], width=0.6)
        bar_labels(ax, bars, values, fmt)
        ax.set_title(title, loc="left", fontsize=11)
        ax.grid(axis="x", visible=False)
        ax.tick_params(axis="x", labelsize=8.5)
    save(fig, "final_comparison.png",
         "Source: docs/results/final_comparison.json. Test/spoken/OOS-eval shown for transparency only.")


def main() -> None:
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    groups = grouped_runs(load_json(RESULTS_DIR / "model_comparison.json"))
    evaluation = load_json(RESULTS_DIR / "evaluation.json")

    plot_metric_by_split(groups, "macro_f1", "Macro-F1 by model and evaluation set", "model_comparison_macro_f1.png",
                         "Macro-F1")
    plot_metric_by_split(groups, "accuracy", "Accuracy by model and evaluation set", "model_comparison_accuracy.png",
                         "Accuracy")
    plot_efficiency(groups)
    plot_accuracy_vs_latency(groups)
    plot_training_curve(load_json(MODEL_DIR / "training_summary.json"))
    plot_per_intent(evaluation)
    plot_out_of_scope(evaluation)
    report = load_json(PROCESSED_DIR / "dataset_report.json")
    plot_dataset(report)
    plot_dataset_sources(report)
    if (RESULTS_DIR / "final_comparison.json").exists():
        plot_finalists(load_json(RESULTS_DIR / "final_comparison.json"))
    if (RESULTS_DIR / "v1" / "evaluation.json").exists():
        plot_v1_vs_v2(load_json(RESULTS_DIR / "v1" / "evaluation.json"), evaluation)
    shutil.copy(RESULTS_DIR / "confusion_matrix.png", GRAPHS_DIR / "confusion_matrix.png")
    print("Graphs written to", GRAPHS_DIR.relative_to(ROOT))


if __name__ == "__main__":
    main()
