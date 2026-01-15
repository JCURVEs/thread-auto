"""
Thread-Auto: AI-powered Tech News Pipeline for Meta Threads.

This is the main entry point for the Thread-Auto pipeline.
It orchestrates RSS collection, AI analysis, and content formatting.

Usage:
    # Dry Run (default)
    python main.py

    # With environment variables
    OPENAI_API_KEY=sk-... DRY_RUN=True python main.py
"""

import os
from typing import Optional

from rss_collector import (
    fetch_feed,
    get_latest_entry,
    get_entry_info,
    DEFAULT_RSS_SOURCES
)
from image_extractor import get_article_image
from ai_analyzer import create_client, generate_thread_content, validate_content
from thread_formatter import print_dry_run, post_to_threads


# --- Configuration ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
THREADS_ACCESS_TOKEN = os.environ.get("THREADS_ACCESS_TOKEN")
RSS_URL = os.environ.get("RSS_URL", DEFAULT_RSS_SOURCES["techcrunch"])
DRY_RUN = os.environ.get("DRY_RUN", "True").lower() in ("true", "1", "yes")


def run_pipeline() -> None:
    """
    Execute the Thread-Auto pipeline.

    Pipeline steps:
    1. Fetch latest news from RSS feed
    2. Extract og:image from article
    3. Analyze content with GPT-4o
    4. Format and output (Dry Run or Production)
    """
    print("\n" + "#" * 50)
    print("# THREAD-AUTO PIPELINE")
    print("#" * 50)

    # Validate API key
    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        print("   export OPENAI_API_KEY='sk-...'")
        return

    # Step 1: Fetch RSS feed
    print(f"\n🔄 [Step 1] RSS 피드 확인 중...")
    print(f"   URL: {RSS_URL}")

    feed = fetch_feed(RSS_URL)
    if not feed:
        print("❌ RSS 피드를 가져올 수 없습니다.")
        return

    entry = get_latest_entry(feed)
    if not entry:
        print("❌ 새 글이 없습니다.")
        return

    info = get_entry_info(entry)
    print(f"✅ 최신 글 발견: {info['title']}")

    # Step 2: Extract image
    print(f"\n🔄 [Step 2] 이미지 추출 중...")
    image_url = get_article_image(info["link"])
    if image_url:
        print(f"✅ 이미지 URL: {image_url[:60]}...")
    else:
        print("⚠️ 이미지 없음 (텍스트만 게시)")

    # Step 3: AI Analysis
    print(f"\n🔄 [Step 3] AI 분석 시작...")
    client = create_client(OPENAI_API_KEY)
    content = generate_thread_content(
        client,
        info["title"],
        info["description"]
    )

    if not content or not validate_content(content):
        print("❌ AI 콘텐츠 생성 실패")
        return

    print(f"✅ 콘텐츠 생성 완료 (타입: {content['type']})")

    # Step 4: Output
    print(f"\n🔄 [Step 4] 출력 처리 중...")
    if DRY_RUN:
        print("   모드: DRY RUN (테스트)")
        print_dry_run(content, image_url, info["link"])
    else:
        print("   모드: PRODUCTION")
        if THREADS_ACCESS_TOKEN:
            success = post_to_threads(
                content,
                image_url,
                info["link"],
                THREADS_ACCESS_TOKEN
            )
            if success:
                print("✅ Threads에 게시 완료!")
            else:
                print("❌ Threads 게시 실패")
        else:
            print("❌ THREADS_ACCESS_TOKEN이 설정되지 않았습니다.")

    print("\n" + "#" * 50)
    print("# PIPELINE 완료")
    print("#" * 50 + "\n")


def example_rss_collector() -> None:
    """
    Demonstrate RSS collector functionality.
    """
    print("\n" + "=" * 50)
    print("RSS COLLECTOR 예제")
    print("=" * 50)

    for name, url in list(DEFAULT_RSS_SOURCES.items())[:2]:
        print(f"\n📰 {name.upper()}: {url}")
        feed = fetch_feed(url)
        if feed:
            entry = get_latest_entry(feed)
            if entry:
                info = get_entry_info(entry)
                print(f"   제목: {info['title'][:50]}...")
                print(f"   링크: {info['link'][:50]}...")


def example_image_extractor() -> None:
    """
    Demonstrate image extractor functionality.
    """
    print("\n" + "=" * 50)
    print("IMAGE EXTRACTOR 예제")
    print("=" * 50)

    test_urls = [
        "https://techcrunch.com/",
        "https://www.theverge.com/",
    ]

    for url in test_urls:
        print(f"\n🔗 URL: {url}")
        image = get_article_image(url)
        if image:
            print(f"   🖼️ 이미지: {image[:60]}...")
        else:
            print("   ⚠️ 이미지 없음")


def main() -> None:
    """
    Main entry point for Thread-Auto application.
    """
    # Run the main pipeline
    run_pipeline()


if __name__ == "__main__":
    main()
