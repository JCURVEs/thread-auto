"""
Main pipeline processing tests.
"""

from datetime import datetime, timezone
import json

import main


def make_recent_entry():
    return {
        "title": "Original RSS Title",
        "link": "https://example.com/article",
        "summary": "RSS summary only",
        "published": datetime.now(timezone.utc).isoformat(),
    }


def make_valid_content():
    return {
        "title": "분석된 제목",
        "summary": "분석된 요약입니다.",
        "easy_explainer": "쉽게 말하면 테스트입니다.",
        "category": "API/인프라",
        "importance": 6,
    }


def test_process_single_entry_uses_full_article_content(monkeypatch):
    """본문이 충분하면 AI 분석과 아카이브 메타데이터에 사용 여부를 넘겨야 함."""

    captured = {}
    article_body = "본문 근거입니다. " * 30

    monkeypatch.setattr(main, "is_duplicate", lambda url: False)
    monkeypatch.setattr(main, "get_article_image", lambda url: None)
    monkeypatch.setattr(main, "fetch_article_content", lambda url: article_body)

    def fake_generate_thread_content(client, title, description, article_content=""):
        captured["title"] = title
        captured["description"] = description
        captured["article_content"] = article_content
        return make_valid_content()

    def fake_save_to_archive(
        data,
        image_url,
        source_url,
        original_title,
        provider,
        model,
        source_name,
        original_summary=None,
        article_content_used=False,
    ):
        captured["original_summary"] = original_summary
        captured["article_content_used"] = article_content_used
        return "archive/test.md"

    monkeypatch.setattr(main, "generate_thread_content", fake_generate_thread_content)
    monkeypatch.setattr(main, "save_to_archive", fake_save_to_archive)

    assert main.process_single_entry(make_recent_entry(), "openai", {}, "test-model")
    assert captured["title"] == "Original RSS Title"
    assert captured["description"] == "RSS summary only"
    assert captured["article_content"] == article_body
    assert captured["original_summary"] == "RSS summary only"
    assert captured["article_content_used"] is True


def test_process_single_entry_falls_back_to_rss_summary_when_body_is_short(monkeypatch):
    """본문이 너무 짧으면 RSS 요약만 AI 분석에 넘겨야 함."""

    captured = {}

    monkeypatch.setattr(main, "is_duplicate", lambda url: False)
    monkeypatch.setattr(main, "get_article_image", lambda url: None)
    monkeypatch.setattr(main, "fetch_article_content", lambda url: "짧음")

    def fake_generate_thread_content(client, title, description, article_content=""):
        captured["article_content"] = article_content
        return make_valid_content()

    def fake_save_to_archive(
        data,
        image_url,
        source_url,
        original_title,
        provider,
        model,
        source_name,
        original_summary=None,
        article_content_used=False,
    ):
        captured["article_content_used"] = article_content_used
        return "archive/test.md"

    monkeypatch.setattr(main, "generate_thread_content", fake_generate_thread_content)
    monkeypatch.setattr(main, "save_to_archive", fake_save_to_archive)

    assert main.process_single_entry(make_recent_entry(), "openai", {}, "test-model")
    assert captured["article_content"] == ""
    assert captured["article_content_used"] is False


def test_process_single_entry_saves_calibrated_importance(monkeypatch):
    """AI가 과한 점수를 줘도 보정된 중요도가 아카이브로 넘어가야 함."""

    captured = {}

    monkeypatch.setattr(main, "is_duplicate", lambda url: False)
    monkeypatch.setattr(main, "get_article_image", lambda url: None)
    monkeypatch.setattr(main, "fetch_article_content", lambda url: "짧음")

    def fake_generate_thread_content(client, title, description, article_content=""):
        content = make_valid_content()
        content["category"] = "연구 논문"
        content["importance"] = 9
        return content

    def fake_save_to_archive(
        data,
        image_url,
        source_url,
        original_title,
        provider,
        model,
        source_name,
        original_summary=None,
        article_content_used=False,
    ):
        captured["data"] = data
        return "archive/test.md"

    monkeypatch.setattr(main, "generate_thread_content", fake_generate_thread_content)
    monkeypatch.setattr(main, "save_to_archive", fake_save_to_archive)

    assert main.process_single_entry(make_recent_entry(), "arxiv_ai", {}, "test-model")
    assert captured["data"]["importance"] == 6
    assert captured["data"]["importance_original"] == 9


