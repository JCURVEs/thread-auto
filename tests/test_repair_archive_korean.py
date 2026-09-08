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


def test_repair_archive_retries_after_quality_failure(monkeypatch, tmp_path):
    """첫 생성문이 깨져도 다음 생성문이 정상이라면 복구해야 함."""
    archive = tmp_path / "2026-09-08.md"
    archive.write_text(
        """# Daily AI Tech News (2026-09-08)

---

## [NVIDIA] English title

**분야:** API/인프라 | **중요도:** 6점

**분석상태:** fallback

**요약:**
Models now run on NVIDIA Jetson.

**쉬운설명:**
AI 분석 결과를 신뢰하기 어렵습니다.

**출처:** https://example.com/jetson

**원문제목:** Models now run on NVIDIA Jetson

**RSS요약:**
Models now run on NVIDIA Jetson.
""",
        encoding="utf-8",
    )
    candidates = iter(
        [
            {
                "title": "Jetson에서 펙ulative 실행",
                "summary": "한글과 영문이 깨진 펙ulative 표현입니다.",
                "easy_explainer": "첫 시도는 저장하면 안 됩니다.",
                "category": "API/인프라",
                "importance": 6,
            },
            {
                "title": "Jetson에서 실행되는 AI 모델",
                "summary": "NVIDIA Jetson에서 AI 모델을 실행하는 방법을 소개합니다.",
                "easy_explainer": "작은 컴퓨터에서도 AI를 구동하는 방법입니다.",
                "category": "API/인프라",
                "importance": 6,
            },
        ]
    )
    monkeypatch.setattr(
        repair,
        "generate_thread_content",
        lambda *args, **kwargs: next(candidates),
    )

    result = repair.repair_archive(archive, client={})
    output = archive.read_text(encoding="utf-8")

    assert result == {"repaired": 1, "failed": 0, "total": 1}
    assert "Jetson에서 실행되는 AI 모델" in output
    assert "펙ulative" not in output
