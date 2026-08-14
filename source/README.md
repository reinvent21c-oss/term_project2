# B 파트 · source/ — 수집과 정제

> 담당 **세인**
> 문서 정리: 영휘 (2026-08-14) — **코드를 읽고 동작을 확인해 쓴 것이라,
> 의도와 다른 곳이 있으면 세인님이 고쳐주세요.** 코드는 한 줄도 건드리지 않았습니다.
> 전체 프로젝트는 루트 [README.md](../README.md), 3인 공통 계약은 [INTERFACE.md](../INTERFACE.md).

파이프라인의 **입구**입니다. 원본 파일을 읽어 형태를 확인하고, 쓸 수 없는 행을 걸러
일정한 모양으로 눕혀 내보냅니다. 여기서 통과한 것만 DB로 들어갑니다.

---

## 1. 담당 범위

| 맡은 것 | 안 맡은 것 |
|---|---|
| CSV 읽기 · 필수 컬럼 검증 | DB 저장 · 조회 (A) |
| 원본 보존 (raw JSONL) | DB 중복 판정 (A) |
| 정제 규칙 — 본문 · 별점 · 날짜 | 감정 분석 · 리포트 (C) |
| 파일 안 중복 제거 | Excel 파싱 (A가 CSV 로 눕혀 넘김) |

**규모** — `source/src/` 229줄, 파일 2개, 함수 10개.

의존성이 **표준 라이브러리뿐**입니다. `csv` · `json` · `re` · `datetime` · `pathlib`.
`pip install` 없이 이 폴더만 따로 돌려볼 수 있습니다.

---

## 2. 폴더 구조

```
source/
├── src/
│   ├── importer.py    75줄 · 함수 4개   CSV → raw JSONL
│   └── cleaner.py    154줄 · 함수 6개   raw JSONL → clean JSONL
├── input/                              원본 CSV
├── raw/                                importer 산출물
└── clean/                              cleaner 산출물
```

---

## 3. 실행

### CLI 를 거쳐 (평소)

```bash
python main.py import --file source/input/cosmetics_reviews_100.csv
python main.py clean          # 원본 파일 없이 DB의 raw 를 다시 정제
```

### 이 폴더만 따로

A쪽 코드 없이도 돕니다. B 영역만 확인할 때 씁니다.

```python
from src.importer import import_reviews
from src.cleaner import clean_reviews

rows = import_reviews("input/cosmetics_reviews_100.csv", "raw/reviews.jsonl")
records = clean_reviews("raw/reviews.jsonl", "clean/reviews.jsonl")
```

### 두 함수의 계약

```python
import_reviews(file_path, output_path) -> list[dict]   # 원본 그대로
clean_reviews(input_path, output_path) -> list[dict]   # 정제본
```

둘 다 **파일 경로를 받아 파일을 쓰고, 리스트도 함께 돌려줍니다.**
A는 반환 리스트를 DB에 넣고, 파일은 B가 혼자 돌릴 때와 같은 자리에 그대로 남습니다.

---

## 4. 수집 — `importer.py`

### 필수 컬럼 5개

```python
REQUIRED_COLUMNS = ["rating", "review_text", "review_date",
                    "product_name", "skin_type"]
```

첫 행의 헤더에 이 다섯 개가 없으면 **읽기 전에 멈춥니다.**

```
ValueError: 필수 컬럼이 없습니다: ['skin_type']
```

정제 단계까지 갔다가 전부 버려지는 것보다, 파일을 열자마자 뭐가 없는지
알려주는 편이 낫기 때문입니다.

### `utf-8-sig` 로 읽습니다

```python
open(path, "r", encoding="utf-8-sig", newline="")
```

Excel 로 저장한 CSV 는 맨 앞에 BOM(`﻿`)이 붙습니다.
그냥 `utf-8` 로 읽으면 **첫 컬럼 이름이 `﻿rating` 이 되어** 필수 컬럼 검증이
"rating 이 없습니다" 로 떨어집니다. `utf-8-sig` 는 BOM 을 알아서 떼어냅니다.

실제로 이 프로젝트의 `cosmetics_reviews_100.csv` 에도 BOM 이 붙어 있습니다.

### 원본을 그대로 남깁니다

읽은 행을 **손대지 않고** JSONL 로 저장합니다.

```python
json.dumps(row, ensure_ascii=False)
```

`ensure_ascii=False` 라 한글이 `좋아요` 가 아니라 `좋아요` 로 남습니다.
사람이 파일을 열어 확인할 수 있어야 하니까요.

원본을 따로 두는 이유는 **정제 규칙을 바꿔 다시 돌리기 위해서**입니다.
CSV 를 지웠거나 못 구하는 상황에서도 `clean` 명령 하나로 재처리됩니다.

### 지금은 CSV 만

```python
if path.suffix.lower() != ".csv":
    raise ValueError("현재는 CSV 파일만 지원합니다.")
```

