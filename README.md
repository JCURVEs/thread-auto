# Thread-Auto v2.0

> AI 뉴스 수집부터 스레드 생성까지 - 완전 자동화 파이프라인

Thread-Auto는 OpenAI, DeepMind, Google Research 등 주요 AI 회사 블로그에서 최신 기술 뉴스를 수집하고, Claude Code Agents를 활용해 @jokerburg.builder 계정용 스레드 시리즈를 자동 생성하는 시스템입니다.

## 소개

### 주요 기능

- **🔄 자동 뉴스 수집**: OpenAI, DeepMind, Google Research, Hugging Face, Meta AI, arXiv 등 9개 소스 (Anthropic RSS 준비 중)
- **🤖 AI 분석**: Groq Llama 3.3 70B로 중요도 평가 및 분야 분류
- **🧵 스레드 자동 생성**: Claude Code Agents로 3가지 콘텐츠 타입 지원
  - 📰 데일리뉴스 (5-7개 스레드)
  - 📄 arXiv 논문 (7-10개 스레드)
  - 🏢 기업분석 (10-15개 스레드)
- **✅ 품질 검수**: 자동 스타일 검수 및 팩트 체크

## 아키텍처

### 전체 흐름

```
┌─────────────────────────────────────────────────────────────┐
│  v1.0: RSS 수집 & 아카이빙                                  │
└─────────────────────────────────────────────────────────────┘
              ↓
    RSS 수집 (9개 소스)
              ↓
    AI 분석 (중요도 평가)
              ↓
    archive/YYYY-MM-DD.md
              ↓
┌─────────────────────────────────────────────────────────────┐
│  v2.0: Claude Code Agents                                    │
└─────────────────────────────────────────────────────────────┘
              ↓
    orchestrator.md (입력 분류)
              ↓
    ┌─────────┬─────────┬──────────┐
    │  뉴스   │  논문   │  기업    │
    │  팀     │  팀     │  팀      │
    └─────────┴─────────┴──────────┘
              ↓
    reviewer.md (품질 검수)
              ↓
    threads/{type}/YYYYMMDD-{slug}/
```

### 에이전트 구조

| 에이전트 | 역할 |
|---------|------|
| `orchestrator.md` | 입력 분류 및 라우팅 (뉴스/논문/기업) |
| `news-curator.md` | archive에서 스레드 후보 선별 |
| `news-thread-writer.md` | 뉴스 스레드 작성 |
| `paper-analyzer.md` | arXiv 논문 분석 |
| `paper-thread-writer.md` | 논문 스레드 작성 |
| `company-researcher.md` | 기업 리서치 |
| `company-thread-writer.md` | 기업 스레드 작성 |
| `reviewer.md` | 품질 검수 및 승인 |

### 디렉토리 구조

```
thread-auto/
├── .github/workflows/
│   ├── daily_news.yml           # 매일 9시 RSS 수집
│   └── thread_generation.yml    # 스레드 생성 워크플로우
├── .claude/agents/              # 8개 에이전트 정의
├── references/                  # 스타일 가이드
├── archive/                     # 일별 뉴스 아카이브
├── threads/                     # 생성된 스레드
│   ├── news/
│   ├── papers/
│   └── companies/
├── main.py                      # v1.0 RSS 수집 파이프라인
└── thread_generator.py          # v2.0 스레드 생성 스크립트
```

## 빠른 시작

### 1. 설치

```bash
git clone https://github.com/jojaehui/thread-auto.git
cd thread-auto
pip install -r requirements.txt
```

### 2. 환경 변수 설정

```bash
export GROQ_API_KEY="gsk_..."        # Groq API 키 (무료)
export COLLECT_ALL_SOURCES="true"    # 모든 소스 수집
```

### 3. RSS 수집 실행

```bash
# 뉴스 수집 및 아카이빙
python main.py
```

결과: `archive/YYYY-MM-DD.md` 파일 생성

### 4. 스레드 생성

#### 방법 1: Python 스크립트

```bash
# 데일리뉴스
python thread_generator.py --type news --input latest

# 논문
python thread_generator.py --type paper --input "https://arxiv.org/abs/2401.12345"

# 기업분석
python thread_generator.py --type company --input "OpenAI"
```

#### 방법 2: Claude Code (권장)

```bash
# 최신 뉴스
claude "오늘 뉴스 스레드 만들어줘"

# 논문
claude "https://arxiv.org/abs/2401.12345 논문 스레드로 만들어줘"

# 기업
claude "Anthropic 기업분석 스레드 만들어줘"
```

## 사용 예시

### 데일리뉴스 → 스레드

```bash
$ python main.py
✅ archive/2026-01-26.md 생성

$ claude "2026-01-26.md 파일에서 스레드 만들어줘"
✅ 스레드 생성 완료

threads/news/20260126-d4rt/
├── thread-01.md
├── thread-02.md
├── ...
├── thread-07.md
├── metadata.json
└── review-report.md
```

**생성된 스레드 예시:**

```markdown
Google DeepMind가 기존보다 300배 빠른 속도로 4차원 세계를 재구성하는 기술을 내놨어요.

왜 알아야 하냐면요,
AI가 3차원을 넘어 시간까지 이해하면 영상 분석이나 로봇 비전이 완전히 달라지거든요.

🧵 정리해드릴게요.
```

## 기술 스택

### v1.0 (RSS 수집)
- Python 3.11+
- feedparser (RSS 파싱)
- Groq API (AI 분석)
- BeautifulSoup4 (이미지 추출)

### v2.0 (스레드 생성)
- Claude Code
- Claude Sonnet 4.5
- 8개 전문 에이전트

## 스레드 스타일

- **말투**: "요"체 (해요, 이에요, 거든요)
- **길이**: 각 스레드 500자 이내
- **구조**: 후킹 → 팩트 → 설명 → 의미 → CTA
- **톤**: @jokerburg.builder 페르소나 (친근하면서 전문적)

## GitHub Actions

### 자동 실행
- **RSS 수집**: 매일 오전 9시 (KST) 자동 실행
- **스레드 생성**: 수동 트리거 또는 RSS 수집 완료 후 실행

### Secrets 설정
Repository Settings → Secrets → Actions에 추가:
- `GROQ_API_KEY`: Groq API 키

## 문서

- [USAGE.md](USAGE.md) - 상세 사용 가이드
- [references/style-guide.md](references/style-guide.md) - 스타일 가이드
- [.claude/agents/](/.claude/agents/) - 에이전트 정의 파일

## 로드맵

- [x] v1.0: 9개 소스 RSS 수집 자동화
- [ ] Anthropic 블로그 스크래퍼 추가 (RSS 미제공)
- [x] v2.0: Claude Code Agents 스레드 생성
- [ ] v3.0: Meta Threads API 자동 포스팅
- [ ] 성과 분석 대시보드
- [ ] 다국어 지원 (영문 스레드)

## 라이선스

MIT License

---

**Built with ❤️ for @jokerburg.builder**
