from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "quotes.db"
DEFAULT_ORIGINS = ("*",)


def database_path() -> Path:
    value = os.getenv("SHADOW_SLAVE_DB")
    return Path(value).expanduser().resolve() if value else DEFAULT_DB


def allowed_origins() -> list[str]:
    value = os.getenv("ALLOWED_ORIGINS")
    if not value:
        return list(DEFAULT_ORIGINS)
    return [origin.strip() for origin in value.split(",") if origin.strip()]
