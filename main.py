"""
Thread-Auto: AI-powered Tech News Pipeline for Meta Threads.

This is the main entry point for the Thread-Auto pipeline.
It orchestrates RSS collection, AI analysis, and content formatting.

Supports multiple FREE AI providers:
- Groq (default, fastest, 14K req/day)
- OpenRouter (Qwen, 400+ models)
- Gemini (Google, 1.5K req/day)
"""

import json
import os
import re
import sys
from collections import Counter
from typing import Optional
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import mktime
import feedparser
from dateutil import parser as date_parser

from rss_collector import (
    fetch_feed,
    fetch_feed_or_scrape,
    fetch_article_content,
    get_latest_entry,
    get_entries,
    get_entry_info,
    DEFAULT_RSS_SOURCES
)
from image_extractor import get_article_image
from ai_analyzer import (
    create_client,
    generate_thread_content,
    calibrate_importance,
    validate_content,
    validate_quality_gate,
    validate_factual_grounding,
    get_provider_info,
    PROVIDERS,
    DEFAULT_PROVIDER
)
from thread_formatter import print_dry_run, post_to_threads
from archiver import save_to_archive, is_duplicate
from source_registry import calculate_collection_score, get_disabled_sources


# --- Configuration ---
AI_PROVIDER = os.environ.get("AI_PROVIDER", DEFAULT_PROVIDER)
AI_MODEL = os.environ.get("AI_MODEL", None)  # None = 제공자 기본 모델 사용
THREADS_ACCESS_TOKEN = os.environ.get("THREADS_ACCESS_TOKEN")
RSS_URL = os.environ.get("RSS_URL", None)  # If None, use all sources
COLLECT_ALL_SOURCES = os.environ.get("COLLECT_ALL_SOURCES", "True").lower() in ("true", "1", "yes")
DRY_RUN = os.environ.get("DRY_RUN", "True").lower() in ("true", "1", "yes")
REQUIRE_DAILY_ARTICLE = os.environ.get("REQUIRE_DAILY_ARTICLE", "False").lower() in ("true", "1", "yes")
ENABLE_FALLBACK_ARCHIVE = os.environ.get("ENABLE_FALLBACK_ARCHIVE", "False").lower() in ("true", "1", "yes")
LAST_RUN_SUMMARY_PATH = Path(__file__).resolve().parent / ".thread_auto_last_run.json"
PROCESS_STATS = Counter()


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


def record_pipeline_stat(name: str) -> None:
    """Record a compact reason counter for the daily run log."""
    PROCESS_STATS[name] += 1


def compact_error(text: str, max_len: int = 80) -> str:
    """Return an error label that is useful in JSON and daily logs."""
    compact = re.sub(r"\s+", " ", str(text)).strip()
    compact = re.sub(r"[^0-9A-Za-z가-힣_:., -]", "", compact)
    return compact[:max_len] or "unknown"


def clean_fallback_text(text: str, max_len: int = 420) -> str:
    """Clean RSS or scraped text enough to store as source-grounded fallback."""
    if not text:
        return ""

    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3].rstrip() + "..."


def infer_fallback_category(source_name: str, title: str, text: str) -> str:
    """Infer a conservative category for fallback archive items."""
    source = source_name.lower()
    haystack = f"{title} {text}".lower()

    if source.startswith("arxiv"):
        return "연구 논문"
    if "nvidia" in source or "cloud" in source or "developer" in source:
        return "API/인프라"
    if "research" in source or "deepmind" in source:
        return "AI 연구"
    if any(keyword in haystack for keyword in ("robot", "embodied", "physical ai", "vla", "3d")):
        return "피지컬 AI"
    if any(keyword in haystack for keyword in ("agent", "workflow", "automation")):
        return "에이전트/자동화"
    if any(keyword in haystack for keyword in ("model", "llm", "reasoning", "multimodal")):
        return "모델/멀티모달"
    return "기타"


