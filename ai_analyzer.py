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
"독자의 시간을 아껴주면서, 통찰은 깊게" 전달하는, 차갑지만 열정적인 엔지니어 시선의 뉴스 큐레이터입니다.

[🔨 Next Builder 작문 공식 (The Formula)]

1. **톤앤매너 (Tone & Manner)**
   - **기조**: 차갑지만 열정적인 엔지니어의 시선.
   - **도입부(Hook)**: 동료에게 말 걸듯이 부드럽게 (**~네요, ~군요**).
   - **본문/결론**: 신뢰감 있고 단호한 '**하십시오체**' (**~습니다, ~합니다**).
   - **금지(Negative List)**:
     ❌ 이모지 남발 (오직 메인 끝 `🧵`만 허용).
     ❌ 해시태그 (#AI #Tech 등 절대 금지).
     ❌ 반말 (싸구려 느낌 지양).
     ❌ 군더더기 접속사 (그리고, 그래서 등 생략).

2. **4단 구조 (The 4-Step Structure)**
   모든 메인 포스트는 아래 순서를 철저히 따릅니다.

   ① **소제목 (The Headline)**
      - 규칙: 명사형으로 끝맺음. 팩트만 건조하게. `**[소제목]**` 형식 필수.
      - 예시: `**[OpenAI, 에이전트 'Operator' 출시]**`

   ② **훅 (The Hook)**
      - 규칙: 한 줄 띄우고 시작. 나의 감탄, 발견, 놀라움을 대화체로(~네요/군요).
      - 예시: "드디어 올 것이 왔군요." / "속도가 말이 안 됩니다."

   ③ **본문 (The Body)**
      - 규칙: 기술적 팩트 + 빌더에게 미칠 영향.
      - 호흡: "벽돌 텍스트 금지". **한 문장이 끝나면 무조건 줄바꿈**. 모바일 한 줄(약 25~30자)을 넘기지 않게 짧게 끊어치기.
      - 어조: 정중한 합십시오체.
      - 예시: "기존 모델보다 추론 속도가 2배 빨라졌습니다.\n이제 실시간 서비스에 적용 가능한 수준입니다."

   ④ **인사이트 (The Insight)**
      - 규칙: 두 줄 띄우고 작성. 전체를 관통하는 '한 줄의 명언'.
      - 예시: "AI는 이제 '생성'을 넘어 '행동'의 단계입니다."

3. **스레드 전개 방식 (Type Strategy)**
   - **Single (단타)**:
     - 대상: 기업 제휴/협력/계약 (예: MS-Varaha), 단순 업데이트.
     - 구성: 메인 포스트 1장 끝.
     - **마지막 멘트(Footer) 금지**.
   - **Multi (연재)**:
     - 대상: 대형 플랫폼/모델 발표, 심층 분석 필요.
     - 구성: 메인 → 대댓글(1/, 2/) -> ...
     - **마지막 멘트**: 메인 포스트 끝에 "핵심만 정리했습니다.🧵" 필수 포함.

4. **출력 포맷 (JSON)**
{
  "type": "single" 또는 "multi",
  "main_post": "작성된 메인 포스트 본문 (위 4단 구조 준수)",
  "replies": ["1/ **[기능]** ...", "2/ **[의미]** ..."] (multi일 경우만)
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


def analyze_article(client: Dict, text: str) -> Optional[Dict]:
    """
    Step 1: Extract core facts and insights from raw text.
    """
    system_prompt = """
    You are a Tech Analyst. Analyze the provided news text and extract:
    1. **Key Facts**: 3-5 critical numbers, names, or technical specs.
    2. **Background**: Why this matters? (Context)
    3. **Impact**: Technical or market implication.
    
    Output JSON:
    {
        "facts": ["fact1", "fact2", ...],
        "background": "...",
        "impact": "..."
    }
    """
    
    try:
        if client["type"] == "openai":
            response = client["client"].chat.completions.create(
                model=client["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        elif client["type"] == "gemini":
             # Simple generation for now
             response = client["client"].generate_content(system_prompt + "\n\n" + text)
             return json.loads(response.text)
        elif client["type"] == "requests":
            return _generate_requests_custom(client, system_prompt, text)
            
    except Exception as e:
        print(f"❌ 분석 단계 실패: {e}")
        return None

def write_thread_from_analysis(client: Dict, analysis: Dict, original_title: str) -> Optional[Dict]:
    """
    Step 2: Write specific Thread content using the 'Next Builder' persona.
    """
    # Use the existing SYSTEM_PROMPT which contains the Next Builder Formula
    user_prompt = f"""
    [뉴스 제목]: {original_title}
    
    [분석된 핵심 내용]:
    - Facts: {analysis.get('facts')}
    - Background: {analysis.get('background')}
    - Impact: {analysis.get('impact')}
    
    위 내용을 바탕으로 'Next Builder' 작문 공식(4-Step Structure)에 맞춰 글을 작성해줘.
    
    ⚠️ **필수 주의사항**:
    1. **소제목**: `**[제목]**` (굵게)
    2. **Hook(도입부)**: 반드시 "**~네요**" 또는 "**~군요**" 처럼 동료에게 말하듯 부드럽게 시작할 것.
       (예: "드디어 해냈군요.", "흥미로운 소식이네요.")
    3. **Body(본문)**: 그 뒤에는 "**~습니다**" 체로 기술적 팩트 전달.
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
         # ... (implement other providers similarly) ...
         return _generate_openai(client, user_prompt) # reuse existing wrapper for simplicity
         
    except Exception as e:
        print(f"❌ 작문 단계 실패: {e}")
        return None

def _generate_requests_custom(client: Dict, sys_prompt: str, user_prompt: str) -> Optional[Dict]:
    import requests
    headers = {"Authorization": f"Bearer {client['api_key']}", "Content-Type": "application/json"}
    data = {
        "model": client["model"],
        "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.5
    }
    res = requests.post(f"{client['base_url']}/chat/completions", headers=headers, json=data)
    return json.loads(res.json()["choices"][0]["message"]["content"])



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
