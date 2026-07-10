"""
Thread generator tests.
"""

import json

from thread_generator import (
    GENERIC_STORYLINE_TITLES,
    HOOK_CLOSING_LINE,
    MAX_THREAD_CHARS,
    ThreadGenerator,
)


def write_archive(tmp_path, content):
    archive_dir = tmp_path / "archive" / "2026" / "07월"
    archive_dir.mkdir(parents=True)
    archive_file = archive_dir / "2026-07-10.md"
    archive_file.write_text(content, encoding="utf-8")
    return archive_file


def sample_archive():
    return """# Daily AI Tech News (2026-07-10)

---

## [OpenAI] 고객사 결제 파트너십 확대

**분야:** API/인프라 | **중요도:** 4점

**요약:**  
기업 고객 결제 파트너십에 대한 내용입니다.

**쉬운설명:**  
기업 도입 사례라는 뜻입니다.

**출처:** https://openai.com/index/payments-partnership

## [Hugging Face] vLLM Transformers 백엔드 네이티브 속도 지원

**분야:** 오픈소스 도구 | **중요도:** 8점

**요약:**  
Transformers에서 vLLM 백엔드를 더 빠르게 사용할 수 있게 됐습니다. 모델 서빙 흐름에서 처리량과 지연 시간을 확인할 만한 업데이트입니다.

**쉬운설명:**  
쉽게 말하면, 모델을 더 빠르게 돌릴 수 있는 실행 엔진을 붙인 거예요.

**출처:** https://huggingface.co/blog/native-speed-vllm-transformers-backend

**원문제목:** Native-speed vLLM Transformers backend

![Article Image](https://example.com/image.png)
"""


def test_parse_archive_extracts_structured_items(tmp_path):
    """아카이브 마크다운을 구조화된 뉴스 아이템으로 파싱해야 함."""

    archive_file = write_archive(tmp_path, sample_archive())
    generator = ThreadGenerator(project_root=tmp_path)

    items = generator.parse_archive(archive_file)

    assert len(items) == 2
    assert items[1]["company"] == "Hugging Face"
    assert items[1]["category"] == "오픈소스 도구"
    assert items[1]["importance"] == 8
    assert items[1]["source_url"] == "https://huggingface.co/blog/native-speed-vllm-transformers-backend"
    assert items[1]["image_url"] == "https://example.com/image.png"


def test_select_news_candidate_skips_low_importance_items(tmp_path):
    """중요도 8점 이상 비즈니스 외 기술 뉴스만 후보로 골라야 함."""

    archive_file = write_archive(tmp_path, sample_archive())
    generator = ThreadGenerator(project_root=tmp_path)
    items = generator.parse_archive(archive_file)

    candidate = generator.select_news_candidate(items)

    assert candidate["company"] == "Hugging Face"
    assert candidate["importance"] == 8


def test_generate_news_thread_writes_thread_files_and_metadata(tmp_path):
    """뉴스 생성기는 실제 thread 파일과 metadata를 작성해야 함."""

    write_archive(tmp_path, sample_archive())
    generator = ThreadGenerator(project_root=tmp_path)

    result = generator.generate_news_thread("2026-07-10")

    assert result == 0
    output_dirs = list((tmp_path / "threads" / "news").glob("20260710-*"))
    assert len(output_dirs) == 1

    output_dir = output_dirs[0]
    thread_files = sorted(output_dir.glob("thread-*.md"))
    assert len(thread_files) == 9
    assert (output_dir / "review-report.md").exists()

    metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
    review_report = (output_dir / "review-report.md").read_text(encoding="utf-8")
    assert metadata["source"] in {
        "archive\\2026\\07월\\2026-07-10.md",
        "archive/2026/07월/2026-07-10.md",
    }
    assert metadata["company"] == "Hugging Face"
    assert metadata["status"] == "draft"
    assert metadata["thread_count"] == 9
    assert metadata["review_status"] == "READY_FOR_HUMAN_REVIEW"
    assert metadata["review_blocking_count"] == 0
    assert metadata["review_warning_count"] == 0
    assert "- 상태: READY_FOR_HUMAN_REVIEW" in review_report
    assert "## 차단 이슈\n- 없음" in review_report
    assert "- source_url_present" in review_report

    title_post = thread_files[0].read_text(encoding="utf-8").strip()
    hook_post = thread_files[1].read_text(encoding="utf-8").strip()
    first_slide = thread_files[2].read_text(encoding="utf-8").strip()

    assert "\n" not in title_post
    assert hook_post.splitlines()[-1] == HOOK_CLOSING_LINE
    assert len(hook_post.splitlines()) == 5
    assert first_slide.startswith("1/ ")
    assert "기존 상식 뒤집기" not in first_slide.splitlines()[0]
    assert "vLLM" in first_slide.splitlines()[0] or "Transformers" in first_slide.splitlines()[0]
    assert 7 <= len(first_slide.splitlines()) <= 9

    for path in thread_files:
        assert len(path.read_text(encoding="utf-8").strip()) <= MAX_THREAD_CHARS


