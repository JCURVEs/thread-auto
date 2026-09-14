# Thread-Auto

AI·테크 뉴스와 논문을 수집하고 한국어로 분석해 날짜별 Markdown으로 보관하는 개인용 콘텐츠 파이프라인입니다.

## 주요 기능

- 공식 블로그, 연구소, arXiv 피드 수집
- 소스별 가중치와 중요도 기반 후보 선별
- 발행일 검증 및 중복 URL 제거
- LLM 기반 한국어 요약
- 연도·월·일 단위 Markdown 아카이브
- Human-in-the-loop 기반 Threads 초안 검토
- 기존 Threads 게시물과 미디어 메타데이터 백업
- GitHub Actions 일일 자동 실행

생성 결과는 사람이 검토하고 승인하는 Human-in-the-loop 워크플로우로 운영됩니다.

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

## 자동 실행

`.github/workflows/daily_news.yml`이 매일 한국 시간 오전 9시에 실행됩니다. 수집 결과는 `archive/`, 실행 기록은 `logs/daily/`에 커밋됩니다.

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
