# C 담당 AI 분석 모듈

고객 리뷰의 Gemini 감정 분석, AI 인사이트 추출, Markdown 리포트 생성을 담당한다.

C 담당 모듈은 AI 분석과 리포트 생성을 담당하며, SQLite 조회·저장 및 CLI 처리는 직접 수행하지 않는다.

A 담당 모듈에서 DB 조회·저장, CLI 처리, 통계 생성 및 차트 생성을 담당하고, C 담당 모듈은 정해진 인터페이스를 통해 데이터를 전달받아 처리한다.

---

## 1. 감정 분석

### `analyze_review(review_text)`

리뷰 1건의 텍스트를 Gemini로 분석한다.

입력:

```python
review_text = "흡수가 빠르고 촉촉해서 좋아요."
```

반환 예시:

```python
{
    "sentiment": "positive",
    "confidence": 0.98
}
```

반환 항목:

- `sentiment`: `positive`, `negative`, `neutral` 중 하나
- `confidence`: `0.0 ~ 1.0` 범위의 신뢰도

감정 분석에는 리뷰 본문만 사용하며 별점은 사용하지 않는다.

Gemini 응답은 반환 전에 감정값과 confidence 범위를 검증한다.

Gemini 호출 중 오류가 발생하거나 응답 JSON 파싱·검증에 실패하면 최대 1회 재시도한다.

- 최초 호출 실패 시 warning 로그를 남기고 1회 재시도한다.
- 재시도 후에도 실패하면 error 로그를 남기고 예외를 호출한 쪽으로 전달한다.
- 빈 문자열이나 문자열이 아닌 입력은 Gemini API를 호출하기 전에 차단한다.

---

### `analyze_reviews(reviews)`

여러 리뷰를 순서대로 감정 분석한다.

A 담당 모듈에서 DB의 리뷰를 조회한 뒤 C 담당에 필요한 `id`, `review_text`만 전달한다.

입력 형식:

```python
reviews = [
    {
        "id": 1,
        "review_text": "발림성이 좋아요."
    },
    {
        "id": 2,
        "review_text": "너무 끈적거려요."
    },
]
```

입력 자료형:

```text
list[dict]
```

각 리뷰의 주요 필드:

- `id`: 리뷰 식별자
- `review_text`: 감정 분석에 사용할 리뷰 본문

`rating`은 감정 분석에 전달하지 않는다.

별점을 감정 분석에 사용하면 모델이 별점 정보에 영향을 받아 별점-감정 일치도 지표의 의미가 약해질 수 있으므로 리뷰 본문만 사용한다.

반환 예시:

```python
{
    "results": [
        {
            "id": 1,
            "sentiment": "positive",
            "confidence": 0.95
        },
        {
            "id": 2,
            "sentiment": "negative",
            "confidence": 0.91
        }
    ],
    "failed_ids": []
}
```

반환 항목:

- `results`: 분석에 성공한 리뷰의 결과 목록
- `failed_ids`: 분석하지 못한 리뷰 ID 목록

각 성공 결과에는 입력받은 `id`를 그대로 포함한다.

```python
{
    "id": 1,
    "sentiment": "positive",
    "confidence": 0.95
}
```

### 여러 리뷰 처리 규칙

#### 1. 입력 ID 유지

입력받은 리뷰의 ID는 성공 결과 또는 실패 결과 중 한쪽에 반드시 나타나야 한다.

```text
성공
→ results에 id 포함

실패
→ failed_ids에 id 포함
```

분석 대상 리뷰가 조용히 누락되지 않도록 한다.

#### 2. 한 리뷰가 실패해도 나머지는 계속 처리

개별 리뷰의 Gemini 분석이 최종적으로 실패하더라도 전체 배치를 중단하지 않는다.

예:

```text
id 1 → 성공
id 2 → 실패
id 3 → 성공
```

반환:

```python
{
    "results": [
        {
            "id": 1,
            "sentiment": "positive",
            "confidence": 0.95
        },
        {
            "id": 3,
            "sentiment": "neutral",
            "confidence": 0.80
        }
    ],
    "failed_ids": [2]
}
```

100건 분석 중 일부 API 호출이 실패해도 이미 성공한 결과와 이후 분석 가능한 리뷰를 버리지 않기 위한 구조이다.

