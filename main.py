"""
Thread-Auto: AI-powered Tech News Pipeline for Meta Threads.

This is the main entry point for the Thread-Auto pipeline.
It orchestrates RSS collection, AI analysis, and content formatting.

Supports multiple FREE AI providers:
- Groq (default, fastest, 14K req/day)
- OpenRouter (Qwen, 400+ models)
- Gemini (Google, 1.5K req/day)

Usage:
    # Groq (default, recommended)
    GROQ_API_KEY=gsk-... python main.py

    # OpenRouter
    AI_PROVIDER=openrouter OPENROUTER_API_KEY=sk-or-... python main.py

    # Gemini
    AI_PROVIDER=gemini GEMINI_API_KEY=AIza... python main.py
"""

import os
from typing import Optional

from rss_collector import (
    fetch_feed,
    get_latest_entry,
    get_entry_info,
    DEFAULT_RSS_SOURCES
)
from image_extractor import get_all_images
from ai_analyzer import (
    create_client,
    generate_thread_content,
    validate_content,
    get_provider_info,
    PROVIDERS,
    DEFAULT_PROVIDER
)
from thread_formatter import print_dry_run, post_to_threads


# --- Configuration ---
AI_PROVIDER = os.environ.get("AI_PROVIDER", DEFAULT_PROVIDER)
AI_MODEL = os.environ.get("AI_MODEL", None)  # None = 제공자 기본 모델 사용
THREADS_ACCESS_TOKEN = os.environ.get("THREADS_ACCESS_TOKEN")
RSS_URL = os.environ.get("RSS_URL", DEFAULT_RSS_SOURCES["techcrunch"])
DRY_RUN = os.environ.get("DRY_RUN", "True").lower() in ("true", "1", "yes")


def get_api_key() -> Optional[str]:
    """Get API key for the configured provider."""
    config = PROVIDERS.get(AI_PROVIDER)
    if not config:
        return None
    return os.environ.get(config["env_key"])



def save_archive(content: dict, image_urls: list[str], source_url: str, title: str) -> None:
    """
    Save the generated content to an archive Markdown file.
    Directory format: archive/YYYY-MM-DD/
    File name format: Sanitize_Title.md
    """
    import datetime
    import re
    
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    # Create directory for the day
    daily_archive_dir = os.path.join("archive", date_str)
    os.makedirs(daily_archive_dir, exist_ok=True)
    
    # Sanitize title for filename
    # Try to extract the Korean title from the AI content first
    raw_title = title  # Default to RSS title
    if content and content.get("main_post"):
        main_text = content["main_post"].strip()
        # Regex to find **[Title]** or [Title] pattern
        match = re.search(r'\[(.*?)\]', main_text)
        if match:
            raw_title = match.group(1).strip()
        else:
            # Fallback: take first few words if no bracket title
            first_line = main_text.split("\n")[0]
            clean_line = re.sub(r'[\*\[\]]', '', first_line).strip()
            if clean_line:
                raw_title = clean_line

    # Keep Korean, alphanumeric, spaces, hyphens, underscores.
    # Korean Unicode range: \uAC00-\uD7A3
    safe_title = re.sub(r'[^a-zA-Z0-9\s\-_가-힣]', '', raw_title)
    # Replace spaces with underscores
    safe_title = re.sub(r'\s+', '_', safe_title).strip()
    
    # Limit length to avoid filesystem issues
    if len(safe_title) > 50:
        safe_title = safe_title[:50]
    
    if not safe_title:
        safe_title = "Untitled_Article"
        
    file_path = os.path.join(daily_archive_dir, f"{safe_title}.md")
    
    with open(file_path, "w", encoding="utf-8") as f:
        # Title
        f.write(f"# {title}\n\n")
        
        # Main Post & Image[0]
        f.write("## Main Post\n")
        if len(image_urls) > 0:
            f.write(f"![Main Image]({image_urls[0]})\n\n")
        f.write(f"{content.get('main_post', '')}\n\n")
        
        # Replies & Distributed Images
        if content.get("type") == "multi":
            f.write("## Replies\n")
            for i, reply in enumerate(content.get("replies", [])):
                f.write(f"### Reply {i+1}\n")
                
                # Check for Image i+1
                if len(image_urls) > i + 1:
                    f.write(f"![Reply Image {i+1}]({image_urls[i+1]})\n\n")
                    
                f.write(f"{reply}\n\n")
                
        # Source
        f.write("## Source\n")
        f.write(f"Original Article: {source_url}\n")
        
    print(f"✅ 아카이브 저장 완료: {file_path}")


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

    # Step 2: Extract Images
    print(f"\n🔄 [Step 2] 이미지 추출 중...")
    image_urls = get_all_images(info["link"])
    
    if image_urls:
        print(f"✅ 이미지 {len(image_urls)}장 발견")
        print(f"   대표 이미지: {image_urls[0][:60]}...")
    else:
        print("⚠️ 이미지 없음 (텍스트만 게시)")
        image_urls = []
        
    # Step 2.5: Fetch Full Article Content
    print(f"\n🔄 [Step 2.5] 기사 본문 스크래핑 중...")
    from rss_collector import fetch_article_content
    full_content = fetch_article_content(info["link"])
    
    if full_content:
        print(f"✅ 본문 추출 성공 ({len(full_content)}자)")
    else:
        print("⚠️ 본문 추출 실패, 요약문으로 대체합니다.")
        full_content = info["description"]

    # Step 3: AI Analysis
    print(f"\n🔄 [Step 3] AI 분석 시작...")
    print(f"   Provider: {AI_PROVIDER}, Model: {model}")

    try:
        client = create_client(
            api_key=api_key,
            provider=AI_PROVIDER,
            model=model
        )
        content = generate_thread_content(
            client,
            info["title"],
            full_content
        )
    except Exception as e:
        print(f"❌ AI 분석 실패: {e}")
        return

    if not content or not validate_content(content):
        print("❌ 유효하지 않은 AI 응답")
        return

    print(f"✅ 콘텐츠 생성 완료 (타입: {content['type']})")

    # Step 4: Output
    print(f"\n🔄 [Step 4] 출력 처리 중...")
    if DRY_RUN:
        print("   모드: DRY RUN (테스트)")
        print_dry_run(content, image_urls, info["link"])
    else:
        print("   모드: PRODUCTION")
        if not THREADS_ACCESS_TOKEN:
            print("❌ THREADS_ACCESS_TOKEN이 없습니다. Dry Run으로 대체합니다.")
            print_dry_run(content, image_urls, info["link"])
        else:
            success = post_to_threads(
                content,
                image_urls,
                info["link"],
                THREADS_ACCESS_TOKEN
            )
            if success:
                print("✅ Threads에 게시 완료!")
            else:
                print("❌ Threads 게시 실패")
            
    # Step 5: Archive
    print(f"\n🔄 [Step 5] 아카이빙 중...")
    save_archive(content, image_urls, info["link"], info["title"])

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
