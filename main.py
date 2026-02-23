"""
Thread-Auto: AI-powered Tech News Pipeline for Meta Threads.

This is the main entry point for the Thread-Auto pipeline.
It orchestrates RSS collection, AI analysis, and content formatting.

Supports multiple FREE AI providers:
- Groq (default, fastest, 14K req/day)
- OpenRouter (Qwen, 400+ models)
- Gemini (Google, 1.5K req/day)
"""

import os
import re
from typing import Optional
from datetime import datetime, timedelta, timezone
from time import mktime
import feedparser
from dateutil import parser as date_parser

from rss_collector import (
    fetch_feed,
    fetch_feed_or_scrape,
    get_latest_entry,
    get_entries,
    get_entry_info,
    DEFAULT_RSS_SOURCES
)
from image_extractor import get_article_image
from ai_analyzer import (
    create_client,
    generate_thread_content,
    validate_content,
    get_provider_info,
    PROVIDERS,
    DEFAULT_PROVIDER
)
from thread_formatter import print_dry_run, post_to_threads
from archiver import save_to_archive, is_duplicate


# --- Configuration ---
AI_PROVIDER = os.environ.get("AI_PROVIDER", DEFAULT_PROVIDER)
AI_MODEL = os.environ.get("AI_MODEL", None)  # None = 제공자 기본 모델 사용
THREADS_ACCESS_TOKEN = os.environ.get("THREADS_ACCESS_TOKEN")
RSS_URL = os.environ.get("RSS_URL", None)  # If None, use all sources
COLLECT_ALL_SOURCES = os.environ.get("COLLECT_ALL_SOURCES", "True").lower() in ("true", "1", "yes")
DRY_RUN = os.environ.get("DRY_RUN", "True").lower() in ("true", "1", "yes")


def get_api_key() -> Optional[str]:
    """Get API key for the configured provider."""
    config = PROVIDERS.get(AI_PROVIDER)
    if not config:
        return None
    return os.environ.get(config["env_key"])


def parse_published_date_utc(entry: dict, link: str) -> Optional[datetime]:
    """
    Extract published date from RSS entry and normalize to UTC.

    Returns:
        datetime object in UTC, or None if no date found
    """
    # Try 1: parsed date fields
    published_date = entry.get("published_parsed") or entry.get("updated_parsed")
    if published_date:
        # Convert struct_time to UTC datetime
        dt = datetime.fromtimestamp(mktime(published_date), tz=timezone.utc)
        return dt

    # Try 2: string date fields
    published_str = entry.get("published") or entry.get("updated")
    if published_str:
        try:
            dt = date_parser.parse(published_str)
            # If no timezone info, assume UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            # Convert to UTC
            return dt.astimezone(timezone.utc)
        except Exception:
            pass

    # Try 3: extract from URL pattern (last resort)
    url_date_match = re.search(r'/(\d{4})/(\d{1,2})/', link)
    if url_date_match:
        year, month = int(url_date_match.group(1)), int(url_date_match.group(2))
        # Use middle of month for better accuracy
        day = 15
        return datetime(year, month, day, tzinfo=timezone.utc)

    return None


# Maximum age for articles to be collected (48 hours covers weekend gaps)
MAX_ARTICLE_AGE_HOURS = int(os.environ.get("MAX_ARTICLE_AGE_HOURS", "48"))
# Number of recent entries to check per source
ENTRIES_PER_SOURCE = int(os.environ.get("ENTRIES_PER_SOURCE", "5"))


def process_single_entry(entry: dict, source_name: str, client: dict, model: str) -> bool:
    """
    Process a single RSS entry.

    Returns True if successfully archived, False otherwise.
    """
    info = get_entry_info(entry)

    # Check 1: Published date (within MAX_ARTICLE_AGE_HOURS, UTC-based)
    published_dt = parse_published_date_utc(entry, info["link"])

    if published_dt:
        now_utc = datetime.now(timezone.utc)
        age = now_utc - published_dt

        if age > timedelta(hours=MAX_ARTICLE_AGE_HOURS):
            print(f"  ⏰ 오래된 글 ({age.days}일 {age.seconds//3600}시간 전) - 스킵")
            return False
    else:
        # No date information - skip for safety
        print(f"  ⚠️ 발행일 정보 없음 - 스킵")
        return False

    # Check 2: Duplicate URL
    if is_duplicate(info["link"]):
        print(f"  🔁 이미 수집됨 - 스킵: {info['title'][:40]}")
        return False

    print(f"  ✅ 수집 대상: {info['title'][:60]}")

    # Step 2: Extract image
    image_url = get_article_image(info["link"])
    if image_url:
        print(f"  🖼️ 이미지: {image_url[:50]}...")
    else:
        print("  ⚠️ 이미지 없음")

    # Step 3: AI Analysis
    print(f"  🤖 AI 분석 중...")
    try:
        content = generate_thread_content(
            client,
            info["title"],
            info["description"]
        )
    except Exception as e:
        print(f"  ❌ AI 분석 실패: {e}")
        return False

    if not content or not validate_content(content):
        print("  ❌ AI 분석 결과가 유효하지 않습니다.")
        return False

    print(f"  ✅ 분석 완료")
    print(f"     📰 {content.get('title', '제목 없음')[:50]}...")
    print(f"     🏷️  {content.get('category')} (중요도: {content.get('importance')}점)")

    # Step 4: Archive
    try:
        save_to_archive(
            content,
            image_url,
            info["link"],
            info["title"],
            AI_PROVIDER,
            model,
            source_name  # Pass company name
        )
        print(f"  💾 아카이브 저장 완료")
        return True
    except Exception as e:
        print(f"  ⚠️ 아카이빙 실패: {e}")
        return False