#### 3. ID가 없는 리뷰는 예외 처리

다음과 같이 `id`가 없는 입력은 개별 리뷰 분석 실패가 아니라 호출자 측 인터페이스 오류로 판단한다.

```python
{
    "review_text": "좋아요."
}
```

이 경우 `failed_ids`로 넘기지 않고 `ValueError`를 발생시킨다.

#### 4. 비어 있는 리뷰 본문

ID는 있지만 `review_text`가 비어 있거나 정상적인 문자열이 아니면 해당 리뷰의 ID를 `failed_ids`에 추가하고 다음 리뷰를 계속 처리한다.

이 함수에서는 DB 조회나 분석 결과 저장을 직접 수행하지 않는다.

---

## 2. AI 인사이트 추출

### `extract_insights(reviews)`

여러 리뷰 텍스트를 바탕으로 Gemini가 종합 인사이트를 생성한다.

입력 형식:

```text
list[str]
```

입력 예시:

```python
reviews = [
    "흡수가 빠르고 촉촉해서 좋아요.",
    "제 피부에는 조금 무겁게 느껴졌어요.",
]
```

인사이트 추출에는 리뷰 ID가 필요하지 않으며 리뷰 본문만 전달받는다.

실제 전체 리뷰 중 인사이트 추출에 사용할 리뷰 건수는 A 담당 모듈에서 설정값을 기준으로 제한하여 전달한다.

반환 예시:

```python
{
    "positive_keywords": [
        "보습력",
        "빠른 흡수"
    ],
    "negative_keywords": [
        "무거운 사용감"
    ],
    "summary": "보습과 흡수력에 대한 평가는 긍정적이지만 일부 사용자는 제형을 무겁게 느꼈습니다.",
    "improvements": [
        "가벼운 사용감을 선호하는 고객을 위한 제형 개선을 검토할 수 있습니다.",
        "피부 타입에 따른 권장 사용 방법을 보다 구체적으로 안내할 수 있습니다."
    ]
}
```

반환 항목:

- `positive_keywords`: 긍정적인 평가에서 추출한 주요 키워드 목록
- `negative_keywords`: 부정적인 평가에서 추출한 주요 키워드 목록
- `summary`: 전체 리뷰에 대한 종합 요약
- `improvements`: 리뷰를 바탕으로 생성한 개선 제안 목록

과제 요구사항을 반영하여 `improvements`는 최소 2개 이상 생성하도록 프롬프트와 결과 검증에 반영했다.

A 담당 인터페이스에서는 `improvements`를 `list[str]` 형식으로 전달받으므로 최소 2개를 반환하는 현재 C 구현과 호환된다.

반환 결과는 필요한 키와 각 값의 자료형이 올바른지 검증한 뒤 사용한다.

Gemini 호출 중 오류가 발생하거나 응답 JSON 파싱·검증에 실패하면 최대 1회 재시도한다.

- 최초 호출 실패 시 warning 로그를 남기고 1회 재시도한다.
- 개선 제안이 2개 미만인 경우에도 검증 실패로 처리하여 1회 재시도한다.
- 정상 입력인데 재시도 후에도 Gemini 호출·파싱·검증이 실패하면 error 로그를 남기고 `None`을 반환한다.
- 빈 리스트, 빈 리뷰 또는 문자열이 아닌 리뷰는 Gemini API를 호출하기 전에 차단한다.

### 실패 처리

입력 자체가 잘못된 경우에는 예외를 발생시킨다.

예:

```text
리스트가 아닌 입력
빈 리스트
빈 리뷰
문자열이 아닌 리뷰
```

반면 정상적인 리뷰 목록을 전달받았지만 Gemini 분석이 최종적으로 실패한 경우에는:

```python
None
```

을 반환한다.

인사이트 생성 실패 때문에 통계 및 차트가 포함된 전체 dashboard 흐름까지 중단되지 않도록 하기 위한 구조이다.

---

## 3. Markdown 리포트 생성

### `generate_markdown_report(stats=None, insights=None, chart_paths=None, output_path=None)`

통계 데이터, AI 인사이트, 차트 이미지 경로를 받아 Markdown 형식의 리뷰 분석 리포트를 생성한다.

