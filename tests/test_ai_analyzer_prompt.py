"""
AI analyzer prompt construction tests.
"""

import json
import pytest

from ai_analyzer import AIAnalysisError, _normalize_generated_korean, generate_thread_content


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeResponse:
    def __init__(self, content):
        self.choices = [FakeChoice(content)]


class FakeCompletions:
    def __init__(self):
        self.last_messages = None

    def create(self, model, messages, response_format, **kwargs):
        self.last_messages = messages
        content = {
            "title": "테스트 제목",
            "summary": "본문을 근거로 작성한 요약입니다.",
            "easy_explainer": "쉽게 말하면 테스트입니다.",
            "category": "API/인프라",
            "importance": 6,
        }
        return FakeResponse(json.dumps(content, ensure_ascii=False))


class FakeChat:
    def __init__(self):
        self.completions = FakeCompletions()


class FakeClient:
    def __init__(self):
        self.chat = FakeChat()


def test_generate_thread_content_includes_article_body_when_provided():
    """기사 본문이 있으면 RSS 요약과 함께 프롬프트에 포함해야 함."""

    fake_client = FakeClient()
    client = {"type": "openai", "client": fake_client, "model": "fake-model"}

    result = generate_thread_content(
        client,
        title="RSS 제목",
        description="짧은 RSS 요약",
        article_content="긴 기사 본문입니다. 실제 근거 문장입니다.",
    )

    user_prompt = fake_client.chat.completions.last_messages[1]["content"]

    assert result["title"] == "테스트 제목"
    assert "RSS 요약: 짧은 RSS 요약" in user_prompt
    assert "[기사 본문]" in user_prompt
    assert "긴 기사 본문입니다. 실제 근거 문장입니다." in user_prompt
    assert "RSS 요약보다 기사 본문을 우선 근거" in user_prompt


def test_generate_thread_content_omits_article_body_when_missing():
    """기사 본문이 없으면 기존 RSS 요약 기반 프롬프트로 동작해야 함."""

    fake_client = FakeClient()
    client = {"type": "openai", "client": fake_client, "model": "fake-model"}

    generate_thread_content(
        client,
        title="RSS 제목",
        description="짧은 RSS 요약",
    )

    user_prompt = fake_client.chat.completions.last_messages[1]["content"]

    assert "RSS 요약: 짧은 RSS 요약" in user_prompt
    assert "[기사 본문]" not in user_prompt


def test_generate_thread_content_preserves_provider_failure_details():
    """Provider 오류를 None으로 덮지 말고 재시도 내역을 전달해야 함."""

    class FailingCompletions:
        def create(self, **kwargs):
            raise RuntimeError("model route unavailable")

    class FailingClient:
        def __init__(self):
            self.chat = type("Chat", (), {"completions": FailingCompletions()})()

    client = {"type": "openai", "client": FailingClient(), "model": "retired-model"}

    with pytest.raises(AIAnalysisError) as exc_info:
        generate_thread_content(client, "제목", "요약", max_retries=2)

    assert exc_info.value.reason == "provider_attempts_exhausted"
    assert len(exc_info.value.details) == 2
    assert all("model route unavailable" in detail for detail in exc_info.value.details)


def test_normalize_generated_korean_repairs_known_mixed_words():
    """반복 확인된 한영 혼합 번역 오류는 저장 전에 교정해야 함."""

    content = {
        "title": "펙ulative 실행 기법",
        "summary": "서rogate 모델을 사용합니다.",
        "easy_explainer": "펙ulative 단계가 먼저 답을 준비합니다.",
    }

    normalized = _normalize_generated_korean(content)

    assert normalized["title"] == "추측 실행 기법"
    assert normalized["summary"] == "대리 모델을 사용합니다."
    assert normalized["easy_explainer"] == "추측 단계가 먼저 답을 준비합니다."
