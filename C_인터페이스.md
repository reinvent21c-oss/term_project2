# C(민규) 인터페이스 명세

> A(영휘) 작성 · 2026-08-12 · 전체 계약은 `INTERFACE.md` 참고
> **이 문서와 코드가 다르면 코드가 기준입니다.**

C가 알아야 할 것만 추렸습니다. 함수 3개의 입출력이 전부입니다.

---

## 0. 먼저 — C가 몰라도 되는 것

| | 이유 |
|---|---|
| DB 스키마 · 테이블 구조 | C는 DB를 만지지 않습니다 |
| `review_hash` · `created_at` | A 내부 사정입니다 |
| CLI 옵션 (`--all`, `--limit` …) | A가 해석합니다 |
| 저장 함수 | 저장은 A만 합니다 |
| 리뷰를 어떻게 고르는지 | A가 골라서 넘깁니다 |

`prompt/` 폴더에서 `import sqlite3` 나 `from modules...` 를 쓸 일이 없습니다.
그래야 민규님이 **DB 없이 자기 폴더만으로 테스트**할 수 있습니다.

---

## 1. `analyzer.analyze_reviews(reviews)`

### 입력

```python
list[dict]
```

각 dict 는 **정확히 두 키**입니다.

```python
[
    {"id": 1, "review_text": "발림성이 좋아요"},
    {"id": 2, "review_text": "너무 끈적거려요"},
]
```

| 키 | 타입 | 보장 |
|---|---|---|
| `id` | `int` | 항상 존재 |
| `review_text` | `str` | 항상 존재, 빈 문자열 아님 |

**`rating` 은 넘어오지 않습니다.** 감정 분석이 별점을 보면 모델이 그대로
따라가서 `별점-감정 일치도` 지표가 항상 100% 가 되고 무의미해집니다.
A쪽에서 두 키만 추려 넘기는 것으로 구조적으로 막고 있습니다.

### 출력

```python
{
    "results": [
        {"id": 1, "sentiment": "positive", "confidence": 0.95},
        {"id": 2, "sentiment": "negative", "confidence": 0.91},
    ],
    "failed_ids": [],
}
```

| 키 | 타입 | 규칙 |
|---|---|---|
| `results[].id` | `int` | 입력받은 id 를 그대로 |
| `results[].sentiment` | `str` | `positive` / `negative` / `neutral` 셋 중 하나 |
| `results[].confidence` | `float` | `0.0` ~ `1.0` |
| `failed_ids` | `list[int]` | 분석하지 못한 id |

### 지켜야 할 것 세 가지

**① 넣은 id 는 반드시 한쪽에 나타납니다.**
`results` 아니면 `failed_ids` 중 어딘가에는 있어야 합니다.
둘 다에 없으면 그 리뷰는 조용히 사라진 것이고, 아무도 모릅니다.
자가 점검이 이걸 확인합니다.

**② 한 건이 실패해도 예외를 던지지 않습니다.**
그 id 만 `failed_ids` 에 넣고 나머지는 계속 처리합니다.
100건 돌리다 50번째에서 API 가 흔들렸다고 앞의 49건을 버리면 안 됩니다.

**③ id 가 없는 dict 는 예외를 던집니다.**
이건 '이 리뷰의 실패' 가 아니라 부르는 쪽(A)의 버그입니다.
조용히 넘기면 어느 리뷰가 빠졌는지 알 수 없게 됩니다.

```python
if not isinstance(review, dict) or "id" not in review:
    raise ValueError(...)          # 호출자 버그 → 예외

if not review_text.strip():
    failed_ids.append(review_id)   # 이 한 건의 실패 → failed_ids
    continue
```

### `analyze_review(review_text)` 는 그대로

단건 함수는 문자열을 받고 `{"sentiment", "confidence"}` 를 돌려줍니다.
빠르게 확인할 때 쓰기 좋아서 형태를 유지했습니다.

---

## 2. `extractor.extract_insights(reviews)`

### 입력

```python
list[str]        # 본문만. id 가 필요 없습니다 — 종합 요약이라서
```

건수는 A가 `config.ai.extract_max_reviews`(기본 60)로 잘라서 넘깁니다.
99건을 통째로 프롬프트에 넣으면 요약이 뭉개집니다.

### 출력

```python
{
    "positive_keywords": ["보습력", "빠른 흡수"],   # list[str]
    "negative_keywords": ["무거운 사용감"],          # list[str]
    "summary": "보습과 흡수력 평가는 긍정적이지만…",   # str
    "improvements": ["가벼운 제형 검토"],            # list[str]
}
```

**추출에 실패하면 `None` 을 돌려줍니다.** 예외를 던지지 않습니다.

인사이트는 리포트의 '있으면 좋은' 부분이지 필수가 아닙니다.
이것 때문에 `dashboard` 가 멈추면 통계와 차트까지 못 보게 됩니다.