반환값:

```text
Markdown 문자열
```

`output_path`가 지정되면 Markdown 파일로도 저장한다.

### 입력 항목

- `stats`: A 담당에서 생성한 통계 데이터 딕셔너리
- `insights`: `extract_insights()` 결과 또는 `None`
- `chart_paths`: 차트 이미지 경로 목록 또는 딕셔너리
- `output_path`: Markdown 파일 저장 경로

`stats`, `insights`, `chart_paths`, `output_path`는 모두 선택적으로 전달할 수 있다.

---

## 4. 통계 데이터 연결

A 담당에서 생성하는 `stats`는 다음 구조를 사용한다.

```python
stats = {
    "meta": {
        # 생성 시각, 필터 등의 정보
    },
    "summary": {
        # 주요 통계
    },
    "chart_data": {
        # 차트 생성용 데이터
    },
    "quality": {
        # 품질 지표
    },
    "top_n": {
        # TOP N 집계
    },
}
```

C 담당 리포트에서는 다음 세 영역을 사용한다.

```text
summary
quality
top_n
```

다음 영역은 현재 리포트 본문에 직접 펼치지 않는다.

```text
meta
chart_data
```

특히 `chart_data`는 matplotlib 차트 생성을 위한 데이터이므로 Markdown 리포트에 직접 출력하지 않는다.

---

### `summary`

예시:

```python
{
    "total": 99,
    "analyzed": 99,
    "unanalyzed": 0,
    "analysis_rate": 1.0,
    "avg_rating": 3.6465,
    "avg_confidence": 0.6656,
    "sentiment_counts": {
        "positive": 46,
        "neutral": 40,
        "negative": 13
    },
    "sentiment_ratios": {
        "positive": 0.4646,
        "neutral": 0.4040,
        "negative": 0.1314
    },
    "rating_counts": {
        1: 8,
        2: 12,
        3: 20,
        4: 26,
        5: 33
    }
}
```

리포트에서는 다음 정보를 출력한다.

- 전체 리뷰 수
- 분석 완료 리뷰 수
- 미분석 리뷰 수
- 분석률
- 평균 별점
- 평균 분석 신뢰도
- 감정별 리뷰 수 및 비율
- 별점별 리뷰 수

`analysis_rate`는 전체 리뷰 기준 비율이고, `sentiment_ratios`는 분석 완료 리뷰 기준 비율이므로 서로 다른 분모를 사용한다.

`rating_counts`의 키는 일반적으로 정수이지만 JSON 변환 과정에서 문자열로 변경될 수 있으므로 두 형식을 모두 처리한다.

---

### `quality`

예시:

```python
{
    "rating_sentiment_agreement": 0.6162,
    "data_completeness": 1.0,
    "avg_review_length": 44.404
}
```

리포트에서는 다음 품질 지표를 출력한다.

- 별점-감정 일치도
- 데이터 완전성
- 평균 리뷰 길이

---

### `top_n`

예시:

```python
{
    "worst_reviews": [
        {
            "id": 23,
            "product_name": "수분 장벽 크림",
            "review_text": "사용 후 피부에 트러블이 생겼어요.",
            "rating": 1,
            "review_date": "2025-03-14",
            "skin_type": "건성",
            "sentiment": "negative",
            "confidence": 0.79
        }
    ],
    "product_counts": [
        ("수분 장벽 크림", 34),
        ("데일리 선크림", 33)
    ],
    "skin_type_counts": [
        ("건성", 34),
        ("지성", 33)
    ]
}
```

리포트에서는 다음 내용을 출력한다.

- 리뷰 수가 많은 제품
- 피부 타입별 리뷰 수
- 낮은 별점 리뷰

`product_counts`, `skin_type_counts`는 정렬된 `(이름, 건수)` 튜플 리스트로 전달받는다.

---

## 5. AI 인사이트와 리포트 연결

`insights`에는 `extract_insights()`의 결과를 전달한다.

```python
{
    "positive_keywords": [],
    "negative_keywords": [],
    "summary": "",
    "improvements": []
}
```

리포트에서는 다음 항목을 출력한다.

```text
AI 인사이트
├─ 긍정 키워드
├─ 부정 키워드
├─ 전체 요약
└─ 개선 제안
```

