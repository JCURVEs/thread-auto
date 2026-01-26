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
from typing import Optional
from datetime import datetime, timedelta
import feedparser

from rss_collector import (
    fetch_feed,
    get_latest_entry,
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


def process_single_source(source_name: str, rss_url: str, client: dict, model: str) -> bool:
    """
    Process a single RSS source.

    Returns True if successful, False otherwise.
    """
    print(f"\n{'='*60}")
    print(f"📡 [{source_name.upper()}] {rss_url}")
    print(f"{'='*60}")

    # Step 1: Fetch RSS feed
    print(f"🔄 RSS 피드 확인 중...")
    feed = fetch_feed(rss_url)
    if not feed:
        print(f"❌ RSS 피드를 가져올 수 없습니다.")
        return False

    entry = get_latest_entry(feed)
    if not entry:
        print(f"⚠️ 새 글이 없습니다.")
        return False

    info = get_entry_info(entry)

    # Check 1: Published date (within 24 hours)
    published_date = entry.get("published_parsed") or entry.get("updated_parsed")
    if published_date:
        from time import struct_time, mktime
        published_dt = datetime.fromtimestamp(mktime(published_date))
        age = datetime.now() - published_dt

        if age > timedelta(hours=24):
            print(f"⏰ 오래된 글 ({age.days}일 {age.seconds//3600}시간 전) - 스킵")
            return False

    # Check 2: Duplicate URL
    if is_duplicate(info["link"]):
        print(f"🔁 이미 수집된 글 - 스킵")
        return False

    print(f"✅ 최신 글: {info['title'][:60]}...")

    # Step 2: Extract image
    image_url = get_article_image(info["link"])
    if image_url:
        print(f"✅ 이미지: {image_url[:50]}...")
    else:
        print("⚠️ 이미지 없음")

    # Step 3: AI Analysis
    print(f"🤖 AI 분석 중...")
    try:
        content = generate_thread_content(
            client,
            info["title"],
            info["description"]
        )
    except Exception as e:
        print(f"❌ AI 분석 실패: {e}")
        return False

    if not content or not validate_content(content):
        print("❌ AI 분석 결과가 유효하지 않습니다.")
        return False

    print(f"✅ 분석 완료")
    print(f"   📰 {content.get('title', '제목 없음')[:50]}...")
    print(f"   🏷️  {content.get('category')} (중요도: {content.get('importance')}점)")

    # Step 4: Archive
    try:
        save_to_archive(
            content,
            image_url,
            info["link"],
            info["title"],
            AI_PROVIDER,
            model
        )
        print(f"💾 아카이브 저장 완료")
        return True
    except Exception as e:
        print(f"⚠️ 아카이빙 실패: {e}")
        return False


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
    success_count = 0
    total_count = len(sources)

    for source_name, rss_url in sources:
        try:
            if process_single_source(source_name, rss_url, client, model):
                success_count += 1
        except Exception as e:
            print(f"❌ 예상치 못한 오류: {e}")

    # Summary
    print("\n" + "#" * 70)
    print(f"# PIPELINE 완료")
    print(f"# 성공: {success_count}/{total_count} 소스")
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
