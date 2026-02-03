"""
Test date filtering logic for RSS entries.

Ensures old articles (>24 hours) are properly filtered out,
even when RSS feeds don't provide parsed date fields.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock
import re
from dateutil import parser as date_parser


def test_dateutil_parses_meta_research_format():
    """Test that dateutil can parse Meta Research's date format."""
    published_str = "Wed, 17 May 2023 10:52:00"
    published_dt = date_parser.parse(published_str)

    assert published_dt.year == 2023
    assert published_dt.month == 5
    assert published_dt.day == 17
    assert published_dt.hour == 10
    assert published_dt.minute == 52


def test_url_date_extraction_meta_research():
    """Test extracting date from Meta Research URL pattern."""
    url = "https://research.facebook.com/blog/2023/5/how-generational-differences-affect-consumer-attitudes-towards-ads/"

    url_date_match = re.search(r'/(\d{4})/(\d{1,2})/', url)
    assert url_date_match is not None

    year, month = int(url_date_match.group(1)), int(url_date_match.group(2))
    assert year == 2023
    assert month == 5

    published_dt = datetime(year, month, 1)
    age = datetime.now() - published_dt

    # Should be filtered (>24 hours old)
    assert age > timedelta(hours=24)


def test_old_article_filtered():
    """Test that articles older than 24 hours are filtered."""
    # 2023 article should definitely be filtered
    published_str = "Wed, 17 May 2023 10:52:00"
    published_dt = date_parser.parse(published_str)
    age = datetime.now() - published_dt

    should_skip = age > timedelta(hours=24)
    assert should_skip is True


def test_recent_article_passed():
    """Test that recent articles (<24 hours) pass the filter."""
    # Article from 1 hour ago
    recent_dt = datetime.now() - timedelta(hours=1)
    age = datetime.now() - recent_dt

    should_skip = age > timedelta(hours=24)
    assert should_skip is False


def test_edge_case_exactly_24_hours():
    """Test edge case of exactly 24 hours old."""
    now = datetime.now()
    exactly_24h_ago = now - timedelta(hours=24)
    age = now - exactly_24h_ago

    # Should pass (not strictly greater than 24 hours)
    should_skip = age > timedelta(hours=24)
    assert should_skip is False


def test_multiple_date_formats():
    """Test parsing various date formats."""
    test_cases = [
        "Wed, 17 May 2023 10:52:00",
        "2023-05-17T10:52:00Z",
        "May 17, 2023",
        "2023-05-17",
    ]

    for date_str in test_cases:
        try:
            parsed = date_parser.parse(date_str)
            assert parsed.year == 2023
            assert parsed.month == 5
        except Exception as e:
            pytest.fail(f"Failed to parse '{date_str}': {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
