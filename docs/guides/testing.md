# 테스트 가이드

이 문서는 현재 저장소에 포함된 검증 도구와 Windows 기준선 검증 기록을 구분해 설명합니다.
실행 방법은 [루트 README](../../README.md), 계약 상세는
[인터페이스 계약](../architecture/interface-contract.md)을 참고하세요.

## Contract smoke check

```text
python chart/check_contract.py
```

모듈 사이의 공개 함수와 계약을 빠르게 확인합니다. ingestion, AI & reporting,
application의 로드 가능 여부와 입력·출력 형태를 검사하며, 실제 Gemini 호출 없이
검증할 수 있도록 구성되어 있습니다.

## Integration / regression suite

```text
python chart/tests/test_integration.py
```

현재 저장소에는 58개의 통합 테스트가 있습니다. SQLite 저장·조회, 데이터 정제 연결,
AI 결과 계약, 통계·경고, 차트, export, Excel 입력, 사람 검수, 역할 경계를 함께 검사합니다.

## 현재 재검증한 환경과 결과

아래는 공식 지원 환경 선언이 아니라, Windows에서 재검증한 기준선 기록입니다.

```text
Python 3.10.9
pip 26.2.1
```

```text
58개 실행
56개 통과
2개 조건부 skip
FAIL / ERROR 0
```

조건부 skip 2개는 `GEMINI_API_KEY`가 없을 때 실제 Gemini API를 호출하는 live test를
건너뜁니다. 키가 없는 환경에서의 정상 동작이며, 나머지 테스트는 API 키 없이 실행됩니다.

## 테스트 범위의 경계

과거 팀 문서에는 AI 분석 단위 테스트 25개 통과 기록이 있으나, 현재 저장소에는
`prompt/tests/`가 없습니다. 따라서 그 기록은 현재 자동 테스트 총계에 포함하지 않습니다.

계약 점검은 빠른 인터페이스 확인용이고, 통합 테스트는 회귀 검증용입니다. 둘은 일부
검증 범위가 겹치지만 목적이 다르므로 함께 유지합니다.