`extract_insights()`가 최종적으로 실패한 경우:

```python
insights = None
```

이 전달될 수 있다.

`generate_markdown_report()`에서는 이를 빈 딕셔너리로 처리하여 인사이트가 없더라도 리포트 생성 자체가 중단되지 않도록 한다.

---

## 6. 차트 연결

C 담당에서는 차트를 직접 생성하지 않는다.

다른 모듈에서 생성된 차트 이미지 경로를 `chart_paths`로 전달받아 Markdown 리포트에 이미지 링크를 추가한다.

`chart_paths`는 리스트 또는 딕셔너리 형식을 모두 지원한다.

### 딕셔너리 예시

```python
chart_paths = {
    "sentiment_distribution": "sentiment_distribution.png",
    "sentiment_trend": "sentiment_trend.png",
    "rating_sentiment": "rating_sentiment.png",
}
```

딕셔너리가 전달되면 실제 파일 경로에 해당하는 value를 사용한다.

### 리스트 예시

```python
chart_paths = [
    "sentiment_distribution.png",
    "sentiment_trend.png",
    "rating_sentiment.png",
]
```

Markdown 출력 예시:

```markdown
## 시각화

![차트 1](sentiment_distribution.png)

![차트 2](sentiment_trend.png)

![차트 3](rating_sentiment.png)
```

차트 경로는 리포트 파일 기준 상대 경로를 사용한다.

절대 경로를 사용할 경우 특정 컴퓨터에서는 보이지만 GitHub 등 다른 환경에서 이미지가 깨질 수 있으므로 사용하지 않는다.

`chart_paths`가 빈 리스트, 빈 딕셔너리 또는 `None`이면 시각화 섹션을 생략한다.

지원하지 않는 자료형이 전달되면 `TypeError`를 발생시킨다.

---

## 7. A 담당과의 연결 범위

A 담당은 다음 영역을 담당한다.

```text
DB 조회
DB 저장
CLI
통계 생성
차트 생성
```

C 담당은 다음 영역을 담당한다.

```text
감정 분석
AI 인사이트 추출
Markdown 리포트 생성
```

전체 연결 흐름:

```text
A: DB에서 분석 대상 리뷰 조회
        ↓
A → C: [{id, review_text}]
        ↓
C: analyze_reviews()
        ↓
C → A:
{
    results: [{id, sentiment, confidence}],
    failed_ids: [...]
}
        ↓
A: 성공 결과 DB 저장
        ↓
A: stats 생성
        ↓
A → C: 리뷰 본문 목록
        ↓
C: extract_insights()
        ↓
A: 차트 생성
        ↓
C: generate_markdown_report()
```

C 모듈에서는 A의 DB 스키마, 테이블 구조, 저장 함수 또는 argparse CLI 구조를 직접 구현하지 않는다.

---

## 8. 환경변수

Gemini API 키는 소스코드에 직접 작성하지 않고 환경변수로 관리한다.

필요한 환경변수:

```text
GEMINI_API_KEY
```

`.env.example`:

```text
GEMINI_API_KEY=your_api_key_here
```

실제 API 키가 들어 있는 `.env` 파일은 Git에 커밋하지 않는다.

`prompt/.gitignore`에는 다음 항목을 Git 추적 대상에서 제외하도록 설정했다.

```text
__pycache__/
*.pyc
.env
```

---

## 9. C 담당 주요 함수

### 단일 리뷰 감정 분석

```text
analyze_review(review_text)
```

입력:

```text
str
```

출력:

```python
{
    "sentiment": "positive | negative | neutral",
    "confidence": 0.0 ~ 1.0
}
```

---

### 여러 리뷰 감정 분석

```text
analyze_reviews(reviews)
```

입력:

```python
[
    {
        "id": int,
        "review_text": str
    }
]
```

출력:

```python
{
    "results": [
        {
            "id": int,
            "sentiment": "positive | negative | neutral",
            "confidence": float
        }
    ],
    "failed_ids": [
        int
    ]
}
```

---

### AI 인사이트 추출

```text
extract_insights(reviews)
```

입력:

```text
list[str]
```

정상 반환:

```python
{
    "positive_keywords": [],
    "negative_keywords": [],
    "summary": "",
    "improvements": []
}
```

