"""Application settings.

All runtime data lives outside the source tree by default: ``data/local`` under
the project root.  The SQLite file is never committed (see .gitignore).
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TRELLIS_", env_file=".env", extra="ignore")

    app_name: str = "Trellis API"
    data_dir: Path = PROJECT_ROOT / "data" / "local"
    database_url: str = ""
    timezone: str = "Asia/Shanghai"
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    legacy_root: Path = PROJECT_ROOT

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "trellis.db"

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{self.sqlite_path}"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = Settings()
