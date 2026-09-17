# -*- coding: utf-8 -*-
"""이번 작업에서 쓴 코드를 한 파일로 모은다.

greenlens_core.py는 노트북에서 자동 생성되는 파일이라 내용이 중복되므로 싣지 않고,
생성 원본인 노트북 코드 셀을 싣는다.
"""
import json
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent      # GreenLens_app/
DESK = HERE.parent                          # 프로젝트 루트
APP = HERE
OUT = DESK / "GreenLens_전체코드.md"

nb = json.loads((DESK / "GreenLens_v8_Pipeline.ipynb").read_text(encoding="utf-8"))

parts: list[str] = []
add = parts.append

add(f"""# GreenLens 전체 코드

생성일 {datetime.now():%Y-%m-%d %H:%M} · 데이터 `GreenLens_40제품_스키마보완본_v7_1.xlsx`

## 파일 구성

| 파일 | 역할 |
|---|---|
| `GreenLens_v8_Pipeline.ipynb` | **원본.** 파이프라인 + 시연 + 평가 |
| `GreenLens_app/greenlens_core.py` | 노트북에서 자동 생성되는 검토 엔진 (직접 수정 금지) |
| `GreenLens_app/app.py` | Streamlit 화면 5개. 판정 로직 없음 |
| `GreenLens_app/build_core.py` | 노트북 → `greenlens_core.py` 생성 |
| `GreenLens_app/requirements.txt` | 의존성 |

`greenlens_core.py`는 아래 1장의 노트북 코드에서 생성되므로 중복을 피해 싣지 않았습니다.
노트북을 고친 뒤 `python build_core.py`를 실행하면 갱신됩니다.

## 실행

```bash
cd "C:\\Users\\jeong\\OneDrive\\바탕 화면\\GreenLens_app"
pip install -r requirements.txt
python -m streamlit run app.py --browser.gatherUsageStats false
```

API 키 없이 동작합니다. 판정은 규칙 비교 11종, Claim 추출은 규칙 패턴 15종입니다.

---

# 1. 파이프라인 — GreenLens_v8_Pipeline.ipynb

노트북 셀 순서 그대로입니다. 마크다운 셀은 `##` 제목으로, 코드 셀은 코드 블록으로 옮겼습니다.
""")

for cell in nb["cells"]:
    src = "".join(cell["source"]).rstrip()
    if not src.strip():
        continue
    cid = cell.get("id", "")
    if cell["cell_type"] == "markdown":
        # 노트북 제목이 이 문서의 장 제목과 같은 높이로 섞이지 않게 한 단계 내린다
        demoted = "\n".join("#" + ln if ln.lstrip().startswith("#") else ln
                            for ln in src.splitlines())
        add(f"\n<!-- cell: {cid} -->\n\n{demoted}\n")
    else:
        if src.lstrip().startswith("%pip"):
            add(f"\n### 설치 (cell `{cid}`)\n\n```bash\n{src.replace('%pip', 'pip')}\n```\n")
        else:
            add(f"\n**코드 셀 `{cid}`**\n\n```python\n{src}\n```\n")

for title, path, lang in [
    ("2. Streamlit 화면 — app.py", APP / "app.py", "python"),
    ("3. 생성 스크립트 — build_core.py", APP / "build_core.py", "python"),
    ("4. 의존성 — requirements.txt", APP / "requirements.txt", "text"),
]:
    add(f"\n---\n\n# {title}\n\n```{lang}\n{path.read_text(encoding='utf-8').rstrip()}\n```\n")

OUT.write_text("\n".join(parts), encoding="utf-8")
text = OUT.read_text(encoding="utf-8")
print(f"작성: {OUT.name} ({len(text.splitlines()):,}줄 / {len(text) / 1024:.0f}KB)")
