"""
RSS Collector module for Thread-Auto.

This module handles RSS feed fetching and parsing from various tech news sources.
Supports multiple sources including TechCrunch, The Verge, Hacker News, etc.
"""

from typing import List, Dict, Any, Optional
import feedparser


# Default RSS feed sources
DEFAULT_RSS_SOURCES = {
    "techcrunch": "https://techcrunch.com/feed/",
    "theverge": "https://www.theverge.com/rss/index.xml",
    "hackernews": "https://news.ycombinator.com/rss",
    "openai": "https://openai.com/blog/rss/",
    "google": "https://blog.google/rss/",
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
        return feed
    except Exception as e:
        print(f"❌ RSS 피드 가져오기 실패: {e}")
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

