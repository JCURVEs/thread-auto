"""
아카이브 글 포맷 테스트.

메인 파이프라인에서 생성되는 마크다운 글의 가독성과 포맷을 검증합니다.
"""

import os
import tempfile
import shutil
from datetime import datetime
import pytest
import archiver
from archiver import save_to_archive


@pytest.fixture
def temp_dir(monkeypatch):
    """테스트용 임시 디렉토리."""
    temp = tempfile.mkdtemp()
    archive_dir = os.path.join(temp, "archive")
    os.makedirs(archive_dir, exist_ok=True)

    # archiver.py가 임시 아카이브 루트를 사용하도록 패치
    monkeypatch.setattr("archiver.get_archive_dir", lambda: archive_dir)

    yield archive_dir

    shutil.rmtree(temp)


def test_output_format_with_all_fields(temp_dir):
    """모든 필드가 포함된 글 포맷 테스트."""

    content = {
        "title": "GPT-5 출시 소식",
        "summary": "OpenAI가 차세대 언어모델 GPT-5를 공개했습니다. 기존 GPT-4 대비 성능이 3배 향상되었으며, 멀티모달 기능이 강화되었습니다.",
        "easy_explainer": "즉, 더 똑똑하고 이미지도 이해하는 AI가 나왔다는 뜻입니다.",
        "category": "LLM 출시",
        "importance": 10
    }

    filepath = save_to_archive(
        data=content,
        image_url="https://example.com/gpt5-image.jpg",
        source_url="https://openai.com/news/gpt5",
        original_title="OpenAI Releases GPT-5",
        provider="groq",
        model="llama-3.3-70b",
        source_name="openai"
    )

    # 생성된 파일 읽기
    with open(filepath, "r", encoding="utf-8") as f:
        output = f.read()

    # 포맷 검증
    assert "# Daily AI Tech News" in output
    assert "[OpenAI] GPT-5 출시 소식" in output
    assert "**분야:** LLM 출시 | **중요도:** 10점" in output
    assert "**요약:**" in output
    assert "OpenAI가 차세대 언어모델 GPT-5를 공개했습니다" in output
    assert "**쉬운설명:**" in output
    assert "즉, 더 똑똑하고 이미지도 이해하는 AI가 나왔다는 뜻입니다" in output
    assert "**출처:** https://openai.com/news/gpt5" in output
    assert "![Article Image](https://example.com/gpt5-image.jpg)" in output

    print("\n✅ 생성된 마크다운:")
    print("=" * 60)
    print(output)
    print("=" * 60)


def test_archive_path_uses_year_month_folders(temp_dir):
    """아카이브 파일은 연도/월 폴더 아래에 저장되어야 함."""

    filepath = archiver.get_archive_path(datetime(2026, 7, 10))

    assert filepath.endswith(os.path.join("archive", "2026", "07월", "2026-07-10.md"))


def test_output_format_without_image(temp_dir):
    """이미지 없는 글 포맷 테스트."""

    content = {
        "title": "Hugging Face 새로운 Transformers 라이브러리 출시",
        "summary": "Transformers 4.50 버전이 공개되었습니다.",
        "easy_explainer": "AI 개발 도구가 업데이트되었습니다.",
        "category": "오픈소스 도구",
        "importance": 7
    }

    filepath = save_to_archive(
        data=content,
        image_url=None,  # 이미지 없음
        source_url="https://huggingface.co/blog/transformers-4.50",
        original_title="Transformers 4.50 Released",
        provider="groq",
        model="llama-3.3-70b",
        source_name="huggingface"
    )

    with open(filepath, "r", encoding="utf-8") as f:
        output = f.read()

    # 이미지 태그가 없어야 함
    assert "![Article Image]" not in output
    assert "[Hugging Face]" in output
    assert "**중요도:** 7점" in output


