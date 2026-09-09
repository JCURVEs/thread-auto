"""Audit publication dates and preserve stale entries outside daily news."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rss_collector import fetch_article_published_date
from scripts.repair_archive_korean import split_archive, parse_entry


def audit(path, apply=False, source=None):
    header, blocks = split_archive(path.read_text(encoding="utf-8"))
    collected = datetime.strptime(path.stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    entries = [parse_entry(block) for block in blocks]
    with ThreadPoolExecutor(max_workers=4) as pool:
        dates = list(pool.map(
            lambda entry: fetch_article_published_date(entry["source_url"]) if not source or entry["source_name"] == source else None,
            entries,
        ))
    report, kept, excluded = [], [], []
    for entry, block, published in zip(entries, blocks, dates):
        status = "unknown"
        if published:
            # With only a collection day, reject only definitely stale items.
            status = "stale" if published < collected - timedelta(hours=48) else "recent"
            if published > collected + timedelta(days=1):
                status = "future"
        row = {"url": entry["source_url"], "published_at": published.isoformat() if published else None, "status": status}
        report.append(row)
        if status in {"stale", "future"}:
            excluded.append({**row, "collected_on": path.stem, "original_block": block})
        else:
            if published and "**원문발행일:**" not in block:
                heading, rest = block.split("\n", 1)
                block = f"{heading}\n\n**원문발행일:** {published.isoformat()}\n\n**수집일:** {path.stem}\n" + rest
            kept.append(block)
    if apply:
        if excluded:
            target = ROOT / "archive" / "excluded" / f"{path.stem}.jsonl"
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("a", encoding="utf-8") as file:
                for row in excluded:
                    file.write(json.dumps(row, ensure_ascii=False) + "\n")
        path.write_text((header + "".join(kept)).rstrip() + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dates", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--source")
    args = parser.parse_args()
    for day in args.dates.split(","):
        path = ROOT / "archive" / day[:4] / f"{day[5:7]}월" / f"{day}.md"
        print(json.dumps({"date": day, "entries": audit(path, args.apply, args.source)}, ensure_ascii=False, indent=2))
