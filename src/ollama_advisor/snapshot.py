"""Daily catalog snapshot export (CSV/JSON) and diff helpers."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .catalog import expand_runnable_rows, get_catalog

DEFAULT_DATA_DIR = Path("data/catalog")
CSV_COLUMNS = [
    "identifier",
    "tag",
    "param_size",
    "required_gb",
    "pulls",
    "capabilities",
    "purposes",
    "description",
]


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def models_to_rows(models: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten catalog models into CSV-friendly rows."""
    rows = expand_runnable_rows(models)
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "identifier": row.get("identifier", ""),
                "tag": row.get("tag", ""),
                "param_size": row.get("param_size", ""),
                "required_gb": row.get("required_gb", ""),
                "pulls": row.get("pulls", ""),
                "capabilities": "|".join(row.get("capabilities") or []),
                "purposes": "|".join(row.get("purposes") or []),
                "description": row.get("description", ""),
            }
        )
    return out


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_identifier_set_from_csv(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return {row.get("identifier", "") for row in reader if row.get("identifier")}


def diff_identifiers(previous: set[str], current: set[str]) -> dict[str, list[str]]:
    return {
        "added": sorted(current - previous),
        "removed": sorted(previous - current),
    }


def write_catalog_snapshot(
    output_dir: Path | str = DEFAULT_DATA_DIR,
    force_refresh: bool = True,
    date: str | None = None,
) -> dict[str, Any]:
    """
    Fetch catalog and write latest + dated snapshot files.

    Writes:
      - models.csv / models.json (latest)
      - history/YYYY-MM-DD.csv
      - latest_diff.json (vs previous models.csv identifiers)
    """
    out_dir = Path(output_dir)
    history_dir = out_dir / "history"
    stamp = date or _utc_today()

    catalog = get_catalog(force_refresh=force_refresh)
    models = catalog["models"]
    rows = models_to_rows(models)

    latest_csv = out_dir / "models.csv"
    previous_ids = load_identifier_set_from_csv(latest_csv)
    current_ids = {r["identifier"] for r in rows if r["identifier"]}
    diff = diff_identifiers(previous_ids, current_ids)

    write_csv(rows, latest_csv)
    write_csv(rows, history_dir / f"{stamp}.csv")

    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "date": stamp,
        "source": catalog.get("source"),
        "updated": catalog.get("updated"),
        "model_count": len({m.get("identifier") for m in models}),
        "variant_count": len(rows),
        "diff": diff,
        "models": models,
    }
    write_json(payload, out_dir / "models.json")
    write_json(
        {
            "date": stamp,
            "source": catalog.get("source"),
            "model_count": payload["model_count"],
            "variant_count": payload["variant_count"],
            "diff": diff,
        },
        out_dir / "latest_diff.json",
    )

    return {
        "date": stamp,
        "source": catalog.get("source"),
        "model_count": payload["model_count"],
        "variant_count": payload["variant_count"],
        "diff": diff,
        "paths": {
            "csv": str(latest_csv),
            "json": str(out_dir / "models.json"),
            "history": str(history_dir / f"{stamp}.csv"),
            "diff": str(out_dir / "latest_diff.json"),
        },
    }
