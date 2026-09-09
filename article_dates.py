"""Publication dates only: never turn crawl or modification time into news."""

import json
import re
from calendar import timegm
from datetime import datetime, timezone
from urllib.parse import urlsplit

from dateutil import parser


def parse_date(value):
    if not isinstance(value, str) or not value.strip():
        return None
    # Incomplete dates must not inherit today's missing components.
    if not re.search(r"\d{4}", value):
        return None
    try:
        first = parser.parse(value, default=datetime(2000, 1, 1))
        second = parser.parse(value, default=datetime(2000, 2, 2))
        if first != second:
            return None
        return first.replace(tzinfo=first.tzinfo or timezone.utc).astimezone(timezone.utc)
    except (ValueError, OverflowError, TypeError):
        return None


def entry_published_date(entry, link):
    dates = []
    published = parse_date(entry.get("published"))
    if published:
        dates.append(published)
    if entry.get("published_parsed"):
        try:
            dates.append(datetime.fromtimestamp(timegm(entry["published_parsed"]), timezone.utc))
        except (ValueError, OverflowError, TypeError):
            pass
    match = re.search(r"/(\d{4})/(\d{1,2})/(\d{1,2})(?:/|$)", urlsplit(link).path)
    if match:
        published = parse_date("-".join(match.groups()))
        if published:
            dates.append(published)
    return min(dates) if dates else None


def page_published_date(soup):
    """Read explicit publication metadata, excluding related-item dates."""
    dates = []
    for tag in soup.select('meta[property="article:published_time"], meta[name="datePublished"], meta[itemprop="datePublished"], meta[name="pubdate"], meta[name="citation_date"]'):
        value = parse_date(tag.get("content"))
        if value:
            dates.append(value)

    def visit(node):
        if isinstance(node, list):
            for item in node:
                visit(item)
        elif isinstance(node, dict):
            kinds = node.get("@type", [])
            kinds = [kinds] if isinstance(kinds, str) else kinds
            if any(kind in {"Article", "NewsArticle", "BlogPosting", "TechArticle"} for kind in kinds):
                value = parse_date(node.get("datePublished"))
                if value:
                    dates.append(value)
            # Follow graph/article wrappers, not arbitrary related content.
            for key in ("@graph", "mainEntity"):
                if key in node:
                    visit(node[key])

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            visit(json.loads(script.get_text()))
        except (ValueError, TypeError):
            continue
    if not dates:
        for tag in soup.select('[itemprop="datePublished"], time[pubdate]'):
            value = parse_date(tag.get("datetime") or tag.get("content") or tag.get_text(" ", strip=True))
            if value:
                dates.append(value)
    return min(dates) if dates else None
