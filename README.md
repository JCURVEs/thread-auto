# Thread-Auto

AI·테크 뉴스와 논문을 수집하고 한국어로 분석해 날짜별 Markdown으로 보관하는 개인용 콘텐츠 파이프라인입니다.

## 주요 기능

- 공식 블로그, 연구소, arXiv 피드 수집
- 소스별 가중치와 중요도 기반 후보 선별
- 발행일 검증 및 중복 URL 제거
- Groq 무료 모델을 이용한 한국어 요약
- 연도·월·일 단위 Markdown 아카이브
- 게시 전 검토용 Threads 초안 생성
- 기존 Threads 게시물과 미디어 메타데이터 백업
- GitHub Actions 일일 자동 실행

자동 게시 기능은 포함하지 않습니다. 생성 결과는 사람이 확인한 뒤 사용해야 합니다.

## 처리 흐름

```text
공식 소스 수집
→ 발행일·중복 검증
→ 중요도 평가 및 한국어 분석
→ 날짜별 아카이브 저장
→ 선택적으로 Threads 초안 생성
```

## 수집 소스

활성 소스는 `source_registry.py`에서 관리합니다.

- AI 연구소: OpenAI, Anthropic, Google DeepMind, Google Research, Meta AI Research
- 개발 생태계: Hugging Face
- 인프라·칩: NVIDIA Technical Blog, NVIDIA Developer Blog, NVIDIA Korea Blog
- 플랫폼: Microsoft Research, Google Cloud AI Blog
- 논문: arXiv `cs.AI`, `cs.LG`, `cs.CV`, `cs.CL`

AMD ROCm, Azure AI, AWS Machine Learning, Microsoft AI, Perplexity는 현재 기본 수집 대상에서 제외되어 있습니다.

## 아카이브

수집 결과는 다음 구조로 저장됩니다.

```text
archive/
└── 2026/
    └── 09월/
        └── 2026-09-14.md
```

AI 분석에 실패한 항목은 공개 Markdown에 불완전한 내용으로 넣지 않고 `archive/pending/`에 보관합니다.

## 설치

```bash
git clone https://github.com/JCURVEs/thread-auto.git
cd thread-auto
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

## 설정

필수 환경 변수:

```powershell
$env:GROQ_API_KEY="your_key"
```

주요 선택 변수:

```powershell
$env:GROQ_MODEL="qwen/qwen3.8-27b"
$env:COLLECT_ALL_SOURCES="true"
$env:MAX_ARTICLE_AGE_HOURS="48"
$env:ENTRIES_PER_SOURCE="5"
$env:ENABLE_PENDING_ARCHIVE="true"
$env:ALLOW_PAID_MODELS="false"
```

기본 AI provider는 Groq이며 유료 모델로 자동 전환하지 않습니다.

## 실행

뉴스 수집:

```bash
python main.py
```

최신 아카이브에서 Threads 초안 생성:

```bash
python thread_generator.py --type news --input latest
```

기존 Threads 게시물 백업:

```powershell
$env:THREADS_ACCESS_TOKEN="your_token"
python scripts/export_threads_history.py --since 2026-01-01
```

미디어 파일까지 내려받으려면 `--download-media` 옵션을 추가합니다. 토큰과 계정 백업 데이터는 `.gitignore`로 제외됩니다.

## 자동 실행

`.github/workflows/daily_news.yml`이 매일 한국 시간 오전 9시에 실행됩니다. 수집 결과는 `archive/`, 실행 기록은 `logs/daily/`에 커밋됩니다.

GitHub 저장소 Secret에 `GROQ_API_KEY`를 등록해야 AI 분석이 동작합니다.

## 테스트

```bash
python -m pytest -q
```

외부 소스 테스트는 해당 웹사이트나 RSS 상태에 따라 실패할 수 있습니다.

## 주요 파일

| 파일 | 역할 |
| --- | --- |
| `source_registry.py` | 수집 소스와 가중치 관리 |
| `rss_collector.py` | RSS 및 공식 페이지 수집 |
| `ai_analyzer.py` | 한국어 분석과 품질 검사 |
| `archiver.py` | 날짜별 Markdown 저장 |
| `thread_generator.py` | 검토용 Threads 초안 생성 |
| `threads_history_client.py` | 기존 Threads 게시물 수집 |

## License

MIT
