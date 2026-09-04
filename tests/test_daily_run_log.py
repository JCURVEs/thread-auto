"""Daily run log tests."""

import json
from datetime import datetime, timezone

import scripts.write_daily_run_log as daily_log


def test_daily_run_log_includes_pipeline_summary(monkeypatch, tmp_path):
    """Daily log should expose whether the pipeline actually archived articles."""

    summary_path = tmp_path / "last_run.json"
    summary_path.write_text(
        json.dumps(
            {
                "status": "failed",
                "total_articles": 0,
                "error": "no_articles_archived",
                "ai_provider": "groq",
                "preferred_ai_provider": "openrouter",
                "provider_selection": ["openrouter:missing_api_key:OPENROUTER_API_KEY"],
                "fallback_archive_enabled": True,
                "stats": {
                    "archived_fallback": 2,
                    "quality_gate_failed": 2,
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(daily_log, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(daily_log, "LOG_DIR", tmp_path / "logs" / "daily")
    monkeypatch.setattr(daily_log, "LAST_RUN_SUMMARY_PATH", summary_path)
    monkeypatch.setattr(daily_log, "latest_archive_path", lambda: "archive/2026/08월/2026-08-16.md")
    monkeypatch.setattr(daily_log, "get_enabled_sources", lambda: {"openai": object()})
    monkeypatch.setattr(daily_log, "get_disabled_sources", lambda: {})
    monkeypatch.setattr(daily_log, "calculate_collection_score", lambda: 100)

    path = daily_log.write_daily_run_log(datetime(2026, 8, 24, 9, 0, tzinfo=timezone.utc))
    output = path.read_text(encoding="utf-8")

    assert "- Pipeline status: failed" in output
    assert "- AI provider: groq" in output
    assert "- Preferred AI provider: openrouter" in output
    assert "- Provider selection: openrouter:missing_api_key:OPENROUTER_API_KEY" in output
    assert "- Archived articles: 0" in output
    assert "- Pipeline error: no_articles_archived" in output
    assert "- Fallback archive: True" in output
    assert "- Pipeline stats: archived_fallback=2, quality_gate_failed=2" in output
