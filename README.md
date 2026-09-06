# Thread-Auto

AI/테크 뉴스와 논문 후보를 수집하고, Threads에 올릴 수 있는 멀티스레드 초안까지 만드는 개인용 콘텐츠 파이프라인입니다.

현재 목표는 자동 게시가 아니라 다음 흐름입니다.

```text
기존 Threads 글 백업/자산화
→ 개인 문체/구조 분석
→ 스타일 프로필 생성
→ 공식 소스 수집
→ 본문/RSS 요약 분석
→ 스레드 초안 생성
→ 게시 전 품질 검수
```

뉴스 수집 파이프라인은 아래 흐름으로 동작합니다.

```text
공식 소스 수집
→ 본문/RSS 요약 분석
→ 연도/월별 아카이브 저장
→ 스레드 초안 생성
→ 게시 전 품질 검수
```

## 현재 상태

- 15개 활성 소스 기반 수집망
- source_registry 기반 소스 가중치/커버리지 관리
- 수집 커버리지 점수 100/100
- 연도/월별 아카이브 구조
- 중요도 보정 및 품질 게이트
- @jokerburg.builder 스타일의 스레드 초안 생성
- Threads 과거 글 로컬 백업/정규화 기반
- 과거 글 기반 스타일 프로필 생성 기반
- 게시 전 리뷰 리포트 생성
- Meta Threads 자동 게시 기능은 아직 적용하지 않음

## 수집 소스

소스는 [source_registry.py](source_registry.py)에서 관리합니다.

### Frontier / Research

```text
openai
anthropic
deepmind
google_research
huggingface
meta_research
```

### 인프라 / 칩

```text
nvidia_technical
nvidia_developer_ai
nvidia_korea_blog
```

### 클라우드 / 플랫폼

```text
microsoft_research
google_cloud_ai
```

### 논문

```text
arxiv_ai
arxiv_lg
arxiv_cv
arxiv_cl
```

### 등록했지만 기본 비활성

```text
microsoft_ai
perplexity
amd_rocm
azure_ai
aws_machine_learning
```

위 소스는 registry에 남겨두었지만, 자동 검증 기준으로 안정적인 수집이 어렵거나 현재 편집 방향에서 제외되어 기본 수집 대상에서는 제외했습니다.

## 소스 가중치

단순히 많이 긁는 방식이 아니라, 소스별 성격을 반영합니다.

```text
frontier_lab
infra_chip
cloud_platform
research_lab
developer_ecosystem
paper_research
```

예를 들어 NVIDIA, NVIDIA Korea, Microsoft Research 같은 실무 임팩트가 큰 소스는 기본보다 높은 가중치를 가집니다.
단, 비즈니스/파트너십성 글은 중요도 보정에서 낮게 제한됩니다.

## 아카이브 구조

수집된 글은 연도와 월 단위로 저장됩니다.

```text
archive/
└── 2026/
    ├── 01월/
    ├── 02월/
    ├── 03월/
    ├── 04월/
    ├── 05월/
    ├── 06월/
    ├── 07월/
    ├── 08월/
    ├── 09월/
    ├── 10월/
    ├── 11월/
    └── 12월/
```

파일명은 일자 기준입니다.

```text
archive/2026/07월/2026-07-09.md
```

## 일일 실행 로그

GitHub Actions는 매일 한국 시간 오전 9시에 실행됩니다.

```text
logs/daily/2026/07월/2026-07-16.md
```

새 글이 없는 날에도 수집 소스 수, 커버리지 점수, 비활성 소스, 최신 아카이브 경로를 기록합니다.  
Actions 커밋 작성자는 기본적으로 `JCURVEs <JCURVEs@users.noreply.github.com>`로 설정되어 GitHub contribution graph에 반영되도록 구성했습니다.

## 스레드 초안 포맷

뉴스 스레드는 총 9개 파일로 생성됩니다.

```text
thread-01.md  제목
thread-02.md  후킹 5줄
thread-03.md  1/
thread-04.md  2/
thread-05.md  3/
thread-06.md  4/
thread-07.md  5/
thread-08.md  6/
thread-09.md  7/
```

본문은 다음 흐름을 따릅니다.

```text
1/ 기존 상식 뒤집기
2/ 문제/병목
3/ 핵심 접근법
4/ 구현 방식
5/ 기술 원리
6/ 결과/성과
7/ 미래 전망/임팩트
```

각 `1/`~`7/` 소제목은 구조명이 아니라 실제 내용이 담긴 문장으로 생성됩니다.

## 스타일 기준

스타일은 [references/style-guide.md](references/style-guide.md)에 공개 가능한 규칙만 저장합니다.

핵심 리듬:

```text
겉보기엔 ...
근데 뜯어보면 ...
핵심은 이겁니다.
먼저 용어부터.
쉽게 말하면 ...
```

원본 프롬프트나 개인 샘플 전문은 저장하지 않습니다.

## 품질 검수

생성된 초안은 `review-report.md`를 함께 만듭니다.

검수 항목:

- 9개 포스트 구조 확인
- 제목 한 줄 여부
- 후킹 5줄 여부
- 마지막 줄 `핵심내용 정리했습니다🧵` 확인
- `1/`~`7/` 넘버링 확인
- 각 슬라이드 7~9줄 확인
- 500자 초과 여부 확인
- 과장 표현 차단
- 근거 없는 숫자 성과 차단
- 출처 URL 포함 여부 확인

`metadata.json`에도 리뷰 상태가 저장됩니다.

```json
{
  "review_status": "READY_FOR_HUMAN_REVIEW",
  "review_blocking_count": 0,
  "review_warning_count": 0
}
```

## Threads 글 자산화

