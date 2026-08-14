# 아키텍처 개요

이 문서는 현재 저장소의 코드 구조를 설명합니다. 실행 방법은 [루트 README](../../README.md),
모듈 간 데이터 계약은 [인터페이스 계약](interface-contract.md)을 참고하세요.

## 전체 흐름

```text
CSV / Excel
  ↓
ingestion (`source/`)
  ↓ raw / clean JSONL
application (`chart/`)의 SQLite 저장소
  ↓
AI sentiment analysis (`prompt/analyzer.py`)
  ↓
AI insights (`prompt/extractor.py`)
  ↓
stats / alerts
  ↓
charts / Markdown report / export
```

`source/raw/`는 입력 행을 보존한 JSONL이고, `source/clean/`은 정제와 파일 내
중복 제거를 마친 JSONL입니다. SQLite는 원본·정제본·분석·인사이트·사람 검수 결과를
저장합니다.

## 역할과 책임

| 역할 | 경로 | 책임 |
|---|---|---|
| 데이터 수집·정제 / ingestion | `source/` | CSV 입력 검증, raw JSONL 보존, clean JSONL 생성 |
| AI 분석·인사이트·리포트 / AI & reporting | `prompt/` | Gemini 감정 분석, 인사이트 추출, Markdown 리포트 렌더링 |
| 애플리케이션·DB·CLI·시각화 / application | `chart/` | CLI, SQLite, 통계·경고, 차트, export, 모듈 연결 |

루트의 [`main.py`](../../main.py)는 얇은 실행 진입점입니다. 파일 경로로
[`chart/main.py`](../../chart/main.py)를 불러오고 `chart/`를 import 경로에 추가합니다.
`chart/main.py`는 argparse 기반의 실제 CLI 본체입니다. 두 파일은 중복 구현이 아니라
실행 진입점과 명령 처리의 분리입니다.

## 경계와 연결

application은 [`chart/modules/paths.py`](../../chart/modules/paths.py)의 파일 기반 로더로
`source/src/`와 `prompt/`의 모듈을 읽습니다. 이 방식은 두 디렉터리에 패키지 파일을
추가하지 않고도 모듈을 연결합니다. [`chart/modules/bridge.py`](../../chart/modules/bridge.py)는
ingestion과 AI & reporting 호출을 한 곳에 모으고, Excel 입력은 임시 CSV로 변환한 뒤
ingestion에 전달합니다.

결과가 SQLite에 저장되기 전에는 [`chart/modules/interfaces.py`](../../chart/modules/interfaces.py)가
분석·통계·인사이트 결과 형태를 검증합니다. 공개 함수와 데이터 구조의 상세는
[인터페이스 계약](interface-contract.md)에 있습니다.

## 데이터와 저장소

SQLite는 한 파일로 실행 상태와 분석 결과를 보관합니다. 정제 단계의 파일 내 중복 제거와
DB 단계의 중복 판정은 서로 다른 범위를 다룹니다. `cleaner.py`는 한 입력 파일 내부의
`review_text`, `product_name`, `review_date` 조합을 제거하고, application은 같은 필드를
정규화한 SHA-256 `review_hash`로 기존 DB 데이터와의 중복을 판정합니다.

raw와 clean을 분리하면 원본 CSV가 없더라도 보관한 raw JSONL을 다시 정제할 수 있고,
정제 전후 데이터를 구분해 확인할 수 있습니다.

## AI 분석의 부분 복구

AI 분석에는 `{id, review_text}`만 전달하고 별점은 전달하지 않습니다. 별점을 입력으로
쓰면 별점-감정 일치도 지표가 순환 논리가 될 수 있기 때문입니다.

`analyze_reviews()`는 여러 리뷰를 batch로 분석합니다. batch 처리 중 실패가 나면 더 작은
batch로 나누어 재시도하고, 끝내 처리하지 못한 ID는 `failed_ids`에 남깁니다. 입력 ID는
성공 결과 또는 실패 목록 중 한쪽에 반드시 나타나야 합니다. 이 구조는 한 건의 실패가
앞선 분석 결과를 버리거나 결과와 ID의 대응을 밀어버리는 것을 막습니다.

## 통계, 차트, 리포트

`stats.calculate_stats()`가 메타데이터, 요약, 차트 데이터, 품질 지표, TOP N, 경고를 한 번에
구성합니다. 차트는 `chart_data`를 사용하고, Markdown reporter는 `summary`, `quality`,
`top_n`을 렌더링합니다. chart 계층은 생성한 이미지 경로를 리포트 파일 기준 상대경로로
변환해 reporter에 전달합니다.

차트 생성은 데이터가 부족한 차트를 건너뛸 수 있으며, export는 CSV·JSONL·XLSX를 지원합니다.
경고 임계치는 `chart/config.json`에 있고, 판단 로직은 stats 계층에 있습니다.

## 관련 문서

- [인터페이스 계약](interface-contract.md)
- [테스트 가이드](../guides/testing.md)
- [application 모듈 안내](../../chart/README.md)
- [AI & reporting 모듈 안내](../../prompt/README.md)
- [ingestion 모듈 안내](../../source/README.md)
