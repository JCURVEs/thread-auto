"""
아카이브 글 포맷 테스트.

메인 파이프라인에서 생성되는 마크다운 글의 가독성과 포맷을 검증합니다.
"""

import os
import tempfile
import shutil
from datetime import datetime
import pytest
from archiver import save_to_archive, get_archive_path


@pytest.fixture
def temp_dir(monkeypatch):
    """테스트용 임시 디렉토리."""
    temp = tempfile.mkdtemp()
    archive_dir = os.path.join(temp, "archive")
    os.makedirs(archive_dir, exist_ok=True)

    # archiver.py가 임시 디렉토리를 사용하도록 패치
    def mock_get_path(date=None):
        if date is None:
            date = datetime.now()
        filename = date.strftime("%Y-%m-%d.md")
        return os.path.join(archive_dir, filename)

    monkeypatch.setattr("archiver.get_archive_path", mock_get_path)

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
    filepath = get_archive_path()
    with open(filepath, "r", encoding="utf-8") as f:
        output = f.read()

    # 모든 글이 포함되어야 함
    assert "[OpenAI] GPT-5 출시" in output
    assert "[DeepMind] Gemini 3.0 발표" in output
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
