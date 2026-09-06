"""
RSS Collector 모듈 테스트.

실제 AI 블로그 피드를 사용하여 RSS 수집 기능을 검증합니다.
"""

import pytest
from rss_collector import (
    fetch_feed,
    fetch_feed_or_scrape,
    fetch_arxiv_api,
    get_latest_entry,
    get_entries,
    get_entry_info,
    DEFAULT_RSS_SOURCES
)
from source_registry import get_high_confidence_online_check_sources


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


def test_arxiv_api_fallback_builds_feed(monkeypatch):
    """arXiv RSS가 비어도 공식 API 응답으로 feed-like entries를 만들어야 함."""

    class FakeResponse:
        content = b"""<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>http://arxiv.org/abs/2609.00001v1</id>
            <updated>2026-09-04T00:00:00Z</updated>
            <published>2026-09-04T00:00:00Z</published>
            <title>Test arXiv Paper</title>
            <summary>This paper tests fallback collection.</summary>
            <link href="http://arxiv.org/abs/2609.00001v1" rel="alternate" type="text/html"/>
          </entry>
        </feed>
        """

        def raise_for_status(self):
            return None

    def fake_get(url, params, headers, timeout):
        assert url == "https://export.arxiv.org/api/query"
        assert params["search_query"] == "cat:cs.AI"
        return FakeResponse()

    import requests

    monkeypatch.setattr(requests, "get", fake_get)

    feed = fetch_arxiv_api("arxiv_ai")
    entries = get_entries(feed, count=1)

    assert len(entries) == 1
    assert entries[0]["title"] == "Test arXiv Paper"
    assert entries[0]["link"] == "http://arxiv.org/abs/2609.00001v1"
    assert entries[0]["published"] == "2026-09-04T00:00:00Z"


def test_all_default_sources_available():
    """모든 기본 RSS 소스가 접근 가능한지 테스트."""
    failed_sources = []
    source_names = get_high_confidence_online_check_sources()

    for source_name in source_names:
        url = DEFAULT_RSS_SOURCES[source_name]
        feed = fetch_feed_or_scrape(source_name, url)
        if feed is None or len(feed.entries) == 0:
            failed_sources.append(source_name)

    # 일부 소스는 일시적으로 다운될 수 있으므로 80% 성공률로 체크
    success_rate = (len(source_names) - len(failed_sources)) / len(source_names)
    assert success_rate >= 0.8, f"Failed sources: {failed_sources}"


@pytest.mark.parametrize(
    "source_name",
    get_high_confidence_online_check_sources()[:3],
)
def test_each_source_has_entries(source_name):
    """각 RSS 소스가 최소 1개 이상의 글을 가지고 있는지 테스트."""
    url = DEFAULT_RSS_SOURCES[source_name]
    feed = fetch_feed_or_scrape(source_name, url)

    # 일시적 다운 허용 (skip)
    if feed is None or len(feed.entries) == 0:
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