정상 입력에 대한 최종 AI 처리 실패:

```python
None
```

`improvements`는 최소 2개 이상을 생성하도록 검증한다.

---

### Markdown 리포트 생성

```text
generate_markdown_report(
    stats=None,
    insights=None,
    chart_paths=None,
    output_path=None
)
```

출력:

```text
Markdown 문자열
```

`output_path`가 지정되면 파일로도 저장한다.

---

## 10. 현재 확인된 테스트 범위

### 실제 Gemini 호출

C 담당 기능 구현 과정에서 실제 Gemini API를 이용한 감정 분석과 AI 인사이트 추출이 정상 동작하는 것을 확인했다.

현재 감정 분석 모델은 다음과 같다.

```text
gemini-3.6-flash
```

감정 분석 결과의 `sentiment`는 다음 세 값 중 하나로 검증한다.

```text
positive
negative
neutral
```

`confidence`는 `0.0 ~ 1.0` 범위로 검증한다.

현재 SQLite DB에도 `gemini-3.6-flash`로 분석된 감정 분석 결과 99건이 저장되어 있다.

---

### 실제 정제 데이터 및 통합 확인

B 담당의 정제 데이터와 A 담당의 SQLite DB 및 통계 모듈을 이용하여 C 모듈과의 연결을 확인했다.

현재 DB 기준 확인된 데이터는 다음과 같다.

```text
raw_reviews : 100건
reviews     : 99건
analyses    : 99건
extractions : 1건

Gemini model : gemini-3.6-flash
```

현재 DB와 `calculate_stats()`를 기준으로 확인한 최신 통계는 다음과 같다.

```text
총 리뷰 수: 99건
분석 완료: 99건 (100.0%)

긍정: 57건 (57.6%)
중립: 38건 (38.4%)
부정: 4건 (4.0%)

평균 별점: 3.65
평균 분석 신뢰도: 0.91
별점-감정 일치도: 81.8%
데이터 완전성: 100.0%
```

A의 `calculate_stats()` 결과와 DB에 저장된 AI 인사이트를 C의 `generate_markdown_report()`에 전달하여 실제 Markdown 리포트를 생성했다.

생성 파일:

```text
chart/output/review_analysis_report.md
```

최종 Markdown에서는 사용자에게 표시되는 감정명을 다음과 같이 한국어로 출력한다.

```text
positive → 긍정
neutral  → 중립
negative → 부정
```

단, Python 내부 데이터 계약과 DB/API에서 사용하는 sentiment 값은 기존 영문 값을 그대로 유지한다.

```text
positive
neutral
negative
```

---

### 자동 테스트

`unittest` 기반 자동 테스트를 작성했으며 현재 총 25개 테스트가 통과하는 것을 확인했다.

```text
analyzer.py  : 10개
extractor.py : 7개
reporter.py  : 8개
합계         : 25개
```

#### analyzer

자동 테스트에서는 다음 내용을 확인한다.

- 단일 리뷰 입력과 결과 구조 검증
- 여러 리뷰 batch 입력 검증
- ID가 없는 리뷰 입력 검증
- 빈 리뷰 처리
- 성공 결과의 리뷰 ID 유지
- Gemini batch 결과 구조 검증
- 허용되지 않은 sentiment 검증
- confidence 범위 검증
- 전체 batch 요청 실패 시 두 그룹으로 분할하여 재시도
- 최종 실패 리뷰를 `failed_ids`로 분리

현재 여러 리뷰 분석은 리뷰마다 Gemini API를 개별 호출하지 않고 batch 방식으로 처리한다.

99건 기준 기본 호출 구조는 다음과 같다.

```text
1차: 99건 batch 요청

전체 batch 실패 시:
2차: 약 50건
3차: 약 49건
```

전체 batch가 실패했을 때 한 번만 두 그룹으로 나누어 재시도하며 계속 재귀적으로 분할하지 않는다.

#### extractor

자동 테스트에서는 다음 내용을 확인한다.

- 입력 자료형 검증
- 빈 리스트 검증
- 빈 리뷰 및 잘못된 자료형 검증
- Gemini 최초 호출 실패 후 1회 재시도
- 개선 제안이 2개 미만인 결과 검증
- 정상 결과 반환
- 최종 AI 처리 실패 시 `None` 반환

