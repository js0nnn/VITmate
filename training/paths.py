"""Project-relative paths shared by the training scripts."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
AUTHORED_DIR = DATA_DIR / "authored"
PROCESSED_DIR = DATA_DIR / "processed"
TAXONOMY_FILE = DATA_DIR / "taxonomy.yaml"

ARTIFACTS_DIR = ROOT / "artifacts"  # candidate checkpoints (git-ignored)
MODEL_DIR = ROOT / "backend" / "trained_model"  # model served by the backend
RESULTS_DIR = ROOT / "docs" / "results"  # metrics and figures for the report
