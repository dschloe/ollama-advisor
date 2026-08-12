"""Core recommendation logic."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .catalog import expand_runnable_rows, get_catalog
from .system import format_specs_summary, get_system_specs


def _in_notebook() -> bool:
    try:
        from IPython import get_ipython  # type: ignore

        shell = get_ipython()
        if shell is None:
            return False
        return shell.__class__.__name__ in {"ZMQInteractiveShell", "Shell"}
    except ImportError:
        return False


def _display_dataframe(df: pd.DataFrame) -> None:
    from IPython.display import HTML, display  # type: ignore

    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.max_colwidth", None)
    pd.set_option("display.width", None)

    html = df.to_html(index=False, escape=False)
    styled = (
        '<div style="max-height:500px; overflow:auto; border:1px solid #ddd;">'
        f"{html}</div>"
    )
    display(HTML(styled))


def recommend(
    purpose: str = "all",
    as_dataframe: bool = True,
    top_n: int | None = None,
    force_refresh: bool = False,
) -> pd.DataFrame | list[dict[str, Any]]:
    """
    Recommend Ollama models runnable on the current machine.

    Parameters
    ----------
    purpose
        Filter by purpose: all, general, coding, reasoning, vision, embedding, audio.
    as_dataframe
        Return a pandas DataFrame when True, else a list of dicts.
    top_n
        Limit to the top N recommendations (after filtering/sorting).
    force_refresh
        Bypass catalog cache and re-crawl ollama.com/library.
    """
    specs = get_system_specs()
    catalog = get_catalog(force_refresh=force_refresh)
    rows = expand_runnable_rows(catalog["models"])

    usable = specs["usable_gb"]
    filtered = [r for r in rows if r["required_gb"] <= usable]

    purpose = purpose.lower().strip()
    if purpose not in {"all", ""}:
        filtered = [r for r in filtered if purpose in r.get("purposes", [])]

    def pulls_key(row: dict[str, Any]) -> float:
        raw = str(row.get("pulls", "") or "0")
        multipliers = {"K": 1e3, "M": 1e6, "B": 1e9}
        try:
            if raw[-1] in multipliers:
                return float(raw[:-1]) * multipliers[raw[-1]]
            return float(raw)
        except (ValueError, IndexError):
            return 0.0

    filtered.sort(key=lambda r: (-pulls_key(r), r["required_gb"], r["tag"]))

    if top_n is not None:
        filtered = filtered[:top_n]

    for row in filtered:
        row["usable_gb"] = usable
        row["platform"] = specs["platform"]
        row["fits"] = True

    columns = [
        "tag",
        "identifier",
        "description",
        "param_size",
        "required_gb",
        "usable_gb",
        "purposes",
        "capabilities",
        "pulls",
        "platform",
        "fits",
    ]

    if not filtered:
        df = pd.DataFrame(columns=columns)
        df.attrs["system_summary"] = format_specs_summary(specs)
        df.attrs["catalog_source"] = catalog.get("source")
        df.attrs["catalog_updated"] = catalog.get("updated")
        if _in_notebook() and as_dataframe:
            _display_dataframe(df)
        return df if as_dataframe else []

    df = pd.DataFrame(filtered)[columns]
    df.attrs["system_summary"] = format_specs_summary(specs)
    df.attrs["catalog_source"] = catalog.get("source")
    df.attrs["catalog_updated"] = catalog.get("updated")

    if _in_notebook() and as_dataframe:
        _display_dataframe(df)

    return df if as_dataframe else filtered