def test_output_includes_source_metadata_when_provided(temp_dir):
    """본문 분석 여부와 RSS 원요약을 아카이브에 남겨야 함."""

    content = {
        "title": "본문 기반 분석 테스트",
        "summary": "본문을 보고 생성한 요약입니다.",
        "easy_explainer": "본문을 썼다는 뜻입니다.",
        "category": "API/인프라",
        "importance": 6
    }

    filepath = save_to_archive(
        data=content,
        image_url=None,
        source_url="https://example.com/source",
        original_title="Original Source Title",
        provider="groq",
        model="llama-3.3-70b",
        source_name="openai",
        original_summary="Original RSS summary",
        article_content_used=True,
    )

    with open(filepath, "r", encoding="utf-8") as f:
        output = f.read()

    assert "**원문제목:** Original Source Title" in output
    assert "**본문분석:** 사용" in output
    assert "**RSS요약:**" in output
    assert "Original RSS summary" in output


def test_output_includes_importance_calibration_metadata(temp_dir):
    """중요도 보정이 발생하면 원점수와 보정 사유를 남겨야 함."""

    content = {
        "title": "중요도 보정 테스트",
        "summary": "보정된 요약입니다.",
        "easy_explainer": "보정 테스트입니다.",
        "category": "연구 논문",
        "importance": 6,
        "importance_original": 9,
        "importance_adjusted_reason": "generic_arxiv_cap"
    }

    filepath = save_to_archive(
        data=content,
        image_url=None,
        source_url="https://example.com/source",
        original_title="Original Source Title",
        provider="groq",
        model="llama-3.3-70b",
        source_name="arxiv_ai",
    )

    with open(filepath, "r", encoding="utf-8") as f:
        output = f.read()

    assert "**중요도보정:** 9점 → 6점 (generic_arxiv_cap)" in output


def test_multiple_articles_same_day(temp_dir):
    """같은 날 여러 글이 append 되는지 테스트."""

    articles = [
        {
            "content": {
                "title": "OpenAI GPT-5 출시",
                "summary": "새로운 모델이 나왔습니다.",
                "easy_explainer": "더 똑똑한 AI입니다.",
                "category": "LLM 출시",
                "importance": 10
            },
            "source": "openai",
            "url": "https://openai.com/news/1"
        },
        {
            "content": {
                "title": "DeepMind Gemini 3.0 발표",
                "summary": "Google의 새 모델입니다.",
                "easy_explainer": "구글의 AI가 업그레이드 되었습니다.",
                "category": "LLM 출시",
                "importance": 9
            },
            "source": "deepmind",
            "url": "https://deepmind.google/blog/2"
        },
        {
            "content": {
                "title": "Meta AI 논문 공개",
                "summary": "새로운 연구 결과를 공유했습니다.",
                "easy_explainer": "메타의 연구 내용입니다.",
                "category": "연구 논문",
                "importance": 8
            },
            "source": "meta_research",
            "url": "https://research.facebook.com/3"
        }
    ]

    # 여러 글 저장
    for article in articles:
        save_to_archive(
            data=article["content"],
            image_url=None,
            source_url=article["url"],
            original_title="Test",
            provider="groq",
            model="llama-3.3-70b",
            source_name=article["source"]
        )

    # 같은 날 파일 읽기
    filepath = archiver.get_archive_path()
    with open(filepath, "r", encoding="utf-8") as f:
        output = f.read()

    # 모든 글이 포함되어야 함
    assert "[OpenAI] OpenAI GPT-5 출시" in output
    assert "[DeepMind] DeepMind Gemini 3.0 발표" in output
    assert "[Meta AI] Meta AI 논문 공개" in output

    # 구분선 확인 (아직 추가 안했지만 가독성 위해 필요할 수 있음)
    print("\n📰 같은 날 여러 글:")
    print("=" * 60)
    print(output)
    print("=" * 60)