def infer_fallback_importance(source_name: str, title: str, text: str) -> int:
    """Give fallback items a useful but conservative curation score."""
    source = source_name.lower()
    haystack = f"{title} {text}".lower()
    importance = 5

    high_signal_sources = (
        "openai",
        "anthropic",
        "deepmind",
        "google_research",
        "nvidia_technical",
        "nvidia_developer_ai",
        "nvidia_korea_blog",
        "microsoft_research",
    )
    if source in high_signal_sources:
        importance += 1
    if any(keyword in haystack for keyword in ("release", "launch", "benchmark", "paper", "research", "model")):
        importance += 1

    return min(7, max(4, importance))


def build_fallback_content(
    info: dict,
    source_name: str,
    original_summary: str,
    article_content: str,
    failure_reason: str,
) -> dict:
    """Build source-grounded archive content when AI analysis cannot be trusted."""
    source_text = article_content or original_summary or info.get("description", "")
    title = clean_fallback_text(info.get("title", "제목 없음"), max_len=120)
    summary = clean_fallback_text(source_text, max_len=420) or title
    category = infer_fallback_category(source_name, title, summary)

    return {
        "title": title,
        "summary": summary,
        "easy_explainer": (
            "AI 분석 결과를 신뢰하기 어려워 원문/RSS 기준으로 먼저 보관한 후보입니다. "
            "게시 전 원문 확인과 스레드 스타일 편집이 필요합니다."
        ),
        "category": category,
        "importance": infer_fallback_importance(source_name, title, summary),
        "analysis_status": "fallback",
        "analysis_error": failure_reason,
    }


def save_fallback_archive(
    info: dict,
    source_name: str,
    image_url: Optional[str],
    model: str,
    original_summary: str,
    article_content: str,
    article_content_used: bool,
    failure_reason: str,
) -> bool:
    """Archive a deterministic fallback item instead of losing the source entirely."""
    record_pipeline_stat("fallback_attempted")
    if not ENABLE_FALLBACK_ARCHIVE:
        record_pipeline_stat("fallback_disabled")
        return False

    content = build_fallback_content(
        info,
        source_name,
        original_summary,
        article_content if article_content_used else "",
        failure_reason,
    )

    try:
        save_to_archive(
            content,
            image_url,
            info["link"],
            info["title"],
            AI_PROVIDER,
            model,
            source_name,
            original_summary=original_summary,
            article_content_used=article_content_used,
        )
        record_pipeline_stat("archived_fallback")
        print(f"  💾 fallback 아카이브 저장 완료 ({failure_reason})")
        return True
    except Exception as e:
        record_pipeline_stat("archive_failed")
        print(f"  ⚠️ fallback 아카이빙 실패: {e}")
        return False


def is_usable_article_content(article_content: str) -> bool:
    """Return True when scraped article text is useful for AI analysis."""
    if not article_content:
        return False
    if article_content.startswith("본문 추출 실패"):
        return False
    return len(article_content.strip()) >= 200


