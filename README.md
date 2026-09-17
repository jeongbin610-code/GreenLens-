# GreenLens

중소기업을 위한 AI 환경성 광고 사전점검 Copilot — 광고 문구를 주장 단위로 나누고,
공식 기준과 검증된 제품 증빙을 대조해 확인된 범위·미확인 범위·필요한 보완 자료를 제시합니다.

## 실행

```bash
cd GreenLens_app
pip install -r requirements.txt
python -m streamlit run app.py --browser.gatherUsageStats false
```

**API 키가 없어도 전부 동작합니다.** 판정은 규칙 비교 11종, Claim 추출은 규칙 패턴 15종으로
이루어지며, LLM은 설명문 생성·범위 해석 참고·Policy RAG에만 보조로 쓰입니다.
LLM을 쓰더라도 **판정 상태는 바뀌지 않습니다.**

LLM 보조를 켜려면 실행 전에 `OPENAI_API_KEY`를 설정하고 `requirements.txt`의 주석 처리된
패키지를 설치하세요.

## 파일 구성

```
GreenLens/
├─ GreenLens_v8_Pipeline.ipynb        ← 원본. 파이프라인 + 시연 + 평가
├─ GreenLens_40제품_스키마보완본_v7_1.xlsx        ← 기본 데이터
├─ GreenLens_40제품_스키마보완본_v7_1_보완.xlsx    ← 스키마 확장본 (선택)
└─ GreenLens_app/
   ├─ app.py                ← Streamlit 화면 5개. 판정 로직 없음
   ├─ greenlens_core.py     ← 노트북에서 자동 생성되는 검토 엔진 (직접 수정 금지)
   ├─ build_core.py         ← 노트북 → greenlens_core.py 생성
   ├─ bundle_code.py        ← 전체 코드를 한 문서로 뽑는 스크립트
   ├─ requirements.txt
   └─ README.md             ← 화면별 구현 내용 · 표시 원칙 · 알려진 제약
```

노트북을 고친 뒤에는 반드시 다시 생성해야 화면에 반영됩니다.

```bash
cd GreenLens_app && python build_core.py
```

## 데이터에 관한 고지

`.xlsx`에는 **한국환경산업기술원 환경표지 인증내역(공개 데이터, 기준일 2026-01-31)**에서
확보한 실제 인증 레코드와, 외부 확보가 불가능한 시험성적서·원료 사양서를 대신하는
**시연용 합성 자료**가 함께 들어 있습니다. 합성분은 `is_synthetic` 열로 구분되고 화면에도
가상 자료로 표시되며, **실제 제품의 측정값이나 환경성을 보증하지 않습니다.**

광고 문구 예시는 검토 흐름을 시험하려고 팀이 작성한 것으로, 해당 기업의 실제 광고나
위반사례가 아닙니다.

## 데이터 파일

코드는 `GreenLens_40제품_스키마보완본_v7_1.xlsx`를 기본으로 찾습니다. 탐색 순서는
현재 디렉터리 → `GreenLens_app/` → 상위 폴더이며, 다른 위치라면 환경변수로 지정합니다.

```bash
set GREENLENS_DATA=경로\파일.xlsx        # Windows
export GREENLENS_DATA=경로/파일.xlsx     # macOS/Linux
```

`_보완.xlsx`는 시트 4개(`claim_ingredient_evidence_link`, `claim_review_result`,
`evidence_submission`, `schema_change_log`)와 `test_cases` 컬럼 10개가 더 있는 확장본입니다.
두 파일 모두 평가 24/24를 통과하며, 쓰려면 위 환경변수로 지정하거나
노트북 설정 셀의 `DATA_FILE`을 바꾸면 됩니다.

`greenlens_company_v7_1.db`(SQLite)는 실행 시 자동 생성되므로 포함하지 않았습니다.

## 검증 현황

```
9절   구조화 Claim → 판정        24/24 · False Pass 0/17 · 부당 판정률 0/6
9.5절 광고 원문 → 추출 → 판정    24/24 · 추출 성공 24/24
8.6절 ⑤ 원인 분기               검색 실패 / 자료 부재 / 검수 상태 4개 경로 재현
```

**이 수치는 블라인드 평가가 아닙니다.** 규칙과 추출 패턴을 이 데이터를 보고 작성했으므로,
발표에서는 정확도보다 부당 판정률(모르는 것을 아는 척하지 않는 비율)을 제시하고
블라인드가 아니라는 점을 밝혀야 합니다. 자세한 제약은 노트북 10절을 참고하세요.

## 설계 원칙

- 근거를 찾지 못하면 판정하지 않고 필요한 자료를 요청합니다. 자료 부재를 거짓으로 단정하지 않습니다.
- AI는 Company DB에 쓰기 권한이 없습니다. 등록은 운영자의 수동 절차입니다.
- 광고 원문에 없는 인증·수치는 Claim으로 만들지 않습니다(검증 게이트).
- 자가 신고 자료만으로는 인증 주장이 확인되지 않습니다. 인증번호는 공개 인증내역에서 역조회합니다.
- 검토 결과와 담당자 확인 상태를 화면에서 분리해 표시합니다.
