# Thread-Auto

> AI News Aggregator: Multi-Source Collection from Major AI Company Blogs

Thread-Auto는 **OpenAI, DeepMind, Google Research, Hugging Face, Meta AI, arXiv** 등 주요 AI 회사의 공식 블로그에서 최신 AI 기술 뉴스를 자동 수집하고, **AI 개발자/연구자 관점**으로 분석하여 매일 아카이빙하는 자동화 파이프라인입니다.

## ✨ 핵심 기능

| 기능 | 설명 |
|------|------|
| 🌐 **멀티 소스** | 9개 AI 회사 공식 블로그 동시 수집 |
| 🎯 **AI 개발자 관점** | 기술 혁신 중심 큐레이션 (비즈니스 뉴스 제외) |
| ⏰ **24시간 신선도** | 최신 뉴스만 수집 (24시간 이내) |
| 🔁 **중복 방지** | 7일 아카이브 기반 중복 URL 필터링 |
| 📊 **엄격한 평가** | 9-10점: 혁신, 7-8점: 실무 기술, 3-4점: 비즈니스 |
| 📱 **가독성** | 회사명 태그, 분야 분류, 중요도 표시 |
| 🤖 **완전 자동화** | 매일 오전 9시 자동 실행 (GitHub Actions) |

## 🔄 파이프라인 동작 방식

```
1. RSS 수집 (9개 소스)
   ↓
2. 24시간 신선도 필터링
   ↓
3. 중복 URL 체크 (7일 아카이브)
   ↓
4. AI 분석 (Groq Llama 3.3 70B)
   - 제목 생성
   - 분야 분류 (7가지 카테고리)
   - 중요도 평가 (1-10점)
   - 요약 + 쉬운설명
   ↓
5. 이미지 추출 (og:image)
   ↓
6. 마크다운 아카이빙 (archive/YYYY-MM-DD.md)
   ↓
7. Git 커밋 & 푸시
```

**매일 오전 9시 자동 실행** → **변경사항이 있으면 자동 커밋**

## 📁 프로젝트 구조

```
thread-auto/
├── .github/
│   └── workflows/
│       └── daily_news.yml       # GitHub Actions 스케줄 (매일 9시)
├── archive/                     # 일별 뉴스 아카이브 (YYYY-MM-DD.md)
├── rss_collector.py             # 9개 AI 블로그 RSS 수집
├── image_extractor.py           # og:image 추출 모듈
├── ai_analyzer.py               # Groq AI 분석 (Llama 3.3 70B)
├── archiver.py                  # 마크다운 아카이빙 + 중복 체크
├── thread_formatter.py          # 포맷팅 및 출력 모듈
├── main.py                      # 메인 파이프라인
├── requirements.txt             # 의존성 목록
└── README.md                    # 프로젝트 문서
```

## 🚀 빠른 시작

### 1. 의존성 설치

```bash
cd thread-auto
pip install -r requirements.txt
```

### 2. 환경 변수 설정

```bash
export GROQ_API_KEY="gsk_..."        # Groq API 키 (무료)
export DRY_RUN="true"                # 테스트 모드 (실제 업로드 안함)
export COLLECT_ALL_SOURCES="true"    # 모든 AI 블로그 수집
```

**무료 AI Provider 지원:**
- **Groq** (기본): Llama 3.3 70B, 14K req/day, 가장 빠름
- **OpenRouter**: Qwen 2.5 72B, 400+ models
- **Gemini**: Google, 1.5K req/day

### 3. 실행

```bash
python main.py
```

## ⚙️ 환경 변수

| 변수 | 필수 | 설명 | 기본값 |
|------|------|------|--------|
| `GROQ_API_KEY` | ✅ | Groq API 키 (무료) | - |
| `AI_PROVIDER` | ❌ | AI 제공자 (groq/openrouter/gemini) | `groq` |
| `AI_MODEL` | ❌ | AI 모델 (빈 값 = 기본 모델) | - |
| `COLLECT_ALL_SOURCES` | ❌ | 모든 AI 블로그 수집 | `true` |
| `RSS_URL` | ❌ | 단일 RSS URL (멀티소스 비활성화) | - |
| `DRY_RUN` | ❌ | 테스트 모드 | `true` |
| `THREADS_ACCESS_TOKEN` | ❌ | Threads API 토큰 | - |

## 🤖 GitHub Actions 설정

