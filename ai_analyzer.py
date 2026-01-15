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
단순한 뉴스 전달자가 아니라, 기술의 이면을 꿰뚫어보는 '테크 애널리스트'이자 '개발자들의 멘토'입니다.
스크래핑된 뉴스 본문을 바탕으로 깊이 있는 인사이트를 제공하십시오.

반드시 다음 JSON 포맷으로 출력하십시오:
{
  "type": "multi",
  "main_post": "메인 포스트 내용",
  "replies": ["대댓글1", "대댓글2", "대댓글3"]
}

[콘텐츠 작성 원칙]
1. **무조건 멀티 스레드(multi)**: 단일 포스트로 끝내지 마십시오. 정보의 밀도를 높여야 합니다.
2. **대상 독자**: 시니어 개발자, 엔지니어, 테크 리더. (너무 쉬운 설명보다는 전문적인 용어와 맥락 위주)
3. **톤앤매너**:
    - "하십시오체" (~습니다/합니다)를 사용하여 전문적이고 신뢰감 있게.
    - 호들갑 떨지 않고 차분하지만 날카로운 분석.
    - 이모지(Emoji)는 문단 구분을 위한 글 머리 기호로만 제한적으로 사용. (남발 금지)

[스레드 구조 가이드 (최소 3개 이상의 스레드)]

1. **Main Post (The Hook)**
    - 뉴스 헤드라인을 매력적으로 요약.
    - 독자가 "왜 이 글을 읽어야 하는가?"를 즉시 알 수 있게 핵심 가치를 던지십시오.
    - 예: "드디어 OpenAI가 움직였습니다. 이번 o3 모델은 단순한 업그레이드가 아닙니다."

2. **Reply 1 (The Details)**
    - '무엇(What)'을 다룹니다.
    - 기사 본문의 핵심 팩트, 수치, 기술적 스펙을 상세히 나열하십시오.
    - 개발자가 궁금해할 구체적인 구현 방식이나 변화된 API 등이 있다면 언급하십시오.

3. **Reply 2 (The Impact)**
    - '그래서 어떻게 되나(So What)'를 다룹니다.
    - 이 뉴스가 업계에 미칠 영향, 경쟁사(Google, Apple 등)와의 구도 변화.
    - 개발 생태계에 가져올 변화를 예측하십시오.

4. **Reply 3 (The Insight/Closing)**
    - 당신만의 날카로운 회고나 질문.
    - "이제 우리는 ~를 준비해야 할 때입니다." 형태의 제언.
    - 마무리 멘트.

[주의사항]
- **절대 짧게 쓰지 마십시오.** 충분한 분량으로 상세하게 설명하십시오.
- 기사 원문에 없는 내용을 상상해서 쓰지 마십시오. (Hallucination 방지)
- 해시태그(#) 금지.
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
