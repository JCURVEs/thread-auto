import archiver


def test_old_archive_is_still_a_duplicate(tmp_path, monkeypatch):
    monkeypatch.setattr(archiver, "get_archive_dir", lambda: str(tmp_path))
    for day in range(1, 10):
        (tmp_path / f"2026-08-{day:02}.md").write_text(
            f"**출처:** https://example.com/article-{day}\n", encoding="utf-8"
        )
    assert archiver.is_duplicate("https://example.com/article-1/?utm_source=newsletter#section")
    assert not archiver.is_duplicate("https://example.com/article-1?version=2")


def test_publication_date_is_distinct_from_collection_date(tmp_path, monkeypatch):
    monkeypatch.setattr(archiver, "get_archive_dir", lambda: str(tmp_path))
    data = {"title": "검증된 기사", "summary": "요약입니다.", "easy_explainer": "쉬운 설명입니다.", "published_at": "2026-09-08T12:00:00+00:00"}
    path = archiver.save_to_archive(data, None, "https://example.com/news", "News", "groq", "test")
    from pathlib import Path
    text = Path(path).read_text(encoding="utf-8")
    assert "**원문발행일:** 2026-09-08T12:00:00+00:00" in text
    assert "**수집일:**" in text
