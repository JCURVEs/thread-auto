"""
Thread-Auto: AI-powered Tech News Pipeline for Meta Threads.

This is the main entry point for the Thread-Auto pipeline.
It orchestrates RSS collection, AI analysis, and content formatting.

Supports multiple FREE AI providers:
- Groq (default, fastest, 14K req/day)
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

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

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
    AIAnalysisError,
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
from archiver import save_to_archive, save_to_pending, is_duplicate
from source_registry import calculate_collection_score, get_disabled_sources


# --- Configuration ---
AI_PROVIDER = os.environ.get("AI_PROVIDER", DEFAULT_PROVIDER)
AI_MODEL = os.environ.get("AI_MODEL", None)  # None = 제공자 기본 모델 사용
AI_PROVIDER_FALLBACKS = os.environ.get("AI_PROVIDER_FALLBACKS", "groq")
ALLOW_PAID_MODELS = os.environ.get("ALLOW_PAID_MODELS", "False").lower() in ("true", "1", "yes")
THREADS_ACCESS_TOKEN = os.environ.get("THREADS_ACCESS_TOKEN")
RSS_URL = os.environ.get("RSS_URL", None)  # If None, use all sources
COLLECT_ALL_SOURCES = os.environ.get("COLLECT_ALL_SOURCES", "True").lower() in ("true", "1", "yes")
DRY_RUN = os.environ.get("DRY_RUN", "True").lower() in ("true", "1", "yes")
REQUIRE_DAILY_ARTICLE = os.environ.get("REQUIRE_DAILY_ARTICLE", "False").lower() in ("true", "1", "yes")
ENABLE_PENDING_ARCHIVE = os.environ.get(
    "ENABLE_PENDING_ARCHIVE",
    os.environ.get("ENABLE_FALLBACK_ARCHIVE", "False"),
).lower() in ("true", "1", "yes")
LAST_RUN_SUMMARY_PATH = Path(__file__).resolve().parent / ".thread_auto_last_run.json"
PROCESS_STATS = Counter()
ACTIVE_AI_PROVIDER = AI_PROVIDER
PROVIDER_SELECTION_LOG = []
FREE_ONLY_PROVIDERS = {"groq"}


def get_api_key(provider: Optional[str] = None) -> Optional[str]:
    """Get API key for the configured provider."""
    config = PROVIDERS.get(provider or AI_PROVIDER)
    if not config:
        return None
    return os.environ.get(config["env_key"])


def get_provider_chain(preferred_provider: str, fallback_spec: str) -> list[str]:
    """Return the provider order to try, preserving preference and removing duplicates."""
    names = [preferred_provider]
    names.extend(
        item.strip()
        for item in fallback_spec.split(",")
        if item.strip()
    )

    chain = []
    seen = set()
    for name in names:
        normalized = name.lower()
        if normalized in seen:
            continue
        chain.append(normalized)
        seen.add(normalized)
    return chain


def get_model_for_provider(provider: str, preferred_model: Optional[str] = None) -> str:
    """Resolve a model override without leaking an incompatible model to fallback providers."""
    config = PROVIDERS[provider]
    provider_model_env = config.get("model_env_key", f"{provider.upper()}_MODEL")
    provider_model = os.environ.get(provider_model_env, "").strip()
    if provider_model:
        return provider_model

    if provider == AI_PROVIDER and preferred_model:
        return preferred_model

    return config["default_model"]


def blocks_paid_model(provider: str, model: str) -> bool:
    """Block known paid model routes unless explicitly allowed."""
    if ALLOW_PAID_MODELS:
        return False

    if provider not in FREE_ONLY_PROVIDERS:
        return True

    return False


def select_ai_client() -> tuple[str, str, Optional[dict], list[str]]:
    """Pick the first configured AI provider and fall back deterministically."""
    skipped = []

    for provider in get_provider_chain(AI_PROVIDER, AI_PROVIDER_FALLBACKS):
        config = PROVIDERS.get(provider)
        if not config:
            skipped.append(f"{provider}:unknown_provider")
            record_pipeline_stat(f"provider_unknown_{provider}")
            continue

        model = get_model_for_provider(provider, AI_MODEL)
        if blocks_paid_model(provider, model):
            skipped.append(f"{provider}:paid_model_blocked:{model}")
            record_pipeline_stat(f"provider_paid_model_blocked_{provider}")
            continue

        api_key = get_api_key(provider)
        if not api_key:
            skipped.append(f"{provider}:missing_api_key:{config['env_key']}")
            record_pipeline_stat(f"provider_missing_key_{provider}")
            continue

        try:
            client = create_client(api_key, provider, model)
            if isinstance(client, dict):
                client["_provider_name"] = provider
            return provider, model, client, skipped
        except Exception as e:
            skipped.append(f"{provider}:client_create_failed:{compact_error(e)}")
            record_pipeline_stat(f"provider_client_failed_{provider}")

    fallback_provider = get_provider_chain(AI_PROVIDER, AI_PROVIDER_FALLBACKS)[0]
    if fallback_provider not in PROVIDERS:
        fallback_provider = DEFAULT_PROVIDER

    fallback_model = get_model_for_provider(fallback_provider, AI_MODEL)
    return fallback_provider, fallback_model, None, skipped


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


def _record_provider_skip(message: str) -> None:
    """Add one provider decision to the run summary without duplicates."""
    if message not in PROVIDER_SELECTION_LOG:
        PROVIDER_SELECTION_LOG.append(message)


def iter_analysis_clients(client: dict, model: str):
    """Yield the primary client, then configured zero-cost runtime fallbacks."""
    primary_provider = client.get("_provider_name") if isinstance(client, dict) else None
    yield primary_provider or ACTIVE_AI_PROVIDER, model, client

    # Direct callers and unit tests can pass a plain client without enabling
    # environment-driven provider fallback.
    if not primary_provider:
        return

    for provider in get_provider_chain(AI_PROVIDER, AI_PROVIDER_FALLBACKS):
        if provider == primary_provider:
            continue

        config = PROVIDERS.get(provider)
        if not config:
            message = f"{provider}:unknown_provider"
            _record_provider_skip(message)
            record_pipeline_stat(f"provider_unknown_{provider}")
            continue

        fallback_model = get_model_for_provider(provider)
        if blocks_paid_model(provider, fallback_model):
            message = f"{provider}:paid_route_blocked:{fallback_model}"
            _record_provider_skip(message)
            record_pipeline_stat(f"provider_paid_model_blocked_{provider}")
            continue

        api_key = get_api_key(provider)
        if not api_key:
            message = f"{provider}:missing_api_key:{config['env_key']}"
            _record_provider_skip(message)
            record_pipeline_stat(f"provider_missing_key_{provider}")
            continue

        try:
            fallback_client = create_client(api_key, provider, fallback_model)
            if isinstance(fallback_client, dict):
                fallback_client["_provider_name"] = provider
            yield provider, fallback_model, fallback_client
        except Exception as e:
            message = f"{provider}:client_create_failed:{compact_error(e)}"
            _record_provider_skip(message)
            record_pipeline_stat(f"provider_client_failed_{provider}")


def analyze_article_with_fallback(
    client: dict,
    model: str,
    info: dict,
    source_name: str,
    article_content: str,
):
    """Analyze one article and validate each provider before accepting it."""
    failures = []
    primary_provider = client.get("_provider_name") if isinstance(client, dict) else ACTIVE_AI_PROVIDER

    for provider, provider_model, provider_client in iter_analysis_clients(client, model):
        print(f"  🤖 AI 분석 중... ({provider}/{provider_model})")
        try:
            content = generate_thread_content(
                provider_client,
                info["title"],
                info["description"],
                article_content,
            )
        except AIAnalysisError as e:
            detail = compact_error(e, max_len=180)
            failures.append(f"{provider}:generation_failed:{detail}")
            record_pipeline_stat("ai_exception")
            record_pipeline_stat(f"ai_exception_{provider}")
            print(f"  ❌ {provider} 분석 실패: {detail}")
            continue
        except Exception as e:
            detail = compact_error(e, max_len=180)
            failures.append(f"{provider}:unexpected_error:{detail}")
            record_pipeline_stat("ai_exception")
            record_pipeline_stat(f"ai_exception_{provider}")
            print(f"  ❌ {provider} 예상치 못한 분석 실패: {detail}")
            continue

        if not content or not validate_content(content):
            missing = [
                key for key in ("title", "summary", "easy_explainer", "category", "importance")
                if not content or key not in content
            ]
            detail = "missing_fields:" + ",".join(missing)
            failures.append(f"{provider}:invalid_content:{detail}")
            record_pipeline_stat("ai_invalid_content")
            record_pipeline_stat(f"ai_invalid_content_{provider}")
            print(f"  ❌ {provider} AI 응답 필드 누락: {', '.join(missing)}")
            continue

        content = calibrate_importance(
            content,
            source_name=source_name,
            original_title=info["title"],
            original_summary=info["description"],
            article_content=article_content,
        )

        is_quality_valid, quality_errors = validate_quality_gate(content)
        if not is_quality_valid:
            detail = compact_error(", ".join(quality_errors), max_len=180)
            failures.append(f"{provider}:quality_gate_failed:{detail}")
            record_pipeline_stat("quality_gate_failed")
            record_pipeline_stat(f"quality_gate_failed_{provider}")
            print(f"  ❌ {provider} 품질 게이트 실패: {detail}")
            continue

        is_grounded, grounding_errors = validate_factual_grounding(
            content,
            original_title=info["title"],
            original_summary=info["description"],
            article_content=article_content,
        )
        if not is_grounded:
            detail = compact_error(", ".join(grounding_errors), max_len=180)
            failures.append(f"{provider}:grounding_failed:{detail}")
            record_pipeline_stat("grounding_failed")
            record_pipeline_stat(f"grounding_failed_{provider}")
            print(f"  ❌ {provider} 근거 검증 실패: {detail}")
            continue

        if provider != primary_provider:
            record_pipeline_stat(f"provider_fallback_success_{provider}")
            print(f"  ✅ 무료 fallback 성공: {provider}")
        return content, provider, provider_model, failures

    return None, primary_provider, model, failures


def queue_pending_item(
    info: dict,
    source_name: str,
    image_url: Optional[str],
    model: str,
    original_summary: str,
    article_content: str,
    article_content_used: bool,
    failure_reason: str,
) -> bool:
    """Queue a failed item as raw data without publishing an English fallback."""
    record_pipeline_stat("pending_attempted")
    if not ENABLE_PENDING_ARCHIVE:
        record_pipeline_stat("pending_disabled")
        return False

    try:
        pending_path = save_to_pending(
            source_url=info["link"],
            original_title=info["title"],
            original_summary=original_summary,
            article_content=article_content if article_content_used else "",
            image_url=image_url,
            provider=ACTIVE_AI_PROVIDER,
            model=model,
            source_name=source_name,
            error=failure_reason,
        )
        record_pipeline_stat("queued_pending")
        print(f"  📥 한국어 분석 대기열로 이동: {pending_path}")
        return False
    except Exception as e:
        record_pipeline_stat("archive_failed")
        print(f"  ⚠️ pending 대기열 저장 실패: {e}")
        return False


def is_usable_article_content(article_content: str) -> bool:
    """Return True when scraped article text is useful for AI analysis."""
    if not article_content:
        return False
    if article_content.startswith("본문 추출 실패"):
        return False
    return len(article_content.strip()) >= 200


def daily_archive_exists(now: Optional[datetime] = None) -> bool:
    """Return whether an archive for the runner's current date already exists."""
    current = now or datetime.now()
    archive_path = (
        Path(__file__).resolve().parent
        / "archive"
        / current.strftime("%Y")
        / current.strftime("%m월")
        / current.strftime("%Y-%m-%d.md")
    )
    return archive_path.is_file() and archive_path.stat().st_size > 0


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
        print(f"  ⚠️ AI 클라이언트 없음 - 한국어 분석 pending 대기열로 보관")
        record_pipeline_stat("ai_missing_client")
        return queue_pending_item(
            info,
            source_name,
            image_url,
            model,
            info["description"],
            analysis_input,
            article_content_used,
            "missing_ai_client",
        )

    content, used_provider, used_model, analysis_failures = analyze_article_with_fallback(
        client,
        model,
        info,
        source_name,
        analysis_input,
    )
    if content is None:
        record_pipeline_stat("all_ai_providers_failed")
        if len(analysis_failures) == 1:
            _, _, provider_reason = analysis_failures[0].partition(":")
            reason = compact_error(provider_reason, max_len=300)
        else:
            reason = "all_providers_failed:" + compact_error(
                " | ".join(analysis_failures),
                max_len=300,
            )
        print(f"  ❌ 사용 가능한 무료 AI 분석 모두 실패: {reason}")
        return queue_pending_item(
            info,
            source_name,
            image_url,
            used_model,
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
            used_provider,
            used_model,
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
        "pending_archive_enabled": ENABLE_PENDING_ARCHIVE,
        "stats": dict(sorted(PROCESS_STATS.items())),
        "ai_provider": ACTIVE_AI_PROVIDER,
        "preferred_ai_provider": AI_PROVIDER,
        "provider_selection": PROVIDER_SELECTION_LOG,
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
    global ACTIVE_AI_PROVIDER, PROVIDER_SELECTION_LOG

    print("\n" + "#" * 70)
    print("# THREAD-AUTO PIPELINE - Multi-Source AI News Collector")
    print(f"# Preferred AI Provider: {AI_PROVIDER.upper()}")
    print(f"# Pending Archive: {'ON' if ENABLE_PENDING_ARCHIVE else 'OFF'}")
    print("#" * 70)
    PROCESS_STATS.clear()
    PROVIDER_SELECTION_LOG = []

    active_provider, model, client, provider_selection = select_ai_client()
    ACTIVE_AI_PROVIDER = active_provider
    PROVIDER_SELECTION_LOG = provider_selection
    provider_config = PROVIDERS[active_provider]
    print(f"# Model: {model}")
    print(f"# Active AI Provider: {active_provider.upper()}")
    print(f"# Free Limit: {provider_config['free_limit']}")
    if provider_selection:
        print(f"# Provider skips: {', '.join(provider_selection)}")

    if client is None:
        if not ENABLE_PENDING_ARCHIVE:
            print("❌ 사용 가능한 AI Provider/API 키가 없습니다.")
            print(f"\n{get_provider_info()}")
            write_pipeline_summary(
                "failed",
                error="no_available_ai_provider",
            )
            return 2

        print("⚠️ 사용 가능한 AI Provider/API 키가 없어 pending 대기열로만 보관합니다.")
        record_pipeline_stat("no_ai_provider_pending")

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

    if total_articles == 0 and REQUIRE_DAILY_ARTICLE and daily_archive_exists():
        record_pipeline_stat("daily_archive_already_exists")
        print("✅ 오늘 아카이브가 이미 있어 중복 없이 정상 종료합니다.")

    elif total_articles == 0 and REQUIRE_DAILY_ARTICLE:
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
