# A2-C 공통 인터페이스 (v3 · A·C 합의 반영본)

> A(영휘) 작성 · 8/10 회의 안건 4번 "공통 인터페이스 합의" 의 통합 후 개정판
> 코드 원본: `chart/modules/adapters.py`, `chart/modules/interfaces.py`
> **이 문서와 코드가 다르면 코드가 기준입니다.**

v1 은 "B/C가 이렇게 만들어 주세요" 였습니다.
v2 는 **B/C가 만든 것을 그대로 두고 A가 어댑터로 흡수한 결과**였습니다.
v3 은 **A와 C가 형태를 맞춰 어댑터를 걷어낸 결과**입니다.

B(`source/`)는 여전히 한 줄도 수정하지 않았습니다.
C(`prompt/`)는 A와 합의해 세 군데를 고쳤고, 바뀐 자리마다
`[A와 합의 · 변경점]` 주석이 달려 있습니다.

---

## 0. 한 장 요약

| 항목 | v1 합의 | 실제 | v2 결론 |
|---|---|---|---|
| clean → SQLite 저장 | A 담당 | 동일 | **유지.** A만 저장한다 |
| 리뷰 ID | AUTOINCREMENT PK + review_hash | 동일 | **유지** |
| review_hash 생성 | `cleaner.make_review_hash()` (B) | B에 없음 | **A가 담당** (`modules/database.py`) |
| clean 필드 | 4개 | **5개 (skin_type 추가)** | **A가 DB 컬럼 추가해 보존** |
| C의 analyze 입출력 | dict 리스트 → results/failed_ids | 문자열 리스트 → 결과 리스트 | **C가 v1 형태로 맞춤** |
| 배치 묶기 | C 담당 | 실제로는 1건씩 호출 | **설정 삭제** (하는 일이 없었음) |
| 부분 실패 | 예외 금지, failed_ids | C가 예외를 던짐 | **C가 failed_ids 로 반환** |
| 어댑터 계층 | — | 251줄 | **53줄로 축소** |
| stats | dict 하나, 칸 분리 | 동일 | **유지** + top_n 확장 |
| 차트 / export | B 담당 | 미착수 | **A로 이관 · 구현 완료** |
| chart_paths | dict {이름: 경로} | C는 리스트로 순회 | **A가 dict→상대경로 리스트 변환** |

### 2026-08-12 개정 (v4)

| 항목 | v3 | v4 | 이유 |
|---|---|---|---|
| `--mock` · `modules/mock_ai.py` | 있음 | **삭제** | C의 Gemini 연결이 끝났습니다. 대역이 남아 있으면 "지금 도는 게 진짜인가" 를 매번 확인해야 하고, 규칙 기반 결과가 DB에 섞여도 `model` 컬럼을 열기 전엔 모릅니다 |
| `ai.use_mock` · `ai.batch_size` | config 에 있음 | **삭제** | 전자는 위와 같고, 후자는 C가 직접 배치로 부르게 되어 아무도 읽지 않습니다 |
| `chart_data` | 3칸 | **7칸** | 대시보드. 요약 타일 · 별점 분포 · 제품별 / 피부타입별 감정 구성 추가 |
| `schema_version` | 2 | **3** | 위 확장 |
| `modules/hashing.py` | 별도 파일 | **database.py 로 합침** | 부르는 곳이 저장 계층 한 군데뿐입니다 |
| `modules/paths.py` | 로더 + 상수 + 죽은 코드 | **죽은 코드 제거** | `resolve_path` · `DATA_INPUT_DIR` · 파일명 후보 목록(`analyzer (1).py`)은 아무도 안 씁니다. 구조가 확정돼서 후보 목록은 특히 의미가 없어졌습니다 |
| `interfaces.py` 문서용 코드 | 있음 | **삭제** | `REVIEW_RECORD_EXAMPLE` · `NULLABLE_KEYS` · `validate_review_record` · `report()` 전부 호출되지 않았습니다 |
| `database.save_sentiment_result`(단수) | 있음 | **삭제** | `save_analysis` 를 그대로 부르는 껍데기였고 아무도 안 불렀습니다 |
| 리포트 | A가 값만 넘김 | **동일 · 요청 3건 추가** | 형식은 전부 C가 정합니다. A가 이미 넘기는데 안 쓰는 값 3가지를 `[TODO]` 로 남겼습니다 (`C_인터페이스.md` 6번) |

### 2026-08-13 개정 (v5) — 평가 반영

