---
description: 새로운 기능(feature) 파일을 생성하고 main.py에 예제 메서드 추가
---

# Create Feature Workflow

새로운 기능을 추가할 때 다음 단계를 따르세요:

## Steps

1. 기능 이름을 확인합니다 (예: `feature_name`)

2. 새 기능 파일 생성: `feature_name.py`
   - 기능 로직을 구현
   - PEP 8 스타일 가이드 준수
   - 적절한 docstring 추가

3. `main.py`에 예제 메서드 추가
   - `example_feature_name()` 메서드 생성
   - 기능 사용 예시 코드 작성

4. `main()` 함수에서 예제 메서드 호출 추가

5. 테스트 파일 생성: `tests/test_feature_name.py`
   - 주요 기능에 대한 유닛 테스트 작성

// turbo
6. 테스트 실행하여 기능 검증
```bash
pytest tests/test_feature_name.py -v
```