def process_single_source(source_name: str, rss_url: str, client: dict, model: str) -> int:
    """
    Process a single RSS source, checking multiple recent entries.

    Returns the number of successfully archived articles.
    """
    print(f"\n{'='*60}")
    print(f"📡 [{source_name.upper()}] {rss_url}")
    print(f"{'='*60}")

    # Step 1: Fetch RSS feed or scrape web
    print(f"🔄 콘텐츠 확인 중...")
    feed = fetch_feed_or_scrape(source_name, rss_url)
    if not feed:
        print(f"❌ 콘텐츠를 가져올 수 없습니다.")
        return 0

    entries = get_entries(feed, count=ENTRIES_PER_SOURCE)
    if not entries:
        print(f"⚠️ 새 글이 없습니다.")
        return 0

    print(f"📋 최근 {len(entries)}개 글 확인 중 (최대 {MAX_ARTICLE_AGE_HOURS}시간 이내)...")

    archived_count = 0
    for i, entry in enumerate(entries, 1):
        title = entry.get('title', '제목 없음')[:50]
        print(f"\n  [{i}/{len(entries)}] {title}")
        try:
            if process_single_entry(entry, source_name, client, model):
                archived_count += 1
        except Exception as e:
            print(f"  ❌ 예상치 못한 오류: {e}")

    if archived_count > 0:
        print(f"\n🎉 [{source_name.upper()}] {archived_count}개 글 수집 완료")
    else:
        print(f"\n⚠️ [{source_name.upper()}] 수집할 새 글이 없습니다.")

    return archived_count


def run_pipeline() -> None:
    """
    Execute the Thread-Auto pipeline.

    Collects news from multiple AI company blogs and research sources.
    """
    print("\n" + "#" * 70)
    print("# THREAD-AUTO PIPELINE - Multi-Source AI News Collector")
    print(f"# AI Provider: {AI_PROVIDER.upper()}")
    print("#" * 70)

    # Validate API key
    api_key = get_api_key()
    if not api_key:
        config = PROVIDERS.get(AI_PROVIDER, {})
        env_key = config.get("env_key", "API_KEY")
        print(f"❌ {env_key} 환경 변수가 설정되지 않았습니다.")
        print(f"\n{get_provider_info()}")
        return

    provider_config = PROVIDERS.get(AI_PROVIDER)
    model = AI_MODEL or provider_config["default_model"]
    print(f"# Model: {model}")
    print(f"# Free Limit: {provider_config['free_limit']}")

    # Create AI client once
    try:
        client = create_client(api_key, AI_PROVIDER, model)
    except Exception as e:
        print(f"❌ AI 클라이언트 생성 실패: {e}")
        return

    # Determine which sources to collect
    if RSS_URL:
        # Single source mode (manual override)
        print(f"# Mode: Single Source (manual)")
        print(f"# URL: {RSS_URL}")
        print("#" * 70)
        sources = [("manual", RSS_URL)]
    else:
        # Multi-source mode (all AI blogs)
        print(f"# Mode: Multi-Source (all AI company blogs)")
        print(f"# Sources: {len(DEFAULT_RSS_SOURCES)}")
        print("#" * 70)
        sources = list(DEFAULT_RSS_SOURCES.items())

    # Process each source
    total_articles = 0
    source_results = []
    total_count = len(sources)

    for source_name, rss_url in sources:
        try:
            count = process_single_source(source_name, rss_url, client, model)
            total_articles += count
            if count > 0:
                source_results.append(f"{source_name}: {count}건")
        except Exception as e:
            print(f"❌ 예상치 못한 오류: {e}")

    # Summary
    print("\n" + "#" * 70)
    print(f"# PIPELINE 완료")
    print(f"# 수집된 기사: {total_articles}건 / {total_count}개 소스")
    if source_results:
        print(f"# 소스별: {', '.join(source_results)}")
    else:
        print(f"# ⚠️ 새로 수집된 기사가 없습니다.")
    print("#" * 70 + "\n")


def show_providers() -> None:
    """Display available AI providers information."""
    print(get_provider_info())


def main() -> None:
    """
    Main entry point for Thread-Auto application.
    """
    # Run the main pipeline
    run_pipeline()


if __name__ == "__main__":
    main()
