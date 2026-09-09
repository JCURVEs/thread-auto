from datetime import datetime, timedelta, timezone
from time import struct_time

from bs4 import BeautifulSoup
import pytest

from article_dates import entry_published_date, page_published_date
import main
import rss_collector


def test_published_string_beats_recent_update_struct():
    entry = {"published": "2026-04-22", "updated_parsed": struct_time((2026, 9, 9, 0, 0, 0, 2, 252, 0))}
    assert entry_published_date(entry, "https://example.com/news").date().isoformat() == "2026-04-22"


def test_parsed_feed_time_is_utc_not_local_time():
    entry = {"published_parsed": struct_time((2026, 9, 9, 12, 0, 0, 2, 252, 0))}
    assert entry_published_date(entry, "https://example.com/news").hour == 12


def test_update_only_has_no_publication_date():
    assert entry_published_date({"updated": "2026-09-09"}, "https://example.com/news") is None


def test_arxiv_original_citation_date_is_used():
    soup = BeautifulSoup('<meta name="citation_date" content="2026/04/22"><meta name="citation_online_date" content="2026/09/09">', "html.parser")
    assert page_published_date(soup).date().isoformat() == "2026-04-22"


def test_jsonld_uses_published_not_modified_or_related_date():
    soup = BeautifulSoup('''<script type="application/ld+json">{"@graph":[
        {"@type":"BlogPosting","datePublished":"2026-04-22","dateModified":"2026-09-09"},
        {"@type":"ItemList","itemListElement":[{"@type":"Article","datePublished":"2020-01-01"}]}]}
        </script>''', "html.parser")
    assert page_published_date(soup).date().isoformat() == "2026-04-22"


@pytest.mark.parametrize("page_date,feed_date,reason", [
    (datetime.now(timezone.utc) - timedelta(days=120), datetime.now(timezone.utc), "skipped_old"),
    (None, None, "skipped_missing_date"),
    (None, datetime.now(timezone.utc) + timedelta(days=1), "skipped_future_date"),
])
def test_bad_dates_never_reach_ai(monkeypatch, page_date, feed_date, reason):
    monkeypatch.setattr(main, "is_duplicate", lambda url: False)
    monkeypatch.setattr(main, "fetch_article_published_date", lambda url: page_date)
    monkeypatch.setattr(main, "generate_thread_content", lambda *args: pytest.fail("AI must not run"))
    monkeypatch.setattr(main, "get_article_image", lambda *args: pytest.fail("Images must not be fetched"))
    main.PROCESS_STATS.clear()
    entry = {"title": "Old pinned Google article", "link": "https://example.com/old", "published": feed_date.isoformat() if feed_date else ""}
    assert not main.process_single_entry(entry, "google_cloud_ai", {}, "test")
    assert main.PROCESS_STATS[reason] == 1


def test_listing_does_not_fabricate_today(monkeypatch):
    import requests
    response = type("Response", (), {"text": '<a href="/blog/products/ai-machine-learning/old">An old pinned announcement</a>', "raise_for_status": lambda self: None})()
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: response)
    feed = rss_collector.fetch_listing_page("google_cloud_ai", "https://cloud.google.com/blog")
    assert len(feed.entries) == 1
    assert feed.entries[0]["published"] == ""


def test_page_date_and_body_share_http_request(monkeypatch):
    import requests
    calls = []
    html = '<meta property="article:published_time" content="2026-04-22"><article><p>' + "Article evidence. " * 30 + '</p></article>'
    response = type("Response", (), {"text": html, "raise_for_status": lambda self: None})()
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: calls.append(args) or response)
    rss_collector._fetch_article_html.cache_clear()
    assert rss_collector.fetch_article_published_date("https://example.com/cache")
    assert rss_collector.fetch_article_content("https://example.com/cache")
    assert len(calls) == 1
    rss_collector._fetch_article_html.cache_clear()