`extract_insights()`의 입력은 리뷰 본문 목록이다.

```python
list[str]
```

C 모듈에서는 인사이트 추출 대상 리뷰 수를 직접 제한하지 않는다.

A와의 인터페이스 계약에서는 A가 다음 설정을 기준으로 리뷰 수를 제한한 뒤 C에 전달하도록 정의되어 있다.

```text
config.ai.extract_max_reviews = 60
```

#### reporter

자동 테스트에서는 다음 내용을 확인한다.

- A의 `summary`, `quality`, `top_n` 통계 출력
- `chart_data`가 Markdown 본문에 직접 출력되지 않는지 확인
- `rating_counts`의 정수 및 문자열 키 처리
- `stats=None`, `insights=None` 처리
- `chart_paths` 딕셔너리 지원
- `chart_paths` 리스트 지원
- 차트가 없을 때 시각화 섹션 생략
- Markdown 파일 저장
- Markdown 감정 표시를 `긍정 / 중립 / 부정`으로 출력

전체 자동 테스트 실행 명령:

```bash
python -m unittest discover -s prompt/tests
```

가장 최근 실행 결과:

```text
Ran 25 tests in 0.005s

OK
```

---

## 11. 현재 통합 상태 및 남은 작업

C 담당의 다음 기능은 현재 기준으로 구현 및 테스트를 완료했다.

```text
Gemini 감정 분석
Gemini batch 분석
감정 분석 결과 검증
AI 인사이트 추출
AI 인사이트 결과 검증
개선 제안 최소 2개 보장
Markdown 리포트 생성
최종 감정명 한국어 표시
```

또한 다음 실제 연결을 확인했다.

- B 정제 데이터가 `source/`에 존재
- SQLite `reviews` 99건 확인
- Gemini 감정 분석 결과 99건 확인
- AI extraction 결과 존재 확인
- A의 `calculate_stats()`와 SQLite DB 연결
- 실제 감정 통계 계산
- matplotlib 차트 생성
- A 통계와 DB 인사이트를 C reporter에 연결
- `review_analysis_report.md` 실제 생성
- 최신 reporter 적용 후 C 전체 자동 테스트 25개 통과

현재 C 기능 자체보다 팀 전체 CLI 통합 단계의 확인사항이 남아 있다.

### 최종 CLI 통합 확인

현재 GitHub `main`에서는 `main.py`를 포함한 최종 CLI 실행 entry point가 확인되지 않았다.

또한 현재 Python 코드에서 `argparse` 기반 최종 CLI 구현도 확인되지 않았다.

미션에서 요구하는 필수 서브커맨드는 다음과 같다.

```text
import
clean
analyze
extract
list
show
stats
dashboard
export
```

A 담당의 최종 CLI 코드가 반영된 뒤 각 명령이 실제 모듈과 연결되는지 확인해야 한다.

C와 직접 관련된 흐름은 다음과 같다.

```text
analyze
→ DB에서 분석 대상 조회
→ C analyze_reviews()
→ sentiment / confidence DB 저장

extract
→ 조건별 리뷰 조회
→ 최대 리뷰 수 제한
→ C extract_insights()
→ extraction 결과 DB 저장

dashboard
→ stats 계산
→ 차트 생성
→ 저장된 AI 인사이트 조회
→ C generate_markdown_report()
```

### extract 최대 리뷰 수 확인

현재 `chart/modules/config.py`에는 다음 기본 설정이 존재한다.

```text
extract_max_reviews = 60
```

C 인터페이스 계약에서도 A가 해당 설정값을 이용하여 최대 60건을 C의 `extract_insights()`에 전달하도록 정의되어 있다.

다만 현재 GitHub `main`에서는 `extract_max_reviews`를 실제 호출 흐름에서 사용하는 코드가 확인되지 않았다.

또한 현재 DB의 `extractions.review_count`에는 다음 값이 저장되어 있다.

```text
99
```

따라서 최종 CLI 통합 코드를 확인하기 전에는 이 값이 전체 조회 대상 리뷰 수인지, 실제 Gemini에 전달한 리뷰 수인지 단정하지 않는다.

