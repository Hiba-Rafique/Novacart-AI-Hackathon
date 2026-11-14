from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_repo_root(module_path: Path) -> Path:
    app_root = module_path.parents[2]
    if (app_root / "policies").is_dir():
        return app_root
    for parent in module_path.parents:
        if (parent / "policies").is_dir():
            return parent
    return app_root


_MODULE_PATH = Path(__file__).resolve()
APP_ROOT = _MODULE_PATH.parents[2]
REPO_ROOT = _find_repo_root(_MODULE_PATH)


class Settings(BaseSettings):
    """Environment-backed runtime settings.

    ``extra="ignore"`` is deliberate: Render injects variables such as ``PORT``
    and ``RENDER_*`` that are not application settings.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    app_timezone: str = "Asia/Karachi"
    log_level: str = "INFO"
    port: int = 7860

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 768
    model_timeout_seconds: float = 20.0
    max_model_concurrency: int = 3
    rag_top_k: int = 15

    policies_dir: Path = REPO_ROOT / "policies"
    data_dir: Path = APP_ROOT / "data"
    index_dir: Path = APP_ROOT / "data" / "index"

    @field_validator("rag_top_k", "embedding_dimensions", "max_model_concurrency")
    @classmethod
    def _positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be positive")
        return value

    @field_validator("model_timeout_seconds")
    @classmethod
    def _positive_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("must be positive")
        return value

    @field_validator("app_timezone")
    @classmethod
    def _valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"invalid timezone: {value}") from exc
        return value

    @field_validator("policies_dir", "data_dir", "index_dir", mode="before")
    @classmethod
    def _resolve_path(cls, value: str | Path) -> Path:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        return path

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.app_timezone)

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key and self.gemini_api_key.strip())


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
