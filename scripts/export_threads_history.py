"""Export authenticated Threads account history into local private assets."""

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from threads_assets import download_media_assets, read_jsonl, THREADS_DATA_DIR, save_threads_export
from threads_history_client import (
    DEFAULT_THREAD_FIELDS,
    ThreadsApiError,
    iter_thread_conversation,
    iter_user_threads,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", help="Start date accepted by Threads API, e.g. 2026-01-01")
    parser.add_argument("--until", help="End date accepted by Threads API, e.g. 2026-08-07")
    parser.add_argument("--limit", type=int, default=50, help="Posts per API page")
    parser.add_argument("--max-pages", type=int, default=None, help="Optional API page limit")
    parser.add_argument(
        "--include-conversations",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fetch conversation trees for posts with replies to preserve 1/ 2/ 3/ chains",
    )
    parser.add_argument(
        "--conversation-max-pages",
        type=int,
        default=None,
        help="Optional page limit per conversation",
    )
    parser.add_argument(
        "--download-media",
        action="store_true",
        help="Download image/video/GIF/thumbnail files after metadata export",
    )
    parser.add_argument("--fields", default=DEFAULT_THREAD_FIELDS, help="Comma-separated Threads fields")
    parser.add_argument("--data-dir", type=Path, default=THREADS_DATA_DIR, help="Private data directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    access_token = os.environ.get("THREADS_ACCESS_TOKEN", "")
    if not access_token:
        print("THREADS_ACCESS_TOKEN 환경 변수가 필요합니다.")
        print("토큰은 .env 또는 로컬 환경 변수에만 두고 GitHub에 올리지 마세요.")
        return 1

    top_level_posts = list(
        iter_user_threads(
            access_token=access_token,
            fields=args.fields,
            limit=args.limit,
            since=args.since,
            until=args.until,
            max_pages=args.max_pages,
        )
    )

    posts_by_id = {str(post.get("id", "")): post for post in top_level_posts if post.get("id")}

    if args.include_conversations:
        for post in top_level_posts:
            post_id = str(post.get("id", ""))
            if not post_id or not post.get("has_replies"):
                continue

            try:
                for conversation_post in iter_thread_conversation(
                    thread_id=post_id,
                    access_token=access_token,
                    fields=args.fields,
                    max_pages=args.conversation_max_pages,
                ):
                    conversation_id = str(conversation_post.get("id", ""))
                    if conversation_id:
                        posts_by_id[conversation_id] = conversation_post
            except ThreadsApiError as error:
                print(f"conversation_fetch_failed id={post_id} error={error}")

    posts = list(posts_by_id.values())
    raw_path, normalized_path, count = save_threads_export(posts, data_dir=args.data_dir)
    print(f"exported_posts={count}")
    print(f"top_level_posts={len(top_level_posts)}")
    print(f"raw_path={raw_path}")
    print(f"normalized_path={normalized_path}")

    if args.download_media:
        normalized_posts = read_jsonl(normalized_path)
        manifest = download_media_assets(normalized_posts, media_dir=args.data_dir / "media")
        print(f"downloaded_media={len(manifest)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
