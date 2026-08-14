# AI & reporting 팀 전달 기록 (archive)

이 문서는 팀 개발 과정에서 AI 분석·인사이트·리포트 역할에 전달했던 요청과 점검 기록을
보존합니다. 현재 공개 계약은 [인터페이스 계약](../architecture/interface-contract.md)이
기준이며, 이 문서는 현재 사용 설명이나 제품 상태 보고가 아닙니다.

## 기록의 배경

당시 application과 AI & reporting의 연결은 다음 세 공개 함수로 정리되었습니다.

```text
analyze_reviews([{id, review_text}])
extract_insights([str])
generate_markdown_report(stats, insights, chart_paths, output_path)
```

분석 결과에는 입력 ID가 성공 결과 또는 `failed_ids`에 남아야 하고, 별점은 AI 분석
입력에 넣지 않는다는 원칙을 합의했습니다. application은 저장 전에 결과를 검증하도록
구성되었습니다.

## 당시 점검과 전달사항

2026-08-12 기준 전달 문서에는 다음 항목이 기록되었습니다.

- `validate_insight_result()`가 개선안 두 개 이상을 요구해, 계약의 최소 형태와 차이가
  있다는 점
- reporter가 `chart_paths` dict의 키를 사용하지 않고 차트 번호만 표기한다는 점
- reporter가 `stats["meta"]`의 생성 시각과 필터를 표시하지 않는다는 점
- 선택 필드가 `None`일 때 문자열 `"None"`이 리포트에 보일 수 있다는 점

이 항목들은 현재 README의 “현재 알려진 제한사항과 후속 검토”에서 기술적 제한사항으로
정리합니다. 당시의 `[FAIL]`, `[TODO]` 표기는 팀 통합 과정의 상태 기록이며 현재 제품의
전체 품질 판정으로 해석하지 않습니다.

## 당시 검증 방식

`python chart/check_contract.py --c`는 Gemini 호출 없이 공개 함수의 입력·출력 형태를
점검했습니다. 빈 본문은 호출 전에 걸러 `failed_ids`로 보내고, ID 없는 입력은 호출자
오류로 처리하는 규칙을 확인했습니다.

과거 문서에는 AI 분석 단위 테스트 25개 통과 기록이 있었지만, 현재 저장소에는
`prompt/tests/`가 없습니다. 따라서 이 기록은 현재 자동 테스트 총계에 포함하지 않습니다.

## 보존 범위

이 archive는 담당자 간 전달 맥락과 당시 개선 요청을 보존하기 위한 것입니다. 최신 API,
데이터 구조, 오류 처리의 기준은 항상 [인터페이스 계약](../architecture/interface-contract.md)과
현재 Python 코드입니다.
