"""
Quality gate tests for AI analysis output.
"""

from ai_analyzer import validate_factual_grounding, validate_quality_gate


def make_content(**overrides):
    content = {
        "title": "새로운 API 도구 공개",
        "summary": "개발자가 모델을 더 쉽게 배포할 수 있는 도구입니다.",
        "easy_explainer": "쉽게 말하면 배포 과정을 줄여주는 도구입니다.",
        "category": "API/인프라",
        "importance": 6,
    }
    content.update(overrides)
    return content


def test_quality_gate_passes_clean_content():
    """문제 없는 콘텐츠는 통과해야 함."""

    is_valid, errors = validate_quality_gate(make_content())

    assert is_valid
    assert errors == []


def test_quality_gate_blocks_foreign_text_leakage():
    """중국어/일본어/키릴 문자 잔여는 저장 전에 차단해야 함."""

    content = make_content(summary="모델의 品質 평가를 수행했습니다.")

    is_valid, errors = validate_quality_gate(content)

    assert not is_valid
    assert any("summary" in error for error in errors)


def test_quality_gate_blocks_forbidden_style_expression():
    """스타일 가이드 금지 표현은 차단해야 함."""

    content = make_content(summary="정말 혁신적인 도구가 공개되었습니다.")

    is_valid, errors = validate_quality_gate(content)

    assert not is_valid
    assert "forbidden_style:정말" in errors
    assert "forbidden_style:혁신적인" in errors


def test_quality_gate_blocks_invalid_category():
    """정의되지 않은 카테고리는 후속 큐레이션을 흐리므로 차단해야 함."""

    content = make_content(category="기타")

    is_valid, errors = validate_quality_gate(content)

    assert not is_valid
    assert "invalid_category:기타" in errors


def test_quality_gate_normalizes_string_importance():
    """문자열 중요도는 저장 전 정수로 정규화해야 함."""

    content = make_content(importance="7점")

    is_valid, errors = validate_quality_gate(content)

    assert is_valid
    assert errors == []
    assert content["importance"] == 7


def test_quality_gate_blocks_broken_translation_expression():
    """깨진 번역투와 붙어 있는 표현은 저장 전에 차단해야 함."""

    content = make_content(summary="이 도구는 모델 평가라고하는 과정을 자동화합니다.")

    is_valid, errors = validate_quality_gate(content)

    assert not is_valid
    assert "broken_translation:라고하는" in errors


def test_quality_gate_allows_english_name_with_korean_particle():
    """영문 제품명 뒤의 한국어 조사는 정상적인 문장으로 허용해야 함."""

    content = make_content(
        summary="Jetson에서 모델을 실행하고 VLM에도 같은 방식을 적용합니다."
    )

    is_valid, errors = validate_quality_gate(content)

    assert is_valid
    assert errors == []


def test_quality_gate_blocks_hangul_leaking_into_english_word():
    """번역 도중 한글과 영문이 섞인 단어는 계속 차단해야 함."""

    content = make_content(summary="펙ulative 실행으로 처리 시간을 줄였습니다.")

    is_valid, errors = validate_quality_gate(content)

    assert not is_valid
    assert "missing_space_near_english:펙ulative" in errors


def test_factual_grounding_blocks_unsupported_metric():
    """원문에 없는 성능 수치는 생성문에 보태면 안 됨."""

    content = make_content(summary="이 도구는 처리 속도를 90% 개선했습니다.")

    is_valid, errors = validate_factual_grounding(
        content,
        original_title="New deployment tool",
        original_summary="A tool for easier model deployment.",
    )

    assert not is_valid
    assert "ungrounded_metric:90%" in errors


def test_factual_grounding_allows_supported_metric():
    """원문에 있는 성능 수치는 통과해야 함."""

    content = make_content(summary="이 도구는 처리 속도를 90% 개선했습니다.")

    is_valid, errors = validate_factual_grounding(
        content,
        original_title="New deployment tool",
        original_summary="The tool improves throughput by 90%.",
    )

    assert is_valid
    assert errors == []


def test_factual_grounding_allows_translated_large_number_units():
    """영문 수량 단위를 정확한 한국어 단위로 옮긴 경우 허용해야 함."""

    content = make_content(
        summary="10억 달러를 투입하고 2.6억 개와 8억 개 모델을 제공합니다."
    )

    is_valid, errors = validate_factual_grounding(
        content,
        original_title="A $1B commitment",
        original_summary="Models have 260M and 800M parameters.",
    )

    assert is_valid
    assert errors == []


def test_factual_grounding_allows_rounded_korean_count():
    """큰 정수는 의미를 해치지 않는 범위의 한국어 반올림을 허용해야 함."""

    content = make_content(summary="약 35만 개의 문서를 공개했습니다.")

    is_valid, errors = validate_factual_grounding(
        content,
        original_summary="The dataset contains 359,240 documents.",
    )

    assert is_valid
    assert errors == []


def test_factual_grounding_allows_latex_and_word_percentages():
    """LaTeX 퍼센트와 영문 percent 표기를 한국어 퍼센트와 같게 봐야 함."""

    content = make_content(summary="지연 시간을 44.9% 줄였고 순위의 40%가 바뀌었습니다.")

    is_valid, errors = validate_factual_grounding(
        content,
        original_summary=r"Latency fell by 44.9\% and nearly 40 percent changed.",
    )

    assert is_valid
    assert errors == []


def test_factual_grounding_allows_spelled_english_large_number():
    """영문으로 적힌 큰 수와 한국어 단위 표기를 같은 값으로 인식해야 함."""

    content = make_content(summary="1,000만 건의 실험으로 결과를 확인했습니다.")

    is_valid, errors = validate_factual_grounding(
        content,
        original_summary="The study confirms this over ten million trials.",
    )

    assert is_valid
    assert errors == []
