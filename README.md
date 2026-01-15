# Thread-Auto

> AI-powered Tech News Pipeline for Meta Threads

Thread-Auto는 테크 뉴스를 실시간으로 감지하고, **'Next Builder(Jokerburg)'**의 페르소나로 분석하여 Meta Threads에 자동 게시하는 AI 파이프라인 시스템입니다.

## ✨ 핵심 기능

| 기능 | 설명 |
|------|------|
| 🚀 **속도** | RSS 기반 실시간 뉴스 감지 |
| 🎯 **관점** | 개발자/엔지니어 관점의 인사이트 큐레이션 |
| 📱 **가독성** | 모바일 최적화 (30자 내외 줄바꿈) |
| 🤖 **자동화** | 수집 → 분석 → 이미지 → 업로드 100% 무인 자동화 |

## 📁 프로젝트 구조

```
thread-auto/
├── .github/
│   └── workflows/
│       └── daily_news.yml       # GitHub Actions 스케줄
├── rss_collector.py             # RSS 피드 수집 모듈
├── image_extractor.py           # og:image 추출 모듈
├── ai_analyzer.py               # OpenAI GPT-4o 분석 모듈
├── thread_formatter.py          # 포맷팅 및 출력 모듈
├── main.py                      # 메인 파이프라인
├── requirements.txt             # 의존성 목록
├── README.md                    # 프로젝트 문서
└── tests/                       # 유닛 테스트
```

## 🚀 빠른 시작

### 1. 의존성 설치

```bash
cd thread-auto
pip install -r requirements.txt
```

### 2. 환경 변수 설정

```bash
export OPENAI_API_KEY="sk-..."
export DRY_RUN="true"  # 테스트 모드 (실제 업로드 안함)
```

### 3. 실행

```bash
python main.py
```

## ⚙️ 환경 변수

| 변수 | 필수 | 설명 | 기본값 |
|------|------|------|--------|
| `OPENAI_API_KEY` | ✅ | OpenAI API 키 | - |
| `THREADS_ACCESS_TOKEN` | ❌ | Threads API 토큰 | - |
| `RSS_URL` | ❌ | RSS 피드 URL | TechCrunch |
| `DRY_RUN` | ❌ | 테스트 모드 | `true` |

## 🤖 GitHub Actions 설정

### Secrets 등록

1. GitHub Repo → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** 클릭
3. 다음 시크릿 추가:
   - `OPENAI_API_KEY`: OpenAI API 키

### 수동 실행 테스트

1. GitHub Repo → **Actions** 탭
2. **Thread-Auto Daily Run** 클릭
3. **Run workflow** 버튼 클릭

### 자동 실행

- 매일 한국 시간 오전 9시 (UTC 00:00)에 자동 실행됩니다.

## 📝 출력 포맷

### Single (단일 포스트)

```
[소제목]

[Hook - 감탄/발견]

[Body - 핵심 내용 2~3문장]
```

### Multi (스레드)

```
[소제목]

[Hook - 감탄/발견]

[Body - 핵심 내용]

핵심만 정리했습니다.🧵
```

대댓글:
- `1/ **[소제목]** - 기술적 팩트`
- `2/ **[소제목]** - 시장 영향력`

마지막 댓글:
- `출처 : https://original-article-url.com`

## 📰 지원 RSS 소스

- TechCrunch
- The Verge
- Hacker News
- OpenAI Blog
- Google Blog

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

- [ ] Human-in-the-loop: 텔레그램 승인 시스템
- [ ] DALL-E 3 이미지 자동 생성
- [ ] 다국어 지원 (한↔영)
- [ ] Threads API 공식 연동

## 📄 라이선스

MIT License