Excel(`.xlsx`)은 **A가 첫 시트를 임시 CSV 로 눕혀** 이 함수에 넘깁니다.
`chart/modules/bridge.py` 의 `xlsx_to_csv()` 입니다.
B 코드는 지금까지와 똑같이 CSV 경로만 받고, 세인님이 나중에 xlsx 를 직접 읽게 되면
A쪽 변환 함수를 지우면 됩니다.

---

## 5. 정제 — `cleaner.py`

### 버리는 기준 네 가지

한 항목이라도 걸리면 그 행은 **통째로 버립니다**(`clean_review()` 가 `None` 반환).

| 검사 | 통과 조건 | 버려지는 예 |
|---|---|---|
| 본문 | 공백 정리 후 **5자 이상** | `"좋아요"`(3자) · `"   "` |
| 별점 | `int` 변환 후 **1~5** | `"0"` · `"6"` · `"다섯"` · 빈칸 |
| 날짜 | 세 형식 중 하나로 해석 가능 | `"2025년 1월"` · 빈칸 |
| — | 위 셋을 모두 통과 | |

### 날짜는 세 형식을 받습니다

```python
["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"]
```

`2025/01/02` 든 `2025.01.02` 든 전부 **`2025-01-02` 로 통일**해서 내보냅니다.
수집처마다 표기가 다른 걸 여기서 한 번에 맞춥니다.
셋 다 아니면 `None` 이고, 그러면 그 행이 버려집니다.

### 공백 정규화

```python
re.sub(r"\s+", " ", text).strip()
```

연속 공백·줄바꿈·탭을 공백 하나로 줄이고 앞뒤를 자릅니다.
`"촉촉하고    좋아요  "` → `"촉촉하고 좋아요"`.

이게 뒤에서 값을 합니다. A의 중복 판정 해시도 같은 정규화를 하기 때문에,
줄바꿈 하나 차이로 같은 리뷰가 두 건이 되는 일이 없습니다.

### 파일 안 중복 제거

```python
(review_text, product_name, review_date)
```

세 필드가 모두 같으면 **먼저 나온 것만** 남깁니다.

이건 **이번 파일 안의 중복**만 봅니다. 이미 DB에 있는 중복은 파일이 알 수 없어서,
그건 A가 `review_hash` UNIQUE 로 막습니다.
**두 곳이 같은 세 필드를 봅니다** — 판정 기준이 갈라지지 않게 맞춰뒀습니다.

### 내보내는 모양

```python
{
    "rating":       5,                    # int
    "review_text":  "촉촉하고 좋아요",       # str
    "review_date":  "2025-01-02",         # str, YYYY-MM-DD 고정
    "product_name": "토너",                # str
    "skin_type":    "건성",                # str
}
```

**정확히 다섯 키**이고, `rating` 은 문자열이 아니라 `int` 입니다.
A의 DB 컬럼이 여기에 맞춰져 있고, 통합 테스트가 이 다섯 키를 직접 확인합니다.

### 콘솔 요약

```
========================================
          데이터 정제 결과
========================================
정제 대상: 100건
정제 완료: 99건
유효하지 않은 데이터: 0건
중복 제거: 1건
최종 clean 데이터: 99건
저장 위치: source/clean/reviews.jsonl
========================================
```

몇 건이 왜 줄었는지가 한눈에 보입니다.
100 → 99 는 **버려진 게 아니라 중복 1건이 합쳐진 것**입니다.

---

## 6. 함수 목록

### `importer.py`

| 함수 | 하는 일 | 실패하면 |
|---|---|---|
| `load_review_file(path)` | CSV 읽어 `list[dict]` | `FileNotFoundError` · `ValueError`(비 CSV) |
| `validate_columns(rows)` | 필수 5컬럼 확인 | `ValueError`(빈 파일 · 컬럼 누락) |
| `save_raw_data(rows, out)` | JSONL 저장 (폴더 자동 생성) | |
| `import_reviews(path, out)` | 위 셋을 순서대로 | 위 예외를 그대로 올림 |

### `cleaner.py`

| 함수 | 하는 일 |
|---|---|
| `normalize_text(text)` | `None`→`""`, 연속 공백 1개, 앞뒤 자름 |
| `validate_rating(rating)` | `int` 1~5 인지 `True`/`False` |
| `normalize_date(text)` | 세 형식 → `YYYY-MM-DD`, 실패 시 `None` |
| `clean_review(review)` | 한 건 정제. 못 쓰면 `None` |
| `remove_duplicates(reviews)` | 세 필드 튜플로 파일 안 중복 제거 |
| `clean_reviews(in, out)` | 전체 흐름 + 요약 출력 + 리스트 반환 |

**예외는 파일 단위에서만 던집니다.** 파일이 없거나 컬럼이 없으면 예외,
행 하나가 이상하면 조용히 건너뛰고 개수만 셉니다.
100건 중 3건이 이상하다고 나머지 97건을 못 쓰게 되면 안 되니까요.

---

## 7. 실측