자동 게시보다 먼저, 기존에 올린 글을 로컬 스타일 자산으로 만듭니다.

```text
Meta Threads API
→ raw export
→ normalized posts corpus
→ style_profile.json
→ thread_generator 스타일 반영
```

개인 계정 글과 토큰은 민감한 데이터이므로 `data/threads/raw/`, `data/threads/normalized/`, `data/threads/style_profile.json`은 git에 올리지 않습니다.

### 1. 기존 Threads 글 백업

`THREADS_ACCESS_TOKEN`은 로컬 환경 변수로만 설정합니다.

```bash
set THREADS_ACCESS_TOKEN=your_threads_access_token
python scripts/export_threads_history.py --since 2026-01-01
```

저장 위치:

```text
data/threads/raw/runs/threads_export_YYYYMMDDTHHMMSSZ.jsonl
data/threads/normalized/posts.jsonl
```

### 2. 스타일 프로필 생성

```bash
python scripts/analyze_threads_style.py --username jokerburg.builder
```

출력:

```text
data/threads/style_profile.json
```

분석 항목:

- 글 길이와 줄 수
- `1/`, `2/` 같은 넘버링 구조 사용률
- 후킹 문구 사용률
- 자주 쓰는 전개 표현
- 문장 종결 패턴
- 생성기가 따라야 할 스타일 힌트

수집 대상:

- 텍스트 본문
- 게시 시간과 permalink
- 이미지/영상 URL
- 영상 썸네일 URL
- GIF URL
- 캐러셀 children
- alt text
- quote/repost/link/poll 메타데이터
- `1/`, `2/`, `3/`처럼 자기 답글로 이어지는 conversation chain

기본 export는 `has_replies`가 있는 글의 conversation을 함께 가져와 멀티스레드 흐름을 보존합니다.
필요하면 `--no-include-conversations`로 끌 수 있습니다.

이미지/영상 파일까지 내려받으려면 `--download-media`를 추가합니다. 영상이 많으면 저장 용량이 커질 수 있어 기본값은 URL/메타데이터 백업입니다.

```bash
python scripts/export_threads_history.py --since 2026-01-01 --download-media
```

## 설치

```bash
git clone https://github.com/JCURVEs/thread-auto.git
cd thread-auto
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 환경 변수

기본 AI 분석 provider는 Groq 무료 티어입니다.
OpenRouter는 `:free` 모델만 기본 허용하며, 유료 모델은 `ALLOW_PAID_MODELS=true`를 직접 켜지 않는 한 차단됩니다.

```bash
set GROQ_API_KEY=your_key
set COLLECT_ALL_SOURCES=true
```

선택 옵션:

```bash
set AI_PROVIDER=groq
set AI_PROVIDER_FALLBACKS=groq,gemini,openrouter
set AI_MODEL=
set OPENROUTER_API_KEY=
set OPENROUTER_MODEL=qwen/qwen3-30b-a3b:free
set GROQ_API_KEY=
set GEMINI_API_KEY=
set MAX_ARTICLE_AGE_HOURS=48
set ENTRIES_PER_SOURCE=5
set ENABLE_FALLBACK_ARCHIVE=true
set ALLOW_PAID_MODELS=false
```

## 실행

### 뉴스 수집

```bash
python main.py
```

실행 시 현재 수집망 정보가 출력됩니다.

```text
Sources: 15
Collection Score: 100/100
Disabled Sources: microsoft_ai, perplexity, amd_rocm, azure_ai, aws_machine_learning
```

### 최신 아카이브에서 스레드 초안 생성

```bash
python thread_generator.py --type news --input latest
```

### 특정 날짜 아카이브에서 생성

```bash
python thread_generator.py --type news --input 2026-07-09
```

출력 예시:

```text
threads/news/20260709-native-speed-vllm-transformers-backe-f2a336/
├── thread-01.md
├── thread-02.md
├── ...
├── thread-09.md
├── metadata.json
└── review-report.md
```

## 테스트

전체 테스트:

```bash
python -m pytest -q
```

네트워크 소스 테스트는 공식 RSS/웹 페이지 상태에 영향을 받을 수 있습니다.

## 주요 파일

```text
source_registry.py       수집 소스, 가중치, 커버리지 점수
rss_collector.py         RSS/공식 페이지 수집
anthropic_scraper.py     Anthropic 전용 Playwright 스크래퍼
ai_analyzer.py           AI 분석, 중요도 보정, 품질 게이트
archiver.py              연도/월별 아카이브 저장
threads_history_client.py Threads API 과거 글 수집 클라이언트
threads_assets.py        과거 글 raw/normalized 로컬 저장
style_analyzer.py        과거 글 기반 문체/구조 분석
scripts/write_daily_run_log.py 일일 실행 로그 생성
scripts/export_threads_history.py Threads 과거 글 백업
scripts/analyze_threads_style.py 스타일 프로필 생성
thread_generator.py      스레드 초안 생성 및 게시 전 리뷰
references/style-guide.md 스타일 가이드
```

## 로드맵

- [x] 15개 활성 소스 수집망 구성
- [x] source_registry 기반 가중치/커버리지 관리
- [x] 연도/월별 아카이브 구조
- [x] 중요도 보정
- [x] @jokerburg.builder 스타일 초안 생성
- [x] Threads 과거 글 자산화 기반
- [x] 과거 글 기반 스타일 분석기
- [x] 게시 전 리뷰 리포트
- [ ] style_profile 기반 thread_generator 반영
- [ ] 논문 큐레이션 추가 고도화
- [ ] 후보 랭킹 리포트
- [ ] 수동 승인 워크플로우
- [ ] Meta Threads 자동 게시

## 라이선스

MIT License
