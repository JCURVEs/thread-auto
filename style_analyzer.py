"""
Analyze past Threads posts into a reusable writing style profile.
"""

from collections import Counter
import json
from pathlib import Path
import re
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Optional

from threads_assets import (
    NORMALIZED_POSTS_PATH,
    STYLE_PROFILE_PATH,
    group_posts_into_threads,
    read_jsonl,
)


STYLE_MARKERS = (
    "근데",
    "핵심은",
    "먼저",
    "쉽게 말하면",
    "문제는",
    "결과가",
    "중요한 건",
    "왜냐하면",
    "이게 중요한 이유",
    "정리하면",
)

ENDING_PATTERNS = (
    "입니다",
    "습니다",
    "거든요",
    "거죠",
    "죠",
    "요",
    "합니다",
    "했습니다",
)


def load_normalized_posts(path: Path = NORMALIZED_POSTS_PATH) -> List[Dict[str, Any]]:
    """Load normalized Threads posts for analysis."""
    return read_jsonl(path)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+\n", "\n", value.strip())


def _sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?。]|다|요|죠)\s+", text)
    return [part.strip() for part in parts if part.strip()]


def _percentile(values: List[int], ratio: float) -> int:
    if not values:
        return 0
    index = min(len(values) - 1, max(0, round((len(values) - 1) * ratio)))
    return sorted(values)[index]


def _top_counter(counter: Counter, limit: int = 10) -> List[Dict[str, Any]]:
    return [
        {"text": key, "count": count}
        for key, count in counter.most_common(limit)
    ]


def analyze_style(
    posts: Iterable[Dict[str, Any]],
    username: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a deterministic style profile from historical Threads posts."""
    post_list = list(posts)
    texts = []
    for post in post_list:
        text = _clean_text(str(post.get("text", "")))
        if not text:
            continue
        if username and post.get("username") and post.get("username") != username:
            continue
        texts.append(text)

    thread_chains = [
        chain
        for chain in group_posts_into_threads(post_list)
        if chain["post_count"] > 1
        and (not username or chain.get("username") == username)
    ]
    chain_texts = [
        _clean_text(str(chain.get("combined_text", "")))
        for chain in thread_chains
        if chain.get("combined_text")
    ]

    char_counts = [len(text) for text in texts]
    line_counts = [len([line for line in text.splitlines() if line.strip()]) for text in texts]
    sentence_counts = [len(_sentences(text)) for text in texts]

    marker_counter = Counter()
    ending_counter = Counter()
    numbering_counter = Counter()
    opening_counter = Counter()

    for text in texts:
        for marker in STYLE_MARKERS:
            if marker in text:
                marker_counter[marker] += text.count(marker)

        for sentence in _sentences(text):
            for ending in ENDING_PATTERNS:
                if sentence.rstrip(".!?").endswith(ending):
                    ending_counter[ending] += 1
                    break

        for line in text.splitlines():
            stripped = line.strip()
            numbering = re.match(r"^(\d+)/\s*(.+)?$", stripped)
            if numbering:
                numbering_counter[numbering.group(1)] += 1
            if stripped:
                opening_counter[stripped[:28]] += 1
                break

    numbered_posts = sum(1 for text in texts if re.search(r"(?m)^\s*\d+/", text))
    hook_posts = sum(1 for text in texts if "핵심내용 정리했습니다" in text)
    media_posts = sum(
        1
        for post in post_list
        if post.get("media_url")
        or post.get("thumbnail_url")
        or post.get("gif_url")
        or post.get("children")
    )

    profile = {
        "profile_version": 1,
        "source": "threads_history",
        "username": username or "",
        "sample_size": len(texts),
        "length": {
            "chars_avg": round(mean(char_counts), 1) if char_counts else 0,
            "chars_median": median(char_counts) if char_counts else 0,
            "chars_p25": _percentile(char_counts, 0.25),
            "chars_p75": _percentile(char_counts, 0.75),
            "lines_avg": round(mean(line_counts), 1) if line_counts else 0,
            "lines_median": median(line_counts) if line_counts else 0,
            "sentences_avg": round(mean(sentence_counts), 1) if sentence_counts else 0,
        },
        "structure": {
            "numbered_post_ratio": round(numbered_posts / len(texts), 3) if texts else 0,
            "hook_phrase_ratio": round(hook_posts / len(texts), 3) if texts else 0,
            "numbering_distribution": _top_counter(numbering_counter, limit=12),
            "thread_chain_count": len(thread_chains),
            "thread_chain_post_count_avg": round(
                mean([chain["post_count"] for chain in thread_chains]),
                1,
            ) if thread_chains else 0,
        },
        "media": {
            "media_post_ratio": round(media_posts / len(post_list), 3) if post_list else 0,
        },
        "voice": {
            "style_markers": _top_counter(marker_counter),
            "sentence_endings": _top_counter(ending_counter),
            "common_openings": _top_counter(opening_counter),
        },
        "generation_hints": build_generation_hints(
            texts=texts + chain_texts,
            marker_counter=marker_counter,
            ending_counter=ending_counter,
            numbered_posts=numbered_posts,
            hook_posts=hook_posts,
            thread_chain_count=len(thread_chains),
        ),
    }
    return profile


def build_generation_hints(
    texts: List[str],
    marker_counter: Counter,
    ending_counter: Counter,
    numbered_posts: int,
    hook_posts: int,
    thread_chain_count: int = 0,
) -> Dict[str, Any]:
    """Convert observed stats into practical prompt hints."""
    sample_size = len(texts)
    numbered_ratio = numbered_posts / sample_size if sample_size else 0
    hook_ratio = hook_posts / sample_size if sample_size else 0
    preferred_markers = [item for item, _ in marker_counter.most_common(6)]
    preferred_endings = [item for item, _ in ending_counter.most_common(5)]

    return {
        "use_numbered_slides": numbered_ratio >= 0.2 or thread_chain_count > 0,
        "use_hook_line": hook_ratio >= 0.1,
        "prefer_thread_chain": thread_chain_count > 0,
        "preferred_markers": preferred_markers,
        "preferred_sentence_endings": preferred_endings,
        "avoid": [
            "원문에 없는 성능 수치 추가",
            "중국어/일본어/러시아어 문자 혼입",
            "마케팅 문구처럼 과장된 표현",
            "너무 긴 한 문장 설명",
        ],
    }


def save_style_profile(profile: Dict[str, Any], path: Path = STYLE_PROFILE_PATH) -> None:
    """Persist the style profile as private local JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
