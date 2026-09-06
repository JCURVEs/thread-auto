"""
AI Analyzer module for Thread-Auto.

This module handles AI-powered analysis using multiple FREE AI providers.
Supports Groq, OpenRouter, Gemini, and more.
"""

import json
import os
import re
import unicodedata
from typing import Dict, Any, Optional, Tuple, List, Set

# System prompt defining the 'AI Tech Newsletter Curator' persona
SYSTEM_PROMPT = """
당신은 'AI Tech Newsletter Curator'입니다.
**AI 개발자/연구자**를 위한 뉴스레터를 작성하며, **기술 혁신**에만 집중합니다.
펀딩/M&A 같은 비즈니스 뉴스는 관심 대상이 아닙니다.

반드시 아래 **JSON 포맷**으로만 응답해야 합니다.
다른 말(서론, 추임새)은 절대 하지 마십시오.

[출력 포맷 (JSON)]
{
  "title": "기사 제목 (기술적으로 명확하게 한글로)",
  "summary": "핵심 내용 요약 (3~4문장, '합니다/했습니다'체, 기술적 세부사항 포함)",
  "easy_explainer": "쉬운 설명 (초등학생도 이해할 수 있게 1문장으로 비유나 풀이)",
  "category": "관련 분야 (아래 카테고리 중 선택)",
  "importance": 정수 (1~10 사이의 중요도 점수, 아래 기준 엄격히 적용)
}

[카테고리 - 반드시 아래 중 하나 선택]
- "LLM 출시" : 새로운 언어모델 공개
- "비전/멀티모달" : 이미지/비디오 AI
- "오픈소스 도구" : 프레임워크, 라이브러리
- "연구 논문" : 학술 발표, arXiv
- "API/인프라" : 클라우드, API 서비스
- "에이전트/자동화" : AI 에이전트, 워크플로우
- "비즈니스" : 펀딩, M&A (낮은 중요도)

[중요도 평가 기준 - AI 개발자 관점에서 엄격 적용]
**9-10점: 업계 판도를 바꿀 혁신**
  - SOTA 달성한 새 모델 (GPT-5, Claude-4급)
  - 패러다임을 바꾸는 기술 (Transformer급 혁신)
  - 게임 체인저 오픈소스 (Llama, Stable Diffusion급)

**7-8점: 실무에 바로 쓸 수 있는 기술**
  - 강력한 오픈소스 도구/프레임워크
  - 획기적인 API/서비스 출시
  - 중요한 모델 업데이트 (성능 2배 이상)

**5-6점: 주목할 만한 업데이트**
  - 점진적 개선 (마이너 버전업)
  - 흥미로운 연구 논문
  - 유용한 신규 기능

**3-4점: 비즈니스 뉴스 (기술보다 돈 이야기)**
  - 펀딩 발표
  - M&A, 인수합병
  - 기업 밸류에이션

**1-2점: 관심 없음**
  - 마케팅성 발표
  - 인사 이동
  - 의미 없는 마일스톤

[작성 규칙]
1. **타이틀**: 기술적 핵심을 명확하게. "어떤 기술인지" 우선.
2. **요약**: 개발자가 알아야 할 기술 스펙, 성능, 사용법 중심.
3. **쉬운설명**: "즉, ~라는 뜻입니다" 또는 비유로 풀이.
4. **중요도**: AI 개발자에게 "정말 알아야 하는가?"로 판단. 비즈니스 뉴스는 무조건 3점 이하.
5. **언어**: 무조건 **한국어**로 작성.
6. **근거 준수**: 원문에 없는 모델명, 제품명, 성능 수치, 기관명은 절대 만들지 말 것.
7. **문장 품질**: 중국어/일본어/러시아어/베트남어 등 다른 언어 문자를 섞지 말 것.
8. **번역 품질**: 직역투, 깨진 번역, 붙어 있는 단어를 피하고 자연스러운 한국어 문장으로 쓸 것.
"""