| 항목 | v4 | v5 | 이유 |
|---|---|---|---|
| `import` 입력 형식 | CSV 만 | **CSV · Excel** | A가 첫 시트를 임시 CSV 로 눕혀 B에게 넘깁니다. B 파일은 그대로입니다 |
| `stats` 칸 | 5개 | **6개 (`alerts` 추가)** | 숫자만 내놓고 "괜찮은가" 를 아무도 말하지 않았습니다 |
| `top_n` | 3키 | **4키 (`keyword_impact` 추가)** | C의 부정 키워드를 A가 계량해 개선 우선순위를 매깁니다 |
| `config` | — | **`alerts` 섹션** | 임계치를 코드가 아니라 설정에 둡니다 |
| `schema_version` | 3 | **4** | 위 확장 |

**C 영역 계약은 이번에도 바뀌지 않았습니다.** `summary` / `quality` 세 함수의
입출력이 그대로이고, `top_n` 은 키가 늘기만 했습니다.

### 2026-08-14 개정 (v6) — 평가 재반영

| 항목 | v5 | v6 | 이유 |
|---|---|---|---|
| CLI | 11개 | **12개 (`review` 추가)** | AI 정확도를 사람 라벨로 재는 수단이 없었습니다 |
| 테이블 | 4개 | **5개 (`human_labels` 추가)** | 검수 라벨과 **검수 시점의 AI 판정 스냅샷**을 함께 보관합니다 |
| 경고 | 콘솔만 | **콘솔 + 로그 파일** | 터미널을 닫으면 사라져서 회차별 추이를 볼 수 없었습니다 |

**C 영역 계약은 그대로입니다.** `review` 는 A가 이미 저장해 둔 `analyses` 를
사람 라벨과 비교할 뿐이고, C의 세 함수를 부르지 않습니다.

다만 **프롬프트를 고칠 때 `analyses.model` 에 버전을 함께 적어주시면**
(`gemini-3.6-flash@v2`) `review score` 가 버전별 일치율을 갈라 보여줍니다.
그게 A/B 비교의 유일한 축입니다. 지금은 모델명만 들어가 있어
버전을 나눌 수 없습니다.

### `human_labels` — 검수 라벨 (v6 신설)

```python
{
    "review_id": 23, "batch": "20260814_081402", "reviewer": "영휘",
    "sentiment": "negative",              # 사람이 매긴 값
    "note": "완곡한 불만",
    "ai_sentiment": "neutral",            # 검수 시점의 AI 판정 (스냅샷)
    "ai_confidence": 0.62,
    "ai_model": "gemini-3.6-flash@v1",
}
```

`(review_id, batch, reviewer)` UNIQUE. 다시 매기면 덮어씁니다.

AI 판정을 스냅샷으로 두는 이유는 `analyses` 가 `review_id` UNIQUE 라
재분석하면 덮어써지기 때문입니다. 스냅샷이 없으면 프롬프트를 바꾼 뒤
"그때 무엇과 비교했는지" 가 사라져 A/B 비교가 성립하지 않습니다.

**C(민규) 영역 계약은 하나도 바뀌지 않았습니다.** `summary` / `quality` /
`top_n` 세 칸과 세 함수의 입출력이 v3 그대로입니다.

---

## 1. 폴더 소유권

```
team7/
├── main.py      ← 루트 런처
├── source/      ← B(세인) 전용. A는 읽기만 한다
│   ├── src/importer.py, src/cleaner.py
│   ├── input/, raw/, clean/
├── prompt/      ← C(민규) 전용. A와 합의한 3군데만 수정됨
│   ├── analyzer.py, extractor.py, reporter.py, README.md
└── chart/       ← A(영휘) 전용
    ├── main.py, config.json, check_contract.py
    └── modules/
```

**A는 `source/` 와 `prompt/` 에 파일을 만들지 않습니다.** `__init__.py` 하나만
넣어도 그 폴더는 더 이상 한 사람의 것이 아니게 되고 머지 충돌이 시작됩니다.
그래서 A는 패키지 import 대신 파일 경로로 모듈을 읽어옵니다
(`chart/modules/paths.py`). 이 규칙은 테스트로 강제합니다
(`test_a_did_not_add_files_to_b_and_c_folders`).

브랜치: `feature/a-source-integration`, `feature/b-import-clean`,
`feature/c-ai-report` → `main` 머지는 A만 수행합니다.

---

## 2. 리뷰 ID와 review_hash

