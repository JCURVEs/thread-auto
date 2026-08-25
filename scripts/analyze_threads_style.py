"""Analyze local Threads history and write a private style profile."""

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from style_analyzer import analyze_style, load_normalized_posts, save_style_profile
from threads_assets import NORMALIZED_POSTS_PATH, STYLE_PROFILE_PATH


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=NORMALIZED_POSTS_PATH)
    parser.add_argument("--output", type=Path, default=STYLE_PROFILE_PATH)
    parser.add_argument("--username", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    posts = load_normalized_posts(args.input)
    if not posts:
        print(f"분석할 posts.jsonl이 없습니다: {args.input}")
        return 1

    profile = analyze_style(posts, username=args.username)
    save_style_profile(profile, args.output)
    print(f"sample_size={profile['sample_size']}")
    print(f"style_profile={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
