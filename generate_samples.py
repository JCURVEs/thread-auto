"""
Generate realistic sample archives for Thread-Auto (Newsletter Format).
Uses ACTUAL recent TechCrunch news with manual 'Newsletter Curator' persona writing.
"""

from archiver import save_to_archive
from datetime import datetime

# Real News 1: Everstone Acquisition (TechCrunch)
sample1_data = {
    "title": "Everstone, 디지털 경험 최적화 플랫폼 통합 (Wingify + AB Tasty)",
    "summary": "사모펀드 Everstone이 Wingify와 AB Tasty를 합병하여 연 매출 1억 달러 규모의 거대 플랫폼을 탄생시켰습니다. 이번 합병으로 VWO와 AB Tasty가 결합되며, A/B 테스트 및 개인화 시장에서 강력한 경쟁력을 확보하게 되었습니다. 파편화된 마테크(MarTech) 시장이 통합되는 중요한 신호탄입니다.",
    "easy_explainer": "마케팅 도구(A/B 테스트)를 만드는 큰 회사 두 곳이 하나로 합쳐져서 더 강력해졌다는 뜻입니다.",
    "category": "M&A·마테크·SaaS",
    "importance": 8
}

save_to_archive(
    sample1_data,
    "https://techcrunch.com/wp-content/uploads/2026/01/wingify-logo.jpg",
    "https://techcrunch.com/2026/01/20/everstone-combines-wingify-ab-tasty-for-100m-digital-experience-optimization-platform/",
    "Everstone combines Wingify, AB Tasty",
    "groq",
    "llama-3.3-70b-versatile"
)

# Real News 2: DeepSeek-V3 Release
sample2_data = {
    "title": "DeepSeek-V3 공개: GPT-4o급 성능에 가격은 1/10",
    "summary": "중국 DeepSeek이 새로운 오픈소스 모델 'DeepSeek-V3'를 공개했습니다. 671B 파라미터 중 37B만 활성화하는 MoE 기술로 추론 효율성을 극대화했으며, GPT-4o와 대등한 성능을 보여줍니다. 특히 API 가격이 매우 저렴하여 AI 접근성을 획기적으로 높였습니다.",
    "easy_explainer": "성능은 최고 수준인데 가격은 엄청나게 싼 새로운 AI가 나와서 누구나 쓸 수 있게 되었다는 이야기입니다.",
    "category": "AI 모델·오픈소스·LLM",
    "importance": 10
}

save_to_archive(
    sample2_data,
    "https://github.com/deepseek-ai/DeepSeek-V3/raw/main/figures/logo.png",
    "https://github.com/deepseek-ai/DeepSeek-V3",
    "DeepSeek-V3 Release",
    "openrouter",
    "deepseek-v3"
)

# Real News 3: OpenAI Operator (Based on leaks/rumors for demo context)
sample3_data = {
    "title": "OpenAI 'Operator': 컴퓨터를 스스로 제어하는 AI 에이전트",
    "summary": "OpenAI가 사용자의 컴퓨터 화면을 보고 마우스와 키보드를 직접 조작하는 'Operator' 에이전트를 준비 중입니다. 웹 브라우징부터 복잡한 코딩 작업까지 자율적으로 수행하며, 단순 채팅을 넘어선 '행동하는 AI'의 시대를 예고했습니다.",
    "easy_explainer": "AI가 내 컴퓨터를 대신 써서, 인터넷 쇼핑이나 업무를 알아서 척척 해준다는 뜻입니다.",
    "category": "AI 에이전트·자동화",
    "importance": 9
}

save_to_archive(
    sample3_data,
    "https://techcrunch.com/wp-content/uploads/2025/01/openai-operator.jpg",
    "https://techcrunch.com/2025/01/20/openai-launches-operator-agent/",
    "OpenAI Operator Agent",
    "groq",
    "mixtral-8x7b"
)

print("✅ 뉴스레터 포맷 샘플 생성 완료!")
