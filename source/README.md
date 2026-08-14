# 데이터 수집 · 정제 모듈

`source/`는 ingestion 계층입니다. CSV 입력을 보존 가능한 raw JSONL로 바꾸고, 검증·정제한
clean JSONL을 생성합니다. 전체 실행 방법은 [루트 README](../README.md), 역할 간 데이터
계약은 [인터페이스 계약](../docs/architecture/interface-contract.md)을 참고하세요.

## 데이터 흐름과 파일 위치

```text
source/input/  CSV 입력
  ↓ importer.py
source/raw/    입력 행을 그대로 보존한 JSONL
  ↓ cleaner.py
source/clean/  정제·파일 내 중복 제거를 마친 JSONL
```

CLI에서는 `python main.py import --file <CSV 또는 Excel 파일>`로 ingestion 흐름을 호출합니다.
Excel 입력은 application이 임시 CSV로 변환한 뒤 importer에 전달하므로, `importer.py` 자체는
CSV만 읽습니다. raw JSONL을 보관하면 원본 CSV 없이도 `clean` 명령으로 다시 정제할 수 있습니다.

## 공개 함수

```python
import_reviews(file_path, output_path) -> list[dict]
clean_reviews(input_path, output_path) -> list[dict]
```

두 함수는 파일 경로를 받아 결과 JSONL을 기록하고, 기록한 레코드 목록도 반환합니다.

## 입력 계약

CSV는 다음 다섯 컬럼을 모두 가져야 합니다.

```python
["rating", "review_text", "review_date", "product_name", "skin_type"]
```

CSV는 `utf-8-sig`로 읽어 Excel BOM을 처리합니다. 파일이 없거나 CSV가 아니거나, 데이터가
비어 있거나 필수 컬럼이 없으면 예외를 냅니다.

## 정제 규칙

한 행은 다음을 모두 만족해야 clean 데이터에 포함됩니다.

| 필드 | 규칙 |
|---|---|
| `review_text` | 공백 정리 후 5자 이상 |
| `rating` | 정수 1~5 |
| `review_date` | `YYYY-MM-DD`, `YYYY/MM/DD`, `YYYY.MM.DD` 중 하나로 해석 가능 |
| `product_name`, `skin_type` | 비어 있으면 빈 문자열로 정규화 |

날짜는 `YYYY-MM-DD`로 정규화합니다. 정제 뒤에는 `(review_text, product_name,
review_date)`가 같은 행을 하나만 남깁니다. 이 중복 제거는 한 파일 안에서만 적용되며,
기존 SQLite 데이터와의 중복은 application이 `review_hash`로 처리합니다.

clean 레코드는 항상 다음 다섯 필드를 가집니다.

```python
{
    "rating": int,
    "review_text": str,
    "review_date": str,
    "product_name": str,
    "skin_type": str,
}
```

## 재처리 시 고려사항

- 날짜를 해석할 수 없는 행은 현재 정제 정책상 제외됩니다.
- `MIN_REVIEW_LENGTH = 5`는 `cleaner.py` 상수입니다.
- 행 단위의 유효성 문제는 건너뛰고 개수를 집계하지만, 파일 단위 문제는 예외로 처리합니다.
- 정제 결과 요약은 `print`로 출력됩니다.

## 관련 문서

- [아키텍처 개요](../docs/architecture/overview.md)
- [테스트 가이드](../docs/guides/testing.md)
- [application 모듈 안내](../chart/README.md)