```sql
id          INTEGER PRIMARY KEY AUTOINCREMENT   -- 참조용 식별자
review_hash TEXT NOT NULL UNIQUE                -- 중복 판정
```

CSV 에 id 를 넣으면 재실행할 때마다 번호가 바뀌어
`analyze --id 5` 가 어제와 다른 리뷰를 가리킵니다.

`review_hash` 는 `product_name + review_text + review_date` 를
정규화(연속 공백 정리·소문자화)한 뒤 SHA-256 을 겁니다.
`review_text` 단독으로 잡으면 **서로 다른 사람이 다른 제품에 남긴 "좋아요"가
전부 한 건으로 뭉개집니다.**

**v1 대비 변경.** v1 은 `cleaner.make_review_hash()` 를 B가 제공한다고 적었지만
B의 `cleaner.py` 에는 그 함수가 없습니다. B는 `(review_text, product_name,
review_date)` 튜플로 **파일 안 중복만** 제거합니다.
그래서 해시 계산은 A의 `modules/hashing.py` 가 담당합니다.
**B가 보는 세 필드와 A가 해시에 거는 세 필드가 같아** 판정 기준은 하나입니다.

역할 분담이 이렇게 갈리는 이유는 그대로입니다.
B의 cleaner 는 '이번 파일 안의 중복' 만 볼 수 있고,
'이미 DB에 있는 중복' 은 DB만 압니다.

---

## 3. B → A 연결

### 실제 시그니처 (파일 기반)

```python
# source/src/importer.py
import_reviews(file_path, output_path) -> list[dict]   # CSV → raw JSONL

# source/src/cleaner.py
clean_reviews(input_path, output_path) -> list[dict]   # raw JSONL → clean JSONL
```

A는 출력 경로를 만들어 주고 결과 리스트만 받아 DB에 넣습니다.
**B가 만든 `source/raw/reviews.jsonl` 과 `source/clean/reviews.jsonl` 은 그대로
남습니다.** B가 혼자 돌릴 때와 산출물 위치가 달라지지 않습니다.

### clean 레코드 (5개 필드 — 확정)

```python
{
    "rating": 4,                       # int  (B가 int 로 변환해 줌)
    "review_text": "발림성이 부드럽고…",  # str
    "review_date": "2025-12-11",       # str  YYYY-MM-DD 정규화됨
    "product_name": "데일리 선크림",     # str
    "skin_type": "지성",                # str  ← v1 에 없던 필드
}
```

`skin_type` 때문에 A의 `reviews` 테이블에 컬럼을 하나 늘렸습니다.
컬럼을 안 만들면 B가 정제한 정보를 A가 조용히 버리게 됩니다.
`stats` 의 `top_n.skin_type_counts` 와 `list --skin-type` 에서 씁니다.

### 차트·export 는 A로 이관되었습니다

v1 에서 B 영역이던 `visualizer` / `exporter` 를 **A가 가져갔습니다.**
파일 위치는 `chart/modules/visualizer.py`, `chart/modules/exporter.py` 입니다.

세인님이 `source/src/` 에 같은 이름의 파일을 만들 필요가 없습니다.
B 영역은 **import / clean 두 가지로 확정**됩니다.

호출은 여전히 `adapters.py` 한 곳을 거칩니다. 나중에 다시 B로 넘기더라도
`main.py` 는 그대로입니다.

---

## 4. C → A 연결

### 실제 시그니처

```python
# prompt/analyzer.py
analyze_review(review_text: str)   -> {"sentiment", "confidence"}
analyze_reviews(review_texts: list[str]) -> [{"sentiment", "confidence"}, ...]

# prompt/extractor.py
extract_insights(reviews: list[str])
    -> {"positive_keywords", "negative_keywords", "summary", "improvements"}

# prompt/reporter.py
generate_markdown_report(stats, insights, chart_paths=None, output_path=None)
    -> Markdown 문자열
```

### 감정 분석 — id 를 C가 들고 다닌다

```python
# A -> C
[{"id": 1, "review_text": "발림성이 좋아요"},
 {"id": 2, "review_text": "너무 끈적거려요"}]

# C -> A
{"results": [{"id": 1, "sentiment": "positive", "confidence": 0.95},
             {"id": 2, "sentiment": "negative", "confidence": 0.91}],
 "failed_ids": []}
```

**넣은 id 는 `results` 아니면 `failed_ids` 중 반드시 한쪽에 나타납니다.**
조용히 사라지면 안 됩니다. 자가 점검이 이걸 확인합니다.

