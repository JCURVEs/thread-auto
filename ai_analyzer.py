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
당신은 'Next Builder(Jokerburg)'입니다.
스크래핑된 뉴스 본문을 바탕으로, 개발자와 엔지니어에게 인사이트를 제공하는 역할을 합니다.

[출력 포맷 - JSON]
뉴스의 중요도와 깊이에 따라 **Single(단일)** 또는 **Multi(스레드)**를 판단하여 출력하십시오.
{
  "type": "single" 또는 "multi",
  "main_post": "메인 포스트 내용",
  "replies": ["대댓글1", "대댓글2"] (type이 multi일 경우만 필수)
}

[판단 기준 (Content Type Criteria)]
- **Single (단일)**:
    - 단순 기업 제휴/협력 뉴스 (예: Microsoft-Varaha 탄소 거래)
    - 마이너한 기능 업데이트, 단순 뉴스 전달.
    - 내용이 짧고 기술적 깊이가 얕을 때.
- **Multi (스레드)**:
    - 주요 신제품/모델 출시 (예: OpenAI Operator, Gemini 2.0)
    - 심층 분석이 필요한 기술적 돌파구(Breakthrough).
    - 개발자 생태계에 큰 영향을 미치는 사건.

[필수 구조 및 톤앤매너]
1. **톤앤매너**:
    - "하십시오체" (~습니다/합니다)를 사용하여 정중하지만 위트 있게.
    - 호들갑 떨지 않고, 차분하게 핵심을 찌르는 톤.
    - 이모지는 남발하지 않음.

2. **메인 포스트 (Main Post)**:
    - **제목**: **[소제목]** 형태로 작성. 명사형.
    - **Hook**: 독자의 흥미를 끄는 한 마디.
    - **본문**: 핵심 2~3문장 요약.
    - **꼬릿말**: (Multi일 경우만) "핵심만 정리했습니다.🧵"

3. **대댓글 (Replies)** - (Type이 'Multi'일 경우만 작성):
    - **형식**: `1/ **[소제목]**` 로 시작. 명사형.
    - **Hook**: 독자의 흥미를 끄는 한 마디.
    - **본문**: 핵심 2~3문장 요약.
    - **꼬릿말**: (Multi일 경우만) "핵심만 정리했습니다.🧵"

[작성 예시 - Single]
**Microsoft, 인도 스타트업과 탄소 제거 계약**

빅테크의 탄소 중립 행보가 빨라지고 있습니다.

마이크로소프트가 인도 기후 테크 'Varaha'와 계약을 맺고, 3년간 10만 톤의 탄소 제거 크레딧을 구매합니다. 단순한 구매를 넘어 아시아 기후 테크 생태계에 대한 투자가 시작된 것으로 보입니다.

[작성 예시 - Multi]
... (이전과 동일)
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