입력 자체가 잘못된 경우(리스트가 아님, 빈 리스트)만 예외를 던집니다.
그건 부르는 쪽의 버그입니다.

---

## 3. `reporter.generate_markdown_report(stats, insights, chart_paths, output_path)`

```python
generate_markdown_report(stats=None, insights=None,
                         chart_paths=None, output_path=None) -> str
```

Markdown 문자열을 돌려주고, `output_path` 가 있으면 파일로도 저장합니다.

- `insights` 가 `None` 일 수 있습니다 → `insights = insights or {}` 로 받습니다.
  `extract` 를 안 돌리고 `dashboard` 만 실행하는 경로가 있습니다.
- `chart_paths` 는 **리스트와 dict 둘 다** 옵니다 → dict 면 `.values()` 로 폅니다.

### `stats` — 칸이 5개, C가 읽는 건 3개

```python
{
    "meta":       {...},   # 생성 시각 · 필터. 헤더에 쓰면 좋습니다
    "summary":    {...},   # ← C
    "chart_data": {...},   # ← 차트 전용. 읽지 않습니다
    "quality":    {...},   # ← C
    "top_n":      {...},   # ← C
}
```

**`chart_data` 는 읽지 않습니다.** matplotlib 에 넣을 배열 뭉치라
리포트에 펼치면 숫자 수백 개가 쏟아집니다.

#### `summary` — 9개 키, 전부 항상 존재

```python
{
    "total":            99,       # int
    "analyzed":         99,       # int
    "unanalyzed":       0,        # int
    "analysis_rate":    1.0,      # float  ← '전체' 기준
    "avg_rating":       3.6465,   # float
    "avg_confidence":   0.6656,   # float
    "sentiment_counts": {"positive": 46, "neutral": 40, "negative": 13},
    "sentiment_ratios": {"positive": 0.4646, ...},   # float ← '분석된 것' 기준
    "rating_counts":    {1: 8, 2: 12, 3: 20, 4: 26, 5: 33},   # 키는 int
}
```

**분모가 다릅니다.** `analysis_rate` 는 전체 기준,
`sentiment_ratios` 는 분석된 것 기준입니다. 섞으면 숫자가 안 맞습니다.

`sentiment_counts` 의 세 키와 `rating_counts` 의 다섯 키는
**값이 0이어도 항상 존재합니다.** `.get()` 으로 방어하지 않으셔도 됩니다.

`rating_counts` 의 키는 `int` 입니다. JSON 을 거쳐 오면 문자열이 될 수 있어
`rating_counts.get(star, rating_counts.get(str(star), 0))` 처럼 둘 다 받으면
안전합니다.

#### `quality` — 3개 키

```python
{
    "rating_sentiment_agreement": 0.6162,   # float, 별점-감정 일치도
    "data_completeness":          1.0,      # float, 선택 필드까지 채워진 비율
    "avg_review_length":          44.404,   # float, 글자 수
}
```

#### `top_n` — 3개 키

```python
{
    "worst_reviews": [               # list[dict], 별점 낮은 순 5건
        {"id": 23, "product_name": "수분 장벽 크림",
         "review_text": "몇 번 사용하니 좁쌀처럼…", "rating": 1,
         "review_date": "2025-03-14", "skin_type": "건성",
         "sentiment": "negative", "confidence": 0.79},
    ],
    "product_counts":   [("수분 장벽 크림", 34), ("데일리 선크림", 33)],
    "skin_type_counts": [("건성", 34), ("지성", 33)],
}
```

`product_counts` 와 `skin_type_counts` 는 **`(이름, 건수)` 튜플 리스트**입니다.
dict 가 아니라 정렬 순서가 보장됩니다.

`worst_reviews` 항목은 8개 키입니다. `review_hash` 나 `created_at` 같은
A 내부 필드는 넣지 않습니다.

### `chart_paths`

```python
{
    "kpi_summary":            "kpi_summary.png",
    "sentiment_distribution": "sentiment_distribution.png",
    "sentiment_trend":        "sentiment_trend.png",
    "rating_distribution":    "rating_distribution.png",
    "rating_sentiment":       "rating_sentiment.png",
    "product_sentiment":      "product_sentiment.png",
    "skin_type_sentiment":    "skin_type_sentiment.png",
}
```

**리포트 파일 기준 상대 경로**입니다. 같은 폴더(`chart/output/`)에 있습니다.
절대 경로를 쓰면 만든 사람 PC 에서만 이미지가 보이고 GitHub 에서는 깨집니다.

**[2026-08-12] 3장에서 7장으로 늘었습니다.** C쪽 코드는 고칠 게 없습니다 —
지금처럼 `.values()` 로 순회하면 그대로 7장이 실립니다.
넣은 순서가 곧 `차트 1 … 차트 7` 순서이고, 요약 타일(`kpi_summary`)이
맨 앞에 오도록 A가 순서를 맞춰 보냅니다.