`source/input/cosmetics_reviews_100.csv` 100건 기준.

```
importer  100건 읽음 → source/raw/reviews.jsonl
cleaner   100건 중 유효 100 · 중복 1 → 99건 → source/clean/reviews.jsonl
A DB      reviews 99건 저장 (신규 99 · 스킵 0)
```

정제 규칙별 동작을 직접 확인한 결과입니다.

| 입력 | 결과 |
|---|---|
| `2025-01-02` / `2025/01/02` / `2025.01.02` | 전부 `2025-01-02` 로 통일 |
| `"2025년 1월"` · 날짜 빈칸 | **버림** |
| 본문 4자 (`"좋아요오"`) | **버림** |
| 별점 `0` · `6` · `"다섯"` | **버림** |
| `"촉촉하고    좋아요  "` | `"촉촉하고 좋아요"` |
| `product_name` 빈칸 | 통과, `""` 로 저장 |

---

## 8. 알려진 제약

**정리한 사람이 A라서, 아래는 지적이 아니라 확인 요청입니다.**
지금 그대로 두어도 전체 흐름은 정상 동작합니다.

### 8.1 날짜가 없으면 리뷰 전체가 버려집니다

`review_date` 는 계약상 **`None` 이 허용되는 필드**입니다.
A의 DB 컬럼도 nullable 이고, 통계는 날짜 없는 리뷰를 추이에서만 빼고 나머지는 셉니다.

그런데 `clean_review()` 는 날짜를 해석 못 하면 그 행을 통째로 버립니다.
날짜 없는 리뷰가 섞인 파일을 받으면 **본문과 별점이 멀쩡한데도 사라집니다.**

지금 CSV 는 100건 전부 날짜가 정상이라 드러나지 않습니다.
의도한 정책이면 그대로 두시고, 아니라면 `review_date` 만 `None` 으로 두고
행은 살리는 쪽이 계약과 맞습니다.

### 8.2 `MIN_REVIEW_LENGTH = 5` 가 상수입니다

`config.json` 으로 바꿀 수 없어서, A쪽 `cleaning.min_review_length` 설정은
`add` 명령(리뷰 직접 추가)에만 적용됩니다. 같은 값(5)으로 맞춰 뒀습니다.
두 곳이 갈라지면 "CLI 로 넣을 땐 되는데 파일로 넣으면 안 되는" 리뷰가 생깁니다.

### 8.3 빈 문자열과 `None`

`product_name` · `skin_type` 이 비어 있으면 `""` 로 저장됩니다.
A의 DB 컬럼은 `NULL` 을 기대하는데 빈 문자열이 들어갑니다.

중복 해시는 `None` 과 `""` 를 같게 보므로 판정에는 영향이 없습니다.
다만 `list` · `show` 출력에서 `(미지정)` 대신 빈칸으로 나옵니다.

### 8.4 출력이 `print` 입니다

A는 `logging` 을 쓰고 `chart/logs/app.log` 에 남기는데, B의 요약표는 `print` 라
파일에 안 남고 `--quiet` 로도 안 꺼집니다.

**일부러 그대로 뒀습니다.** 요약표는 사람이 보라고 만든 것이고,
로깅 방식을 A가 B 코드에 강요할 이유가 없습니다.

---

## 9. A·C 와 맞물리는 지점

```
CSV ─[B importer]→ raw JSONL ─[A save_raw]→ SQLite raw_reviews
                       │
                       └─[B cleaner]→ clean JSONL ─[A save_clean]→ SQLite reviews
                                                          (해시 중복 판정)
```

- **A는 B를 `bridge.py` 한 곳에서만 부릅니다.** `main.py` 가 `source/` 를 직접 import 하지 않습니다
- **B는 A를 import 하지 않습니다.** 그래서 세인님이 A쪽 코드 없이 이 폴더만으로 테스트할 수 있습니다
- `source/src/` 에는 `__init__.py` 가 없습니다. A가 넣지 않기로 했고, 통합 테스트가 그걸 감시합니다

A쪽 통합 테스트가 B와의 접점에서 보는 것:

- clean 레코드가 **정확히 다섯 키**인가, `rating` 이 `int` 인가
- `skin_type` 이 DB 왕복에서 사라지지 않는가
- 같은 파일을 두 번 넣어도 행이 안 늘어나는가
- B의 dedup 키와 A의 해시 키가 같은 세 필드인가

```bash
python chart/check_contract.py --b       # B 영역만
```

2026-08-13 기준 `[OK]` 2 / 2 입니다.

---

## 10. 남은 것

- **자동 테스트가 없습니다.** A 43개 · C 25개가 있고 B는 0개입니다.
  A쪽 통합 테스트가 접점을 보고는 있지만, 정제 규칙 자체(경계값 4자/5자,
  별점 0/1/5/6, 날짜 세 형식)는 B 영역 테스트로 두는 게 맞습니다.
  위 7번 표가 그대로 테스트 케이스가 됩니다
- 8.1 날짜 정책 확인
