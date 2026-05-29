"""Massive Dynamic — CSV data helper."""
import csv
import json
import logging
from pathlib import Path

logger = logging.getLogger("massive")

BASE_DIR = Path(__file__).resolve().parent.parent
CURATED_DIR = BASE_DIR / "data" / "curated"


def read_csv(filename: str) -> list[dict]:
    path = CURATED_DIR / filename
    if not path.exists():
        logger.warning("CSV not found: %s", path)
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_json(filename: str) -> list[dict]:
    path = BASE_DIR / "data" / filename
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


# Keep backwards-compatible API
def query(sql: str, *args) -> list[dict]:
    logger.debug("CSV mode: query called with %s", sql[:60])
    return []


def execute(sql: str, *args) -> None:
    logger.debug("CSV mode: execute called with %s", sql[:60])
