"""
AI Analyzer module for Thread-Auto.

This module handles AI-powered analysis using multiple FREE AI providers.
Supports Groq, OpenRouter, Gemini, and more.

Easily switch between providers via environment variable AI_PROVIDER.
"""

import json
import os
from typing import Dict, Any, Optional, Callable
from abc import ABC, abstractmethod


# System prompt defining the 'Next Builder' persona
SYSTEM_PROMPT = """
당신은 'Next Builder'입니다.
개발자와 엔지니어에게 **인사이트**를 제공하는 테크 뉴스 큐레이터입니다.

[판단 기준 (Content Type Criteria)]
1. **Single (단일)**:
    - 기업 제휴/협력/계약 (예: MS-Varaha 탄소 계약).
    - 단순 기능 업데이트, 숫자/실적 발표.
    - **단순 소식**. 핵심 내용이 짧고 명확할 때.
2. **Multi (스레드)**:
    - 완전히 새로운 **플랫폼/모델 출시** (예: OpenAI Operator, Gemini 2.0).
    - 깊은 기술적 분석이나 업계에 미치는 영향(Insight)이 할 말이 많을 때.
    - **중요 뉴스**.

[작성 규칙 (Writing Rules)]
1. **어조**: 정중한 **하십시오체** (~습니다/합니다).
    - "해요"체 금지. "이다"체 금지.
2. **스타일**:
    - 문장은 **짧고 간결하게**.
    - **줄바꿈**을 자주 사용하여 모바일 가독성을 극대화할 것.
    - **절대 길게 늘어쓰지 말 것.**
3. **금지 사항**:
    - 이모지 남발 금지 (Single은 아예 금지, Multi는 메인 마지막 🧵만 허용).
    - 해시태그(#) 금지.
    - 반말 금지.

[메인 포스트 구조 (Main Post Structure)]
반드시 아래 순서를 따르십시오:
1. **제목**: `**[소제목]**` (굵게, 대괄호 포함). 핵심을 찌르는 명사형.
2. **Hook**: 독자의 흥미를 끄는 한 마디. (줄바꿈)
3. **Body**: 핵심 내용 요약 (2~3문장). (줄바꿈)
4. **Insight**: 이 뉴스가 가지는 의미나 여파 (1~2문장). (줄바꿈)
5. **Footer**: (Multi일 경우만) "핵심만 정리했습니다.🧵"

[작성 예시 - Best Practice]
**[OpenAI, PC 제어 에이전트 'Operator' 출시]**

드디어 AI에게 마우스를 쥐여주는군요.

단순한 채팅을 넘어, 브라우저를 열고 클릭하고 결제까지 수행하는 '행동하는 AI'가 나왔습니다.
기존 워크플로우 자동화 툴들이 긴장해야 할 수준의 정교함을 보여줍니다.
이제 인간은 지시하고, 실행은 AI가 맡는 시대가 열렸습니다.

AI는 이제 '말'이 아니라 '행동'으로 증명합니다.

(Multi일 경우만: 핵심만 정리했습니다.🧵)

[출력 포맷 - JSON]
{
  "type": "single" 또는 "multi",
  "main_post": "작성된 메인 포스트 본문 (10줄 이내)",
  "replies": ["대댓글1", "대댓글2"] (multi일 경우만 포함)
}
"""


# =============================================================================
# FREE AI PROVIDER CONFIGURATIONS (무료 AI 제공자 설정)
# Update this section when better free models become available!
# =============================================================================
PROVIDERS = {
    # Groq: 가장 빠름, 일 14,400회 무료, 신용카드 불필요
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
        "free_limit": "14,400 req/day, 70K tokens/min",
        "models": [
            "llama-3.3-70b-versatile",  # 추천: 성능 우수
            "llama-3.1-8b-instant",     # 빠른 응답
            "mixtral-8x7b-32768",       # 넓은 컨텍스트
            "gemma2-9b-it",             # 구글 Gemma
        ]
    },
    # OpenRouter: 400+ 모델, 일 50회 무료
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "qwen/qwen3-30b-a3b:free",
        "env_key": "OPENROUTER_API_KEY",
        "free_limit": "50 req/day, 20 req/min",
        "models": [
            "qwen/qwen3-30b-a3b:free",      # Qwen3 무료
            "qwen/qwen3-235b-a22b:free",    # Qwen3 대형 무료
            "meta-llama/llama-3.3-70b-instruct:free",
            "google/gemma-2-9b-it:free",
        ]
    },
    # Gemini: 일 1,500회 무료
    "gemini": {
        "base_url": None,  # Uses native SDK
        "default_model": "gemini-1.5-flash",
        "env_key": "GEMINI_API_KEY",
        "free_limit": "1,500 req/day, 15 req/min",
        "models": [
            "gemini-1.5-flash",    # 빠름, 무료 추천
            "gemini-1.5-pro",      # 강력, 일 50회
            "gemini-2.0-flash",    # 최신
        ]
    },
}

