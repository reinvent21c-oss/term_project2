#!/usr/bin/env python3
"""
고객 리뷰 감정 분석 대시보드 — 루트 런처.

    python main.py import --file source/input/cosmetics_reviews_100.csv
    python main.py analyze --unanalyzed --limit 20
    python main.py extract
    python main.py dashboard

실제 CLI 는 chart/main.py 에 있다. 이 파일은 그걸 불러주기만 한다.

왜 루트에 런처를 두나
  담당자별로 폴더를 나누면(chart/ prompt/ source/) 실행 진입점이
  하위 폴더로 들어가 버린다. `python chart/main.py` 도 동작하지만,
  명세 8장 예시가 `python main.py` 형태라 루트에 맞춰 둔다.
  팀원이 README 를 안 봐도 레포를 열자마자 실행 파일이 보이는 이점도 있다.

importlib 로 파일 경로를 직접 지정하는 이유
  이 파일과 chart/main.py 의 이름이 둘 다 main.py 다.
  평범하게 `import main` 하면 어느 쪽이 잡힐지 sys.path 순서에 달린다.
  파일 경로를 못 박으면 그 애매함이 없어진다.
"""

import importlib.util
import sys
from pathlib import Path


CHART_DIR = Path(__file__).resolve().parent / "chart"
ENTRY = CHART_DIR / "main.py"


def load_cli():
    """chart/main.py 를 모듈로 읽어온다."""

    if not ENTRY.exists():
        raise SystemExit(
            f"[ERROR] CLI 파일을 찾을 수 없습니다: {ENTRY}\n"
            f"        chart/ 폴더가 레포 루트에 있는지 확인하세요."
        )

    # chart/ 를 import 경로에 넣어야 chart/main.py 안의
    # `from modules...` 가 chart/modules 를 찾는다.
    sys.path.insert(0, str(CHART_DIR))

    spec = importlib.util.spec_from_file_location("chart_cli", ENTRY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


if __name__ == "__main__":
    sys.exit(load_cli().main())
