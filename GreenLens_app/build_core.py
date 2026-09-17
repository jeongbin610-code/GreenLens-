# -*- coding: utf-8 -*-
"""GreenLens_v8_Pipeline.ipynb → greenlens_core.py

Streamlit 앱이 쓰는 파이프라인 모듈을 노트북에서 생성한다.
노트북이 단일 원본이고, 앱은 여기서 만들어진 모듈을 import 한다.
시연·평가 셀은 제외한다 (정답표를 읽는 코드가 앱에 들어가지 않도록).
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent      # GreenLens_app/
ROOT = HERE.parent                          # 프로젝트 루트 (노트북·데이터가 있는 곳)
NB = ROOT / "GreenLens_v8_Pipeline.ipynb"
OUT = HERE / "greenlens_core.py"

# 앱에 들어갈 셀 (순서 유지). 시연(5e11ee8b, f2-demo)·평가(93cb68a2, f2-eval)·
# getpass(24ad822d)는 제외한다.
INCLUDE = [
    "65bbd780",   # 설정
    "6bbef567",   # 데이터 로드 (정답 누출 차단 포함)
    "44d531fa",   # Company DB 적재
    "91bf59f2",   # Company DB 읽기 (read-only)
    "94bce024",   # 검증 규칙 11종
    "f9cf37d3",   # LLM 보조 (선택)
    "f2-rule",    # F-2 규칙 추출
    "f2-gate",    # F-2 검증 게이트 + extract_claims
    "diag",       # ⑤ 검색 실패 vs 자료 부재 원인 분기
    "ceaacf4b",   # LangGraph
    "f2-entry",   # 광고 단위 진입점
]

HEADER = '''# -*- coding: utf-8 -*-
"""GreenLens 검토 파이프라인 — 자동 생성 파일.

이 파일은 GreenLens_v8_Pipeline.ipynb에서 생성된다. 직접 고치지 말 것.
노트북을 수정한 뒤 다음을 실행하면 갱신된다.

    python build_core.py

평가 정답표(test_cases)를 읽는 코드는 포함되지 않는다.
"""
'''

nb = json.loads(NB.read_text(encoding="utf-8"))
by_id = {c.get("id"): c for c in nb["cells"]}

parts = [HEADER]
for cid in INCLUDE:
    cell = by_id.get(cid)
    assert cell is not None, f"노트북에 셀 {cid}가 없습니다"
    parts.append(f"\n# ══════════ notebook cell: {cid} ══════════\n")
    parts.append("".join(cell["source"]).rstrip() + "\n")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(parts), encoding="utf-8")
print(f"작성: {OUT} ({len(OUT.read_text(encoding='utf-8').splitlines())}줄, 셀 {len(INCLUDE)}개)")
