"""
Test multilingual text detection and validation.
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_analyzer import detect_foreign_text, validate_korean_content


class TestForeignTextDetection:
    """Test foreign character detection"""

    def test_pure_korean_passes(self):
        """Pure Korean text should pass"""
        text = "이것은 순수 한국어 텍스트입니다."
        assert not detect_foreign_text(text)

    def test_korean_with_english_passes(self):
        """Korean with English technical terms should pass"""
        text = "Transformer 아키텍처를 사용합니다."
        assert not detect_foreign_text(text)

    def test_korean_with_numbers_passes(self):
        """Korean with numbers should pass"""
        text = "2024년 1월 15일에 출시되었습니다."
        assert not detect_foreign_text(text)

    def test_chinese_detected(self):
        """Chinese characters should be detected"""
        text = "研究 결과입니다"
        assert detect_foreign_text(text)

    def test_japanese_hiragana_detected(self):
        """Japanese hiragana should be detected"""
        text = "そこ에서 시작합니다"
        assert detect_foreign_text(text)

    def test_japanese_katakana_detected(self):
        """Japanese katakana should be detected"""
        text = "カタカナ 텍스트"
        assert detect_foreign_text(text)

    def test_cyrillic_detected(self):
        """Cyrillic characters should be detected"""
        text = "научный 연구"
        assert detect_foreign_text(text)

    def test_threshold_sensitivity(self):
        """Test threshold parameter"""
        # 5% foreign (below 10% default)
        text = "한국어 텍스트입니다 텍스트입니다 텍스트입니다 研"
        assert not detect_foreign_text(text, threshold=0.1)

        # Higher percentage of foreign
        text = "研究 한국"
        assert detect_foreign_text(text, threshold=0.1)

    def test_strict_mode_detects_single_foreign_character(self):
        """Strict validation should catch even sparse mixed-script leakage."""
        text = "한국어 텍스트입니다 텍스트입니다 텍스트입니다 研"
        assert detect_foreign_text(text, threshold=0.1, strict=True)

    def test_empty_string_passes(self):
        """Empty string should pass"""
        assert not detect_foreign_text("")

    def test_punctuation_only_passes(self):
        """Punctuation-only text should pass"""
        text = "... !!! ???"
        assert not detect_foreign_text(text)


class TestContentValidation:
    """Test full content validation"""

    def test_valid_content_passes(self):
        """Valid Korean content should pass"""
        content = {
            "title": "새로운 AI 모델 출시",
            "summary": "OpenAI가 GPT-5를 출시했습니다.",
            "easy_explainer": "더 똑똑한 AI가 나왔다는 뜻입니다"
        }
        is_valid, _ = validate_korean_content(content)
        assert is_valid

    def test_content_with_english_terms_passes(self):
        """Content with English technical terms should pass"""
        content = {
            "title": "Transformer 기반의 새로운 LLM",
            "summary": "Google이 Gemini 2.0을 발표했습니다.",
            "easy_explainer": "API를 통해 사용할 수 있습니다"
        }
        is_valid, _ = validate_korean_content(content)
        assert is_valid

    def test_chinese_in_title_fails(self):
        """Chinese in title should fail"""
        content = {
            "title": "新しい研究 결과",
            "summary": "한국어 요약",
            "easy_explainer": "한국어 설명"
        }
        is_valid, error = validate_korean_content(content)
        assert not is_valid
        assert "title" in error

    def test_japanese_in_summary_fails(self):
        """Japanese in summary should fail"""
        content = {
            "title": "한국어 제목",
            "summary": "そこから始まる 연구 결과",
            "easy_explainer": "한국어 설명"
        }
        is_valid, error = validate_korean_content(content)
        assert not is_valid
        assert "summary" in error

    def test_mixed_foreign_in_explainer_fails(self):
        """Mixed foreign languages in explainer should fail"""
        content = {
            "title": "한국어 제목",
            "summary": "한국어 요약",
            "easy_explainer": "研究 과정입니다"
        }
        is_valid, error = validate_korean_content(content)
        assert not is_valid
        assert "easy_explainer" in error

    def test_missing_fields_pass_validation(self):
        """Missing fields should not cause validation failure"""
        content = {
            "title": "한국어 제목만 있음"
        }
        is_valid, _ = validate_korean_content(content)
        assert is_valid  # Only validates existing fields

    def test_cyrillic_detected_in_content(self):
        """Cyrillic script in content should fail"""
        content = {
            "title": "научные исследования",
            "summary": "한국어 요약",
            "easy_explainer": "한국어 설명"
        }
        is_valid, error = validate_korean_content(content)
        assert not is_valid
        assert "title" in error

    def test_sparse_foreign_character_in_long_summary_fails(self):
        """A single CJK character in a long Korean summary should fail validation."""
        content = {
            "title": "한국어 제목",
            "summary": "이 기술은 개발자가 모델을 더 안정적으로 운영하도록 돕는 品질 검증 절차입니다.",
            "easy_explainer": "쉽게 말하면 배포 전 점검표입니다."
        }
        is_valid, error = validate_korean_content(content)
        assert not is_valid
        assert "summary" in error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