### extraction 저장 확인

`chart/modules/database.py`에는 다음 저장 함수가 구현되어 있다.

```python
save_extraction(
    scope,
    review_count,
    data,
    model=None,
    db_path=None,
)
```

하지만 현재 GitHub `main`에서는 이 함수를 호출하는 최종 CLI 통합 코드가 확인되지 않았다.

최종적으로 다음 흐름을 확인해야 한다.

```text
리뷰 조건 조회
→ extract_max_reviews 적용
→ C extract_insights()
→ save_extraction()
→ dashboard / report에서 저장 결과 활용
```

### config.json 확인

`chart/modules/config.py`에는 다음과 같은 설정 기본값과 검증 로직이 구현되어 있다.

```text
duplicate_policy    : skip / upsert
AI model            : gemini-3.6-flash
extract_max_reviews : 60
visualization       : PNG
```

다만 미션 요구사항에 명시된 실제 `config.json` 파일은 현재 저장소에서 확인되지 않았다.

최종 통합 단계에서 실제 `config.json` 제공 여부를 확인해야 한다.

Gemini API 키 값 자체는 소스코드나 공개 설정 파일에 직접 작성하지 않고 다음 환경변수를 사용한다.

```text
GEMINI_API_KEY
```

### Gemini 최종 live smoke test

현재 개발환경에서는 다음 내용을 확인했다.

```text
google-genai 2.17.0
python-dotenv 1.2.2
Gemini SDK import 정상
dotenv import 정상
C 자동 테스트 25개 통과
DB에 기존 Gemini 분석 결과 99건 존재
```

기존 Gemini 분석 결과가 이미 존재하므로 99건 전체를 다시 분석할 필요는 없다.

A의 최종 CLI가 반영된 뒤 리뷰 1~2건 정도를 실제 Gemini API로 분석하여 다음 흐름만 최종 확인한다.

```text
CLI analyze
→ 실제 Gemini 응답
→ 결과 DB 저장
```

필요하면 `extract`도 1회 실행하여 Gemini 인사이트 생성과 DB 저장을 확인한다.

### 최종 제출 전 확인

- A의 최종 CLI entry point 확인
- argparse 기반 필수 서브커맨드 실행 확인
- `analyze --all / --id / --unanalyzed` 확인
- `extract`의 기간/감정/제품 조건 확인
- `extract_max_reviews=60` 실제 적용 확인
- `save_extraction()` 호출 확인
- `list` 필터·정렬·페이지네이션 확인
- `show` 단건 상세조회 확인
- `stats` CLI 출력 확인
- `dashboard` 전체 실행 확인
- `export` 필터 및 파일 출력 확인
- 실제 `config.json` 확인
- Gemini 소량 live smoke test
- `chart/output`을 최종 Git에 포함할지 팀 기준 확인
- 전체 자동 테스트 재실행
- 최종 Git 상태 및 push 확인

최종 CLI 실행 명령은 현재 존재하지 않는 과거 파일명을 임의로 작성하지 않고, A 담당의 실제 최종 entry point가 GitHub `main`에 반영된 뒤 동작을 확인한 명령만 기록한다.

---

## 12. 현재 C 인터페이스 요약

```text
analyze_review(review_text)
    → {sentiment, confidence}


analyze_reviews([
    {id, review_text},
    ...
])
    → {
        results: [
            {id, sentiment, confidence},
            ...
        ],
        failed_ids: [id, ...]
    }


extract_insights([
    "리뷰 본문",
    ...
])
    → {
        positive_keywords,
        negative_keywords,
        summary,
        improvements
    }
    또는
    None


generate_markdown_report(
    stats,
    insights,
    chart_paths,
    output_path
)
    → Markdown 문자열
```

핵심 원칙:

```text
감정 분석에는 review_text만 사용
↓
rating은 AI 분석에 전달하지 않음

개별 리뷰 분석 실패
↓
failed_ids에 기록하고 다음 리뷰 계속 처리

호출자 인터페이스 오류
↓
예외 발생

인사이트 최종 실패
↓
None 반환

리포트
↓
stats의 summary / quality / top_n 사용
chart_data는 직접 출력하지 않음

chart_paths
↓
list / dict 모두 지원
```