def test_build_news_posts_uses_storyline_order(tmp_path):
    """생성 글은 1/부터 7/까지 정해진 스토리 흐름을 따라야 함."""

    archive_file = write_archive(tmp_path, sample_archive())
    generator = ThreadGenerator(project_root=tmp_path)
    candidate = generator.select_news_candidate(generator.parse_archive(archive_file))

    posts = generator.build_news_posts(candidate)

    assert len(posts) == 9
    expected_keywords_by_slide = [
        ("vLLM", "Transformers", "백엔드"),
        ("병목", "적용 속도"),
        ("Hugging Face", "연결"),
        ("vLLM", "Transformers", "백엔드", "구현부"),
        ("vLLM", "Transformers", "백엔드", "흐름"),
        ("중요도", "숫자", "성과"),
        ("vLLM", "Transformers", "백엔드", "방식"),
    ]

    for index, post in enumerate(posts[2:], 1):
        first_line = post.splitlines()[0]
        assert first_line.startswith(f"{index}/ ")
        subtitle = first_line.removeprefix(f"{index}/ ")
        assert subtitle not in GENERIC_STORYLINE_TITLES
        assert any(keyword in subtitle for keyword in expected_keywords_by_slide[index - 1])


def test_story_slide_title_uses_natural_topic_marker(tmp_path):
    """내용형 소제목에서 은/는 조사가 어색하게 붙지 않아야 함."""

    archive_file = write_archive(tmp_path, sample_archive())
    generator = ThreadGenerator(project_root=tmp_path)
    candidate = generator.select_news_candidate(generator.parse_archive(archive_file))

    posts = generator.build_news_posts(candidate)

    subtitles = [post.splitlines()[0] for post in posts[2:]]

    assert all("백엔드은" not in subtitle for subtitle in subtitles)
    assert all("Hugging Face은" not in subtitle for subtitle in subtitles)
    assert all("점로" not in subtitle for subtitle in subtitles)


def test_story_slide_title_normalizes_translated_product_terms(tmp_path):
    """제품명에 가까운 영문 기술어가 어색한 직역으로 남지 않아야 함."""

    generator = ThreadGenerator(project_root=tmp_path)
    topic = generator._topic_phrase("네이티브 속도 vLLM 변형기 모델링 백엔드", "Hugging Face")
    title = generator._display_title({
        "title": "네이티브 속도 vLLM 변형기 모델링 백엔드",
    })

    assert topic == "vLLM Transformers 백엔드"
    assert title == "네이티브 속도 vLLM Transformers 백엔드"


def test_news_posts_follow_jokerburg_style_rhythm(tmp_path):
    """생성 글은 짧은 진단문과 실무 관점의 리듬을 유지해야 함."""

    archive_file = write_archive(tmp_path, sample_archive())
    generator = ThreadGenerator(project_root=tmp_path)
    candidate = generator.select_news_candidate(generator.parse_archive(archive_file))

    posts = generator.build_news_posts(candidate)
    hook = posts[1]
    body = "\n".join(posts[2:])

    assert "겉보기엔" in hook
    assert "근데 뜯어보면" in hook
    assert "먼저 용어부터." in body
    assert "핵심은 이겁니다." in body
    assert "실무" in body
    assert all(7 <= len(post.splitlines()) <= 9 for post in posts[2:])


def test_pre_publish_review_blocks_unsupported_metrics_and_overclaims(tmp_path):
    """근거 없는 숫자 성과나 과장 표현은 게시 전 차단해야 함."""

    archive_file = write_archive(tmp_path, sample_archive())
    generator = ThreadGenerator(project_root=tmp_path)
    candidate = generator.select_news_candidate(generator.parse_archive(archive_file))
    posts = generator.build_news_posts(candidate)
    posts[5] = posts[5] + "\n기존 대비 90% 개선된 게임체인저입니다."

    review = generator.review_news_posts(candidate, posts)

    assert review["status"] == "BLOCKED"
    assert "unsupported_metric:90%" in review["blocking"]
    assert "overclaim:게임체인저" in review["blocking"]


def test_pre_publish_review_blocks_broken_thread_structure(tmp_path):
    """스레드 구조가 깨지면 게시 전 차단해야 함."""

    archive_file = write_archive(tmp_path, sample_archive())
    generator = ThreadGenerator(project_root=tmp_path)
    candidate = generator.select_news_candidate(generator.parse_archive(archive_file))
    posts = generator.build_news_posts(candidate)
    posts[1] = posts[1].replace(HOOK_CLOSING_LINE, "다음에 계속")
    posts[3] = posts[3].replace("2/ ", "두번째 ")

    review = generator.review_news_posts(candidate, posts)

    assert review["status"] == "BLOCKED"
    assert "hook_closing_missing" in review["blocking"]
    assert "slide_2_numbering" in review["blocking"]


def test_generic_story_slide_title_is_rejected(tmp_path):
    """구조명 자체를 소제목으로 쓰는 실수를 막아야 함."""

    generator = ThreadGenerator(project_root=tmp_path)

    try:
        generator._build_story_slide("1/", "기존 상식 뒤집기", ["본문입니다."] * 6)
    except ValueError as exc:
        assert "Generic slide subtitle" in str(exc)
    else:
        raise AssertionError("generic subtitle should be rejected")


def test_generate_news_thread_returns_failure_without_candidate(tmp_path):
    """후보가 없으면 파일을 만들지 않고 실패 코드를 반환해야 함."""

    archive = """# Daily AI Tech News (2026-07-10)

## [OpenAI] 고객사 사례

**분야:** 비즈니스 | **중요도:** 3점

**요약:**  
고객사 사례입니다.

**쉬운설명:**  
비즈니스 뉴스입니다.

**출처:** https://example.com/customer-story
"""
    write_archive(tmp_path, archive)
    generator = ThreadGenerator(project_root=tmp_path)

    result = generator.generate_news_thread("2026-07-10")

    assert result == 1
    assert not (tmp_path / "threads").exists()
