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


def test_process_single_entry_archives_fallback_when_quality_gate_fails(monkeypatch):
    """Fallback archive가 켜져 있으면 품질 실패도 원문 기반 후보로 보관해야 함."""

    captured = {}

    monkeypatch.setattr(main, "ENABLE_FALLBACK_ARCHIVE", True)
    main.PROCESS_STATS.clear()
    monkeypatch.setattr(main, "is_duplicate", lambda url: False)
    monkeypatch.setattr(main, "get_article_image", lambda url: None)
    monkeypatch.setattr(main, "fetch_article_content", lambda url: "원문 본문입니다. " * 30)

    def fake_generate_thread_content(client, title, description, article_content=""):
        content = make_valid_content()
        content["summary"] = "정말 혁신적인 도구이며 品質 평가를 포함합니다."
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
        captured["article_content_used"] = article_content_used
        return "archive/test.md"

    monkeypatch.setattr(main, "generate_thread_content", fake_generate_thread_content)
    monkeypatch.setattr(main, "save_to_archive", fake_save_to_archive)

    assert main.process_single_entry(make_recent_entry(), "openai", {}, "test-model")
    assert captured["data"]["analysis_status"] == "fallback"
    assert captured["data"]["analysis_error"].startswith("quality_gate_failed")
    assert captured["article_content_used"] is True
    assert main.PROCESS_STATS["quality_gate_failed"] == 1
    assert main.PROCESS_STATS["archived_fallback"] == 1


def test_process_single_entry_archives_fallback_without_ai_client(monkeypatch):
    """AI 클라이언트가 없을 때도 fallback 후보를 저장할 수 있어야 함."""

    captured = {}

    monkeypatch.setattr(main, "ENABLE_FALLBACK_ARCHIVE", True)
    main.PROCESS_STATS.clear()
    monkeypatch.setattr(main, "is_duplicate", lambda url: False)
    monkeypatch.setattr(main, "get_article_image", lambda url: "https://example.com/image.png")
    monkeypatch.setattr(main, "fetch_article_content", lambda url: "")

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
        captured["image_url"] = image_url
        captured["source_name"] = source_name
        return "archive/test.md"

    monkeypatch.setattr(main, "save_to_archive", fake_save_to_archive)

    assert main.process_single_entry(make_recent_entry(), "nvidia_korea_blog", None, "fallback")
    assert captured["data"]["analysis_status"] == "fallback"
    assert captured["data"]["category"] == "API/인프라"
    assert captured["image_url"] == "https://example.com/image.png"
    assert captured["source_name"] == "nvidia_korea_blog"


def test_select_ai_client_prefers_groq_free_provider(monkeypatch):
    """기본 provider는 Groq 무료 티어여야 함."""

    main.PROCESS_STATS.clear()
    monkeypatch.setattr(main, "AI_PROVIDER", "groq")
    monkeypatch.setattr(main, "AI_PROVIDER_FALLBACKS", "groq,gemini,openrouter")
    monkeypatch.setattr(main, "AI_MODEL", None)
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    monkeypatch.setattr(
        main,
        "get_api_key",
        lambda provider=None: "groq-key" if provider == "groq" else None,
    )
    monkeypatch.setattr(
        main,
        "create_client",
        lambda api_key, provider, model: {
            "api_key": api_key,
            "provider": provider,
            "model": model,
        },
    )

    provider, model, client, skipped = main.select_ai_client()

    assert provider == "groq"
    assert model == "llama-3.3-70b-versatile"
    assert client["provider"] == "groq"
    assert client["api_key"] == "groq-key"
    assert skipped == []


def test_select_ai_client_blocks_paid_openrouter_model_by_default(monkeypatch):
    """OpenRouter 유료 모델은 명시 허용 전에는 호출하지 않아야 함."""

    main.PROCESS_STATS.clear()
    monkeypatch.setattr(main, "AI_PROVIDER", "openrouter")
    monkeypatch.setattr(main, "AI_PROVIDER_FALLBACKS", "openrouter,groq,gemini")
    monkeypatch.setattr(main, "AI_MODEL", None)
    monkeypatch.setattr(main, "ALLOW_PAID_MODELS", False)
    monkeypatch.setenv("OPENROUTER_MODEL", "qwen/qwen3.8-flash")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    monkeypatch.setattr(
        main,
        "get_api_key",
        lambda provider=None: f"{provider}-key",
    )
    monkeypatch.setattr(
        main,
        "create_client",
        lambda api_key, provider, model: {
            "api_key": api_key,
            "provider": provider,
            "model": model,
        },
    )

    provider, model, client, skipped = main.select_ai_client()

    assert provider == "groq"
    assert model == "llama-3.3-70b-versatile"
    assert client["provider"] == "groq"
    assert any(item == "openrouter:paid_model_blocked:qwen/qwen3.8-flash" for item in skipped)
    assert main.PROCESS_STATS["provider_paid_model_blocked_openrouter"] == 1


