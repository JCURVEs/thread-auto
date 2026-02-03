"""
RSS Collector 모듈 테스트.

실제 AI 블로그 피드를 사용하여 RSS 수집 기능을 검증합니다.
"""

import pytest
from rss_collector import (
    fetch_feed,
    get_latest_entry,
    get_entries,
    get_entry_info,
    DEFAULT_RSS_SOURCES
)


def test_fetch_feed_openai():
    """OpenAI RSS 피드 가져오기 테스트."""
    feed = fetch_feed(DEFAULT_RSS_SOURCES["openai"])

    assert feed is not None
    assert hasattr(feed, 'entries')
    assert len(feed.entries) > 0


def test_fetch_feed_invalid_url():
    """잘못된 URL 처리 테스트."""
    feed = fetch_feed("https://invalid-url-that-does-not-exist.com/feed.xml")

    # 에러 처리가 되어야 함 (None 또는 빈 entries)
    assert feed is None or len(feed.entries) == 0


def test_get_latest_entry():
    """최신 글 추출 테스트."""
    feed = fetch_feed(DEFAULT_RSS_SOURCES["openai"])
    entry = get_latest_entry(feed)

    assert entry is not None
    assert "title" in entry
    assert "link" in entry


def test_get_latest_entry_empty_feed():
    """빈 피드에서 최신 글 추출 테스트."""
    # 빈 피드 객체 시뮬레이션
    class EmptyFeed:
        entries = []

    entry = get_latest_entry(EmptyFeed())
    assert entry is None


def test_get_entries_count():
    """여러 글 가져오기 테스트."""
    feed = fetch_feed(DEFAULT_RSS_SOURCES["huggingface"])
    entries = get_entries(feed, count=3)

    assert isinstance(entries, list)
    assert len(entries) <= 3  # 최대 3개
    assert len(entries) > 0    # 최소 1개는 있어야 함


def test_get_entry_info():
    """글 정보 추출 테스트."""
    feed = fetch_feed(DEFAULT_RSS_SOURCES["google_research"])
    entry = get_latest_entry(feed)
    info = get_entry_info(entry)

    assert "title" in info
    assert "link" in info
    assert "description" in info
    assert "published" in info

    # 값이 비어있지 않은지 확인
    assert len(info["title"]) > 0
    assert len(info["link"]) > 0


def test_all_default_sources_available():
    """모든 기본 RSS 소스가 접근 가능한지 테스트."""
    failed_sources = []

    for source_name, url in DEFAULT_RSS_SOURCES.items():
        feed = fetch_feed(url)
        if feed is None or len(feed.entries) == 0:
            failed_sources.append(source_name)

    # 일부 소스는 일시적으로 다운될 수 있으므로 80% 성공률로 체크
    success_rate = (len(DEFAULT_RSS_SOURCES) - len(failed_sources)) / len(DEFAULT_RSS_SOURCES)
    assert success_rate >= 0.8, f"Failed sources: {failed_sources}"


@pytest.mark.parametrize("source_name,url", list(DEFAULT_RSS_SOURCES.items())[:3])
def test_each_source_has_entries(source_name, url):
    """각 RSS 소스가 최소 1개 이상의 글을 가지고 있는지 테스트."""
    feed = fetch_feed(url)

    # 일시적 다운 허용 (skip)
    if feed is None:
        pytest.skip(f"{source_name} is temporarily unavailable")

    assert len(feed.entries) > 0, f"{source_name} has no entries"


def test_anthropic_scraper_date_validation():
    """Test that Anthropic articles without dates are skipped"""
    try:
        from anthropic_scraper import fetch_anthropic_news
    except ImportError:
        pytest.skip("anthropic_scraper not available")

    articles = fetch_anthropic_news(limit=5)

    # All articles should have valid dates (not None, not empty)
    for article in articles:
        assert article.get("published") is not None, "Article has None date"
        assert article["published"] != "", "Article has empty date string"
        # Date should be in ISO format or parseable
        assert len(article["published"]) > 0