### Secrets 등록

1. GitHub Repo → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** 클릭
3. 다음 시크릿 추가:
   - `GROQ_API_KEY`: Groq API 키 (https://console.groq.com/keys)

### 수동 실행 테스트

1. GitHub Repo → **Actions** 탭
2. **Thread-Auto Daily Run** 클릭
3. **Run workflow** 버튼 클릭

### 자동 실행

- 매일 한국 시간 오전 9시 (UTC 00:00)에 자동 실행됩니다.

## 📝 아카이브 포맷

매일 `archive/YYYY-MM-DD.md` 파일에 다음 형식으로 저장됩니다:

```markdown
# Daily AI Tech News (2026-01-26)

*Collected from OpenAI, DeepMind, Google Research, Hugging Face, Meta AI, arXiv*

---

## [OpenAI] Codex 에이전트 루프 기술 분석

**분야:** 에이전트/자동화 | **중요도:** 7점

**요약:**
Codex CLI는 Responses API를 통해 모델, 도구, 프롬프트, 성능을 오케스트레이션하는 방법에 대해 설명합니다...

**쉬운설명:**
즉, 인공지능이 작업을 자동화하도록 도와주는 Codex 시스템이 어떻게 돌아가는지 자세히 설명하는 글이랍니다.

**출처:** https://openai.com/index/unrolling-the-codex-agent-loop

![Article Image](https://images.ctfassets.net/kftzwdyauwt9/...)

---
```

### AI 분석 분야 (7가지)

- **LLM 출시**: GPT-5, Claude 4 등 새 모델 출시
- **비전/멀티모달**: 이미지/비디오 AI 기술
- **오픈소스 도구**: Hugging Face, LangChain 등
- **연구 논문**: arXiv, 학회 논문
- **API/인프라**: 클라우드 AI 서비스
- **에이전트/자동화**: AI 에이전트, 워크플로우
- **비즈니스**: 펀딩, M&A (낮은 중요도)

## 📰 수집 소스 (9개 AI 블로그)

### AI 회사 공식 블로그
- **OpenAI** - https://openai.com/news/rss.xml
- **DeepMind** - https://deepmind.google/blog/rss.xml
- **Google Research** - https://research.google/blog/rss
- **Hugging Face** - https://huggingface.co/blog/feed.xml
- **Meta AI Research** - https://research.facebook.com/feed

### arXiv 논문 (AI 관련)
- **cs.AI** - Artificial Intelligence
- **cs.LG** - Machine Learning
- **cs.CV** - Computer Vision
- **cs.CL** - Natural Language Processing

### 필터링 기준
- ⏰ **24시간 이내** 발행된 글만 수집
- 🔁 **7일 중복 체크** - 이미 아카이빙된 URL 제외
- 📊 **중요도 7점 이상** - AI 개발자에게 유용한 기술 뉴스

## 🎯 중요도 평가 기준

AI 개발자/연구자 관점에서 기술 혁신에만 집중합니다:

| 점수 | 기준 | 예시 |
|------|------|------|
| **9-10점** | 업계 판도를 바꿀 혁신 | GPT-5 출시, 새로운 아키텍처 발견 |
| **7-8점** | 실무에 바로 쓸 수 있는 기술 | 새 API 출시, 오픈소스 도구 |
| **5-6점** | 주목할 만한 업데이트 | 모델 성능 개선, 새 기능 추가 |
| **3-4점** | 비즈니스 뉴스 | 펀딩, M&A, 파트너십 발표 |
| **1-2점** | 관심 없음 | 회사 소식, 인터뷰, 마케팅 |

**7점 미만은 수집하지 않습니다** - 기술적 가치가 있는 뉴스만 아카이빙

## 🔧 개발 가이드

### 새 모듈 추가

1. 기능 파일 생성 (예: `new_feature.py`)
2. `main.py`에 예제 메서드 추가
3. 테스트 작성 (`tests/test_new_feature.py`)

### 테스트 실행

```bash
pytest tests/ -v
```

## 📋 향후 계획

- [ ] Anthropic, Mistral, Cohere 블로그 추가
- [ ] 주간/월간 요약 리포트 생성
- [ ] Slack/Discord 알림 연동
- [ ] 웹 대시보드 (아카이브 검색/필터링)
- [ ] Meta Threads 자동 포스팅 연동

## 📄 라이선스

MIT License