def test_company_name_tags(temp_dir):
    """회사명 태그가 올바르게 표시되는지 테스트."""

    companies = {
        "openai": "OpenAI",
        "deepmind": "DeepMind",
        "google_research": "Google Research",
        "huggingface": "Hugging Face",
        "meta_research": "Meta AI",
        "nvidia_technical": "NVIDIA",
        "amd_rocm": "AMD ROCm",
        "microsoft_research": "Microsoft Research",
        "azure_ai": "Azure AI",
        "aws_machine_learning": "AWS ML",
        "google_cloud_ai": "Google Cloud AI",
        "arxiv_ai": "arXiv AI",
        "arxiv_lg": "arXiv ML",
        "arxiv_cv": "arXiv Vision",
        "arxiv_cl": "arXiv NLP"
    }

    for source_key, expected_name in companies.items():
        content = {
            "title": f"{expected_name} 테스트",
            "summary": "테스트 요약",
            "easy_explainer": "테스트 설명",
            "category": "연구 논문",
            "importance": 5
        }

        filepath = save_to_archive(
            data=content,
            image_url=None,
            source_url=f"https://example.com/{source_key}",
            original_title="Test",
            provider="groq",
            model="llama-3.3-70b",
            source_name=source_key
        )

    with open(filepath, "r", encoding="utf-8") as f:
        output = f.read()

    # 모든 회사명 태그 확인
    for expected_name in companies.values():
        assert f"[{expected_name}]" in output

    print("\n🏢 회사명 태그:")
    print("=" * 60)
    print(output)
    print("=" * 60)


def test_importance_score_display(temp_dir):
    """중요도 점수가 올바르게 표시되는지 테스트."""

    scores = [10, 9, 7, 5, 3]

    for score in scores:
        content = {
            "title": f"중요도 {score}점 글",
            "summary": f"이 글의 중요도는 {score}점입니다.",
            "easy_explainer": "테스트 설명",
            "category": "LLM 출시" if score >= 9 else "비즈니스",
            "importance": score
        }

        filepath = save_to_archive(
            data=content,
            image_url=None,
            source_url=f"https://example.com/test-{score}",
            original_title="Test",
            provider="groq",
            model="llama-3.3-70b",
            source_name="openai"
        )

    with open(filepath, "r", encoding="utf-8") as f:
        output = f.read()

    # 모든 중요도 점수 확인
    for score in scores:
        assert f"**중요도:** {score}점" in output

    print("\n⭐ 중요도 점수 표시:")
    print("=" * 60)
    print(output)
    print("=" * 60)


def test_extract_source_url_supports_current_and_legacy_formats():
    """중복 체크용 URL 파서가 현재/레거시 포맷을 모두 지원해야 함."""

    assert archiver.extract_source_url("**출처:** https://example.com/current") == "https://example.com/current"
    assert archiver.extract_source_url("전체링크 : https://example.com/legacy") == "https://example.com/legacy"
    assert archiver.extract_source_url("출처: https://example.com/plain") == "https://example.com/plain"
    assert archiver.extract_source_url("**요약:** URL이 아닌 줄") is None


def test_get_archived_urls_reads_current_and_legacy_source_formats(temp_dir, monkeypatch):
    """중복 방지가 저장 포맷 변경 후에도 동작해야 함."""

    monkeypatch.setattr(archiver, "get_archive_dir", lambda: temp_dir)

    nested_dir = os.path.join(temp_dir, "2026", "07월")
    os.makedirs(nested_dir, exist_ok=True)
    current_archive = os.path.join(nested_dir, "2026-07-09.md")
    legacy_archive = os.path.join(temp_dir, "2026-07-08.md")

    with open(current_archive, "w", encoding="utf-8") as f:
        f.write("## [OpenAI] 현재 포맷\n\n")
        f.write("**출처:** https://example.com/current\n")

    with open(legacy_archive, "w", encoding="utf-8") as f:
        f.write("## 레거시 포맷\n\n")
        f.write("전체링크 : https://example.com/legacy\n")

    archived_urls = archiver.get_archived_urls(days=7)

    assert "https://example.com/current" in archived_urls
    assert "https://example.com/legacy" in archived_urls
    assert archiver.is_duplicate("https://example.com/current")
    assert archiver.is_duplicate("https://example.com/legacy")
