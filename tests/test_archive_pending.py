"""Tests for raw pending items that must not enter public Markdown archives."""

import json

import archiver


def test_save_to_pending_preserves_source_and_deduplicates(monkeypatch, tmp_path):
    monkeypatch.setattr(archiver, "get_archive_dir", lambda: str(tmp_path / "archive"))

    path = archiver.save_to_pending(
        source_url="https://example.com/article",
        original_title="English title",
        original_summary="English summary",
        article_content="Raw article",
        image_url=None,
        provider="groq",
        model="qwen/qwen3.8-27b",
        source_name="openai",
        error="provider_failed",
    )

    record = json.loads(open(path, encoding="utf-8").readline())
    assert record["original_summary"] == "English summary"
    assert record["model"] == "qwen/qwen3.8-27b"
    assert archiver.is_duplicate("https://example.com/article")

