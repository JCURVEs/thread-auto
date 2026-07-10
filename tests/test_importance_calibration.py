"""
Importance calibration tests.
"""

from ai_analyzer import calibrate_importance


def make_content(category="연구 논문", importance=9):
    return {
        "title": "테스트 제목",
        "summary": "테스트 요약입니다.",
        "easy_explainer": "쉽게 말하면 테스트입니다.",
        "category": category,
        "importance": importance,
    }


def test_generic_arxiv_paper_is_capped_at_six():
    """일반 논문 초록은 모델이 9점을 줘도 6점으로 제한해야 함."""

    content = make_content(importance=9)

    calibrated = calibrate_importance(
        content,
        source_name="arxiv_ai",
        original_title="A Novel Framework for Text Understanding",
        original_summary="We propose a framework and discuss implications.",
    )

    assert calibrated["importance"] == 6
    assert calibrated["importance_original"] == 9
    assert "generic_arxiv_cap" in calibrated["importance_adjusted_reason"]


def test_arxiv_with_practical_benchmark_signal_can_keep_eight():
    """벤치마크/코드/성능 근거가 있는 논문은 8점까지 유지 가능해야 함."""

    content = make_content(importance=8)

    calibrated = calibrate_importance(
        content,
        source_name="arxiv_lg",
        original_title="Open-source Long Context Inference Benchmark",
        original_summary="Code is available on GitHub and improves throughput by 2x.",
    )

    assert calibrated["importance"] == 8
    assert "importance_original" not in calibrated


def test_business_signals_are_capped_below_thread_threshold():
    """파트너십/고객 사례 같은 비즈니스성 글은 스레드 후보 임계값 아래로 내려야 함."""

    content = make_content(category="API/인프라", importance=8)

    calibrated = calibrate_importance(
        content,
        source_name="openai",
        original_title="OpenAI announces payments partnership with Example Bank",
        original_summary="The customer adoption case study focuses on enterprise rollout.",
    )

    assert calibrated["importance"] == 4
    assert calibrated["importance_original"] == 8
    assert "business_signal_cap" in calibrated["importance_adjusted_reason"]


def test_model_release_without_business_signal_keeps_high_score():
    """실제 모델 출시 신호는 높은 중요도를 유지해야 함."""

    content = make_content(category="LLM 출시", importance=9)

    calibrated = calibrate_importance(
        content,
        source_name="openai",
        original_title="Introducing GPT-5.2",
        original_summary="A new model release improves coding accuracy by 3x.",
    )

    assert calibrated["importance"] == 9
    assert "importance_original" not in calibrated


def test_high_weight_platform_source_can_boost_practical_article():
    """실무 기술 신호가 있는 고가중치 플랫폼 소스는 한 단계 보정 가능해야 함."""

    content = make_content(category="API/인프라", importance=7)

    calibrated = calibrate_importance(
        content,
        source_name="aws_machine_learning",
        original_title="Optimize inference throughput with managed GPU serving",
        original_summary="The post includes benchmark results and improves latency by 2x.",
    )

    assert calibrated["importance"] == 8
    assert calibrated["importance_original"] == 7
    assert "source_weight_boost" in calibrated["importance_adjusted_reason"]
    assert calibrated["source_weight"] > 1.0


def test_non_numeric_importance_is_normalized():
    """모델이 문자열 점수를 반환해도 1-10 정수로 정규화해야 함."""

    content = make_content(category="오픈소스 도구", importance="7점")

    calibrated = calibrate_importance(
        content,
        source_name="huggingface",
        original_title="New open-source library",
        original_summary="The SDK is available now.",
    )

    assert calibrated["importance"] == 7