def test_select_ai_client_allows_openrouter_free_model(monkeypatch):
    """OpenRouter를 쓰더라도 :free 모델이면 허용해야 함."""

    main.PROCESS_STATS.clear()
    monkeypatch.setattr(main, "AI_PROVIDER", "openrouter")
    monkeypatch.setattr(main, "AI_PROVIDER_FALLBACKS", "openrouter,groq,gemini")
    monkeypatch.setattr(main, "AI_MODEL", None)
    monkeypatch.setattr(main, "ALLOW_PAID_MODELS", False)
    monkeypatch.setenv("OPENROUTER_MODEL", "qwen/qwen3-30b-a3b:free")
    monkeypatch.setattr(
        main,
        "get_api_key",
        lambda provider=None: "openrouter-key" if provider == "openrouter" else None,
    )
    monkeypatch.setattr(
        main,
        "create_client",
        lambda api_key, provider, model: {
            "api_key": api_key,
            "provider": provider,
            "model": model,
        },
    )

    provider, model, client, skipped = main.select_ai_client()

    assert provider == "openrouter"
    assert model == "qwen/qwen3-30b-a3b:free"
    assert client["provider"] == "openrouter"
    assert skipped == []


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
    monkeypatch.setattr(main, "get_api_key", lambda provider=None: None)

    exit_code = main.run_pipeline()

    assert exit_code == 2
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "failed"
    assert summary["error"] == "no_available_ai_provider"
    assert any(
        item.startswith("groq:missing_api_key")
        for item in summary["provider_selection"]
    )


def test_run_pipeline_can_archive_fallback_when_api_key_missing(monkeypatch, tmp_path):
    """Fallback archive가 켜져 있으면 API 키 문제도 수집 자체를 끊지 않아야 함."""

    summary_path = tmp_path / "last_run.json"
    calls = {}

    monkeypatch.setattr(main, "LAST_RUN_SUMMARY_PATH", summary_path)
    monkeypatch.setattr(main, "ENABLE_FALLBACK_ARCHIVE", True)
    monkeypatch.setattr(main, "REQUIRE_DAILY_ARTICLE", True)
    monkeypatch.setattr(main, "get_api_key", lambda provider=None: None)
    monkeypatch.setattr(main, "DEFAULT_RSS_SOURCES", {"openai": "https://example.com/rss"})

    def fake_process_single_source(source_name, rss_url, client, model):
        calls["client"] = client
        calls["model"] = model
        return 1

    monkeypatch.setattr(main, "process_single_source", fake_process_single_source)

    exit_code = main.run_pipeline()

    assert exit_code == 0
    assert calls["client"] is None
    assert calls["model"]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "success"
    assert summary["total_articles"] == 1
    assert summary["fallback_archive_enabled"] is True
    assert summary["ai_provider"] == "groq"
    assert summary["stats"]["no_ai_provider_fallback"] == 1


def test_run_pipeline_can_fail_when_no_articles_required(monkeypatch, tmp_path):
    """일일 글 생성이 필수인 실행에서 0건 수집은 실패로 기록해야 함."""

    summary_path = tmp_path / "last_run.json"
    monkeypatch.setattr(main, "LAST_RUN_SUMMARY_PATH", summary_path)
    monkeypatch.setattr(main, "REQUIRE_DAILY_ARTICLE", True)
    monkeypatch.setattr(main, "get_api_key", lambda provider=None: "key")
    monkeypatch.setattr(main, "create_client", lambda api_key, provider, model: {})
    monkeypatch.setattr(main, "DEFAULT_RSS_SOURCES", {"openai": "https://example.com/rss"})
    monkeypatch.setattr(main, "process_single_source", lambda source_name, rss_url, client, model: 0)

    exit_code = main.run_pipeline()

    assert exit_code == 3
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "failed"
    assert summary["total_articles"] == 0
    assert summary["error"] == "no_articles_archived"