**왜 문자열 리스트가 아니라 id 를 함께 넘기나**

v2 까지는 A가 본문만 넘기고 `zip` 으로 id 를 다시 붙였습니다.
그런데 C가 한 건을 빠뜨리면 그 뒤가 전부 한 칸씩 밀립니다.
3번 리뷰의 감정이 4번에 붙는데 **에러가 나지 않습니다.**
정상 종료하고 DB 에 조용히 틀린 값이 들어갑니다.
id 를 들고 다니면 이 부류의 버그가 성립하지 않습니다.

**입력에 rating 을 넣지 않는다**

감정 분석이 별점을 보면 모델이 그대로 따라가서
`별점-감정 일치도` 가 항상 100% 가 되고 지표가 순환논리로 죽습니다.
프롬프트 규칙에 기대는 대신 **데이터를 아예 주지 않습니다.**

```python
# main.py cmd_analyze — 이 한 줄이 그 경계다
payload = [
    {"id": review["id"], "review_text": review["review_text"]}
    for review in reviews
]
```

`get_unanalyzed_reviews()` 는 rating 포함 13개 키를 돌려줍니다.
그대로 넘기면 위 보장이 깨집니다.

**A가 하는 일** — 대상 조회, 두 키로 추리기, `language` 채우기,
결과 저장, 종료 코드 결정(전부 성공 `0`, 일부 실패 `2`).

### 인사이트 추출 — 실패는 None

```python
extract_insights(reviews: list[str]) -> insights | None
```

인사이트는 리포트의 '있으면 좋은' 부분이지 필수가 아닙니다.
이것 때문에 dashboard 가 멈추면 통계와 차트까지 못 봅니다.
입력 자체가 잘못된 경우(리스트가 아님, 빈 리스트)만 예외를 던집니다.

### 리포트 — stats 를 C가 직접 렌더

```python
generate_markdown_report(stats, insights=None, chart_paths=None, output_path=None)
```

A의 5칸 `stats` 를 그대로 받아 C가 `summary` / `quality` / `top_n` 을
읽어 Markdown 으로 만듭니다. `chart_data` 는 읽지 않습니다.

v2 까지는 A가 한글 평면 dict 로 접어서 넘겼는데,
그러면 **리포트에 뭐가 들어갈지를 A가 정하게 됩니다.**
리포트 형식은 리포트를 만드는 쪽이 정하는 게 맞습니다.

- `insights` 가 `None` 이면 C가 안내 문구로 대체합니다.
- `chart_paths` 는 리스트와 `{이름: 경로}` dict 둘 다 받습니다.
- 경로는 A가 리포트 파일 기준 상대 경로로 바꿔 넘깁니다.
  절대 경로면 만든 사람 PC 에서만 이미지가 보입니다.

---

## 5. stats — dict 하나, 칸은 용도별로

**집계는 `chart/modules/stats.py` 에서만 합니다.**
B가 차트용으로 한 번 세고 C가 리포트용으로 또 세면, 같은 데이터인데
차트는 89건 리포트는 90건이 되는 일이 반드시 생깁니다.

```python
calculate_stats(filters, keywords=None, thresholds=None) -> {
    "meta":       {"schema_version": 4, "generated_at": ..., "filters": ...},
    "summary":    {...},   # ← C만 사용
    "chart_data": {...},   # ← 차트만 사용
    "quality":    {...},   # ← C만 사용 (명세 4.8 품질 지표)
    "top_n":      {...},   # ← C만 사용 (명세 4.8 TOP N + 개선 우선순위)
    "alerts":     [...],   # ← A의 CLI 출력. C가 리포트에 실어도 됩니다
}
```

**규칙: 서로의 칸을 참조하지 않습니다.**

`chart_data` 는 곧바로 matplotlib 에 넣을 수 있는 형태입니다.
**차트 쪽에서 추가 집계를 하지 않습니다.** 칸 하나가 차트 한 장입니다.
칸 이름은 `modules/visualizer.py` 의 `CHART_ORDER` 와 같아야 하고,
그 순서가 곧 리포트의 `차트 1, 차트 2 …` 순서입니다.

```python
"chart_data": {
    "kpi_summary":          {...},   # 요약 타일 6칸
    "sentiment_distribution": {...},
    "sentiment_trend":      {...},
    "rating_distribution":  {...},
    "rating_sentiment":     {...},
    "product_sentiment":    {...},
    "skin_type_sentiment":  {...},
}
```

