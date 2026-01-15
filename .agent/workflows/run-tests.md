---
description: 프로젝트의 모든 유닛 테스트 실행
---

# Run Tests Workflow

프로젝트의 테스트를 실행합니다.

## Steps

// turbo
1. 모든 테스트 실행
```bash
pytest tests/ -v
```

// turbo
2. 커버리지 리포트 생성 (선택)
```bash
pytest tests/ --cov=. --cov-report=term-missing
```
