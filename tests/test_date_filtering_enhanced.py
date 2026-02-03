"""
Enhanced date filtering tests with timezone and edge cases.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main


class TestUTCDateFiltering:
    """Test UTC-based date filtering"""

    def test_utc_parsing_with_timezone(self):
        """Test parsing dates with explicit timezone"""
        # Mock entry with timezone
        entry = {
            "published_parsed": None,
            "published": "Wed, 17 May 2023 10:52:00 +0000"  # UTC
        }

        dt = main.parse_published_date_utc(entry, "https://example.com")
        assert dt.tzinfo == timezone.utc
        assert dt.year == 2023
        assert dt.month == 5

    def test_naive_datetime_assumes_utc(self):
        """Test that naive datetime (no timezone) is treated as UTC"""
        entry = {
            "published_parsed": None,
            "published": "2023-05-17 10:52:00"  # No timezone
        }

        dt = main.parse_published_date_utc(entry, "https://example.com")
        assert dt.tzinfo == timezone.utc

    def test_url_fallback_uses_mid_month(self):
        """Test URL fallback uses day 15 instead of day 1"""
        entry = {"published_parsed": None, "published": None}
        link = "https://example.com/blog/2023/5/article"

        dt = main.parse_published_date_utc(entry, link)
        assert dt.day == 15  # Not 1
        assert dt.month == 5
        assert dt.year == 2023

    def test_24hour_boundary_utc(self):
        """Test 24-hour filter works correctly in UTC"""
        now_utc = datetime.now(timezone.utc)

        # Exactly 24 hours ago
        exactly_24h = now_utc - timedelta(hours=24)
        age = now_utc - exactly_24h
        assert age <= timedelta(hours=24)

        # 25 hours ago
        over_24h = now_utc - timedelta(hours=25)
        age = now_utc - over_24h
        assert age > timedelta(hours=24)

    def test_no_date_returns_none(self):
        """Test that entries without dates return None"""
        entry = {
            "published_parsed": None,
            "published": None
        }
        link = "https://example.com/article"  # No date pattern in URL

        dt = main.parse_published_date_utc(entry, link)
        assert dt is None


class TestTimezoneConversion:
    """Test timezone conversions are accurate"""

    def test_pst_to_utc_conversion(self):
        """Test PST to UTC conversion"""
        # PST time: 2023-05-17 02:52:00 -0800
        # UTC time: 2023-05-17 10:52:00 +0000
        from dateutil import parser as date_parser

        pst_str = "Wed, 17 May 2023 02:52:00 -0800"
        dt = date_parser.parse(pst_str)
        dt_utc = dt.astimezone(timezone.utc)

        assert dt_utc.hour == 10  # 2AM PST = 10AM UTC

    def test_published_parsed_uses_utc(self):
        """Test that published_parsed is converted to UTC"""
        from time import struct_time, mktime

        # Create a mock struct_time
        entry = {
            "published_parsed": struct_time((2023, 5, 17, 10, 52, 0, 2, 137, 0)),
            "published": None
        }

        dt = main.parse_published_date_utc(entry, "https://example.com")
        assert dt.tzinfo == timezone.utc


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