def test_process_single_entry_blocks_quality_gate_failures(monkeypatch):
    """품질 게이트 실패 콘텐츠는 아카이브에 저장하지 않아야 함."""

    captured = {"saved": False}

    monkeypatch.setattr(main, "is_duplicate", lambda url: False)
    monkeypatch.setattr(main, "get_article_image", lambda url: None)
    monkeypatch.setattr(main, "fetch_article_content", lambda url: "짧음")

    def fake_generate_thread_content(client, title, description, article_content=""):
        content = make_valid_content()
        content["summary"] = "정말 혁신적인 도구이며 品質 평가를 포함합니다."
        return content

    def fake_save_to_archive(*args, **kwargs):
        captured["saved"] = True
        return "archive/test.md"

    monkeypatch.setattr(main, "generate_thread_content", fake_generate_thread_content)
    monkeypatch.setattr(main, "save_to_archive", fake_save_to_archive)

    assert not main.process_single_entry(make_recent_entry(), "openai", {}, "test-model")
    assert captured["saved"] is False


def test_process_single_entry_blocks_ungrounded_claims(monkeypatch):
    """원문에 없는 구체 수치를 만든 콘텐츠는 저장하지 않아야 함."""

    captured = {"saved": False}

    monkeypatch.setattr(main, "is_duplicate", lambda url: False)
    monkeypatch.setattr(main, "get_article_image", lambda url: None)
    monkeypatch.setattr(main, "fetch_article_content", lambda url: "짧음")

    def fake_generate_thread_content(client, title, description, article_content=""):
        content = make_valid_content()
        content["summary"] = "이 도구는 처리 속도를 90% 개선했습니다."
        return content

    def fake_save_to_archive(*args, **kwargs):
        captured["saved"] = True
        return "archive/test.md"

    monkeypatch.setattr(main, "generate_thread_content", fake_generate_thread_content)
    monkeypatch.setattr(main, "save_to_archive", fake_save_to_archive)

    assert not main.process_single_entry(make_recent_entry(), "openai", {}, "test-model")
    assert captured["saved"] is False


def test_run_pipeline_fails_when_api_key_missing(monkeypatch, tmp_path):
    """API 키가 없으면 Actions가 초록으로 지나가면 안 됨."""

    summary_path = tmp_path / "last_run.json"
    monkeypatch.setattr(main, "LAST_RUN_SUMMARY_PATH", summary_path)
    monkeypatch.setattr(main, "get_api_key", lambda: None)

    exit_code = main.run_pipeline()

    assert exit_code == 2
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "failed"
    assert summary["error"].startswith("missing_api_key")


def test_run_pipeline_can_fail_when_no_articles_required(monkeypatch, tmp_path):
    """일일 글 생성이 필수인 실행에서 0건 수집은 실패로 기록해야 함."""

    summary_path = tmp_path / "last_run.json"
    monkeypatch.setattr(main, "LAST_RUN_SUMMARY_PATH", summary_path)
    monkeypatch.setattr(main, "REQUIRE_DAILY_ARTICLE", True)
    monkeypatch.setattr(main, "get_api_key", lambda: "key")
    monkeypatch.setattr(main, "create_client", lambda api_key, provider, model: {})
    monkeypatch.setattr(main, "DEFAULT_RSS_SOURCES", {"openai": "https://example.com/rss"})
    monkeypatch.setattr(main, "process_single_source", lambda source_name, rss_url, client, model: 0)

    exit_code = main.run_pipeline()

    assert exit_code == 3
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "failed"
    assert summary["total_articles"] == 0
    assert summary["error"] == "no_articles_archived"