def process_single_entry(entry: dict, source_name: str, client: Optional[dict], model: str) -> bool:
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
            record_pipeline_stat("skipped_old")
            return False
    else:
        # No date information - skip for safety
        print(f"  ⚠️ 발행일 정보 없음 - 스킵")
        record_pipeline_stat("skipped_missing_date")
        return False

    # Check 2: Duplicate URL
    if is_duplicate(info["link"]):
        print(f"  🔁 이미 수집됨 - 스킵: {info['title'][:40]}")
        record_pipeline_stat("skipped_duplicate")
        return False

    print(f"  ✅ 수집 대상: {info['title'][:60]}")

    # Step 2: Extract image
    image_url = get_article_image(info["link"])
    if image_url:
        print(f"  🖼️ 이미지: {image_url[:50]}...")
    else:
        print("  ⚠️ 이미지 없음")

    # Step 3: Fetch full article text for better analysis
    print(f"  📄 본문 추출 중...")
    article_content = fetch_article_content(info["link"])
    article_content_used = is_usable_article_content(article_content)
    if article_content_used:
        print(f"  ✅ 본문 추출 완료 ({len(article_content)}자)")
    else:
        print(f"  ⚠️ 본문 추출 실패/부족 - RSS 요약으로 분석")

    # Step 4: AI Analysis
    analysis_input = article_content if article_content_used else ""
    if client is None:
        print(f"  ⚠️ AI 클라이언트 없음 - fallback 아카이브로 보관")
        record_pipeline_stat("ai_missing_client")
        return save_fallback_archive(
            info,
            source_name,
            image_url,
            model,
            info["description"],
            analysis_input,
            article_content_used,
            "missing_ai_client",
        )

    print(f"  🤖 AI 분석 중...")
    try:
        content = generate_thread_content(
            client,
            info["title"],
            info["description"],
            analysis_input
        )
    except Exception as e:
        print(f"  ❌ AI 분석 실패: {e}")
        reason = f"ai_exception:{compact_error(e)}"
        record_pipeline_stat("ai_exception")
        return save_fallback_archive(
            info,
            source_name,
            image_url,
            model,
            info["description"],
            analysis_input,
            article_content_used,
            reason,
        )

    if not content or not validate_content(content):
        print("  ❌ AI 분석 결과가 유효하지 않습니다.")
        record_pipeline_stat("ai_invalid_content")
        return save_fallback_archive(
            info,
            source_name,
            image_url,
            model,
            info["description"],
            analysis_input,
            article_content_used,
            "ai_invalid_content",
        )

    content = calibrate_importance(
        content,
        source_name=source_name,
        original_title=info["title"],
        original_summary=info["description"],
        article_content=analysis_input
    )

    is_quality_valid, quality_errors = validate_quality_gate(content)
    if not is_quality_valid:
        print(f"  ❌ 품질 게이트 실패: {', '.join(quality_errors)}")
        reason = f"quality_gate_failed:{compact_error(', '.join(quality_errors))}"
        record_pipeline_stat("quality_gate_failed")
        return save_fallback_archive(
            info,
            source_name,
            image_url,
            model,
            info["description"],
            analysis_input,
            article_content_used,
            reason,
        )

    is_grounded, grounding_errors = validate_factual_grounding(
        content,
        original_title=info["title"],
        original_summary=info["description"],
        article_content=analysis_input,
    )
    if not is_grounded:
        print(f"  ❌ 근거 검증 실패: {', '.join(grounding_errors)}")
        reason = f"grounding_failed:{compact_error(', '.join(grounding_errors))}"
        record_pipeline_stat("grounding_failed")
        return save_fallback_archive(
            info,
            source_name,
            image_url,
            model,
            info["description"],
            analysis_input,
            article_content_used,
            reason,
        )

    print(f"  ✅ 분석 완료")
    print(f"     📰 {content.get('title', '제목 없음')[:50]}...")
    if "importance_original" in content:
        print(
            f"     🏷️  {content.get('category')} "
            f"(중요도: {content.get('importance_original')}→{content.get('importance')}점)"
        )
    else:
        print(f"     🏷️  {content.get('category')} (중요도: {content.get('importance')}점)")

    # Step 5: Archive
    try:
        save_to_archive(
            content,
            image_url,
            info["link"],
            info["title"],
            AI_PROVIDER,
            model,
            source_name,  # Pass company name
            original_summary=info["description"],
            article_content_used=article_content_used
        )
        print(f"  💾 아카이브 저장 완료")
        record_pipeline_stat("archived_ai")
        return True
    except Exception as e:
        print(f"  ⚠️ 아카이빙 실패: {e}")
        record_pipeline_stat("archive_failed")
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
        record_pipeline_stat("source_fetch_failed")
        return 0

    entries = get_entries(feed, count=ENTRIES_PER_SOURCE)
    if not entries:
        print(f"⚠️ 새 글이 없습니다.")
        record_pipeline_stat("source_no_entries")
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
            record_pipeline_stat("entry_unexpected_error")

    if archived_count > 0:
        print(f"\n🎉 [{source_name.upper()}] {archived_count}개 글 수집 완료")
    else:
        print(f"\n⚠️ [{source_name.upper()}] 수집할 새 글이 없습니다.")

    return archived_count


