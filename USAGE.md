# Thread-Auto v2.0 사용 가이드

## 시스템 개요

Thread-Auto v2.0은 Claude Code Agents를 활용한 AI 콘텐츠 자동 스레드 생성 시스템입니다.

**3가지 콘텐츠 타입 지원:**
- 📰 데일리뉴스 (기존 RSS 파이프라인 활용)
- 📄 논문 (arXiv 논문 분석)
- 🏢 기업분석 (AI/테크 기업 리서치)

## 빠른 시작

### 1. 데일리뉴스 스레드 생성

```bash
# 최신 아카이브에서 스레드 생성
python thread_generator.py --type news --input latest

# 특정 날짜 뉴스
python thread_generator.py --type news --input 2026-01-31
```

또는 Claude에게 직접:
```bash
claude "오늘 뉴스 스레드 만들어줘"
claude "2026-01-30 뉴스 중에 스레드 만들어줘"
```

### 2. 논문 스레드 생성

```bash
# arXiv URL로
python thread_generator.py --type paper --input "https://arxiv.org/abs/2401.12345"

# 논문 제목으로
claude "Attention is All You Need 논문 설명해줘"
```

### 3. 기업분석 스레드 생성

```bash
# 기업명으로
python thread_generator.py --type company --input "OpenAI"
claude "Anthropic 기업분석 스레드"

# 티커로
python thread_generator.py --type company --input "NVDA"
```

## 에이전트 시스템

### 🎯 라우팅 구조

```
입력
 │
 ├─ orchestrator.md ──┬─→ 뉴스 팀
 │                    ├─→ 논문 팀
 │                    └─→ 기업분석 팀
 │
 └─→ reviewer.md (품질 검수)
```

### 📋 에이전트 목록

#### 공통
- **orchestrator.md** - 입력 분류 및 라우팅
- **reviewer.md** - 품질 검수 및 승인

#### 데일리뉴스 팀
- **news-curator.md** - archive/에서 스레드 후보 선별
- **news-thread-writer.md** - 5-7개 스레드 시리즈 작성

#### 논문 팀
- **paper-analyzer.md** - arXiv 논문 심층 분석
- **paper-thread-writer.md** - 7-10개 스레드 시리즈 작성

#### 기업분석 팀
- **company-researcher.md** - 기업 종합 리서치
- **company-thread-writer.md** - 10-15개 스레드 시리즈 작성

## 워크플로우

### 자동 실행 (GitHub Actions)

```yaml
# 뉴스 자동 생성 (daily_news.yml 완료 후)
workflow_run 트리거 자동 실행

# 수동 실행
Actions → Thread Generation → Run workflow
  Content type: news/paper/company
  Input: latest/URL/기업명
```

### 로컬 실행

1. **thread_generator.py 실행**
   ```bash
   python thread_generator.py --type news --input latest
   ```

2. **출력된 Claude 명령 실행**
   ```bash
   claude '2026-01-26.md 파일에서 스레드 만들어줘'
   ```

3. **에이전트가 자동으로 순차 실행**
   - 큐레이션/분석 → 스레드 작성 → 검수

4. **결과 확인**
   ```bash
   ls threads/news/
   ls threads/papers/
   ls threads/companies/
   ```

## 출력 구조

```
threads/
├── news/
│   └── 20260131-openai-gpt5/
│       ├── thread-01.md
│       ├── thread-02.md
│       ├── ...
│       └── metadata.json
├── papers/
│   └── 20260131-2401.12345/
│       ├── thread-01.md
│       ├── ...
│       └── metadata.json
└── companies/
    └── 20260131-anthropic/
        ├── thread-01.md
        ├── ...
        └── metadata.json
```

## 스타일 가이드

`references/style-guide.md` 참조

**핵심 원칙:**
- "요"체 사용 (해요, 이에요, 거든요)
- AI틱 표현 금지 (혁신적, 획기적, 놀라운)
- 구체적 숫자와 실제 사례
- 각 스레드 500자 이내
- 첫 스레드 강력한 후킹
- 마지막 스레드 CTA 포함

## 팁

### 효율적인 큐레이션
- 중요도 8점 이상 뉴스만 선별
- 한국 오디언스 관심도 고려
- 기술 혁신 중심 (비즈니스 뉴스 제외)

### 논문 설명
- 중학생도 이해할 수 있게
- 모든 전문 용어에 비유 추가
- 일상 예시 활용

### 기업분석
- 객관적 팩트 + 주관적 해석 구분
- 좋은 점 + 나쁜 점 균형
- 숫자 근거 필수

## 문제 해결

### 에이전트가 활성화되지 않을 때
```bash
# .claude/agents/ 파일 확인
ls -la .claude/agents/

# Claude Code 재시작
```

### 아카이브 파일 없음
```bash
# 먼저 daily_news 워크플로우 실행
# 또는 기존 아카이브 파일 확인
ls archive/2026/01월/
```

## 다음 단계

1. ✅ 시스템 구축 완료
2. 🔄 실제 스레드 생성 테스트
3. 📊 품질 검수 및 개선
4. 🚀 프로덕션 배포

---

**@jokerburg.builder** 계정용 최적화 완료 🎯