데이터가 없어 못 그린 장은 아예 오지 않습니다. 개수를 세거나
특정 이름이 있다고 가정하지 마시고 있는 것만 순회해 주세요.

차트가 없으면 빈 dict 또는 `None` 이 옵니다 → 시각화 섹션을 생략합니다.

---

## 4. 자가 점검

```bash
python chart/check_contract.py --c     # C 영역만. API 를 부르지 않습니다
python main.py dashboard               # 전체 흐름 확인. 키 없이도 됩니다
```

**[2026-08-12] `--mock` 과 `modules/mock_ai.py` 를 없앴습니다.**
연결이 끝났는데 대역이 남아 있으면 "지금 도는 게 진짜 분석인가" 를
실행할 때마다 플래그로 확인해야 하고, 규칙 기반 결과가 DB에 섞여 들어가도
`model` 컬럼을 열어보기 전까지는 아무도 모릅니다.

이제 `analyze` 와 `extract` 는 항상 실제 Gemini 를 부릅니다.
키가 없으면 시작 전에 멈춥니다 (99번 실패하고 나서가 아니라).

`--c` 점검은 여전히 키 없이 돕니다. C 코드가 Gemini 를 부르기 **전에**
입력을 검사하기 때문입니다. 그 순서 자체가 계약입니다 —
빈 본문 한 건 때문에 요금이 나가면 안 되니까요.

점검이 확인하는 것

- `analyze_reviews([{"review_text": ...}])` → id 가 없으면 `ValueError`
- `analyze_reviews([{"id": 1, "review_text": "   "}])` → `failed_ids: [1]`
- `validate_analysis_result()` 가 잘못된 값을 거르는지
- `validate_insight_result()` 가 **계약상 정상인 값을 거부하지 않는지**
- `generate_markdown_report()` 가 5칸 stats 를 받아 파일을 쓰는지

### 지금 [FAIL] 로 잡히는 것 하나

```
[FAIL] extractor 공개 함수
         - 계약상 정상인 인사이트를 거부했습니다:
           improvements는 2개 이상이어야 합니다.
```

`validate_insight_result()` 가 `improvements` 를 2개 이상으로 요구하는데,
위 2번 계약에는 개수 하한이 없습니다.

이게 왜 문제가 되냐면, 모델이 개선 제안을 1개만 준 날
검증기가 예외를 던지고 → 재시도 후에도 같으면 `extract_insights()` 가
`None` 을 돌려주고 → `extract` 명령이 통째로 실패합니다.
키워드와 요약은 멀쩡히 나왔는데 제안 개수 하나 때문에 전부 버려집니다.

둘 중 하나로 맞춰 주세요.

1. 프롬프트에 이미 "2개 이상" 을 넣어두셨으니 계약에도 그 조건을 적는다
2. 검증기에서 개수 조건을 빼고, 부족하면 부족한 대로 돌려준다

A쪽은 어느 쪽이든 그대로 받습니다. `validate_insights()` 는 타입만 봅니다.

---

## 5. A가 검증하는 항목

`modules/interfaces.py` 가 C의 결과를 받자마자 확인합니다.
어긋나면 **DB 에 값이 들어가기 전에** 멈춥니다.

- `results` / `failed_ids` 키 존재
- 각 `id` 가 `int` 이고 **중복이 없는가**
- 성공과 실패에 **같은 id 가 들어 있지 않은가**
- `sentiment` 가 세 값 중 하나인가
- `confidence` 가 `0.0` ~ `1.0` 숫자인가

민규님을 못 믿어서가 아니라, 나중에 코드를 고쳤을 때
조용히 틀린 값이 쌓이는 걸 막으려는 장치입니다.

---

## 6. 리포트에 부탁드리는 것 3가지

리포트 형식은 **전부 민규님이 정합니다.** A는 값만 넘기고 마크다운에는
손대지 않습니다. 아래 셋은 A가 새로 보내겠다는 게 아니라
**지금도 보내고 있는데 리포트가 안 쓰는 값**입니다.
A쪽에서 더 넘길 건 없고, 쓸지 말지만 정해주시면 됩니다.

`python chart/check_contract.py --c` 를 돌리면 `[TODO]` 세 줄로 나옵니다.
고치면 `[OK]` 로 바뀝니다.
**`[FAIL]` 이 아니라 `[TODO]` 입니다** — 약속 위반이 아니니 안 고쳐도
수요일 전달 조건은 충족합니다.

---

### ① `chart_paths` 의 키를 쓰기

지금 `reporter.py` 가 값만 뽑습니다.

```python
chart_paths = list(chart_paths.values())    # 키를 버립니다
```

A는 이렇게 보냅니다.

