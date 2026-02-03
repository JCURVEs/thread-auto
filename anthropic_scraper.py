"""
Anthropic News Scraper

Anthropic doesn't provide an RSS feed, so we scrape their news page.
Their website is a Next.js SPA, requiring Playwright for JavaScript rendering.
"""

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from typing import List, Dict, Any
from datetime import datetime
import re

ANTHROPIC_NEWS_URL = "https://www.anthropic.com/news"
DEFAULT_TIMEOUT = 10000  # 10 seconds


def fetch_anthropic_news(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Scrape Anthropic news page using Playwright.

    Args:
        limit: Maximum number of articles to fetch

    Returns:
        List of dictionaries in RSS entry format:
        {
            "title": str,
            "link": str,
            "description": str,
            "published": str  # ISO format
        }
    """
    try:
        with sync_playwright() as p:
            # Launch headless Chromium browser
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Navigate and wait for network to be idle (SPA content loaded)
            page.goto(ANTHROPIC_NEWS_URL, wait_until="networkidle", timeout=DEFAULT_TIMEOUT)

            # Wait a bit more for any lazy-loaded content
            page.wait_for_timeout(2000)  # 2 seconds

            articles = []

            # Find all article links (Anthropic uses /news/[slug] pattern)
            # Look for links that contain /news/ but are not just /news
            article_links = page.query_selector_all('a[href*="/news/"]')

            seen_urls = set()

            for link_element in article_links:
                if len(articles) >= limit:
                    break

                href = link_element.get_attribute('href')
                if not href or href == '/news' or href == '/news/':
                    continue

                # Convert relative URL to absolute
                if href.startswith('/'):
                    full_url = f"https://www.anthropic.com{href}"
                else:
                    full_url = href

                # Skip duplicates
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                # Extract title (try various selectors)
                title_element = link_element.query_selector('h2, h3, h4, [class*="title"], [class*="heading"]')
                if not title_element:
                    # If no title found inside link, try getting text from link itself
                    title_text = link_element.inner_text().strip()
                    if not title_text or len(title_text) > 200:
                        continue
                else:
                    title_text = title_element.inner_text().strip()

                if not title_text:
                    continue

                # Extract description/summary
                description_element = link_element.query_selector('p, [class*="description"], [class*="summary"]')
                description_text = description_element.inner_text().strip() if description_element else title_text

                # Extract date (look for date-like elements)
                date_element = link_element.query_selector('time, [class*="date"], [datetime]')
                if date_element:
                    # Try to get datetime attribute first
                    date_attr = date_element.get_attribute('datetime')
                    if date_attr:
                        date_text = date_attr
                    else:
                        date_text = date_element.inner_text().strip()
                else:
                    # No date found - skip this article for safety
                    date_text = None

                # Try to parse and normalize date
                try:
                    # If it looks like "Jan 15, 2024" format
                    if re.match(r'[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}', date_text):
                        parsed_date = datetime.strptime(date_text, '%b %d, %Y')
                        date_text = parsed_date.isoformat()
                    # If it's already ISO format, keep it
                    elif 'T' in date_text or re.match(r'\d{4}-\d{2}-\d{2}', date_text):
                        pass
                    else:
                        # Fallback - skip this article
                        date_text = None
                except Exception:
                    date_text = None

                # Skip articles without parseable dates
                if date_text is None:
                    continue

                articles.append({
                    "title": title_text,
                    "link": full_url,
                    "description": description_text if len(description_text) >= 10 else title_text,
                    "published": date_text
                })

            browser.close()

            print(f"✓ Anthropic 스크래핑 성공: {len(articles)}개 기사")
            return articles

    except PlaywrightTimeout:
        print(f"❌ Anthropic 스크래핑 타임아웃 (10초 초과)")
        return []
    except Exception as e:
        print(f"❌ Anthropic 스크래핑 실패: {e}")
        return []


if __name__ == "__main__":
    # Test the scraper
    print("Testing Anthropic scraper...")
    articles = fetch_anthropic_news(limit=5)

    if articles:
        print(f"\n성공! {len(articles)}개 기사 발견:\n")
        for i, article in enumerate(articles, 1):
            print(f"{i}. {article['title']}")
            print(f"   URL: {article['link']}")
            print(f"   Date: {article['published']}")
            print(f"   Description: {article['description'][:100]}...")
            print()
    else:
        print("\n실패: 기사를 찾을 수 없습니다.")
