"""Fetch PyPI download stats and update README tables."""

import json
import html
import re
import urllib.request
from urllib.error import HTTPError
from datetime import datetime, timezone, timedelta

PACKAGE = "ollama-advisor"
KST = timezone(timedelta(hours=9))


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ollama-advisor-readme-stats/0.1",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def fetch_text(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ollama-advisor-readme-stats/0.1",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_daily_downloads() -> int:
    try:
        recent = fetch_json(f"https://pypistats.org/api/packages/{PACKAGE}/recent")
        return int(recent["data"]["last_day"])
    except HTTPError as exc:
        if exc.code != 429:
            raise

    page = fetch_text(f"https://pypistats.org/packages/{PACKAGE}")
    match = re.search(r"Downloads last day:\s*([0-9,]+)", html.unescape(page))
    if not match:
        raise RuntimeError("Could not determine daily downloads from PyPI Stats")
    return int(match.group(1).replace(",", ""))


def load_previous_stats(readme_path: str) -> tuple[str | None, int | None, int | None]:
    try:
        with open(readme_path, "r") as f:
            content = f.read()
    except FileNotFoundError:
        return None, None, None

    date_match = re.search(r"\| \*\*Today\*\* \((\d{4}-\d{2}-\d{2})\) \| ([0-9,]+|—) \|", content)
    total_match = re.search(r"\| \*\*Total \(cumulative\)\*\* \| ([0-9,]+|—) \|", content)

    prev_date = date_match.group(1) if date_match else None
    prev_daily = None
    prev_total = None

    if date_match and date_match.group(2) != "—":
        prev_daily = int(date_match.group(2).replace(",", ""))
    if total_match and total_match.group(1) != "—":
        prev_total = int(total_match.group(1).replace(",", ""))

    return prev_date, prev_daily, prev_total


def compute_total(today_str: str, daily: int, prev_date: str | None, prev_daily: int | None, prev_total: int | None) -> int:
    if prev_total is None:
        return daily
    if prev_date == today_str and prev_daily is not None:
        return prev_total - prev_daily + daily
    return prev_total + daily


def main():
    today_str = datetime.now(KST).strftime("%Y-%m-%d")
    daily = fetch_daily_downloads()
    prev_date, prev_daily, prev_total = load_previous_stats("README.md")
    total = compute_total(today_str, daily, prev_date, prev_daily, prev_total)

    stats_block = (
        f"## 📦 Download Stats\n"
        f"\n"
        f"| Metric | Count |\n"
        f"|--------|------:|\n"
        f"| **Today** ({today_str}) | {daily:,} |\n"
        f"| **Total (cumulative)** | {total:,} |\n"
        f"\n"
        f"> Updated daily via GitHub Actions\n"
    )

    for readme_path in ("README.md", "README.ko.md"):
        try:
            with open(readme_path, "r") as f:
                content = f.read()
        except FileNotFoundError:
            continue

        pattern = r"## 📦 Download Stats\n.*?(?=\n## |\Z)"
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, stats_block.rstrip(), content, flags=re.DOTALL)
        else:
            content = content.rstrip() + "\n\n" + stats_block

        with open(readme_path, "w") as f:
            f.write(content)

    print(f"Updated: daily={daily}, total={total}")


if __name__ == "__main__":
    main()
