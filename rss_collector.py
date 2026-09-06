"""
RSS Collector module for Thread-Auto.

This module handles RSS feed fetching and parsing from AI company blogs and research sources.
Focused on breakthrough AI tech, new models, and research papers.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from urllib.parse import urljoin
import feedparser

from source_registry import (
    get_enabled_sources,
    get_source_config,
    get_source_fetch_mode,
)


DEFAULT_RSS_SOURCES = get_enabled_sources()

ARXIV_SOURCE_CATEGORIES = {
    "arxiv_ai": "cs.AI",
    "arxiv_lg": "cs.LG",
    "arxiv_cv": "cs.CV",
    "arxiv_cl": "cs.CL",
}


def fetch_feed(url: str) -> Optional[feedparser.FeedParserDict]:
    """
    Fetch and parse an RSS feed from the given URL.

    Args:
        url: The RSS feed URL to fetch.

    Returns:
        Parsed feed dictionary if successful, None otherwise.

    Example:
        >>> feed = fetch_feed("https://techcrunch.com/feed/")
        >>> print(feed.feed.title)
    """
    try:
        feed = feedparser.parse(url)
        if feed.bozo:
            # Feed parsing had issues but may still contain entries
            print(f"⚠️ RSS 파싱 경고: {feed.bozo_exception}")
            if not feed.entries:
                fallback_feed = _fetch_feed_with_requests(url)
                if fallback_feed is not None:
                    return fallback_feed
        return feed
    except Exception as e:
        print(f"❌ RSS 피드 가져오기 실패: {e}")
        return _fetch_feed_with_requests(url)


def _fetch_feed_with_requests(url: str) -> Optional[feedparser.FeedParserDict]:
    """Fetch a feed with requests when feedparser's URL opener fails."""
    try:
        import requests

        headers = {
            "User-Agent": "Thread-Auto/2.0 (+https://github.com/JCURVEs/thread-auto)"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        if feed.bozo:
            print(f"⚠️ RSS fallback 파싱 경고: {feed.bozo_exception}")
        return feed
    except Exception as e:
        print(f"❌ RSS fallback 가져오기 실패: {e}")
        return None


def fetch_feed_or_scrape(source_name: str, url: str) -> Optional[Any]:
    """
    Fetch content either via RSS feed or web scraping.

    For sources without RSS feeds (like Anthropic), uses web scraping.
    For sources with RSS feeds, uses standard feedparser.

    Args:
        source_name: The source identifier (e.g. "anthropic", "openai")
        url: RSS feed URL or web page URL

    Returns:
        Parsed feed or mock feed object with entries, None if failed

    Example:
        >>> feed = fetch_feed_or_scrape("anthropic", "https://www.anthropic.com/news")
        >>> entries = feed.entries
    """
    fetch_mode = get_source_fetch_mode(source_name)

    # Special handling for sources without RSS feeds
    if source_name == "anthropic":
        try:
            from anthropic_scraper import fetch_anthropic_news

            articles = fetch_anthropic_news()

            if not articles:
                return None

            # Create a mock feed object compatible with feedparser structure
            class MockFeed:
                def __init__(self, entries):
                    self.entries = entries
                    self.bozo = False

            return MockFeed(articles)

        except ImportError:
            print(f"❌ anthropic_scraper 모듈을 찾을 수 없습니다.")
            return None
        except Exception as e:
            print(f"❌ Anthropic 스크래핑 실패: {e}")
            return None

    if fetch_mode == "html_listing":
        return fetch_listing_page(source_name, url)

    # Default: use RSS feed
    feed = fetch_feed(url)
    filtered_feed = filter_feed_entries(source_name, feed)
    if source_name in ARXIV_SOURCE_CATEGORIES and not get_entries(filtered_feed, count=1):
        print(f"⚠️ arXiv RSS entries 없음 - API fallback 시도: {source_name}")
        return fetch_arxiv_api(source_name)

    return filtered_feed


def make_mock_feed(entries: List[Dict[str, Any]]) -> Any:
    """Create a feed-like object compatible with feedparser outputs."""
    class MockFeed:
        def __init__(self, feed_entries):
            self.entries = feed_entries
            self.bozo = False

    return MockFeed(entries)


def filter_feed_entries(source_name: str, feed: Any) -> Optional[Any]:
    """Filter broad RSS feeds by source registry topic keywords when configured."""
    if not feed or not hasattr(feed, "entries"):
        return feed

    config = get_source_config(source_name)
    keywords = tuple(config.get("topic_keywords", ()))
    if not keywords:
        return feed

    filtered = []
    for entry in feed.entries:
        text = " ".join([
            str(entry.get("title", "")),
            str(entry.get("summary", "")),
            str(entry.get("description", "")),
            str(entry.get("link", "")),
        ]).lower()
        if any(keyword.lower() in text for keyword in keywords):
            filtered.append(dict(entry))

    return make_mock_feed(filtered)


def fetch_listing_page(source_name: str, url: str, limit: int = 15) -> Optional[Any]:
    """Scrape simple official blog listing pages into feed-like entries."""
    try:
        import requests
        from bs4 import BeautifulSoup

        config = get_source_config(source_name)
        url_pattern = str(config.get("url_pattern", "")).lower()
        headers = {
            "User-Agent": "Thread-Auto/2.0 (+https://github.com/JCURVEs/thread-auto)"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        entries = []
        seen_urls = set()

        for anchor in soup.find_all("a", href=True):
            if len(entries) >= limit:
                break

            title = " ".join(anchor.get_text(" ").split())
            if len(title) < 12 or len(title) > 180:
                continue
            if title.lower().startswith(("skip to", "see all", "./")):
                continue

            link = urljoin(url, anchor["href"])
            lower_link = link.lower()
            if url_pattern and url_pattern not in lower_link:
                continue
            if link in seen_urls:
                continue

            seen_urls.add(link)
            entries.append({
                "title": title,
                "link": link,
                "summary": title,
                "description": title,
                "published": datetime.now(timezone.utc).isoformat(),
            })

        if not entries:
            return None

        return make_mock_feed(entries)
    except Exception as e:
        print(f"❌ HTML listing 스크래핑 실패 ({source_name}): {e}")
        return None


def fetch_arxiv_api(source_name: str, limit: int = 15) -> Optional[Any]:
    """Fetch recent arXiv entries via the official Atom API when RSS is empty."""
    category = ARXIV_SOURCE_CATEGORIES.get(source_name)
    if not category:
        return None

    try:
        import requests

        headers = {
            "User-Agent": "Thread-Auto/2.0 (+https://github.com/JCURVEs/thread-auto)"
        }
        response = requests.get(
            "https://export.arxiv.org/api/query",
            params={
                "search_query": f"cat:{category}",
                "sortBy": "submittedDate",
                "sortOrder": "descending",
                "max_results": str(limit),
            },
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()

        feed = feedparser.parse(response.content)
        entries = []
        for entry in feed.entries[:limit]:
            title = " ".join(str(entry.get("title", "")).split())
            summary = " ".join(str(entry.get("summary", "")).split())
            link = str(entry.get("link", ""))
            if not title or not link:
                continue

            entries.append({
                "title": title,
                "link": link,
                "summary": summary,
                "description": summary,
                "published": entry.get("published", entry.get("updated", "")),
                "updated": entry.get("updated", ""),
            })

        if not entries:
            return None

        return make_mock_feed(entries)
    except Exception as e:
        print(f"❌ arXiv API fallback 실패 ({source_name}): {e}")
        return None


def get_latest_entry(feed: feedparser.FeedParserDict) -> Optional[Dict[str, Any]]:
    """
    Get the latest (most recent) entry from a parsed feed.

    Args:
        feed: A parsed feedparser dictionary.

    Returns:
        The latest entry as a dictionary, or None if no entries exist.

    Example:
        >>> feed = fetch_feed("https://techcrunch.com/feed/")
        >>> entry = get_latest_entry(feed)
        >>> print(entry['title'])
    """
    if not feed or not feed.entries:
        return None
    return dict(feed.entries[0])


def get_entries(
    feed: feedparser.FeedParserDict,
    count: int = 5
) -> List[Dict[str, Any]]:
    """
    Get a specified number of entries from a parsed feed.

    Args:
        feed: A parsed feedparser dictionary.
        count: Number of entries to retrieve (default: 5).

    Returns:
        List of entry dictionaries.

    Example:
        >>> feed = fetch_feed("https://techcrunch.com/feed/")
        >>> entries = get_entries(feed, count=3)
        >>> for e in entries:
        ...     print(e['title'])
    """
    if not feed or not feed.entries:
        return []
    return [dict(entry) for entry in feed.entries[:count]]


def get_entry_info(entry: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract key information from a feed entry.

    Args:
        entry: A feed entry dictionary.

    Returns:
        Dictionary with title, link, and description.

    Example:
        >>> info = get_entry_info(entry)
        >>> print(info['title'], info['link'])
    """
    return {
        "title": entry.get("title", ""),
        "link": entry.get("link", ""),
        "description": entry.get("summary", entry.get("description", "")),
        "published": entry.get("published", ""),
    }

def fetch_article_content(url: str) -> str:
    """
    Fetch the full article content from the URL.
    
    Args:
        url: The article URL.
        
    Returns:
        The extracted text content of the article.
    """
    import requests
    from bs4 import BeautifulSoup
    
    try:
        # User-Agent header is often required to avoid 403 Forbidden
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
            
        # Extract text from p tags (most common for articles)
        paragraphs = soup.find_all("p")
        text_content = "\n\n".join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 20])
        
        # Fallback if content is too short
        if len(text_content) < 200:
            return "본문 추출 실패: 내용이 너무 짧습니다."
            
        return text_content[:4000]  # Limit context length for AI
        
    except Exception as e:
        print(f"⚠️ 본문 스크래핑 실패 ({url}): {e}")
        return ""

