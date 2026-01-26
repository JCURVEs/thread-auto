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
from archiver import save_to_archive


# --- Configuration ---
AI_PROVIDER = os.environ.get("AI_PROVIDER", DEFAULT_PROVIDER)
AI_MODEL = os.environ.get("AI_MODEL", None)  # None = 제공자 기본 모델 사용
THREADS_ACCESS_TOKEN = os.environ.get("THREADS_ACCESS_TOKEN")
RSS_URL = os.environ.get("RSS_URL", DEFAULT_RSS_SOURCES["huggingface"])  # Default: Hugging Face
DRY_RUN = os.environ.get("DRY_RUN", "True").lower() in ("true", "1", "yes")


def get_api_key() -> Optional[str]:
    """Get API key for the configured provider."""
    config = PROVIDERS.get(AI_PROVIDER)
    if not config:
        return None
    return os.environ.get(config["env_key"])


def run_pipeline() -> None:
    """
    Execute the Thread-Auto pipeline.

    Pipeline steps:
    1. Fetch latest news from RSS feed
    2. Extract og:image from article
    3. Analyze content with AI (Groq/OpenRouter/Gemini)
    4. Format and output (Dry Run or Production)
    5. Save Archive
    """
    print("\n" + "#" * 50)
    print("# THREAD-AUTO PIPELINE")
    print(f"# AI Provider: {AI_PROVIDER.upper()}")
    print("#" * 50)

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
    print("#" * 50)

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

    # Step 3: AI Analysis (Newsletter Format)
    print(f"\n🔄 [Step 3] AI 뉴스레터 분석 중...")
    print(f"   Provider: {AI_PROVIDER}, Model: {model}")

    try:
        client = create_client(api_key, AI_PROVIDER, model)
        content = generate_thread_content(
            client,
            info["title"],
            info["description"]
        )
    except Exception as e:
        print(f"❌ AI 클라이언트 생성 또는 분석 실패: {e}")
        return

    if not content or not validate_content(content):
        print("❌ AI 분석 결과가 유효하지 않습니다.")
        return

    print(f"✅ 분석 완료: {content.get('title', '제목 없음')}")

    # Step 3.5: Archive (Main Goal)
    print(f"\n💾 [Step 3.5] 아카이빙 중...")
    try:
        archive_path = save_to_archive(
            content,
            image_url,
            info["link"],
            info["title"],
            AI_PROVIDER,
            model
        )
    except Exception as e:
        print(f"⚠️ 아카이빙 실패: {e}")

    # Step 4: Output (Dry Run only for now)
    print(f"\n🔄 [Step 4] 출력 및 결과 확인")
    if DRY_RUN:
        print("   [Dry Run: 뉴스레터 프리뷰]")
        print(f"   📰 제목: {content.get('title')}")
        print(f"   📝 요약: {content.get('summary')}")
        print(f"   🧠 쉬운설명: {content.get('easy_explainer')}")
        print(f"   🏷️  분야: {content.get('category')} (중요도: {content.get('importance')})")
    else:
        print("   ⚠️ 현재 Production 모드(Threads 업로드)는 뉴스레터 포맷 적용 중으로 비활성화되었습니다.")
        print("   ✅ 아카이빙은 정상적으로 완료되었습니다.")

    print("\n" + "#" * 50)
    print("# PIPELINE 완료")
    print("#" * 50 + "\n")


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
