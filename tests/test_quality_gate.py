"""
Quality gate tests for AI analysis output.
"""

from ai_analyzer import validate_quality_gate


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