def write_pipeline_summary(
    status: str,
    total_articles: int = 0,
    total_sources: int = 0,
    source_results: Optional[list] = None,
    error: str = "",
) -> None:
    """Write a local machine-readable summary for the daily log step."""
    payload = {
        "status": status,
        "total_articles": total_articles,
        "total_sources": total_sources,
        "source_results": source_results or [],
        "error": error,
        "require_daily_article": REQUIRE_DAILY_ARTICLE,
        "fallback_archive_enabled": ENABLE_FALLBACK_ARCHIVE,
        "stats": dict(sorted(PROCESS_STATS.items())),
        "ai_provider": AI_PROVIDER,
        "dry_run": DRY_RUN,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    LAST_RUN_SUMMARY_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def run_pipeline() -> int:
    """
    Execute the Thread-Auto pipeline.

    Collects news from multiple AI company blogs and research sources.
    """
    print("\n" + "#" * 70)
    print("# THREAD-AUTO PIPELINE - Multi-Source AI News Collector")
    print(f"# AI Provider: {AI_PROVIDER.upper()}")
    print(f"# Fallback Archive: {'ON' if ENABLE_FALLBACK_ARCHIVE else 'OFF'}")
    print("#" * 70)
    PROCESS_STATS.clear()

    # Validate API key
    api_key = get_api_key()
    provider_config = PROVIDERS.get(AI_PROVIDER)
    if not provider_config:
        print(f"❌ 지원하지 않는 AI Provider입니다: {AI_PROVIDER}")
        write_pipeline_summary("failed", error=f"unknown_provider:{AI_PROVIDER}")
        return 2

    model = AI_MODEL or provider_config["default_model"]
    if not api_key:
        config = PROVIDERS.get(AI_PROVIDER, {})
        env_key = config.get("env_key", "API_KEY")
        if not ENABLE_FALLBACK_ARCHIVE:
            print(f"❌ {env_key} 환경 변수가 설정되지 않았습니다.")
            print(f"\n{get_provider_info()}")
            write_pipeline_summary(
                "failed",
                error=f"missing_api_key:{env_key}",
            )
            return 2

        print(f"⚠️ {env_key} 환경 변수가 없어 fallback archive 모드로 진행합니다.")
        client = None
        record_pipeline_stat("missing_api_key_fallback")
    else:
        # Create AI client once
        try:
            client = create_client(api_key, AI_PROVIDER, model)
        except Exception as e:
            if not ENABLE_FALLBACK_ARCHIVE:
                print(f"❌ AI 클라이언트 생성 실패: {e}")
                write_pipeline_summary("failed", error=f"client_create_failed:{e}")
                return 2

            print(f"⚠️ AI 클라이언트 생성 실패 - fallback archive 모드로 진행: {e}")
            client = None
            record_pipeline_stat("client_create_failed_fallback")

    print(f"# Model: {model}")
    print(f"# Free Limit: {provider_config['free_limit']}")

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
        print(f"# Collection Score: {calculate_collection_score()}/100")
        disabled_sources = get_disabled_sources()
        if disabled_sources:
            disabled_names = ", ".join(disabled_sources.keys())
            print(f"# Disabled Sources: {disabled_names}")
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

    if total_articles == 0 and REQUIRE_DAILY_ARTICLE:
        error = "no_articles_archived"
        print(f"❌ REQUIRE_DAILY_ARTICLE=true 이지만 새 아카이브가 없습니다: {error}")
        write_pipeline_summary(
            "failed",
            total_articles=total_articles,
            total_sources=total_count,
            source_results=source_results,
            error=error,
        )
        return 3

    write_pipeline_summary(
        "success",
        total_articles=total_articles,
        total_sources=total_count,
        source_results=source_results,
    )
    return 0


def show_providers() -> None:
    """Display available AI providers information."""
    print(get_provider_info())


def main() -> None:
    """
    Main entry point for Thread-Auto application.
    """
    # Run the main pipeline
    raise SystemExit(run_pipeline())


if __name__ == "__main__":
    main()
