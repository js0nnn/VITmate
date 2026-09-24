"""Application settings, read from environment variables or a `.env` file."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", env_prefix="VITMATE_", extra="ignore")

    env: str = "development"  # "production" hides API docs
    model_dir: Path = ROOT / "backend" / "trained_model"
    knowledge_file: Path = ROOT / "data" / "knowledge" / "vit_knowledge.yaml"
    frontend_dist: Path = ROOT / "frontend" / "dist"  # served at / when it exists

    # Predictions below this softmax probability get the "please rephrase" reply.
    # 0.35 maximised validation macro-F1 in the threshold sweep (docs/results/evaluation.md).
    confidence_threshold: float = Field(0.35, ge=0.0, le=1.0)
    max_message_length: int = 500
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    torch_threads: int | None = None  # limit CPU threads on small hosts
    log_level: str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    for field in ("model_dir", "knowledge_file", "frontend_dist"):
        path = getattr(settings, field)
        if not path.is_absolute():  # relative paths are relative to the project root
            setattr(settings, field, ROOT / path)
    return settings