# =============================================================================
# FREE AI PROVIDER CONFIGURATIONS
# =============================================================================
PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
        "model_env_key": "GROQ_MODEL",
        "free_limit": "14,400 req/day"
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "qwen/qwen3-30b-a3b:free",
        "env_key": "OPENROUTER_API_KEY",
        "model_env_key": "OPENROUTER_MODEL",
        "free_limit": "free models only (:free)",
        "headers": {
            "HTTP-Referer": "https://github.com/JCURVEs/thread-auto",
            "X-Title": "thread-auto",
        },
        "extra_body": {
            "reasoning": {"enabled": False},
        },
    },
    "gemini": {
        "base_url": None,
        "default_model": "gemini-flash-latest",
        "env_key": "GEMINI_API_KEY",
        "model_env_key": "GEMINI_MODEL",
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
    provider_config = next(
        (
            config
            for config in PROVIDERS.values()
            if config.get("base_url") == base_url
        ),
        {},
    )
    headers = dict(provider_config.get("headers", {}))

    try:
        from openai import OpenAI
        return {
            "type": "openai",
            "client": OpenAI(
                api_key=api_key,
                base_url=base_url,
                default_headers=headers or None,
            ),
            "model": model,
            "extra_body": provider_config.get("extra_body"),
        }
    except ImportError:
        return {
            "type": "requests",
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
            "headers": headers,
            "extra_body": provider_config.get("extra_body"),
        }


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


def generate_thread_content(
    client: Dict,
    title: str,
    description: str,
    article_content: str = "",
    max_retries: int = 2
) -> Optional[Dict]:
    """
    Generate newsletter content from news with foreign text validation.
    Now specifically follows the Newsletter format.
    """
    article_section = ""
    if article_content:
        article_section = f"""

    [기사 본문]
    {article_content}
    """

    user_prompt = f"""
    [뉴스 원문]
    제목: {title}
    RSS 요약: {description}
    {article_section}

    **중요**: 원문에 외국어(영어, 중국어, 일본어 등)가 포함되어 있다면 의미를 이해한 뒤 자연스러운 한국어로 다시 쓰세요.
    기술 용어는 통용되는 표현을 우선 사용하고, 필요한 경우에만 원문을 괄호에 병기하세요. 예: "트랜스포머(Transformer)"
    기사 본문이 제공된 경우에는 RSS 요약보다 기사 본문을 우선 근거로 삼으세요.
    본문에 없는 성능 수치, 모델명, 발표 내용은 추측하지 마세요.
    원문에 없는 예시 제품명이나 벤치마크명을 보태지 마세요.
    번역이 애매한 고유명사는 원문 표기를 유지하세요.
    중국어/일본어 한자, 히라가나, 가타카나, 키릴 문자, 베트남어 단어를 섞어 쓰지 마세요.
    "数学", "品質", "最近", "検証", "提出", "khuyến", "Depends" 같은 깨진 혼합 문자는 절대 쓰지 마세요.
    한국어와 영어 단어가 붙어 있으면 띄어 쓰세요. 예: "최신Foundation" 금지, "최신 Foundation" 허용.

    위 뉴스를 'Tech Newsletter Curator'의 관점에서 분석하여 **순수 한국어로만** JSON을 작성해줘.
    """

    for attempt in range(max_retries):
        try:
            content = None

            if client["type"] == "openai":
                request_kwargs = {
                    "model": client["model"],
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.2,
                }
                if client.get("extra_body"):
                    request_kwargs["extra_body"] = client["extra_body"]

                response = client["client"].chat.completions.create(
                    **request_kwargs
                )
                content = json.loads(response.choices[0].message.content)

            elif client["type"] == "gemini":
                response = client["client"].generate_content(user_prompt)
                # Cleanup Markdown code blocks if present
                raw = response.text.replace("```json", "").replace("```", "").strip()
                content = json.loads(raw)

            elif client["type"] == "requests":
                import requests
                headers = {
                    "Authorization": f"Bearer {client['api_key']}",
                    "Content-Type": "application/json",
                    **client.get("headers", {}),
                }
                data = {
                    "model": client["model"],
                    "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.2,
                }
                if client.get("extra_body"):
                    data.update(client["extra_body"])
                res = requests.post(f"{client['base_url']}/chat/completions", headers=headers, json=data)
                content = json.loads(res.json()["choices"][0]["message"]["content"])

            # Validate Korean content
            if content:
                is_valid, error_msg = validate_korean_content(content)
                if not is_valid:
                    print(f"⚠️ 외국어 감지 ({error_msg}) - 재시도 {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        continue  # Retry
                    print("❌ 최대 재시도 초과 - 오염된 응답 폐기")
                    return None

            return content

        except Exception as e:
            print(f"❌ AI 분석 에러 (시도 {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return None

    return None


BUSINESS_KEYWORDS = (
    "funding", "raises", "raised", "series a", "series b", "investment",
    "valuation", "m&a", "acquisition", "acquires", "acquired", "partnership",
    "customer", "customers", "case study", "adoption", "government",
    "payments", "policy", "privacy policy", "hiring", "jobs",
    "투자", "펀딩", "인수", "합병", "파트너십", "제휴", "고객사", "도입",
    "정부", "정책", "채용", "결제", "사례"
)

PRACTICAL_TECH_KEYWORDS = (
    "open-source", "open source", "오픈소스", "github", "code", "코드",
    "api", "sdk", "library", "라이브러리",
    "benchmark", "벤치마크", "dataset", "데이터셋", "release", "released",
    "공개", "출시", "available", "사용 가능", "throughput", "latency",
    "speed", "faster", "memory", "gpu", "tokens/s", "정확도", "속도",
    "지연", "처리량", "메모리", "성능"
)

BREAKTHROUGH_KEYWORDS = (
    "sota", "state-of-the-art", "frontier model", "foundation model",
    "new model", "model release", "outperforms", "beats", "surpasses",
    "2x", "3x", "10x", "배 빠", "배 향상", "최고 성능", "프론티어 모델",
    "새 모델", "모델 출시"
)

ALLOWED_CATEGORIES = {
    "LLM 출시",
    "비전/멀티모달",
    "오픈소스 도구",
    "연구 논문",
    "API/인프라",
    "에이전트/자동화",
    "비즈니스",
}

FORBIDDEN_STYLE_EXPRESSIONS = (
    "혁신적인",
    "획기적인",
    "놀라운",
    "정말",
    "매우",
    "엄청",
    "할 수 있습니다",
    "하게 됩니다",
    "이것은",
)

OVERCLAIM_EXPRESSIONS = (
    "완전히 바꿉니다",
    "완전히 달라집니다",
    "무조건",
    "반드시 성공",
    "업계 판도를 바꿉니다",
)

BROKEN_TRANSLATION_EXPRESSIONS = (
    "라고하는",
    "기반으로하는",
    "측정하는데",
    "그리고나서",
    "할 수 있도록 해줍니다",
    "중요한 간격",
    "정확도를 향상 시킵니다",
)

GENERIC_GROUNDING_TERMS = {
    "ai",
    "api",
    "cpu",
    "gpu",
    "llm",
    "ml",
    "rag",
    "sdk",
    "sota",
    "transformer",
}


def _coerce_importance(value: Any) -> int:
    """Normalize model-provided importance into a 1-10 integer."""
    if isinstance(value, (int, float)):
        score = int(value)
    else:
        match = re.search(r"\d+", str(value))
        score = int(match.group(0)) if match else 5

    return max(1, min(10, score))


def _contains_any(text: str, keywords: Tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _has_substantial_metric(text: str) -> bool:
    """Detect concrete performance numbers rather than vague hype."""
    patterns = (
        r"\b\d+(\.\d+)?\s?%",
        r"\b\d+(\.\d+)?x\b",
        r"\b\d+(\.\d+)?\s?배",
        r"\b\d+(\.\d+)?\s?(ms|tokens/s|tok/s|gb|fps)\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def calibrate_importance(
    content: Dict[str, Any],
    source_name: str = "",
    original_title: str = "",
    original_summary: str = "",
    article_content: str = "",
    source_weight: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Apply source-aware importance calibration after AI scoring.

    The model is useful for first-pass judgement, but it tends to overrate
    generic arXiv abstracts and business announcements. This function lowers
    weak items and allows a small boost for high-signal infrastructure/platform
    sources when practical technical evidence is present.
    """
    original_importance = _coerce_importance(content.get("importance", 5))
    importance = original_importance
    category = str(content.get("category", ""))
    source = source_name.lower()
    if source_weight is None:
        try:
            from source_registry import get_source_weight

            source_weight = get_source_weight(source_name)
        except Exception:
            source_weight = 1.0

    evidence_text = " ".join([
        str(content.get("title", "")),
        str(content.get("summary", "")),
        str(content.get("easy_explainer", "")),
        original_title,
        original_summary,
        article_content,
    ]).lower()

    cap = 10
    reasons = []

    if category == "비즈니스":
        cap = min(cap, 3)
        reasons.append("business_category_cap")
    elif _contains_any(evidence_text, BUSINESS_KEYWORDS):
        cap = min(cap, 4)
        reasons.append("business_signal_cap")

    has_practical_signal = _contains_any(evidence_text, PRACTICAL_TECH_KEYWORDS)
    has_breakthrough_signal = (
        _contains_any(evidence_text, BREAKTHROUGH_KEYWORDS)
        or _has_substantial_metric(evidence_text)
    )

    if source.startswith("arxiv"):
        research_cap = 6
        if has_practical_signal:
            research_cap = 8
        if has_breakthrough_signal and has_practical_signal:
            research_cap = 9
        cap = min(cap, research_cap)
        if research_cap < 8:
            reasons.append("generic_arxiv_cap")
    elif category == "연구 논문" and not has_practical_signal:
        cap = min(cap, 6)
        reasons.append("generic_research_cap")

    importance = min(importance, cap)

    if (
        source_weight >= 1.1
        and 7 <= importance <= 8
        and has_practical_signal
        and category != "비즈니스"
        and not source.startswith("arxiv")
    ):
        boosted_importance = min(10, importance + 1)
        if boosted_importance != importance:
            importance = boosted_importance
            reasons.append("source_weight_boost")

    content["importance"] = importance
    content["source_weight"] = source_weight

    if importance != original_importance:
        content["importance_original"] = original_importance
        content["importance_adjusted_reason"] = ", ".join(reasons)

    return content


def validate_quality_gate(content: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Final quality gate before archiving AI analysis.

    This blocks structurally valid but low-quality output, especially foreign
    text leakage and style-guide violations that hurt downstream thread drafts.
    """
    errors = []

    if not validate_content(content):
        return False, ["missing_required_fields"]

    for field in ("title", "summary", "easy_explainer"):
        value = str(content.get(field, "")).strip()
        if not value:
            errors.append(f"{field}_empty")
        elif value in ("요약 없음", "설명 없음", "제목 없음"):
            errors.append(f"{field}_placeholder")

    is_korean_valid, korean_error = validate_korean_content(content)
    if not is_korean_valid:
        errors.append(korean_error)

    category = content.get("category")
    if category not in ALLOWED_CATEGORIES:
        errors.append(f"invalid_category:{category}")

    importance = _coerce_importance(content.get("importance", 5))
    if importance != content.get("importance"):
        content["importance"] = importance
    if not 1 <= importance <= 10:
        errors.append("importance_out_of_range")

    text = " ".join(
        str(content.get(field, ""))
        for field in ("title", "summary", "easy_explainer")
    )

    for expression in FORBIDDEN_STYLE_EXPRESSIONS:
        if expression in text:
            errors.append(f"forbidden_style:{expression}")

    for expression in OVERCLAIM_EXPRESSIONS:
        if expression in text:
            errors.append(f"overclaim:{expression}")

    for expression in BROKEN_TRANSLATION_EXPRESSIONS:
        if expression in text:
            errors.append(f"broken_translation:{expression}")

    attached_word = re.search(r"[가-힣][A-Za-z]{3,}|[A-Za-z]{3,}[가-힣]{2,}", text)
    if attached_word:
        errors.append(f"missing_space_near_english:{attached_word.group(0)}")

    return len(errors) == 0, errors


def _foreign_char_samples(text: str, strict: bool = False, limit: int = 5) -> List[str]:
    """Return suspicious non-Korean character samples from generated Korean text."""
    samples = []
    seen = set()

    for char in text:
        if char.isspace() or not char.isalnum():
            continue

        try:
            name = unicodedata.name(char, "")
        except ValueError:
            continue

        script = name.split()[0] if name else ""
        is_disallowed_script = script in {
            "CJK",
            "HIRAGANA",
            "KATAKANA",
            "CYRILLIC",
            "ARABIC",
            "THAI",
        }
        is_non_ascii_latin = (
            strict
            and script == "LATIN"
            and ord(char) > 127
        )

        if not (is_disallowed_script or is_non_ascii_latin):
            continue

        if char not in seen:
            samples.append(char)
            seen.add(char)
        if len(samples) >= limit:
            break

    return samples


def detect_foreign_text(text: str, threshold: float = 0.1, strict: bool = False) -> bool:
    """
    Detect if text contains significant foreign characters.

    Args:
        text: Text to analyze
        threshold: Maximum allowed ratio of foreign characters (default: 10%)

    Returns:
        True if foreign text ratio exceeds threshold
    """
    if not text:
        return False

    total_chars = 0
    foreign_chars = 0

    if strict and _foreign_char_samples(text, strict=True):
        return True

    for char in text:
        # Skip whitespace and punctuation
        if char.isspace() or not char.isalnum():
            continue

        total_chars += 1

        # Check if character is NOT Hangul, Latin, or common symbols
        try:
            script = unicodedata.name(char, '').split()[0]
            if script not in ['HANGUL', 'LATIN', 'DIGIT', 'FULLWIDTH']:
                # Detect CJK, Cyrillic, Arabic, etc.
                if script in ['CJK', 'HIRAGANA', 'KATAKANA', 'CYRILLIC', 'ARABIC', 'THAI']:
                    foreign_chars += 1
        except (ValueError, IndexError):
            # Character without a name, skip
            pass

    if total_chars == 0:
        return False

    ratio = foreign_chars / total_chars
    return ratio > threshold


def validate_korean_content(content: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate that content is primarily in Korean.

    Returns:
        (is_valid, error_message)
    """
    # Check all text fields
    text_fields = ['title', 'summary', 'easy_explainer']

    for field in text_fields:
        if field not in content:
            continue

        text = content[field]
        if detect_foreign_text(text, strict=True):
            samples = "".join(_foreign_char_samples(text, strict=True))
            suffix = f": {samples}" if samples else ""
            return False, f"{field} contains foreign characters{suffix}"

    return True, ""


def _extract_claim_metrics(text: str) -> Set[str]:
    """Extract concrete numbers that should be grounded in source text."""
    patterns = (
        r"\b\d+(\.\d+)?\s?%",
        r"\b\d+(\.\d+)?\s?(x|배)\b",
        r"\b\d+(\.\d+)?\s?(ms|tokens/s|tok/s|gb|tb|fps|auroc|f1)\b",
        r"\b\d+(\.\d+)?\s?(billion|million|trillion)\b",
        r"\b\d+(\.\d+)?\s?(억|만|조)\b",
    )
    found = set()
    lowered = text.lower()
    for pattern in patterns:
        for match in re.finditer(pattern, lowered):
            found.add(re.sub(r"\s+", "", match.group(0)))
    return found


def _extract_versioned_terms(text: str) -> Set[str]:
    """Extract high-risk product/model/version tokens that should appear in evidence."""
    terms = set()
    lowered = text.lower()
    for match in re.finditer(r"\b[a-z][a-z0-9_.-]*\d[a-z0-9_.-]*\b", lowered):
        term = match.group(0).strip(".,;:()[]{}")
        if term and term not in GENERIC_GROUNDING_TERMS:
            terms.add(term)
    return terms


def validate_factual_grounding(
    content: Dict[str, Any],
    original_title: str = "",
    original_summary: str = "",
    article_content: str = "",
) -> Tuple[bool, List[str]]:
    """
    Block generated claims that introduce unsupported concrete facts.

    This is intentionally conservative: it only checks high-risk concrete
    details such as metrics and versioned model/product names, where adding a
    made-up value would make the archive misleading.
    """
    evidence = " ".join([original_title, original_summary, article_content]).lower()
    evidence_compact = re.sub(r"\s+", "", evidence)
    generated = " ".join(
        str(content.get(field, ""))
        for field in ("title", "summary", "easy_explainer")
    )

    errors = []

    for metric in sorted(_extract_claim_metrics(generated)):
        if metric not in evidence_compact:
            errors.append(f"ungrounded_metric:{metric}")

    evidence_terms = _extract_versioned_terms(evidence)
    for term in sorted(_extract_versioned_terms(generated)):
        if term not in evidence_terms and term not in evidence:
            errors.append(f"ungrounded_versioned_term:{term}")

    return len(errors) == 0, errors


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
