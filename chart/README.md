# application 모듈 안내

`chart/`는 애플리케이션·DB·CLI·시각화 계층입니다. 루트 실행 진입점은
[`../main.py`](../main.py)이고, 실제 argparse CLI는 [`main.py`](main.py)입니다.
설치와 전체 명령은 [루트 README](../README.md)를, 전체 구조는
[아키텍처 개요](../docs/architecture/overview.md)를 참고하세요.

## 책임

- SQLite 스키마, 저장·조회, DB 중복 판정
- CLI 명령 처리와 종료 코드
- ingestion 및 AI & reporting 모듈 연결
- 통계, 경고, 대시보드 차트, CSV·JSONL·XLSX export
- 사람 라벨 기반 AI 검수와 결과 기록

## 주요 모듈

| 경로 | 역할 |
|---|---|
| `main.py` | CLI 파싱 및 명령 핸들러 연결 |
| `modules/paths.py` | 저장소 상대경로와 외부 모듈의 파일 기반 로딩 |
| `modules/bridge.py` | ingestion·AI & reporting 호출, Excel→CSV 변환 |
| `modules/database.py` | SQLite 스키마·저장·조회·중복 해시 |
| `modules/stats.py` | 통계, 경고, 개선 우선순위 계산 |
| `modules/visualizer.py` | 대시보드 차트 생성 |
| `modules/interfaces.py` | 저장 전 공개 계약 검증 |
| `modules/exporter.py` | CSV·JSONL·XLSX 내보내기 |
| `modules/audit.py` | 사람 라벨 표본·점수 계산 |

## 설계 경계

application은 `source/`와 `prompt/`를 파일 경로로 불러와 직접 패키지 의존을 만들지
않습니다. `bridge.py`가 외부 모듈 호출을 모으고, `interfaces.py`가 AI 분석·인사이트·통계
결과를 DB 저장 전에 확인합니다.

통계는 `stats.calculate_stats()` 한 곳에서 계산합니다. 차트는 `chart_data`를 사용하고,
reporter에는 `summary`, `quality`, `top_n`과 상대 차트 경로를 전달합니다.

## 저장소와 생성물

기본 SQLite 경로는 `chart/db/reviews.db`입니다. `REVIEW_DB_PATH` 환경변수 또는
`config.json`의 `database.path`로 경로를 바꿀 수 있습니다. `db/`, `logs/`, `output/`은
실행 시 생성되는 로컬 산출물이며 Git에서 제외됩니다.

## 검증

```text
python chart/check_contract.py
python chart/tests/test_integration.py
```

두 검증 도구의 역할과 현재 기준선 결과는 [테스트 가이드](../docs/guides/testing.md)에
정리되어 있습니다. 역할 간 데이터 구조는 [인터페이스 계약](../docs/architecture/interface-contract.md)을
참고하세요.