# Default provider (환경변수로 변경 가능)
DEFAULT_PROVIDER = "groq"


def get_provider_info() -> str:
    """
    Get information about available AI providers and current config.

    Returns:
        Formatted string with provider information.
    """
    lines = ["=" * 50, "🤖 사용 가능한 무료 AI 제공자", "=" * 50]
    for name, config in PROVIDERS.items():
        lines.append(f"\n[{name.upper()}]")
        lines.append(f"  모델: {config['default_model']}")
        lines.append(f"  무료 한도: {config['free_limit']}")
        lines.append(f"  환경변수: {config['env_key']}")
    return "\n".join(lines)


def create_client(api_key: str, provider: str = None, model: str = None):
    """
    Create an AI client for the specified provider.

    Args:
        api_key: API key for the provider.
        provider: Provider name (groq, openrouter, gemini).
        model: Optional model override.

    Returns:
        Configured client instance.
    """
    provider = provider or DEFAULT_PROVIDER
    config = PROVIDERS.get(provider)

    if not config:
        raise ValueError(f"Unknown provider: {provider}")

    model = model or config["default_model"]

    if provider == "gemini":
        return _create_gemini_client(api_key, model)
    else:
        return _create_openai_compatible_client(api_key, config["base_url"], model)


def _create_openai_compatible_client(api_key: str, base_url: str, model: str):
    """
    Create client for OpenAI-compatible APIs (Groq, OpenRouter).
    """
    try:
        from openai import OpenAI
        return {
            "type": "openai",
            "client": OpenAI(api_key=api_key, base_url=base_url),
            "model": model
        }
    except ImportError:
        # Fallback to requests
        return {
            "type": "requests",
            "api_key": api_key,
            "base_url": base_url,
            "model": model
        }


def _create_gemini_client(api_key: str, model: str):
    """Create client for Google Gemini API."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)

        generation_config = genai.GenerationConfig(
            temperature=0.7,
            max_output_tokens=1000,
            response_mime_type="application/json"
        )

        return {
            "type": "gemini",
            "client": genai.GenerativeModel(
                model_name=model,
                generation_config=generation_config,
                system_instruction=SYSTEM_PROMPT
            ),
            "model": model
        }
    except ImportError:
        raise ImportError("google-generativeai 패키지가 필요합니다.")


def generate_thread_content(
    client: Dict,
    title: str,
    description: str
) -> Optional[Dict[str, Any]]:
    """
    Generate thread content from news title and description.

    Args:
        client: Client dictionary from create_client().
        title: News article title.
        description: News article description/summary.

    Returns:
        Dictionary with type, main_post, and replies.
    """
    user_prompt = f"뉴스 제목: {title}\n\n뉴스 내용:\n{description}"

    try:
        if client["type"] == "openai":
            return _generate_openai(client, user_prompt)
        elif client["type"] == "gemini":
            return _generate_gemini(client, user_prompt)
        elif client["type"] == "requests":
            return _generate_requests(client, user_prompt)
    except Exception as e:
        print(f"❌ AI 분석 실패: {e}")
        return None


def _generate_openai(client: Dict, user_prompt: str) -> Optional[Dict]:
    """Generate using OpenAI-compatible API."""
    response = client["client"].chat.completions.create(
        model=client["model"],
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
        max_tokens=1000
    )
    return json.loads(response.choices[0].message.content)


def _generate_gemini(client: Dict, user_prompt: str) -> Optional[Dict]:
    """Generate using Gemini API."""
    response = client["client"].generate_content(user_prompt)
    return json.loads(response.text)


def _generate_requests(client: Dict, user_prompt: str) -> Optional[Dict]:
    """Generate using raw requests (fallback)."""
    import requests

    headers = {
        "Authorization": f"Bearer {client['api_key']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": client["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.7,
        "max_tokens": 1000
    }

    response = requests.post(
        f"{client['base_url']}/chat/completions",
        headers=headers,
        json=data,
        timeout=60
    )
    response.raise_for_status()
    return json.loads(response.json()["choices"][0]["message"]["content"])


def validate_content(content: Dict[str, Any]) -> bool:
    """
    Validate that generated content follows the required format.

    Args:
        content: Generated content dictionary.

    Returns:
        True if content is valid, False otherwise.
    """
    if not content:
        return False

    if "type" not in content or "main_post" not in content:
        return False

    if content["type"] not in ["single", "multi"]:
        return False

    if content["type"] == "multi":
        if "replies" not in content or not isinstance(content["replies"], list):
            return False

    return True
