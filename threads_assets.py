"""
Local storage helpers for Threads account assets.

Raw exports and normalized post corpora may contain private account history, so
the default data paths are ignored by git.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

from dateutil import parser as date_parser
import requests


PROJECT_ROOT = Path(__file__).resolve().parent
THREADS_DATA_DIR = PROJECT_ROOT / "data" / "threads"
RAW_RUNS_DIR = THREADS_DATA_DIR / "raw" / "runs"
NORMALIZED_DIR = THREADS_DATA_DIR / "normalized"
MEDIA_DIR = THREADS_DATA_DIR / "media"
NORMALIZED_POSTS_PATH = NORMALIZED_DIR / "posts.jsonl"
STYLE_PROFILE_PATH = THREADS_DATA_DIR / "style_profile.json"


def utc_run_id() -> str:
    """Return a compact UTC run id for export filenames."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_threads_timestamp(value: str) -> Optional[datetime]:
    """Parse a Threads timestamp into UTC when possible."""
    if not value:
        return None
    try:
        parsed = date_parser.parse(value)
    except (TypeError, ValueError):
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalize_post(post: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize one raw Threads API media object for style analysis."""
    timestamp = parse_threads_timestamp(str(post.get("timestamp", "")))
    root_post = post.get("root_post") if isinstance(post.get("root_post"), dict) else {}
    replied_to = post.get("replied_to") if isinstance(post.get("replied_to"), dict) else {}
    children = post.get("children", [])
    if not isinstance(children, list):
        children = []

    normalized: Dict[str, Any] = {
        "id": str(post.get("id", "")).strip(),
        "username": str(post.get("username", "")).strip(),
        "text": str(post.get("text", "")).strip(),
        "timestamp": timestamp.isoformat() if timestamp else str(post.get("timestamp", "")),
        "date": timestamp.date().isoformat() if timestamp else "",
        "media_type": str(post.get("media_type", "")).strip(),
        "media_product_type": str(post.get("media_product_type", "")).strip(),
        "media_url": str(post.get("media_url", "")).strip(),
        "gif_url": str(post.get("gif_url", "")).strip(),
        "thumbnail_url": str(post.get("thumbnail_url", "")).strip(),
        "alt_text": str(post.get("alt_text", "")).strip(),
        "link_attachment_url": str(post.get("link_attachment_url", "")).strip(),
        "children": children,
        "permalink": str(post.get("permalink", "")).strip(),
        "shortcode": str(post.get("shortcode", "")).strip(),
        "is_quote_post": bool(post.get("is_quote_post", False)),
        "quoted_post": post.get("quoted_post"),
        "reposted_post": post.get("reposted_post"),
        "has_replies": bool(post.get("has_replies", False)),
        "is_reply": bool(post.get("is_reply", False)),
        "is_reply_owned_by_me": bool(post.get("is_reply_owned_by_me", False)),
        "root_post_id": str(root_post.get("id", "")).strip(),
        "replied_to_id": str(replied_to.get("id", "")).strip(),
        "poll_attachment": post.get("poll_attachment"),
        "raw": post,
    }
    return normalized


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Read JSON lines from a file, returning an empty list when absent."""
    if not path.exists():
        return []

    records = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records


def write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> None:
    """Write records as UTF-8 JSON lines."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            file.write("\n")


def media_urls_for_post(post: Dict[str, Any]) -> List[Dict[str, str]]:
    """Return downloadable media URLs from a normalized or raw Threads post."""
    media_items = []
    for field in ("media_url", "thumbnail_url", "gif_url"):
        value = str(post.get(field, "")).strip()
        if value:
            media_items.append({"field": field, "url": value})

    children = post.get("children", [])
    if isinstance(children, list):
        for index, child in enumerate(children):
            if not isinstance(child, dict):
                continue
            for field in ("media_url", "thumbnail_url", "gif_url"):
                value = str(child.get(field, "")).strip()
                if value:
                    media_items.append({"field": f"children_{index}_{field}", "url": value})

    return media_items


def _extension_from_url_or_type(url: str, content_type: str = "") -> str:
    path = urlparse(url).path
    suffix = Path(path).suffix.lower()
    if suffix and re.match(r"^\.[a-z0-9]{2,5}$", suffix):
        return suffix

    content_type = content_type.lower()
    if "jpeg" in content_type or "jpg" in content_type:
        return ".jpg"
    if "png" in content_type:
        return ".png"
    if "webp" in content_type:
        return ".webp"
    if "gif" in content_type:
        return ".gif"
    if "mp4" in content_type:
        return ".mp4"
    if "quicktime" in content_type:
        return ".mov"
    return ".bin"


def download_media_assets(
    posts: Iterable[Dict[str, Any]],
    media_dir: Path = MEDIA_DIR,
    timeout: int = 60,
    session: Any = None,
) -> List[Dict[str, str]]:
    """
    Download media files referenced by normalized posts.

    This is optional because historical video exports can become large.
    """
    http = session or requests
    manifest = []
    seen_urls = set()

    for post in posts:
        post_id = str(post.get("id", "")).strip()
        if not post_id:
            continue

        post_date = str(post.get("date", "")).strip() or "unknown"
        year_month = post_date[:7] if len(post_date) >= 7 else "unknown"
        target_dir = media_dir / year_month / post_id

        for item in media_urls_for_post(post):
            url = item["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)

            response = http.get(url, timeout=timeout)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            extension = _extension_from_url_or_type(url, content_type)
            filename = f"{item['field']}{extension}"
            path = target_dir / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(response.content)
            manifest.append({
                "post_id": post_id,
                "field": item["field"],
                "url": url,
                "path": str(path),
                "content_type": content_type,
            })

    return manifest


def merge_normalized_posts(
    new_posts: Iterable[Dict[str, Any]],
    existing_posts: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Merge normalized posts by id, preferring newer export values."""
    merged: Dict[str, Dict[str, Any]] = {}
    for post in existing_posts:
        post_id = str(post.get("id", ""))
        if post_id:
            merged[post_id] = post

    for post in new_posts:
        post_id = str(post.get("id", ""))
        if post_id:
            merged[post_id] = post

    return sorted(
        merged.values(),
        key=lambda item: str(item.get("timestamp", "")),
        reverse=True,
    )


def save_threads_export(
    raw_posts: Iterable[Dict[str, Any]],
    data_dir: Path = THREADS_DATA_DIR,
    run_id: Optional[str] = None,
) -> Tuple[Path, Path, int]:
    """Save raw export and merged normalized corpus."""
    posts = list(raw_posts)
    normalized_posts = [normalize_post(post) for post in posts]
    run_id = run_id or utc_run_id()

    raw_path = data_dir / "raw" / "runs" / f"threads_export_{run_id}.jsonl"
    normalized_path = data_dir / "normalized" / "posts.jsonl"

    write_jsonl(raw_path, posts)
    existing = read_jsonl(normalized_path)
    merged = merge_normalized_posts(normalized_posts, existing)
    write_jsonl(normalized_path, merged)

    return raw_path, normalized_path, len(normalized_posts)


def group_posts_into_threads(posts: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Group normalized posts into root thread chains.

    A Threads multi-post sequence is represented as a top-level post plus
    replies. We keep only the data shape here; style analysis can then learn
    from the full 1/ 2/ 3/ chain rather than isolated posts.
    """
    post_list = list(posts)
    by_root: Dict[str, List[Dict[str, Any]]] = {}

    for post in post_list:
        root_id = post.get("root_post_id") or post.get("id")
        if not root_id:
            continue
        by_root.setdefault(str(root_id), []).append(post)

    threads = []
    for root_id, items in by_root.items():
        ordered = sorted(items, key=lambda item: str(item.get("timestamp", "")))
        root = next((item for item in ordered if item.get("id") == root_id), ordered[0])
        threads.append({
            "root_post_id": root_id,
            "username": root.get("username", ""),
            "started_at": root.get("timestamp", ""),
            "permalink": root.get("permalink", ""),
            "post_count": len(ordered),
            "posts": ordered,
            "combined_text": "\n\n".join(
                item.get("text", "")
                for item in ordered
                if item.get("text")
            ),
            "media": [
                {
                    "post_id": item.get("id", ""),
                    "media_type": item.get("media_type", ""),
                    "media_url": item.get("media_url", ""),
                    "thumbnail_url": item.get("thumbnail_url", ""),
                    "gif_url": item.get("gif_url", ""),
                    "children": item.get("children", []),
                    "alt_text": item.get("alt_text", ""),
                }
                for item in ordered
                if item.get("media_url") or item.get("thumbnail_url") or item.get("gif_url") or item.get("children")
            ],
        })

    return sorted(threads, key=lambda item: item.get("started_at", ""), reverse=True)
