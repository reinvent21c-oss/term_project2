# 인터페이스 계약

이 문서는 현재 코드 기준의 역할 간 공개 계약입니다. 코드와 문서가 다르면 코드가 기준이며,
계약 점검은 `python chart/check_contract.py`로 수행할 수 있습니다.

역할은 다음과 같이 부릅니다.

- 데이터 수집·정제 / ingestion: `source/`
- AI 분석·인사이트·리포트 / AI & reporting: `prompt/`
- 애플리케이션·DB·CLI·시각화 / application: `chart/`

## 경로와 소유 경계

application은 파일 기반 로더를 통해 ingestion과 AI & reporting을 불러옵니다. 이 연결은
`chart/modules/paths.py`와 `chart/modules/bridge.py`에 모여 있습니다. application은
`source/`와 `prompt/`에 패키지 파일을 추가하지 않으며, 두 모듈은 application을 import하지
않습니다.

## ingestion → application

```python
import_reviews(file_path, output_path) -> list[dict]
clean_reviews(input_path, output_path) -> list[dict]
```

`import_reviews()`는 CSV를 읽고 필수 컬럼을 검사한 뒤 raw JSONL을 기록합니다.
`clean_reviews()`는 raw JSONL을 읽어 clean JSONL을 기록합니다. 두 함수 모두 저장한
레코드 목록도 반환합니다.

clean 레코드는 정확히 다음 다섯 필드를 가집니다.

```python
{
    "rating": 4,                         # int, 1~5
    "review_text": "발림성이 부드럽고…", # str
    "review_date": "2025-12-11",        # str, YYYY-MM-DD
    "product_name": "데일리 선크림",      # str
    "skin_type": "지성",                # str
}
```

ingestion은 입력 파일 내부의 중복을 처리합니다. application은 이 레코드에서 정규화한
`product_name`, `review_text`, `review_date`의 SHA-256 해시를 만들어 SQLite의 중복을
처리합니다.

## application → AI sentiment analysis → application

application은 분석 대상에서 다음 두 필드만 추려 AI 분석에 전달합니다.

```python
[
    {"id": 1, "review_text": "발림성이 좋아요"},
    {"id": 2, "review_text": "너무 끈적거려요"},
]
```

```python
analyze_review(review_text: str) -> {"sentiment", "confidence"}
analyze_reviews(reviews: list[dict]) -> {
    "results": [{"id", "sentiment", "confidence"}],
    "failed_ids": [int],
}
```

`sentiment`는 `positive`, `neutral`, `negative` 중 하나이고, `confidence`는
0.0~1.0 범위의 숫자입니다. 입력 ID는 `results` 또는 `failed_ids` 중 정확히 한쪽에
나타나야 합니다. ID 누락은 호출자 오류로 예외 처리하고, ID가 있으나 본문이 비어 있거나
분석에 실패한 경우에는 해당 ID를 `failed_ids`에 기록합니다.

별점은 AI 분석 입력에 포함하지 않습니다. application은 결과를 저장하기 전에 인터페이스
검증을 수행하고, 분석 실패가 일부만 있으면 성공 결과는 저장한 뒤 종료 코드 2를 반환합니다.

## AI insight extraction

```python
extract_insights(reviews: list[str]) -> {
    "positive_keywords": list[str],
    "negative_keywords": list[str],
    "summary": str,
    "improvements": list[str],
} | None
```

입력이 리스트가 아니거나 비어 있거나 비어 있는 문자열을 포함하면 `ValueError`를 냅니다.
현재 결과 검증은 `improvements`에 두 개 이상의 항목을 요구합니다. Gemini 호출 또는 결과
검증이 실패하면 재시도 후 `None`을 반환합니다. 인사이트가 없어도 통계·차트·리포트 생성은
계속될 수 있습니다.

## Markdown reporter

```python
generate_markdown_report(
    stats=None,
    insights=None,
    chart_paths=None,
    output_path=None,
) -> str
```

`stats`가 있을 때 reporter는 `summary`, `quality`, `top_n`을 사용합니다.
`insights=None`은 빈 인사이트로 처리하고, `chart_paths`는 리스트·dict·`None`을 받습니다.
`output_path`가 주어지면 UTF-8 Markdown 파일을 기록합니다.

application은 dashboard에서 생성한 chart 경로를 리포트 파일 기준 상대경로로 넘깁니다.

## stats 계약

`calculate_stats()`는 다음 여섯 영역을 반환합니다.

```python
{
    "meta": {"schema_version", "generated_at", "filters"},
    "summary": {...},
    "chart_data": {...},
    "quality": {...},
    "top_n": {...},
    "alerts": [...],
}
```

`chart_data`는 차트 생성에, `summary`·`quality`·`top_n`은 reporter에 사용됩니다.
`alerts`는 경고가 없으면 빈 리스트입니다. `top_n["keyword_impact"]`는 AI가 추출한
부정 키워드를 리뷰 본문으로 다시 계량한 결과이며, 본문에서 찾지 못한 키워드는
`matched: False`로 남습니다.

## 사람 검수 데이터

application은 사람 검수 결과를 `human_labels`에 저장합니다. `(review_id, batch, reviewer)`가
고유하며, 같은 조합을 다시 저장하면 덮어씁니다. 각 레이블에는 검수 시점 AI 감정·확신도·모델
스냅샷을 함께 보관할 수 있습니다. 이 기능은 AI & reporting의 세 공개 함수를 호출하지 않습니다.

## 관련 문서

- [아키텍처 개요](overview.md)
- [AI & reporting 모듈 안내](../../prompt/README.md)
- [ingestion 모듈 안내](../../source/README.md)
- [역사적 C 전달 기록](../archive/team-handoff-c.md)
