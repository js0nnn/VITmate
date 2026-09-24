"""Fine-tune a pretrained transformer for VITmate intent classification.

The best checkpoint (highest validation macro-F1) is saved to
backend/trained_model/, which is the model the backend serves.

Usage:
    python -m training.train                       # final model from training/config.yaml
    python -m training.train --model distilbert-base-uncased --output-dir artifacts/x
"""

from __future__ import annotations

import argparse
import copy
import logging
import math
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import torch
import yaml
from torch.utils.data import DataLoader
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

from training.common import classification_metrics, load_labels, load_split, set_seed, write_json
from training.paths import MODEL_DIR, ROOT

logger = logging.getLogger("train")
CONFIG_FILE = Path(__file__).with_name("config.yaml")


@dataclass
class TrainConfig:
    model_name: str
    learning_rate: float = 5e-5
    batch_size: int = 16
    max_epochs: int = 25
    patience: int = 4  # early stopping on validation macro-F1
    warmup_ratio: float = 0.1
    weight_decay: float = 0.01
    max_length: int = 64
    seed: int = 42
    save_fp16: bool = False  # halve the checkpoint size; weights are upcast to fp32 when loaded


def class_weights(intents: list[str], labels: list[str]) -> torch.Tensor:
    """Inverse square-root frequency weights to soften class imbalance."""
    counts = Counter(intents)
    weights = torch.tensor([1.0 / math.sqrt(counts[label]) for label in labels])
    return weights / weights.mean()


def evaluate_loader(model, loader) -> tuple[list[int], list[int]]:
    model.eval()
    y_true, y_pred = [], []
    with torch.inference_mode():
        for batch in loader:
            labels = batch.pop("labels")
            logits = model(**batch).logits
            y_true.extend(labels.tolist())
            y_pred.extend(logits.argmax(dim=-1).tolist())
    return y_true, y_pred


def fine_tune(config: TrainConfig, output_dir: Path) -> dict:
    """Train with early stopping, save the best checkpoint and return a summary."""
    set_seed(config.seed)
    labels = load_labels()
    label_to_id = {label: i for i, label in enumerate(labels)}
    train_texts, train_intents = load_split("train")
    val_texts, val_intents = load_split("val")

    tokenizer = AutoTokenizer.from_pretrained(config.model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        config.model_name,
        num_labels=len(labels),
        id2label=dict(enumerate(labels)),
        label2id=label_to_id,
    )

    def collate(batch):
        texts, ids = zip(*batch)
        encoded = tokenizer(list(texts), padding=True, truncation=True,
                            max_length=config.max_length, return_tensors="pt")
        encoded["labels"] = torch.tensor(ids)
        return encoded

    train_pairs = list(zip(train_texts, [label_to_id[i] for i in train_intents]))
    val_pairs = list(zip(val_texts, [label_to_id[i] for i in val_intents]))
    generator = torch.Generator().manual_seed(config.seed)
    train_loader = DataLoader(train_pairs, batch_size=config.batch_size, shuffle=True,
                              collate_fn=collate, generator=generator)
    val_loader = DataLoader(val_pairs, batch_size=64, collate_fn=collate)

    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate,
                                  weight_decay=config.weight_decay)
    total_steps = len(train_loader) * config.max_epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer, int(total_steps * config.warmup_ratio), total_steps
    )
    loss_fn = torch.nn.CrossEntropyLoss(weight=class_weights(train_intents, labels))

    best_f1, best_state, best_epoch, stale = -1.0, None, 0, 0
    history = []
    started = time.perf_counter()
    for epoch in range(1, config.max_epochs + 1):
        model.train()
        running_loss = 0.0
        for batch in train_loader:
            targets = batch.pop("labels")
            loss = loss_fn(model(**batch).logits, targets)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            running_loss += loss.item()

        y_true, y_pred = evaluate_loader(model, val_loader)
        val = classification_metrics([labels[i] for i in y_true], [labels[i] for i in y_pred])
        epoch_log = {"epoch": epoch, "train_loss": round(running_loss / len(train_loader), 4),
                     "val_accuracy": val["accuracy"], "val_macro_f1": val["macro_f1"]}
        history.append(epoch_log)
        logger.info("epoch %(epoch)d  loss %(train_loss).4f  val_acc %(val_accuracy).4f  "
                    "val_macro_f1 %(val_macro_f1).4f", epoch_log)

        if val["macro_f1"] > best_f1:
            best_f1, best_epoch, stale = val["macro_f1"], epoch, 0
            best_state = copy.deepcopy(model.state_dict())
        else:
            stale += 1
            if stale >= config.patience:
                logger.info("Early stopping after epoch %d (best epoch %d)", epoch, best_epoch)
                break

    model.load_state_dict(best_state)
    num_parameters = sum(p.numel() for p in model.parameters())
    if config.save_fp16:
        model.half()
    output_dir.mkdir(parents=True, exist_ok=True)
    # Shards stay below GitHub's 100 MB per-file limit; transformers reloads them transparently.
    model.save_pretrained(output_dir, max_shard_size="90MB")
    tokenizer.save_pretrained(output_dir)

    summary = {
        "config": asdict(config),
        "best_epoch": best_epoch,
        "best_val_macro_f1": best_f1,
        "training_seconds": round(time.perf_counter() - started, 1),
        "num_parameters": num_parameters,
        "train_size": len(train_pairs),
        "val_size": len(val_pairs),
        "history": history,
    }
    write_json(output_dir / "training_summary.json", summary)
    return summary


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", help="Hugging Face model id (default: training/config.yaml)")
    parser.add_argument("--output-dir", type=Path, default=MODEL_DIR)
    parser.add_argument("--learning-rate", type=float)
    parser.add_argument("--epochs", type=int)
    args = parser.parse_args()

    settings = yaml.safe_load(CONFIG_FILE.read_text())
    if args.model:
        settings["model_name"] = args.model
    if args.learning_rate:
        settings["learning_rate"] = args.learning_rate
    if args.epochs:
        settings["max_epochs"] = args.epochs
    config = TrainConfig(**settings)

    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    summary = fine_tune(config, output_dir)
    logger.info("Saved best model (epoch %d, val macro-F1 %.4f) to %s",
                summary["best_epoch"], summary["best_val_macro_f1"], output_dir.relative_to(ROOT))


if __name__ == "__main__":
    main()