```python
"sentiment_trend": {
    "granularity": "week",              # 데이터 밀도 따라 A가 자동 결정
    "labels": ["2025-05-05", ...],
    "series": {"positive": [...], "neutral": [...], "negative": [...]},
    "negative_ratio": [0.21, ...],      # labels 와 길이 동일
}

"product_sentiment": {                  # skin_type_sentiment 도 같은 모양
    "labels": ["수분 장벽 크림", ...],    # 건수 많은 순, top_n 개
    "series": {"positive": [...], "neutral": [...], "negative": [...]},
    "totals": [34, ...],                # labels 와 길이 동일
}
```

`kpi_summary` 는 **새로 세는 값이 하나도 없습니다.** `summary` 와 `quality`
에서 그대로 옮겨온 숫자입니다. 여기서 한 번이라도 다시 세면 타일의
'평균 별점 3.65' 와 리포트의 '평균 별점 3.6' 이 갈라지고,
둘 중 뭐가 맞는지 확인할 방법이 없어집니다.
`interfaces.validate_stats()` 가 `kpi_summary.total == summary.total` 을
직접 확인합니다.

**비율의 분모가 다릅니다.** `analysis_rate` 는 전체 기준,
`sentiment_ratios` 는 분석된 것 기준입니다. 섞으면 숫자가 안 맞습니다.

`schema_version` 은 형태가 바뀌면 올립니다.
**skin_type 반영으로 1 → 2, 대시보드 chart_data 확장으로 2 → 3,
alerts / keyword_impact 추가로 3 → 4.**

### `alerts` — 임계치 판정 결과 (v4 신설)

```python
[
    {
        "level": "critical" | "warning" | "info",
        "code": "negative_spike",
        "title": "부정 비율이 직전 월 대비 급증했습니다",
        "scope": "2025-05",
        "value": 0.14, "threshold": 0.10,
        "detail": "2025-04 0% → 2025-05 14% (+14%p, 표본 14건)",
        "hypotheses": ["제품 '수분 장벽 크림' 에 몰려 있습니다 …"],
        "next_metrics": ["해당 구간의 생산 로트·유통 경로", …],
    },
]
```

경고가 없으면 **빈 리스트**입니다. 임계치는 `config.json` 의 `alerts` 섹션,
판정 로직과 대응 절차는 `chart/README.md` 4.10 절에 있습니다.

`hypotheses` 는 **확인해볼 후보**이지 원인이 아닙니다. 리포트에 실을 때도
단정하는 문장으로 바꾸지 말아 주세요.

### `top_n["keyword_impact"]` — 개선 우선순위 (v4 신설)

```python
[
    {"keyword": "유분 증가", "matched": True, "matched_terms": ["유분"],
     "reviews": 8, "share": 0.081, "avg_rating": 2.75,
     "rating_gap": -0.90, "negative_ratio": 0.25, "priority": 0.55},
    {"keyword": "트러블 발생", "matched": False, "matched_terms": ["트러"],
     "reviews": 0, "share": 0.0, "avg_rating": 0.0,
     "rating_gap": 0.0, "negative_ratio": 0.0, "priority": 0.0},
]
```

C가 뽑은 `negative_keywords` 를 A가 본문으로 되짚어 계량한 것입니다.
`priority` 내림차순으로 정렬되어 있습니다.

`matched: False` 는 **모델이 본문에 없는 표현으로 요약했다**는 뜻입니다.
버리지 않고 남기는 이유는 그것 자체가 요약 품질 신호이기 때문입니다.
리포트에 실을 때는 순위에서 빼고 따로 표시해 주세요.

`extract` 를 안 돌렸으면 **빈 리스트**입니다.

---

## 6. dashboard 연결 흐름

```
A: stats       = calculate_stats(filters)
A: chart_paths = generate_charts(stats["chart_data"], output_dir, config)
C: report      = generate_markdown_report(stats, insights, chart_paths, path)
A: main.py dashboard 명령에서 전체 연결
```

차트도 A 소유지만 호출 창구는 `adapters.py` 로 유지합니다.
`main.py` 는 `source/` 나 `prompt/` 를 직접 import 하지 않습니다.

`chart_paths` 는 `{이름: 경로}` dict 입니다. 리스트로 주면 순서가 곧 의미가 되어
한 장이 빠지면 전부 밀립니다. 이름을 붙이면 리포트가 원하는 차트를 골라 씁니다.

