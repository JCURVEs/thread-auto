"""
AI Analyzer module for Thread-Auto.

This module handles AI-powered analysis of news articles using OpenAI GPT-4o.
It generates thread content following the 'Next Builder' persona guidelines.
"""

import json
from typing import Dict, Any, Optional
from openai import OpenAI


# System prompt defining the 'Next Builder' persona
SYSTEM_PROMPT = """
당신은 'Next Builder(Jokerburg)'입니다.
테크 뉴스를 분석하여 개발자와 엔지니어에게 인사이트를 제공하는 역할입니다.

뉴스의 중요도와 깊이에 따라 '단일 포스트(single)'와 '멀티 스레드(multi)'를 판단하여 JSON으로 출력하십시오.

[출력 포맷 - JSON]
{
  "type": "single" 또는 "multi",
  "main_post": "메인 포스트 내용 (공백 포함 10줄 이내)",
  "replies": ["1/ ...", "2/ ..."]  // multi일 경우만, 없으면 빈 배열
}

[콘텐츠 타입 판단 기준]
- Single (단일): 단순 업데이트, 짧은 소식, 루머
- Multi (스레드): 주요 기술 발표, 신제품 출시, 심층 분석이 필요한 뉴스

[메인 포스트 구조]
1. 소제목: 명사형으로 간결하게 (예: OpenAI, o3 모델 공개)
2. (공백)
3. Hook: 대화하듯 자연스러운 감탄/발견 (예: 드디어 올 것이 왔군요.)
4. (공백)
5. Body/Insight: 핵심 내용과 함의를 2~3문장으로 끊어서 서술.
6. (공백)
7. Trigger (Multi일 경우만): "핵심만 정리했습니다.🧵"

[대댓글 구조 - Multi일 경우만]
- 1/ **[소제목]**: 기술적 팩트 전달
- 2/ **[소제목]**: 시장 영향력 해석

[필수 규칙]
- 정중하고 신뢰감 있는 '하십시오체' (~습니다/합니다) 사용
- 이모지(Emoji) 사용 금지 (단, 멀티 스레드 예고용 '🧵'만 허용)
- 해시태그(#) 사용 금지
- 본문에 URL 절대 포함 금지
- 시(Poem)처럼 짧게 끊어서 작성 (벽돌 텍스트 지양)
- 30자 내외로 줄바꿈하여 모바일 가독성 최적화
"""


def create_client(api_key: str) -> OpenAI:
    """
    Create an OpenAI client with the given API key.

    Args:
        api_key: OpenAI API key.

    Returns:
        Configured OpenAI client instance.

    Example:
        >>> client = create_client("sk-...")
    """
    return OpenAI(api_key=api_key)


def generate_thread_content(
    client: OpenAI,
    title: str,
    description: str,
    model: str = "gpt-4o"
) -> Optional[Dict[str, Any]]:
    """
    Generate thread content from news title and description.

    Args:
        client: OpenAI client instance.
        title: News article title.
        description: News article description/summary.
        model: OpenAI model to use (default: gpt-4o).

    Returns:
        Dictionary with type, main_post, and replies (if multi).
        Returns None if generation fails.

    Example:
        >>> client = create_client("sk-...")
        >>> content = generate_thread_content(
        ...     client,
        ...     "OpenAI Releases GPT-5",
        ...     "OpenAI has announced the release of GPT-5..."
        ... )
        >>> print(content['type'])  # 'single' or 'multi'
        >>> print(content['main_post'])
    """
    user_prompt = f"""
뉴스 제목: {title}

뉴스 내용:
{description}
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=1000
        )

        content = response.choices[0].message.content
        return json.loads(content)

    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 오류: {e}")
        return None
    except Exception as e:
        print(f"❌ AI 분석 실패: {e}")
        return None


def validate_content(content: Dict[str, Any]) -> bool:
    """
    Validate that generated content follows the required format.

    Args:
        content: Generated content dictionary.

    Returns:
        True if content is valid, False otherwise.

    Example:
        >>> is_valid = validate_content(content)
    """
    if not content:
        return False

    # Check required fields
    if "type" not in content or "main_post" not in content:
        return False

    # Check type value
    if content["type"] not in ["single", "multi"]:
        return False

    # Check replies for multi type
    if content["type"] == "multi":
        if "replies" not in content or not isinstance(content["replies"], list):
            return False

    return True
