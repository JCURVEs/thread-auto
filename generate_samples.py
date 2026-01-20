"""
Generate realistic sample archives for Thread-Auto.
Uses ACTUAL recent TechCrunch news with manual 'Next Builder' persona writing
to demonstrate the archive quality without needing a live API key right now.
"""

from archiver import save_to_archive
from datetime import datetime

# Real News 1: Everstone Acquisition (TechCrunch)
# Link: https://techcrunch.com/2026/01/20/everstone-combines-wingify-ab-tasty-for-100m-digital-experience-optimization-platform/
sample1_data = {
    "type": "single",
    "main_post": "**[Everstone, 디지털 경험 최적화 플랫폼 통합]**\n\n시장이 빠르게 통합되고 있군요.\n\n사모펀드 Everstone이 Wingify와 AB Tasty를 합병하여 연 매출 1억 달러 규모의 거대 플랫폼을 탄생시켰습니다.\nVWO와 AB Tasty의 결합은 A/B 테스트 시장의 판도를 바꿀 중요한 움직임입니다.\n\n파편화된 마테크(MarTech) 시장의 옥석 가리기가 시작되었습니다.",
    "replies": []
}

save_to_archive(
    sample1_data,
    "https://techcrunch.com/wp-content/uploads/2026/01/wingify-logo.jpg", # Real-ish placeholder
    "https://techcrunch.com/2026/01/20/everstone-combines-wingify-ab-tasty-for-100m-digital-experience-optimization-platform/",
    "Everstone combines Wingify, AB Tasty for $100M+ digital experience optimization platform",
    "groq",
    "llama-3.3-70b-versatile"
)

# Real News 2: DeepSeek-V3 Release (Recent Hot Topic)
# Source: DeepSeek AI GitHub/Paper
sample2_data = {
    "type": "multi",
    "main_post": "**[DeepSeek-V3, 오픈소스의 반란]**\n\n성능은 GPT-4o급인데, 가격은 1/10이라니 놀랍습니다.\n\n중국 DeepSeek이 새로운 MoE(Mixture-of-Experts) 모델 'DeepSeek-V3'를 공개했습니다.\n총 671B 파라미터 중 활성 파라미터는 37B에 불과하여, 추론 효율성이 극대화되었습니다.\n\n이제 '거대함'보다 '영리함'이 무기인 시대입니다.\n핵심만 정리했습니다.🧵",
    "replies": [
        "1/ **[아키텍처: MLA & DeepSeekMoE]**\n기존 Transformer의 헤드를 획기적으로 압축한 MLA(Multi-Head Latent Attention) 기술을 적용했습니다.\n덕분에 KV 캐시 메모리를 90% 이상 절약하면서도 긴 컨텍스트를 처리할 수 있게 되었습니다.\n이것이 바로 압도적인 가성비의 비결입니다.",
        "2/ **[의미: 독점의 균열]**\n그동안 '고성능 = 빅테크 독점'이라는 공식이 지배적이었습니다.\n하지만 DeepSeek-V3는 누구나 최고 수준의 AI를 저렴하게 쓸 수 있다는 가능성을 증명했습니다.\n오픈소스 생태계에 다시 불이 붙겠네요."
    ]
}

save_to_archive(
    sample2_data,
    "https://github.com/deepseek-ai/DeepSeek-V3/raw/main/figures/logo.png",
    "https://github.com/deepseek-ai/DeepSeek-V3",
    "DeepSeek-V3: A Strong, Economical, and Efficient Mixture-of-Experts Language Model",
    "openrouter",
    "deepseek-v3"
)

print("✅ 리얼 데이터 샘플 생성 완료!")