차트는 7장이고, **데이터가 없어 못 그린 장은 dict 에 들어가지 않습니다.**
날짜가 하나도 없으면 추이가, 제품명이 하나도 없으면 제품별 구성이 빠집니다.
필수로 보는 것은 `sentiment_distribution` / `sentiment_trend` /
`rating_sentiment` 세 장뿐입니다. 나머지까지 필수로 걸면 데이터가 부족한 날
`dashboard` 가 통째로 멈춰서 통계도 리포트도 못 보게 됩니다.
빠진 장은 `main.py dashboard` 가 이름을 찍어줍니다.

---

## 7. 자가 점검

```bash
python chart/check_contract.py --b     # B 자가 점검
python chart/check_contract.py --c     # C 자가 점검
python chart/check_contract.py --a     # A 자가 점검
python chart/check_contract.py         # 전체

python chart/tests/test_integration.py # A 통합 테스트 26개
```

**미구현은 `[SKIP]`, 계약 위반만 `[FAIL]` 입니다.**
B/C가 이미 통과시킨 자기 기능 테스트를 다시 돌리는 게 아니라,
A가 그 함수를 실제로 부를 때 깨지는 지점만 봅니다.

현재 상태: **통과 14 · 실패 0 · 미구현 0** · 통합 테스트 26개 통과.

---

## 8. B·C 에게 확인만 부탁드리는 것

고쳐 달라는 요청이 아닙니다. **어긋난 부분은 A가 이미 흡수했습니다.**
다만 아래 4가지가 "의도한 대로 맞는지"만 확인해 주시면 통합이 확정됩니다.

**세인님(B)**

1. clean 레코드 5개 필드(`rating`/`review_text`/`review_date`/`product_name`/
   `skin_type`)가 최종인가요? A의 DB 컬럼을 여기에 맞췄습니다.
2. `cleaner.py` 의 `MIN_REVIEW_LENGTH = 5` 가 상수로 고정되어 있습니다.
   config 로 바꿀 수 없어 A쪽 `cleaning.min_review_length` 는
   `add` 명령(직접 추가)에만 적용됩니다. 이대로 두면 될까요?
3. **차트 3종과 export 는 A가 가져갔습니다.** 만들지 않으셔도 됩니다.
   B 영역은 import / clean 두 가지로 확정입니다.
4. `feature/b-import-clean` 브랜치를 `main` 에 언제 반영할지 알려주시면
   그 시점에 맞춰 통합 브랜치를 정리하겠습니다.

**민규님(C)**

1. `analyze_reviews()` 가 중간에 실패하면 앞선 결과까지 사라집니다.
   A가 1건씩 재시도로 흡수했지만, C 쪽에서 그대로 두실 건지만 알려주세요.
2. `generate_markdown_report()` 의 `chart_paths` 는 **리스트** 기준으로
   동작합니다. A가 dict → 상대경로 리스트로 바꿔 넘기고 있습니다. 맞나요?
3. `insights=None` 이면 `AttributeError` 가 납니다.
   A가 빈 인사이트로 대체하고 있습니다. C 쪽에서 방어하실 생각이 있으신가요?
4. 질문하셨던 4가지 답입니다.
   - **DB → C 데이터 형태**: `{"id", "product_name", "review_text", "rating",
     "review_date", "skin_type", "sentiment", "confidence", "language"}`.
     `rating`/`review_date`/`skin_type`/`sentiment` 는 `None` 일 수 있습니다.
     다만 C는 이 dict 를 직접 받지 않습니다 — A 어댑터가 `review_text` 만
     뽑아 넘기므로 **지금 C 코드 그대로 두시면 됩니다.**
   - **결과 저장 함수**: `database.save_sentiment_results(results, model)`.
     저장은 A가 합니다. C는 부를 일이 없습니다.
   - **stats 형태**: 5번 항목 그대로. C가 보는 칸은 `summary`/`quality`/`top_n`
     이고, A가 한글 평면 dict 로 접어서 넘깁니다.
   - **차트 경로**: `chart_paths` 리스트. 지금 C 코드 그대로 동작합니다.

---

## 9. 아직 담당자가 없는 항목

- **차트 3종 / export** — **완료.** A가 이관받아 구현했습니다.
- **로깅 통일** (명세 4.10) — A가 루트 로거를 잡아두어
  C의 `logging.getLogger(__name__)` 은 자동으로 `chart/logs/app.log` 에
  함께 남습니다. B의 `print` 는 B 영역이라 그대로 뒀습니다.
- **샘플 데이터 30건 이상** (명세 4.13) — B가 100건 제공,
  정제 후 99건으로 충족했습니다.
