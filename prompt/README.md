# AI 분석 · 인사이트 · 리포트 모듈

`prompt/`는 Gemini 기반 감정 분석, 인사이트 추출, Markdown 리포트 생성을 담당합니다.
전체 역할 간 계약은 [인터페이스 계약](../docs/architecture/interface-contract.md), 실행 방법은
[루트 README](../README.md)를 참고하세요.

## 환경변수

`analyze`와 `extract`는 Gemini API 키가 필요합니다. `chart/.env.example`을 `chart/.env`로
복사한 뒤 다음 값을 설정합니다.

```text
GEMINI_API_KEY=your_api_key_here
```

실제 키는 커밋하지 않습니다. API 키가 없으면 CLI는 분석·추출을 시작하기 전에 중단합니다.

## 감정 분석

```python
analyze_review(review_text: str) -> {
    "sentiment": "positive" | "neutral" | "negative",
    "confidence": float,
}

analyze_reviews(reviews: list[dict]) -> {
    "results": [{"id": int, "sentiment": str, "confidence": float}],
    "failed_ids": [int],
}
```

`analyze_reviews()` 입력의 각 항목은 `id`와 비어 있지 않은 `review_text`를 가져야 합니다.
ID가 없으면 `ValueError`를 내고, ID는 있지만 본문이 비어 있거나 분석에 실패하면 해당 ID를
`failed_ids`에 기록합니다.

여러 리뷰는 batch로 분석합니다. batch 호출이 실패하면 더 작은 batch로 나누어 재시도하며,
성공 결과는 유지합니다. 입력 ID는 `results` 또는 `failed_ids` 중 한쪽에 반드시 남습니다.
별점은 분석 입력에 포함하지 않습니다.

## AI 인사이트

```python
extract_insights(reviews: list[str]) -> {
    "positive_keywords": list[str],
    "negative_keywords": list[str],
    "summary": str,
    "improvements": list[str],
} | None
```

입력은 하나 이상의 비어 있지 않은 문자열로 구성된 리스트여야 합니다. 입력 형식이 잘못되면
`ValueError`를 냅니다. 현재 결과 검증은 `improvements`에 두 개 이상의 항목을 요구합니다.
Gemini 호출이나 결과 검증이 실패하면 한 번 재시도한 뒤 `None`을 반환합니다. 호출자는
`None`을 허용해야 합니다.

## Markdown reporter

```python
generate_markdown_report(
    stats=None,
    insights=None,
    chart_paths=None,
    output_path=None,
) -> str
```

`stats`가 있으면 `summary`, `quality`, `top_n`을 읽어 리포트를 구성합니다.
`insights=None`은 빈 인사이트로 처리합니다. `chart_paths`는 리스트·dict·`None`을 받을 수
있고, `output_path`가 있으면 해당 경로에 UTF-8 Markdown 파일을 저장합니다.

application은 리포트 파일 기준 상대 차트 경로를 전달합니다. reporter가 읽는 통계와
차트 경로 구조의 상세는 [인터페이스 계약](../docs/architecture/interface-contract.md)을
참고하세요.

## 관련 문서

- [아키텍처 개요](../docs/architecture/overview.md)
- [테스트 가이드](../docs/guides/testing.md)
- [역사적 팀 전달 기록](../docs/archive/team-handoff-c.md)
