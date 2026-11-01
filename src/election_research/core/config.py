"""Application configuration and environment settings."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field


def find_project_root() -> Path:
    """Locate the project root directory containing pyproject.toml."""
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").is_file():
            return parent
    return Path(__file__).resolve().parents[3]


PROJECT_ROOT = find_project_root()


class Settings(BaseModel):
    """Strongly typed application settings loaded from environment or defaults."""

    project_root: Path = Field(default_factory=find_project_root)
    app_env: Literal["development", "testing", "production"] = "development"
    log_level: str = "INFO"

    data_dir_name: str = "data"
    duckdb_path_rel: str = "data/metadata/election.duckdb"

    hf_token: str | None = None
    ai_model_id: str = "Qwen/Qwen3.5-4B"

    @classmethod
    def load(cls) -> "Settings":
        """Load settings from environment variables and .env file."""
        root = find_project_root()
        env_path = root / ".env"
        if env_path.is_file():
            load_dotenv(env_path, override=False)

        raw_env = os.environ.get("APP_ENV", "development").lower()
        if raw_env not in ("development", "testing", "production"):
            raw_env = "development"

        return cls(
            project_root=root,
            app_env=raw_env,  # type: ignore[arg-type]
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
            data_dir_name=os.environ.get("DATA_DIR", "data"),
            duckdb_path_rel=os.environ.get("DUCKDB_PATH", "data/metadata/election.duckdb"),
            hf_token=os.environ.get("HF_TOKEN"),
            ai_model_id=os.environ.get("AI_MODEL_ID", "Qwen/Qwen3.5-4B"),
        )

    @property
    def data_dir(self) -> Path:
        p = Path(self.data_dir_name)
        return p if p.is_absolute() else (self.project_root / p).resolve()

    @property
    def bronze_dir(self) -> Path:
        return self.data_dir / "bronze"

    @property
    def silver_dir(self) -> Path:
        return self.data_dir / "silver"

    @property
    def gold_dir(self) -> Path:
        return self.data_dir / "gold"

    @property
    def metadata_dir(self) -> Path:
        return self.data_dir / "metadata"

    @property
    def manifests_dir(self) -> Path:
        return self.metadata_dir / "manifests"

    @property
    def processing_history_dir(self) -> Path:
        return self.metadata_dir / "processing_history"

    @property
    def duckdb_path(self) -> Path:
        p = Path(self.duckdb_path_rel)
        return p if p.is_absolute() else (self.project_root / p).resolve()

    def ensure_directories(self) -> None:
        """Create standard data directories if they do not exist."""
        for path in [
            self.bronze_dir,
            self.silver_dir,
            self.gold_dir,
            self.metadata_dir,
            self.manifests_dir,
            self.processing_history_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached instance of the application settings."""
    return Settings.load()
