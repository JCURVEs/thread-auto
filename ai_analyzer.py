"""
AI Analyzer module for Thread-Auto.

This module handles AI-powered analysis using multiple FREE AI providers.
Supports Groq, OpenRouter, Gemini, and more.
"""

import json
import os
from typing import Dict, Any, Optional

# System prompt defining the 'Newsletter Curator' persona
SYSTEM_PROMPT = """
당신은 'Tech Newsletter Curator'입니다.
복잡한 테크 뉴스를 일반인도 이해하기 쉽게 핵심만 요약하여 전달하는 역할입니다.

반드시 아래 **JSON 포맷**으로만 응답해야 합니다.
다른 말(서론, 추임새)은 절대 하지 마십시오.

[출력 포맷 (JSON)]
{
  "title": "기사 제목 (흥미롭고 명확하게 한글로)",
  "summary": "핵심 내용 요약 (3~4문장, '합니다/했습니다'체)",
  "easy_explainer": "쉬운 설명 (초등학생도 이해할 수 있게 1문장으로 비유나 풀이)",
  "category": "관련 분야 (예: AI 윤리, 반도체, 로봇 등)",
  "importance": 정수 (1~10 사이의 중요도 점수)
}

[작성 규칙]
1. **타이틀**: 시선을 끌지만 낚시성 없는 명확한 한국어 제목.
2. **요약**: 기사의 6하원칙을 포함하여 전문적인 내용도 정확하게 전달.
3. **쉬운설명**: "즉, ~라는 뜻입니다" 또는 비유를 사용하여 매우 쉽게 풀이.
4. **언어**: 무조건 **한국어**로 작성.
"""

# =============================================================================
# FREE AI PROVIDER CONFIGURATIONS
# =============================================================================
PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
        "free_limit": "14,400 req/day"
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "qwen/qwen3-30b-a3b:free",
        "env_key": "OPENROUTER_API_KEY",
        "free_limit": "50 req/day"
    },
    "gemini": {
        "base_url": None,
        "default_model": "gemini-flash-latest",
        "env_key": "GEMINI_API_KEY",
        "free_limit": "1,500 req/day"
    },
}

DEFAULT_PROVIDER = "groq"


def create_client(api_key: str, provider: str = None, model: str = None):
    """Create AI client."""
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
    try:
        from openai import OpenAI
        return {"type": "openai", "client": OpenAI(api_key=api_key, base_url=base_url), "model": model}
    except ImportError:
        return {"type": "requests", "api_key": api_key, "base_url": base_url, "model": model}


def _create_gemini_client(api_key: str, model: str):
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        return {
            "type": "gemini",
            "client": genai.GenerativeModel(model_name=model, system_instruction=SYSTEM_PROMPT),
            "model": model
        }
    except ImportError:
        raise ImportError("google-generativeai package required")


def generate_thread_content(client: Dict, title: str, description: str) -> Optional[Dict]:
    """
    Generate newsletter content from news.
    Now specifically follows the Newsletter format.
    """
    user_prompt = f"""
    [뉴스 원문]
    제목: {title}
    내용: {description}
    
    위 뉴스를 'Tech Newsletter Curator'의 관점에서 분석하여 JSON으로 작성해줘.
    """
    
    try:
        if client["type"] == "openai":
            response = client["client"].chat.completions.create(
                model=client["model"],
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
            
        elif client["type"] == "gemini":
            response = client["client"].generate_content(user_prompt)
            # Cleanup Markdown code blocks if present
            raw = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(raw)
            
        elif client["type"] == "requests":
            import requests
            headers = {"Authorization": f"Bearer {client['api_key']}", "Content-Type": "application/json"}
            data = {
                "model": client["model"],
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}],
                "response_format": {"type": "json_object"}
            }
            res = requests.post(f"{client['base_url']}/chat/completions", headers=headers, json=data)
            return json.loads(res.json()["choices"][0]["message"]["content"])
            
    except Exception as e:
        print(f"❌ AI 분석 에러: {e}")
        return None


def validate_content(content: Dict[str, Any]) -> bool:
    """Validate newsletter format."""
    required_keys = ["title", "summary", "easy_explainer", "category", "importance"]
    return all(key in content for key in required_keys)


def get_provider_info() -> str:
    """
    Display available AI providers information.

    Returns:
        Formatted string with provider details.
    """
    lines = [
        "\n" + "=" * 60,
        "Available AI Providers",
        "=" * 60,
        ""
    ]

    for name, config in PROVIDERS.items():
        lines.append(f"[{name.upper()}]")
        lines.append(f"  Model: {config['default_model']}")
        lines.append(f"  Free Limit: {config['free_limit']}")
        lines.append(f"  Environment Variable: {config['env_key']}")
        lines.append(f"  Base URL: {config['base_url'] or 'Native SDK'}")
        lines.append("")

    lines.append("=" * 60)
    lines.append("Set AI_PROVIDER environment variable to choose provider.")
    lines.append("Example: export AI_PROVIDER=groq")
    lines.append("=" * 60 + "\n")

    return "\n".join(lines)
