"""Tests for repairing legacy fallback Markdown entries."""

from scripts import repair_archive_korean as repair


def test_repair_archive_replaces_fallback_with_korean_content(monkeypatch, tmp_path):
    archive = tmp_path / "2026-09-07.md"
    archive.write_text(
        """# Daily AI Tech News (2026-09-07)

---

## [arXiv AI] English generated title

**분야:** 연구 논문 | **중요도:** 6점

**분석상태:** fallback

**분석오류:** ai_invalid_content

**요약:**  
English fallback summary.

**쉬운설명:**  
AI 분석 결과를 신뢰하기 어렵습니다.

**출처:** https://arxiv.org/abs/2609.00001

**원문제목:** A Useful Research Paper

**본문분석:** 사용

**RSS요약:**  
This paper presents a useful method for reducing inference latency.

![Article Image](https://example.com/paper.png)
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        repair,
        "generate_thread_content",
        lambda *args, **kwargs: {
            "title": "추론 지연을 줄이는 새로운 방법",
            "summary": "이 논문은 추론 지연 시간을 줄이는 방법을 제안합니다.",
            "easy_explainer": "컴퓨터가 답을 더 빨리 내도록 길을 짧게 만든 것입니다.",
            "category": "연구 논문",
            "importance": 6,
        },
    )

    result = repair.repair_archive(archive, client={})
    output = archive.read_text(encoding="utf-8")

    assert result == {"repaired": 1, "failed": 0, "total": 1}
    assert "**분석상태:** fallback" not in output
    assert "AI 분석 결과를 신뢰" not in output
    assert "추론 지연을 줄이는 새로운 방법" in output
    assert "컴퓨터가 답을 더 빨리" in output
    assert "This paper presents" in output

