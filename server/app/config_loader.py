import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.mock.catalog import DATA_ASSETS, METRIC_DEFINITIONS
from app.settings import settings


DEFAULT_DATA_ASSETS_PATH = Path(__file__).resolve().parents[1] / "config" / "data_assets.json"


def data_assets_path() -> Path:
    return settings.chatbi_data_assets_path


@lru_cache(maxsize=1)
def load_data_catalog() -> dict[str, Any]:
    path = data_assets_path()
    if not path.exists():
        return fallback_data_catalog(path, "config file not found")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fallback_data_catalog(path, f"failed to load config file: {exc}")

    assets = payload.get("assets")
    metric_definitions = payload.get("metric_definitions")
    if not isinstance(assets, list) or not isinstance(metric_definitions, list):
        return fallback_data_catalog(path, "config file must contain assets and metric_definitions lists")

    return {
        "version": payload.get("version", "external"),
        "source": "json",
        "path": str(path),
        "assets": assets,
        "metric_definitions": metric_definitions,
    }


def fallback_data_catalog(path: Path, reason: str) -> dict[str, Any]:
    return {
        "version": "fallback.mock.constants",
        "source": "fallback",
        "path": str(path),
        "fallback_reason": reason,
        "assets": DATA_ASSETS,
        "metric_definitions": METRIC_DEFINITIONS,
    }
