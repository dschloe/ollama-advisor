"""Fetch PyPI download stats and update README badge tables."""

import json
import re
import urllib.request
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


def main():
    recent = fetch_json(f"https://pypistats.org/api/packages/{PACKAGE}/recent")
    today_str = datetime.now(KST).strftime("%Y-%m-%d")

    daily = recent["data"]["last_day"]

    overall = fetch_json(
        f"https://pypistats.org/api/packages/{PACKAGE}/overall?mirrors=true"
    )
    total = sum(row["downloads"] for row in overall["data"])

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