```python
{
    "kpi_summary":            "kpi_summary.png",
    "sentiment_distribution": "sentiment_distribution.png",
    ...
}
```

그래서 리포트에는 이렇게 나옵니다.

```markdown
![차트 1](kpi_summary.png)
![차트 2](sentiment_distribution.png)
```

두 가지가 걸립니다. 리포트만 봐서는 **차트 6이 뭔지 알 수 없고**,
데이터가 없어 한 장이 빠지면(날짜가 하나도 없으면 추이가 빠집니다)
**그 뒤 번호가 전부 밀립니다.** 어제 리포트의 차트 5와 오늘 리포트의
차트 5가 다른 그림이 됩니다.

이렇게 되면 좋겠습니다.

```markdown
### 리뷰 분석 요약
![리뷰 분석 요약](kpi_summary.png)

### 감정 분포
![감정 분포](sentiment_distribution.png)
```

제목 표는 `reporter.py` 안에 두시면 됩니다. 표현은 C 영역이라
A가 한글 제목을 보내지 않습니다. 참고용으로만 적습니다.

| 키 | 제안 제목 |
|---|---|
| `kpi_summary` | 리뷰 분석 요약 |
| `sentiment_distribution` | 감정 분포 |
| `sentiment_trend` | 기간별 감정 추이 |
| `rating_distribution` | 별점 분포 |
| `rating_sentiment` | 별점별 감정 구성 |
| `product_sentiment` | 제품별 감정 구성 |
| `skin_type_sentiment` | 피부타입별 감정 구성 |

**모르는 키가 오면 키 이름을 그대로 쓰시면 됩니다.** A가 나중에 차트를
더 늘려도 리포트가 안 깨집니다.

넣은 순서는 이미 읽기 좋은 순서(요약이 맨 앞)로 A가 맞춰 보냅니다.
순서는 그대로 두시면 됩니다.

---

### ② `stats["meta"]` 를 헤더에 쓰기

`meta` 를 한 번도 읽지 않고 계십니다. 안에 이게 들어 있습니다.

```python
"meta": {
    "schema_version": 3,
    "generated_at": "2026-08-12 09:12:18",
    "filters": {"product": "데일리 선크림", "skin_type": None,
                "date_from": None, "date_to": None},
}
```

지금은 리포트에 **언제 만든 건지, 어떤 범위로 뽑은 건지가 없습니다.**
`dashboard --product "데일리 선크림"` 으로 뽑은 리포트와 전체 리포트가
파일 안에서 구분되지 않습니다. 파일명의 타임스탬프만 다릅니다.

제목 아래 한 줄이면 됩니다.

```markdown
# 고객 리뷰 분석 리포트

생성 2026-08-12 09:12:18 · 범위 제품=데일리 선크림
```

`filters` 는 네 키가 항상 있고 값은 `None` 일 수 있습니다.
`None` 이 아닌 것만 골라 이어붙이고, 전부 `None` 이면 "전체" 로 쓰시면 됩니다.

---

### ③ 선택 필드가 `None` 인 경우

`top_n["worst_reviews"]` 의 `product_name` / `review_date` / `skin_type` 은
**계약상 `None` 일 수 있습니다.** (`add` 명령으로 직접 넣은 리뷰가 그렇습니다)

지금 f-string 에 그대로 들어가서 이렇게 찍힙니다.

```markdown
- [1점] None / negative / 몇 번 사용하니 좁쌀처럼…
```

`review.get("product_name") or "(제품 미지정)"` 정도면 됩니다.

같은 김에, `worst_reviews` 항목에는 지금 안 쓰시는 키가 네 개 더 있습니다.
`id` · `review_date` · `skin_type` · `confidence` 입니다. 필요하면 쓰세요.

---

### A가 넘기는 것 (변경 없음)

```python
generate_markdown_report(stats, insights, chart_paths, output_path)
```

| 인자 | 지금 상태 |
|---|---|
| `stats` | 5칸 전부 보냅니다. `chart_data` 는 읽지 마세요 |
| `insights` | `extract` 를 안 돌렸으면 `None` 입니다 |
| `chart_paths` | `{이름: 상대경로}` dict. 없으면 빈 dict |
| `output_path` | A가 정한 `chart/output/report_<시각>.md` |

---

## 한 장 요약

```
analyze_reviews([{id, review_text}])
    -> {results: [{id, sentiment, confidence}], failed_ids: [int]}

extract_insights([str])
    -> {positive_keywords, negative_keywords, summary, improvements} | None

generate_markdown_report(stats, insights, chart_paths, output_path)
    -> Markdown str
       stats 는 summary / quality / top_n 만 읽는다
```

- id 는 받은 대로 돌려준다
- 한 건 실패는 `failed_ids`, 호출자 버그는 예외
- rating 은 넘어오지 않는다
- DB · CLI 는 모른다
