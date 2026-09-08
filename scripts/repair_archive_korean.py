"""Repair legacy fallback archive entries with validated Korean summaries."""

import argparse
import os
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ai_analyzer import (  # noqa: E402
    AIAnalysisError,
    PROVIDERS,
    calibrate_importance,
    create_client,
    generate_thread_content,
    validate_content,
    validate_factual_grounding,
    validate_quality_gate,
)


SOURCE_KEYS = {
    "OpenAI": "openai",
    "Anthropic": "anthropic",
    "DeepMind": "deepmind",
    "Google Research": "google_research",
    "Hugging Face": "huggingface",
    "Meta AI": "meta_research",
    "NVIDIA": "nvidia_technical",
    "NVIDIA Korea": "nvidia_korea_blog",
    "Microsoft Research": "microsoft_research",
    "Google Cloud AI": "google_cloud_ai",
    "arXiv AI": "arxiv_ai",
    "arXiv ML": "arxiv_lg",
    "arXiv Vision": "arxiv_cv",
    "arXiv NLP": "arxiv_cl",
}

MAX_QUALITY_ATTEMPTS = 3


def split_archive(text: str) -> tuple[str, list[str]]:
    """Split one daily Markdown archive into its header and entry blocks."""
    starts = [match.start() for match in re.finditer(r"(?m)^## \[", text)]
    if not starts:
        return text, []

    header = text[: starts[0]]
    blocks = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(text)
        blocks.append(text[start:end].rstrip() + "\n\n")
    return header, blocks


def extract_field(block: str, label: str) -> str:
    """Extract a Markdown metadata field with a possibly multiline value."""
    pattern = re.compile(
        rf"\*\*{re.escape(label)}:\*\*\s*(.*?)"
        rf"(?=\n\*\*[^*\n]+:\*\*|\n!\[|\Z)",
        re.DOTALL,
    )
    match = pattern.search(block)
    return match.group(1).strip() if match else ""


def parse_entry(block: str) -> dict:
    """Parse the fields needed to regenerate one fallback entry."""
    heading = re.search(r"(?m)^## \[([^\]]+)\] (.+)$", block)
    if not heading:
        raise ValueError("entry_heading_missing")

    source_label, current_title = heading.groups()
    image = re.search(r"(?m)^!\[[^\]]*\]\(.+\)$", block)
    rss_summary = extract_field(block, "RSS요약") or extract_field(block, "요약")
    return {
        "source_label": source_label,
        "source_name": SOURCE_KEYS.get(source_label, source_label.lower().replace(" ", "_")),
        "current_title": current_title.strip(),
        "original_title": extract_field(block, "원문제목") or current_title.strip(),
        "rss_summary": rss_summary,
        "source_url": extract_field(block, "출처"),
        "image_line": image.group(0) if image else "",
    }


def render_entry(entry: dict, content: dict) -> str:
    """Render a repaired entry in the canonical Korean archive format."""
    lines = [
        f"## [{entry['source_label']}] {content['title']}\n\n",
        f"**분야:** {content['category']} | **중요도:** {content['importance']}점\n\n",
    ]
    if "importance_original" in content:
        reason = content.get("importance_adjusted_reason", "rule_based_calibration")
        lines.append(
            f"**중요도보정:** {content['importance_original']}점 → "
            f"{content['importance']}점 ({reason})\n\n"
        )
    lines.extend(
        [
            f"**요약:**  \n{content['summary']}\n\n",
            f"**쉬운설명:**  \n{content['easy_explainer']}\n\n",
            f"**출처:** {entry['source_url']}\n\n",
            f"**원문제목:** {entry['original_title']}\n\n",
            "**본문분석:** 미사용\n\n",
            f"**RSS요약:**  \n{entry['rss_summary']}\n\n",
        ]
    )
    if entry["image_line"]:
        lines.append(entry["image_line"] + "\n\n")
    return "".join(lines)


def repair_archive(path: Path, client: dict, limit: int = 0) -> dict:
    """Repair fallback entries in one archive and return operation counts."""
    original = path.read_text(encoding="utf-8")
    header, blocks = split_archive(original)
    repaired = 0
    failed = 0
    output_blocks = []

    for block in blocks:
        if "**분석상태:** fallback" not in block or (limit and repaired >= limit):
            output_blocks.append(block)
            continue

        entry = parse_entry(block)
        if not entry["rss_summary"] or not entry["source_url"]:
            print(f"[FAIL] {entry['current_title']}: source metadata missing")
            failed += 1
            output_blocks.append(block)
            continue

        content = None
        errors = []
        for attempt in range(1, MAX_QUALITY_ATTEMPTS + 1):
            try:
                candidate = generate_thread_content(
                    client,
                    entry["original_title"],
                    entry["rss_summary"],
                    max_retries=3,
                )
            except AIAnalysisError as error:
                errors = [str(error)]
                continue

            if not validate_content(candidate):
                errors = ["invalid content"]
                continue

            candidate = calibrate_importance(
                candidate,
                source_name=entry["source_name"],
                original_title=entry["original_title"],
                original_summary=entry["rss_summary"],
            )
            quality_ok, quality_errors = validate_quality_gate(candidate)
            grounded, grounding_errors = validate_factual_grounding(
                candidate,
                original_title=entry["original_title"],
                original_summary=entry["rss_summary"],
            )
            errors = quality_errors + grounding_errors
            if quality_ok and grounded:
                content = candidate
                break
            print(
                f"[RETRY {attempt}/{MAX_QUALITY_ATTEMPTS}] "
                f"{entry['current_title']}: {', '.join(errors)}"
            )

        if content is None:
            print(f"[FAIL] {entry['current_title']}: {', '.join(errors)}")
            failed += 1
            output_blocks.append(block)
            continue

        output_blocks.append(render_entry(entry, content))
        repaired += 1
        print(f"[OK] {entry['current_title']} -> {content['title']}")

    updated = header + "".join(output_blocks)
    if updated != original:
        path.write_text(updated.rstrip() + "\n", encoding="utf-8")
    return {"repaired": repaired, "failed": failed, "total": len(blocks)}


def archive_path_for_date(date_text: str) -> Path:
    """Resolve YYYY-MM-DD to the repository's year/month archive path."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_text):
        raise ValueError(f"invalid date: {date_text}")
    year, month, _ = date_text.split("-")
    return ROOT_DIR / "archive" / year / f"{month}월" / f"{date_text}.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dates", required=True, help="Comma-separated YYYY-MM-DD dates")
    parser.add_argument("--limit", type=int, default=0, help="Maximum repairs per file; 0 means all")
    args = parser.parse_args()

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("[ERROR] GROQ_API_KEY is required")
        return 2

    model = os.environ.get("GROQ_MODEL") or PROVIDERS["groq"]["default_model"]
    client = create_client(api_key, "groq", model)
    total_repaired = 0
    total_failed = 0

    for date_text in [value.strip() for value in args.dates.split(",") if value.strip()]:
        path = archive_path_for_date(date_text)
        if not path.is_file():
            print(f"[ERROR] archive not found: {path}")
            total_failed += 1
            continue
        result = repair_archive(path, client, limit=args.limit)
        total_repaired += result["repaired"]
        total_failed += result["failed"]
        print(f"[RESULT] {date_text}: {result}")

    print(f"[TOTAL] repaired={total_repaired}, failed={total_failed}")
    return 1 if total_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
