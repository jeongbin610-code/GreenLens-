# -*- coding: utf-8 -*-
"""GreenLens — 환경성 광고 사전점검 Copilot (Streamlit MVP)

기획서 8-2의 5개 화면을 구현한다.
  1 광고 입력 · 2 분석 진행 · 3 검토 Report · 4 보완 및 재검토 · 5 최종 확인

판정 로직은 greenlens_core(노트북에서 생성)에 있고, 이 파일은 화면만 담당한다.
"""
from __future__ import annotations

import html
import json
import sys
import uuid
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="GreenLens", page_icon="🌿", layout="wide")


def apply_b2b_style() -> None:
    """공공 B2B 검토 도구에 맞춘 절제된 시각 체계."""
    st.markdown("""
    <style>
      :root {
        --gl-navy: #17324d;
        --gl-blue: #176b87;
        --gl-blue-soft: #eaf3f6;
        --gl-surface: #ffffff;
        --gl-bg: #f5f7fa;
        --gl-line: #d9e1e8;
        --gl-muted: #5d6b7a;
      }
      .stApp { background: var(--gl-bg); color: var(--gl-navy); }
      [data-testid="stHeader"] { background: rgba(245,247,250,.92); }
      [data-testid="stSidebar"] { background: #f8fafc; border-right: 1px solid var(--gl-line); }
      [data-testid="stSidebar"] > div:first-child { padding: 1.5rem 1rem; }
      .block-container { max-width: 1180px; padding-top: 2.2rem; padding-bottom: 3rem; }
      h1, h2, h3 { color: var(--gl-navy) !important; letter-spacing: -0.025em; }
      h1 { font-weight: 700 !important; }
      h3 { font-weight: 650 !important; }
      [data-testid="stCaptionContainer"] { color: var(--gl-muted); }
      [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--gl-surface); border: 1px solid var(--gl-line);
        border-radius: 10px; box-shadow: none;
      }
      [data-testid="stAlert"] { border-radius: 8px; border: 1px solid var(--gl-line); }
      [data-testid="stMetric"] { background: var(--gl-surface); border: 1px solid var(--gl-line); border-radius: 8px; padding: .8rem 1rem; }
      [data-testid="stMetricLabel"] { color: var(--gl-muted); font-size: .8rem; }
      [data-testid="stMetricValue"] { color: var(--gl-navy); }
      .stButton > button { border-radius: 6px; border-color: #bfcbd5; color: var(--gl-navy); background: #fff; font-weight: 600; }
      .stButton > button[kind="primary"] { background: var(--gl-blue); border-color: var(--gl-blue); color: #fff; }
      .stButton > button:hover { border-color: var(--gl-blue); color: var(--gl-blue); }
      .stButton > button[kind="primary"]:hover { background: #10566f; color: #fff; }
      [data-baseweb="select"] > div, .stTextArea textarea, .stTextInput input {
        background: #fff !important; border-color: #c8d2dc !important; border-radius: 6px !important;
      }
      [data-baseweb="select"] > div:focus-within, .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: var(--gl-blue) !important; box-shadow: 0 0 0 1px var(--gl-blue) !important;
      }
      [data-testid="stExpander"] { background: #fff; border: 1px solid var(--gl-line); border-radius: 8px; }
      hr { border-color: var(--gl-line) !important; }
      @media (max-width: 900px) {
        .block-container { padding: 1.25rem 1rem 2rem; }
      }
    </style>
    """, unsafe_allow_html=True)


apply_b2b_style()


@st.cache_resource(show_spinner="검토 엔진과 Company DB를 준비하는 중…")
def load_core():
    # greenlens_core는 적재 상황을 print로 알린다. Windows 콘솔 기본 인코딩(cp949)에서는
    # '—' 같은 문자가 UnicodeEncodeError를 내므로 stdout을 UTF-8로 맞춘다.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    import greenlens_core as gl
    return gl


gl = load_core()
ss = st.session_state

# 기획서: "친환경 인증 완료" 같은 승인성 배지를 쓰지 않는다.
# '근거 확인'도 초록색을 피해 승인으로 읽히지 않게 한다.
STATUS_STYLE = {
    "SUPPORTED": ("#1d4ed8", "#eff6ff"),
    "PARTIALLY_SUPPORTED": ("#b45309", "#fffbeb"),
    "CONTRADICTED": ("#b91c1c", "#fef2f2"),
    "INSUFFICIENT": ("#4b5563", "#f3f4f6"),
}
STATUS_NOTE = {
    "SUPPORTED": "등록된 자료와 일치합니다. 광고의 법적 적합성을 보장하지는 않습니다.",
    "PARTIALLY_SUPPORTED": "자료가 주장의 일부만 덮습니다. 확인된 범위로 표현을 좁히면 재검토할 수 있습니다.",
    "CONTRADICTED": "자료와 주장이 서로 다른 값·대상을 가리킵니다. 사실관계를 바로잡아야 합니다.",
    "INSUFFICIENT": "근거를 확인하지 못했습니다. 주장이 거짓이라는 뜻이 아니며, 자료 요청 단계입니다.",
}
STEPS = ["1 광고 입력", "2 분석 진행", "3 검토 Report", "4 보완 및 재검토", "5 최종 확인"]


# ─────────────────────────────────────────────
# 세션 상태
# ─────────────────────────────────────────────
def init_state() -> None:
    ss.setdefault("stage", "input")
    ss.setdefault("ad_text", "")
    ss.setdefault("product_ids", [])
    ss.setdefault("results", [])
    ss.setdefault("reviewed_sig", None)
    ss.setdefault("decisions", {})
    ss.setdefault("run_seq", 0)
    ss.setdefault("form_rev", 0)
    # LangGraph 체크포인터는 모듈 단위로 공유된다. 브라우저 세션마다 thread_id를
    # 다르게 주지 않으면 새로고침·다중 접속 시 이전 검토 상태를 이어받는다.
    ss.setdefault("session_key", uuid.uuid4().hex[:8])
    ss.setdefault("session_product_ids", [])
    ss.setdefault("intake_evidence", [])


def signature(ad_text: str, product_ids: list[str]) -> str:
    return json.dumps([ad_text.strip(), sorted(product_ids)], ensure_ascii=False)


init_state()

# ad_text / product_ids는 위젯 키가 아니라 별도 상태로 들고 있는다.
# Streamlit은 렌더링되지 않은 위젯의 state를 버리므로, 위젯 키를 그대로 쓰면
# 검토 화면으로 넘어간 순간 입력값이 사라진다.
# 예시 버튼으로 값을 바꿀 때는 form_rev를 올려 위젯을 새로 만든다.
# (session_state에서 키만 지워도 프론트엔드는 이전 값을 그대로 들고 있다)
if "_pending" in ss:
    pending = ss.pop("_pending")
    ss["product_ids"] = pending["product_ids"]
    ss["ad_text"] = pending["ad_text"]
    ss["form_rev"] += 1


# ─────────────────────────────────────────────
# 표시 도우미
# ─────────────────────────────────────────────
def pill(text: str, fg: str, bg: str) -> str:
    return (f"<span style='background:{bg};color:{fg};border:1px solid {fg}33;"
            f"border-radius:6px;padding:2px 9px;font-size:0.82rem;font-weight:600;"
            f"white-space:nowrap'>{html.escape(text)}</span>")


def highlight(ad_text: str, span: list[int]) -> str:
    s, e = span
    s, e = max(0, s), min(len(ad_text), e)
    return (html.escape(ad_text[:s])
            + "<mark style='background:#fde68a;color:#111827;padding:1px 2px'>"
            + html.escape(ad_text[s:e]) + "</mark>"
            + html.escape(ad_text[e:]))


def source_badge(is_synthetic, source_type: str = "") -> str:
    """공개·제출·합성 자료를 구분해 표시한다."""
    if str(is_synthetic) == "True" or "합성" in str(source_type):
        return "가상(합성) 자료"
    if "제출" in str(source_type):
        return "기업 제출 자료"
    return "공식/공개 기록"


# 판정이 무엇과 무엇을 대조한 결과인지 값 대 값으로 보여준다.
# "주장 인증번호는 29431이나 등록된 번호는 29432"라는 문장보다 29431 ≠ 29432가 빨리 읽힌다.
_MATCH_CODES = {"CERT_NO_EQUAL", "CERT_RECORD_VALID", "CERT_VALID", "VALUE_EQUAL",
                "VALUE_AND_SCOPE_EQUAL", "THRESHOLD_MET", "PERIOD_VALID"}


def comparison_rows(claim: dict, report: dict) -> list[tuple[str, str, str, str]]:
    """(항목, 광고 주장, 대조한 자료, 관계기호). 대조할 자료가 없으면 빈 목록."""
    code = report.get("reason_code", "")
    evidence = report.get("evidence", [])
    if not evidence:
        return []
    ev = evidence[0]
    sign = "=" if code in _MATCH_CODES else "≠"
    rows: list[tuple[str, str, str, str]] = []

    if code.startswith("CERT_NO"):
        actual = ", ".join(sorted({e["cert_no"] for e in evidence if e.get("cert_no")}))
        rows.append(("인증번호", str(claim.get("claim_value", "")), actual or "-", sign))
    elif code.startswith("CERT_") or code in ("PERIOD_VALID", "PERIOD_EXPIRED"):
        rows.append(("인증 유효기간", f"기준일 {gl.EVALUATION_AS_OF}",
                     f"~ {ev.get('valid_to') or '기간 미기재'}", sign))
    elif code.startswith("THRESHOLD"):
        criterion = gl.get_criterion(claim.get("criterion_id", "")) or {}
        rows.append((str(criterion.get("시험항목", "시험값")),
                     f"{ev.get('value','')}{ev.get('unit','')}",
                     f"{criterion.get('기준연산자','')} {criterion.get('기준값','')}"
                     f"{criterion.get('단위','')}".strip(), sign))
    elif claim.get("claim_value"):
        rows.append(("수치", f"{claim.get('claim_value','')}{claim.get('claim_unit','')}",
                     f"{ev.get('value','')}{ev.get('unit','')}",
                     "≠" if code in ("VALUE_DIFFERENT", "UNIT_DIFFERENT") else "="))

    scope_sign = {"VALUE_AND_SCOPE_EQUAL": "=", "CLAIM_SCOPE_BROADER": "⊃",
                  "SCOPE_UNCLEAR": "?"}.get(code)
    if scope_sign:
        rows.append(("적용 범위", claim.get("claim_scope") or "미명시",
                     ev.get("scope") or "미기재", scope_sign))
    return rows


def render_comparison(rows: list[tuple[str, str, str, str]]) -> None:
    tone = {"=": ("#1d4ed8", "#eff6ff"), "≠": ("#b91c1c", "#fef2f2"),
            "⊃": ("#b45309", "#fffbeb"), "?": ("#4b5563", "#f3f4f6")}
    for label, left, right, sign in rows:
        fg, bg = tone.get(sign, tone["?"])
        st.markdown(
            "<div style='display:flex;align-items:center;gap:12px;background:#f9fafb;"
            "color:#111827;border-radius:8px;padding:10px 14px;margin-bottom:6px'>"
            "<div style='flex:1;min-width:0'>"
            f"<div style='font-size:0.72rem;color:#6b7280'>광고 주장 · {html.escape(label)}</div>"
            f"<div style='font-size:0.98rem;font-weight:600'>{html.escape(str(left))}</div></div>"
            f"<div style='flex:0 0 auto;font-size:1.1rem;font-weight:700;color:{fg};"
            f"background:{bg};border-radius:6px;padding:1px 10px'>{sign}</div>"
            "<div style='flex:1;min-width:0'>"
            "<div style='font-size:0.72rem;color:#6b7280'>대조한 자료</div>"
            f"<div style='font-size:0.98rem;font-weight:600'>{html.escape(str(right))}</div></div>"
            "</div>",
            unsafe_allow_html=True,
        )


def current(rec: dict) -> dict:
    """해당 Claim의 현재 상태 (interrupt 대기 중이면 request, 아니면 report)."""
    return rec["state"]


def status_of(rec: dict) -> str:
    st_ = current(rec)
    return "INSUFFICIENT" if st_["needs_human"] else st_["report"]["status"]


def label_of(rec: dict) -> str:
    st_ = current(rec)
    return st_["request"]["label"] if st_["needs_human"] else st_["report"]["label"]


def review_state_of(rec: dict) -> str:
    st_ = current(rec)
    return "담당자 필수 확인" if st_["needs_human"] else st_["report"]["review_state"]


# ─────────────────────────────────────────────
# 사이드바 — 상시 안내
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### GreenLens")
    st.caption("환경성 광고 사전점검 시스템")

    st.info(
        "본 결과는 제공된 자료와 등록된 기준을 바탕으로 한 **사전점검 참고자료**입니다. "
        "제품의 친환경성이나 광고의 법적 적합성을 보증하지 않으며, "
        "최종 게시는 담당자 검토 후 결정해야 합니다.",
        icon="ℹ️",
    )

    st.markdown("**자료 기준일**")
    st.code(gl.EVALUATION_AS_OF, language=None)

    st.markdown("**등록 자료**")
    st.caption(
        f"제품 {len(gl.product_master):,}건 · 공개 Evidence {len(gl.public_evidence):,}건 · "
        f"기준 {len(gl.criteria_master)}건\n\n"
        f"AI는 Company DB에 쓰기 권한이 없습니다. 등록은 운영자의 수동 절차입니다."
    )

    st.markdown("**AI 구성**")
    st.caption(
        f"- 판정: 규칙 비교 {len(gl.RULES)}종 (LLM이 판정을 바꾸지 않음)\n"
        f"- Claim 추출: 규칙 패턴 {len(gl.CLAIM_PATTERNS)}종\n"
        f"- LLM 보조: {'사용' if gl.USE_LLM else '미사용'}\n"
        f"- Policy RAG: {'사용' if gl.policy_retriever else '미사용(기준 직접 조회)'}"
    )

    with st.expander("개인정보 · 입력 안내"):
        st.caption(
            "- 주민등록번호·전화번호·주소 등 개인정보를 입력하지 마세요.\n"
            "- 기업 기밀자료 대신 예시 또는 가상 자료를 사용하세요.\n"
            "- 제출 자료는 이번 검토에만 쓰이며 Company DB에 저장되지 않습니다.\n"
            "- 지원 형식: 텍스트 추출이 가능한 PDF, TXT, 직접 입력. "
            "이미지로만 된 PDF는 수동 입력 경로를 이용하세요 (OCR은 후속 과제)."
        )

    st.info(
        "화면의 제품은 공개 인증 기록이지만, 입력하는 광고 문구는 검토용 예시이며 "
        "해당 기업의 실제 광고나 위반사례가 아닙니다.",
        icon="ℹ️",
    )

    if ss.results:
        st.divider()
        if st.button("새 검토 시작", width="stretch"):
            rev = ss.get("form_rev", 0) + 1
            # 직접 입력한 임시 제품은 검토가 끝나면 지운다 (기획서: 세션 범위로만 보관)
            for pid in ss.get("session_product_ids", []):
                gl.clear_session_product(pid)
            for k in ("results", "decisions", "reviewed_sig", "ad_text",
                      "product_ids", "extraction", "intake_evidence", "session_product_ids"):
                ss.pop(k, None)
            init_state()
            ss.form_rev = rev
            st.rerun()


# ─────────────────────────────────────────────
# 상단 진행 표시
# ─────────────────────────────────────────────
STAGE_INDEX = {"input": 0, "review": 2, "final": 4}
st.title("환경성 광고 사전점검")
st.caption("광고 Claim과 등록·제출 증빙을 대조해 확인 범위와 필요한 다음 조치를 안내합니다.")

# 같은 엔진을 두 사용자가 쓴다. 기업은 게시 전 한 건을 점검하고,
# 감독기관은 등록된 문구를 한 번에 훑어 우선 검토 대상을 좁힌다.
ss.mode = st.radio(
    "사용 방식",
    ["단건 검토", "일괄 스크리닝"],
    index=["단건 검토", "일괄 스크리닝"].index(ss.get("mode", "단건 검토")),
    horizontal=True, label_visibility="collapsed",
    captions=["기업 담당자 — 게시 전 광고 문구 한 건을 점검",
              "감독기관 — 등록된 문구를 한 번에 훑어 우선 검토 대상 선별"],
)

if ss.mode == "단건 검토":
    cur_step = STAGE_INDEX[ss.stage]
    cols = st.columns(len(STEPS))
    for i, (col, name) in enumerate(zip(cols, STEPS)):
        done = i <= cur_step
        col.markdown(
            f"<div style='text-align:center;padding:6px 2px;border-top:3px solid "
            f"{'#2563eb' if done else '#9ca3af55'};color:{'inherit' if done else '#9ca3af'};"
            f"font-size:0.85rem;font-weight:{600 if done else 400}'>{name}</div>",
            unsafe_allow_html=True,
        )
st.write("")

# ─────────────────────────────────────────────
# 제품 목록
# ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def product_options(full: bool) -> dict[str, str]:
    if full:
        df = gl.product_master[["product_id", "company_name", "product_name", "EL_code"]].fillna("")
        # 기획서 대상 업종은 생활소비재다. 가구·이중 바닥재는 데이터에는 있으나 검토 대상이 아니다.
        df = df[~df["EL_code"].isin(gl.NON_CONSUMER_GROUPS)]
    else:
        df = gl.demo_catalog[["product_id", "company_name", "product_name"]].fillna("")
    df = df.drop_duplicates("product_id")
    return {r["product_id"]: f"{r['product_name']} · {r['company_name']} ({r['product_id']})"
            for r in df.to_dict("records")}


@st.cache_data(show_spinner=False)
def el_code_options() -> dict[str, str]:
    """직접 입력 제품의 제품군 선택지.
    기획서가 정한 대상 업종(생활소비재) 중 인증기준이 등록된 제품군만 제시한다.
    필수가 아니다 — 모르면 비워 두고 진행할 수 있다."""
    return {"": "기타"} | gl.mvp_group_options()


@st.cache_data(show_spinner=False)
def catalog_samples() -> dict[str, str]:
    df = gl.demo_catalog[["product_id", "primary_claim_text"]].fillna("")
    return dict(df.drop_duplicates("product_id").values)


SCENARIOS = [
    ("인증번호 범위 확인",
     ["PRD-E0028", "PRD-E0038"],
     "키친솝 올리브&바질 1.2L와 3L는 모두 환경표지 인증번호 29431을 받은 친환경 제품입니다."),
    ("근거가 있는 표현 + 모호한 표현",
     ["PRD-E0028"],
     "키친솝 올리브&바질 친환경 주방세제 1.2L는 환경표지 인증번호 29431 제품입니다. "
     "지구를 생각한 친환경 세제입니다. 레몬 향이 상쾌합니다."),
    ("자료 요청 → 보충 → 재검토",
     ["PRD-S0001"],
     "퓨어클린 주방세제 1L는 제품 전체에 재생 플라스틱 30%를 사용했습니다."),
    ("기준 검색 실패 → 재조회",
     ["P-D005"],
     "그린렌즈 디시케어 베이직 500은 계면활성제 함량 기준을 충족합니다."),
]


# ─────────────────────────────────────────────
# 화면 1 — 광고 입력
# ─────────────────────────────────────────────
def screen_input() -> None:
    if switched := ss.pop("_switched_to", None):
        name, dropped = switched
        st.info(
            f"검토 대상을 직접 입력한 '{name}'(임시 제품)으로 바꿨습니다."
            + (f" 기존에 선택한 제품 {dropped}건은 해제했습니다. "
               "한 광고에 함께 검토하려면 제품 선택에서 다시 추가하세요." if dropped else ""),
            icon="🔄")
    st.subheader("1. 광고 입력")

    with st.container(border=True):
        st.markdown("##### 빠른 시연")
        st.caption("대표적인 검토 흐름을 불러와 화면과 판정 기준을 확인할 수 있습니다.")
        cols = st.columns(len(SCENARIOS))
        for col, (name, pids, text) in zip(cols, SCENARIOS):
            if col.button(name, width="stretch", help=text):
                ss["_pending"] = {"product_ids": pids, "ad_text": text}
                st.rerun()

    st.write("")
    with st.container(border=True):
        st.markdown("##### 검토 대상과 광고 문구")
        st.caption("제품을 먼저 특정한 뒤, 게시 예정 문구를 그대로 입력하세요.")
        product_col, text_col = st.columns([1, 1.35], gap="large")
        with product_col:
            full = st.checkbox(
                "전체 제품 목록에서 선택",
                help="기본은 시연용 카탈로그 40건입니다. 체크하면 Company DB의 전체 제품에서 고릅니다.",
            )
            options = product_options(full)
            # 예시가 카탈로그 밖 제품을 고른 경우, 그리고 직접 입력한 임시 제품을 선택지에 보강한다
            if outside := [p for p in ss.product_ids if p not in options]:
                every = product_options(True)
                options = {**options, **{p: every[p] for p in outside if p in every}}
            options |= {p: f"{gl.SESSION_PRODUCTS[p]['product_name']} · 직접 입력 (임시)"
                        for p in ss.session_product_ids if p in gl.SESSION_PRODUCTS}
            ss.product_ids = st.multiselect(
                "제품 선택",
                options=list(options),
                default=[p for p in ss.product_ids if p in options],
                format_func=lambda p: options[p],
                key=f"w_products_{ss.form_rev}",
                help="한 광고에 여러 SKU가 함께 등장하면 모두 선택하세요. "
                     "용량별로 인증번호가 다를 수 있어 SKU마다 따로 검토합니다.",
            )
            with st.expander("목록에 없는 제품 직접 입력"):
                st.caption(
                    "Company DB에 없는 제품도 검토할 수 있습니다. 입력한 제품은 **이번 검토에만** "
                    "쓰이며 Company DB에 등록되지 않습니다. 등록은 운영자가 자료를 검증한 뒤 "
                    "수행하는 별도 절차입니다."
                )
                name = st.text_input("제품명", key=f"sp-name-{ss.form_rev}",
                                     placeholder="에코브라이트 주방세제 1L")
                company = st.text_input("회사명 (선택)", key=f"sp-co-{ss.form_rev}")
                groups = el_code_options()
                el = st.selectbox(
                    "제품군 (선택)", list(groups), format_func=lambda k: groups[k],
                    key=f"sp-el-{ss.form_rev}",
                    help="적용할 인증기준을 좁히는 데만 씁니다. 필수가 아니며, 해당하는 제품군이 "
                         "없으면 '기타'로 두어도 검토는 진행됩니다. 다만 기준을 특정하지 못하면 "
                         "'자료 요청'으로 처리되고 담당자 확인이 필요합니다.")
                if not el:
                    st.caption("'기타'로 두면 적용할 인증기준을 좁히지 못해 "
                               "기준 대조 항목은 담당자 확인으로 넘어갑니다.")
                if st.button("이 제품으로 검토", key=f"sp-go-{ss.form_rev}", width="stretch"):
                    if not name.strip():
                        st.warning("제품명을 입력해 주세요.")
                    else:
                        product = gl.register_session_product(
                            product_name=name, company_name=company, el_code=el,
                            product_category=groups.get(el, ""))
                        ss.session_product_ids.append(product["product_id"])
                        # 검토 대상을 이 제품으로 바꾼다. 기존 선택을 남겨 두면 관계없는
                        # 제품에까지 같은 Claim이 붙어 결과가 섞인다.
                        replaced = [p for p in ss.product_ids
                                    if p != product["product_id"]]
                        ss["_pending"] = {"product_ids": [product["product_id"]],
                                          "ad_text": ss.ad_text}
                        ss["_switched_to"] = (product["product_name"], len(replaced))
                        st.rerun()
                st.caption(
                    "임시 제품에는 공개 인증 기록이 없으므로 대부분 '자료 요청'으로 시작합니다. "
                    "인증 주장은 자가 신고 자료만으로 확인되지 않고, 공개 인증내역 조회로 대조합니다."
                )

            if ss.product_ids:
                samples = catalog_samples()
                picks = [(p, samples[p]) for p in ss.product_ids if p in samples]
                if picks:
                    with st.expander(f"선택한 제품의 카탈로그 예시 문구 ({len(picks)}건)"):
                        for pid, text in picks:
                            c1, c2 = st.columns([5, 1])
                            c1.caption(text)
                            if c2.button("입력", key=f"use-{pid}", width="stretch"):
                                ss["_pending"] = {"product_ids": ss.product_ids, "ad_text": text}
                                st.rerun()
        with text_col:
            ss.ad_text = st.text_area(
                "광고 문구",
                value=ss.ad_text,
                key=f"w_ad_{ss.form_rev}",
                height=205,
                placeholder="예) 이 제품은 환경표지 인증을 받았으며, 용기 본체에 재생 플라스틱 30%를 사용했습니다.",
                help="게시 예정인 문구를 그대로 붙여 넣으세요. 여러 문장을 넣으면 문장별로 나누어 검토합니다.",
            )

    # 기획서 8-2: 입력이 바뀌면 이전 검토 상태를 초기화한다.
    # 위젯 값을 읽은 뒤에 비교해야 같은 실행에서 변경을 잡아낼 수 있다.
    if ss.reviewed_sig and signature(ss.ad_text, ss.product_ids) != ss.reviewed_sig:
        ss.results, ss.decisions, ss.reviewed_sig = [], {}, None
        ss.intake_evidence = []
        st.info("입력이 변경되어 이전 검토 결과를 초기화했습니다.", icon="🔄")

    with st.expander("이번 검토에 참고할 증빙 첨부 (선택)"):
        st.caption("제출 자료는 이번 검토에만 반영되며 Company DB에 저장되지 않습니다.")
        intake = evidence_form("intake", ss.product_ids)
        if intake:
            ss.intake_evidence = intake
            st.success(f"{len(intake)}건을 이번 검토에 사용합니다.")

    st.write("")
    ready = bool(ss.ad_text.strip()) and bool(ss.product_ids)
    if st.button("검토 시작", type="primary", disabled=not ready, width="stretch"):
        run_review()
    if not ready:
        st.caption("제품을 선택하고 광고 문구를 입력하면 검토를 시작할 수 있습니다.")


# ─────────────────────────────────────────────
# 증빙 입력 폼 (첨부 · 보완 화면에서 공용)
# ─────────────────────────────────────────────
def read_pdf_text(file) -> tuple[str, bool]:
    """(추출 텍스트, 이미지 PDF 여부)"""
    try:
        from pypdf import PdfReader
    except ImportError:
        return "", False
    try:
        text = "\n".join((p.extract_text() or "") for p in PdfReader(file).pages)
    except Exception:
        return "", False
    return text.strip(), not text.strip()


def evidence_form(key: str, product_ids: list[str]) -> list[dict]:
    """자료 제출 입력. 반환: Evidence 레코드 목록 (없으면 빈 목록)."""
    if not product_ids:
        st.caption("먼저 제품을 선택하세요.")
        return []

    records: list[dict] = []
    target = (product_ids[0] if len(product_ids) == 1 else
              st.selectbox("자료가 해당하는 제품", product_ids, key=f"{key}-target"))

    tab_manual, tab_file, tab_sample = st.tabs(["직접 입력", "파일 첨부", "시연용 샘플"])

    with tab_manual:
        st.caption("인증서·성적서의 항목을 그대로 옮겨 적으세요. 없는 값은 비워 두면 됩니다.")
        c1, c2, c3 = st.columns(3)
        ev_type = c1.text_input("자료 유형", key=f"{key}-type",
                                placeholder="재생원료 함량 확인서")
        value = c2.text_input("수치", key=f"{key}-value", placeholder="30")
        unit = c3.text_input("단위", key=f"{key}-unit", placeholder="%")
        c4, c5, c6 = st.columns(3)
        scope = c4.text_input("적용 부위·범위", key=f"{key}-scope", placeholder="용기 본체")
        cert_no = c5.text_input("인증번호", key=f"{key}-cert", placeholder="29431")
        valid_to = c6.text_input("유효기간 종료일", key=f"{key}-to", placeholder="2028-08-17")
        content = st.text_area("내용 / 원문 발췌", key=f"{key}-content", height=80)
        if st.button("이 자료 사용", key=f"{key}-manual-go"):
            if not any([ev_type, value, scope, cert_no, content]):
                st.warning("최소한 자료 유형이나 수치 중 하나는 입력해 주세요.")
            else:
                records.append({
                    "evidence_id": f"SESSION-MANUAL-{datetime.now():%H%M%S}",
                    "product_id": target, "evidence_type": ev_type, "content": content,
                    "cert_no": cert_no, "value": value, "unit": unit, "scope": scope,
                    "valid_to": valid_to, "verification_status": "승인",
                    "is_synthetic": "True", "origin": "SESSION",
                })

    with tab_file:
        up = st.file_uploader("PDF 또는 TXT", type=["pdf", "txt"], key=f"{key}-file")
        if up is not None:
            if up.name.lower().endswith(".pdf"):
                text, is_image = read_pdf_text(up)
                if is_image:
                    st.warning(
                        "텍스트를 추출하지 못했습니다. 이미지로만 된 PDF로 보입니다. "
                        "'직접 입력' 탭에 항목을 옮겨 적어 주세요. (OCR은 후속 과제입니다)",
                        icon="🖼️",
                    )
                    text = ""
            else:
                text = up.read().decode("utf-8", errors="replace")
            if text:
                st.text_area("추출된 텍스트", text[:2000], height=120, disabled=True,
                             key=f"{key}-preview")
                st.caption(
                    "수치·적용 범위는 " +
                    ("LLM이 구조화합니다." if gl.parse_evidence_text else
                     "자동으로 구조화되지 않습니다(LLM 미사용). 규칙 대조가 필요하면 '직접 입력'을 쓰세요.")
                )
                if st.button("이 자료 사용", key=f"{key}-file-go"):
                    records.append({"__text__": text, "product_id": target})

    with tab_sample:
        pool = [e for e in gl.SESSION_EVIDENCE_POOL.values() if e["product_id"] == target]
        if not pool:
            st.caption("이 제품에는 준비된 시연용 자료가 없습니다.")
        for e in pool:
            st.markdown(
                f"**{e['evidence_id']}** · {e.get('evidence_type','')} · "
                f"{e.get('value','')}{e.get('unit','')} · 적용 범위 `{e.get('scope','')}` "
                + pill(source_badge(e.get("is_synthetic"), e.get("origin", "")), "#7c2d12", "#fff7ed"),
                unsafe_allow_html=True,
            )
            if st.button("이 자료 제출", key=f"{key}-sample-{e['evidence_id']}"):
                records.append(gl.sample_session_evidence(e["evidence_id"]))

    return records


# ─────────────────────────────────────────────
# 화면 2 — 분석 진행
# ─────────────────────────────────────────────
def run_review() -> None:
    ss.run_seq += 1
    prefix = f"{ss.session_key}-RUN{ss.run_seq}"
    intake = [e for e in ss.intake_evidence if not e.get("__text__")]

    with st.status("검토를 진행합니다", expanded=True) as box:
        st.write("① Claim 추출 — 광고 문구를 검증 가능한 단위로 나눕니다")
        ex = gl.extract_claims(ss.ad_text, ss.product_ids)
        st.write(f"　→ Claim {len(ex['claims'])}건 추출"
                 + (f", {len(ex['rejected'])}건은 원문에 없어 기각" if ex["rejected"] else ""))

        results = []
        bar = st.progress(0.0)
        for i, claim in enumerate(ex["claims"], 1):
            st.write(f"② ③ ④ `{claim['claim_id']}` 기준 검색 → 근거 조회 → 대조")
            tid = gl.claim_thread_id(prefix, claim)
            state = gl.start_review(claim, tid, session_evidence=intake)
            results.append({"claim": claim, "thread_id": tid, "state": state, "history": []})
            bar.progress(i / max(1, len(ex["claims"])))

        st.write("⑤ 검토 Report 생성 완료")
        box.update(label=f"검토 완료 — Claim {len(results)}건", state="complete", expanded=False)

    ss.extraction = ex
    ss.results = results
    ss.reviewed_sig = signature(ss.ad_text, ss.product_ids)
    ss.decisions = {}
    ss.stage = "review"
    st.rerun()


# ─────────────────────────────────────────────
# 화면 3·4 — 검토 Report + 보완 및 재검토
# ─────────────────────────────────────────────
def render_claim(idx: int, rec: dict) -> None:
    claim, state = rec["claim"], rec["state"]
    status = status_of(rec)
    fg, bg = STATUS_STYLE[status]

    temp = claim["product_id"] in gl.SESSION_PRODUCTS
    st.markdown(
        f"#### {claim['claim_id']} · {claim.get('product_name','')} "
        f"<span style='color:#6b7280;font-size:0.8rem'>({claim['product_id']})</span>"
        + (" " + pill("임시 제품 · Company DB 미등록", "#7c2d12", "#fff7ed") if temp else ""),
        unsafe_allow_html=True,
    )
    # 담당자가 문구를 고친 뒤에는 원문이 아니라 수정한 문장을 보여준다.
    revised = claim.get("revised")
    body_html = html.escape(claim["claim_text"]) if revised else highlight(ss.ad_text, claim["span"])
    st.markdown(
        "<div style='background:#f9fafb;color:#111827;border-left:3px solid #d1d5db;"
        f"padding:8px 12px;font-size:0.92rem'>{body_html}</div>",
        unsafe_allow_html=True,
    )
    st.caption("담당자가 수정한 문장입니다. 원문은 아래 '변경 전후'에서 확인할 수 있습니다."
               if revised else "노란색 표시가 이 Claim으로 추출된 부분입니다.")
    st.write("")

    # 검토 결과와 담당자 확인 상태를 분리 표시 (기획서 F-5)
    st.markdown(
        "검토 결과 " + pill(label_of(rec), fg, bg)
        + " &nbsp;&nbsp; 확인 상태 " + pill(review_state_of(rec), "#374151", "#f3f4f6"),
        unsafe_allow_html=True,
    )
    st.caption(STATUS_NOTE[status])

    body = state["request"] if state["needs_human"] else state["report"]

    # 무엇과 무엇을 대조했는지 값으로 먼저 보여주고, 설명은 그 아래에 둔다
    if not state["needs_human"]:
        render_comparison(comparison_rows(claim, state["report"]))

    reasons = body.get("reason", body.get("rationale", []))
    for line in reasons:
        st.markdown(f"- {line}")

    # ⑤ 근거를 못 찾은 원인 — 검색 실패인지 자료 부재인지
    diag = body.get("diagnosis") or {}
    if diag:
        st.caption(f"원인 분기 — **[{diag['kind']}]** {diag['label']}  \n{diag['detail']}")
    if state["needs_human"]:
        # 사람 개입 대기 중에도 그래프가 지나온 경로를 볼 수 있어야 한다
        trace = gl.graph.get_state(gl._cfg(rec["thread_id"])).values.get("trace", [])
        if trace:
            with st.expander("처리 경로"):
                st.code("\n".join(trace), language=None)

    if claim.get("unspecified"):
        st.caption(f"미명시 항목: {', '.join(claim['unspecified'])} — 추정해 채우지 않았습니다.")
    if not claim.get("validation_rule_id"):
        st.caption("이 문장은 MVP가 지원하는 Claim 유형으로 분류되지 않아 담당자 검토가 필요합니다.")

    if not state["needs_human"]:
        report = state["report"]
        for w in report.get("warnings", []):
            st.warning(w, icon="⏳")

        tabs = st.tabs(["판단 기준", "확인한 자료", "부족한 자료", "처리 경로"])
        with tabs[0]:
            refs = report.get("policy_refs", [])
            if refs:
                st.dataframe(
                    pd.DataFrame(refs).rename(columns={
                        "criterion_id": "기준 ID", "item": "시험항목", "doc": "기준 문서",
                        "page": "참고 조항", "trust": "신뢰등급"}),
                    hide_index=True, width="stretch")
                st.caption("신뢰등급이 VERIFIED가 아닌 기준은 단독 판정 근거로 쓰지 않습니다.")
            else:
                st.caption("이 Claim에 연결된 Policy 기준이 없습니다.")
        with tabs[1]:
            evs = report.get("evidence", [])
            if evs:
                df = pd.DataFrame(evs)
                df["출처 유형"] = df.apply(
                    lambda r: source_badge(r["is_synthetic"], r.get("source_type", "")), axis=1)
                st.dataframe(
                    df[["evidence_id", "출처 유형", "evidence_type", "cert_no",
                        "value", "unit", "scope", "valid_to"]].rename(columns={
                        "evidence_id": "자료 ID", "evidence_type": "자료 유형",
                        "cert_no": "인증번호", "value": "값", "unit": "단위",
                        "scope": "적용 범위", "valid_to": "유효기간 종료"}),
                    hide_index=True, width="stretch")
                if (df["is_synthetic"].astype(str) == "True").any():
                    st.caption("⚠ 가상(합성) 자료가 포함되어 있습니다. "
                               "실제 제품의 측정값이나 환경성을 보증하지 않습니다.")
            else:
                st.caption("대조에 사용한 자료가 없습니다.")
        with tabs[2]:
            missing = report.get("missing_evidence", [])
            if missing:
                for m in missing:
                    st.markdown(f"- {m}")
            else:
                st.caption("추가로 요청한 자료가 없습니다.")
            if report.get("rejected_session_evidence"):
                st.caption(f"제품이 달라 제외한 제출 자료: {report['rejected_session_evidence']}")
        with tabs[3]:
            st.caption(f"Policy 조회 {report.get('policy_attempts', 1)}회"
                       + (" (질의 재구성 후 재조회 포함)" if report.get("policy_attempts", 1) > 1 else ""))
            st.code("\n".join(report.get("trace", [])), language=None)
            if report.get("diagnostics"):
                st.caption("근거를 못 찾은 원인 기록 — 검색 실패와 자료 부재를 구분합니다.")
                st.dataframe(
                    pd.DataFrame(report["diagnostics"])[["kind", "cause", "detail"]].rename(
                        columns={"kind": "구분", "cause": "원인", "detail": "설명"}),
                    hide_index=True, width="stretch")
            if report.get("explanation"):
                st.caption("AI 설명문 (검색된 근거와 구분되는 해석입니다)")
                st.info(report["explanation"])

        if report.get("change_from_previous"):
            ch = report["change_from_previous"]
            st.success(
                f"변경 전후 — 검토 결과: **{ch['status'][0]} → {ch['status'][1]}**  \n"
                f"문구: {ch['claim_text'][0]}  \n→ {ch['claim_text'][1]}",
                icon="🔁",
            )

    # ── 화면 4: 보완 ──
    if state["needs_human"]:
        req = state["request"]
        if req.get("request_kind") == "PRODUCT_ID":
            # Company DB는 정형 조회라 재조회로 풀리지 않는다 → 식별 기준을 사람에게 확인
            st.warning(
                "자료가 없는 것이 아니라 **제품 식별**이 어긋났을 수 있습니다. "
                "같은 회사·같은 제품군에서 이름이 거의 같은 제품에는 자료가 등록되어 있습니다.",
                icon="🔍")
            st.caption(req["notice"])
            cands = req.get("candidate_products", [])
            keep = f"__keep__{claim['product_id']}"
            labels = {keep: f"제품이 맞습니다 — 그대로 진행 ({claim['product_id']})"}
            labels |= {c["product_id"]: f"{c['product_name']} ({c['product_id']}) · 이름 유사도 {c['similarity']}"
                       for c in cands}
            pick = st.radio("이 광고의 제품이 다음 중 하나입니까?", list(labels),
                            format_func=lambda k: labels[k], key=f"pick-{idx}")
            if st.button("확인하고 재검토", key=f"pick-go-{idx}"):
                confirm_product(idx, None if pick == keep else pick)
        else:
            st.error("판정을 내리지 않고 필요한 자료를 요청합니다. 자료 부재는 거짓이나 위반이 아닙니다.",
                     icon="📄")
            st.markdown("**요청한 자료**")
            # 담당자가 공급업체에 하나씩 요청하고 지워가는 단위라 체크리스트로 둔다.
            # 체크 표시는 담당자 메모일 뿐이며 판정에는 영향을 주지 않는다.
            for n, m in enumerate(req["missing_evidence"]):
                st.checkbox(m, key=f"req-{idx}-{n}-{len(rec['history'])}")
            st.caption(req["notice"] + " 체크는 담당자 메모이며 판정에는 반영되지 않습니다.")
            with st.expander("자료 제출하고 재검토", expanded=True):
                new_ev = evidence_form(f"fix{idx}", [claim["product_id"]])
                if new_ev:
                    submit_evidence(idx, new_ev)

    # ── 화면 4: 문구 수정 ──
    with st.expander("문구 수정 후 재검토"):
        st.caption("문구 수정은 담당자가 합니다. 수정한 문장에서 Claim을 다시 추출해 재검토합니다.")
        new_text = st.text_area("수정한 문장", value=claim["claim_text"],
                                key=f"revise-{idx}-{len(rec['history'])}", height=80)
        if st.button("수정문으로 재검토", key=f"revise-go-{idx}-{len(rec['history'])}"):
            revise(idx, new_text)


def submit_evidence(idx: int, records: list[dict]) -> None:
    rec = ss.results[idx]
    text_rec = next((r for r in records if r.get("__text__")), None)
    structured = [r for r in records if not r.get("__text__")]
    rec["history"].append(dict(rec["state"]))
    rec["state"] = gl.resume_review(
        rec["thread_id"],
        evidence=structured,
        evidence_text=text_rec["__text__"] if text_rec else None,
    )
    st.rerun()


def confirm_product(idx: int, product_id: str | None) -> None:
    """제품 식별 확인에 응답한다. 제품을 바꾸면 그 제품의 자료로 다시 대조한다."""
    rec = ss.results[idx]
    rec["history"].append(dict(rec["state"]))
    rec["state"] = gl.resume_review(rec["thread_id"], product_id=product_id or "")
    if product_id:
        product = gl.get_product(product_id) or {}
        rec["claim"] = {**rec["claim"], "product_id": product_id,
                        "product_name": product.get("product_name", "")}
    st.rerun()


def revise(idx: int, new_text: str) -> None:
    rec = ss.results[idx]
    claim = rec["claim"]
    if not new_text.strip():
        st.warning("수정한 문장을 입력해 주세요.")
        return

    ex = gl.extract_claims(new_text, [claim["product_id"]])
    if not ex["claims"]:
        st.warning("수정한 문장에서 검증 가능한 환경성 주장을 찾지 못했습니다. "
                   "주장을 삭제하려면 원문에서 해당 문장을 지우고 새로 검토하세요.")
        return

    new_claim = ex["claims"][0]
    ss.run_seq += 1
    new_thread = f"{rec['thread_id']}|rev{ss.run_seq}"
    rec["history"].append(dict(rec["state"]))
    rec["state"] = gl.revise_claim(
        rec["thread_id"], new_thread,
        claim_text=new_claim["claim_text"],
        validation_rule_id=new_claim["validation_rule_id"],
        criterion_id=new_claim["criterion_id"],
        claim_value=new_claim["claim_value"],
        claim_unit=new_claim["claim_unit"],
        claim_scope=new_claim["claim_scope"],
    )
    rec["thread_id"] = new_thread
    # 원문 하이라이트가 어긋나지 않도록 수정된 문장을 Claim에 반영
    merged = {**claim, **{k: new_claim[k] for k in
                          ("claim_text", "validation_rule_id", "criterion_id",
                           "claim_value", "claim_unit", "claim_scope", "unspecified",
                           "confidence")}}
    merged["span"] = [0, 0]      # 수정문은 원문 위치와 대응하지 않는다
    merged["revised"] = True
    rec["claim"] = merged
    st.rerun()


def screen_review() -> None:
    st.subheader("3. 검토 Report")
    counts = pd.Series([status_of(r) for r in ss.results]).value_counts()
    cols = st.columns(4)
    for col, key in zip(cols, ["SUPPORTED", "PARTIALLY_SUPPORTED", "CONTRADICTED", "INSUFFICIENT"]):
        col.metric(gl.STATUS_LABELS[key], int(counts.get(key, 0)))

    need = sum(1 for r in ss.results if review_state_of(r) == "담당자 필수 확인")
    if need:
        st.warning(f"담당자 필수 확인 항목 {need}건이 있습니다.", icon="👤")

    if ss.extraction["rejected"]:
        with st.expander(f"추출 단계에서 기각한 항목 {len(ss.extraction['rejected'])}건"):
            st.caption("광고 원문에 없는 주장·수치는 Claim으로 만들지 않습니다.")
            for r in ss.extraction["rejected"]:
                st.markdown(f"- `{r['matched_text'][:40]}` → {', '.join(r['reject_reason'])}")

    if ss.extraction["unknown_products"]:
        st.error(f"Company DB에서 찾지 못한 제품: {ss.extraction['unknown_products']} "
                 "— 자료 부재가 아니라 제품 식별 문제입니다.", icon="🔍")

    st.divider()
    for idx, rec in enumerate(ss.results):
        with st.container(border=True):
            render_claim(idx, rec)

    st.write("")
    c1, c2 = st.columns(2)
    if c1.button("입력 수정", width="stretch"):
        ss.stage = "input"
        st.rerun()
    if c2.button("최종 확인으로", type="primary", width="stretch"):
        ss.stage = "final"
        st.rerun()


# ─────────────────────────────────────────────
# 화면 5 — 최종 확인
# ─────────────────────────────────────────────
def screen_final() -> None:
    st.subheader("5. 최종 확인")
    st.caption("검토 결과와 담당자 확인은 별개입니다. 근거가 확인된 항목도 게시 전 확인을 거칩니다.")

    for idx, rec in enumerate(ss.results):
        claim = rec["claim"]
        status = status_of(rec)
        fg, bg = STATUS_STYLE[status]
        with st.container(border=True):
            c1, c2 = st.columns([3, 2])
            with c1:
                st.markdown(f"**{claim['claim_id']}** · {claim.get('product_name','')}")
                st.caption(claim["claim_text"])
                st.markdown(
                    "검토 결과 " + pill(label_of(rec), fg, bg)
                    + " &nbsp; 확인 상태 " + pill(review_state_of(rec), "#374151", "#f3f4f6"),
                    unsafe_allow_html=True,
                )
                body = rec["state"]["request"] if rec["state"]["needs_human"] else rec["state"]["report"]
                missing = body.get("missing_evidence", [])
                note = "" if rec["state"]["needs_human"] else rec["state"]["report"].get("review_note", "")
                reasons = body.get("reason", body.get("rationale", []))
                if missing:
                    st.caption("미확인 범위 · 필요한 조치: " + " / ".join(missing))
                elif note:
                    st.caption("필요한 조치: " + note)
                elif reasons:
                    st.caption("판단 근거: " + " / ".join(reasons))
            with c2:
                ss.decisions[claim["claim_id"]] = st.radio(
                    "담당자 확인",
                    ["확인 전", "확인 완료", "보류"],
                    index=["확인 전", "확인 완료", "보류"].index(
                        ss.decisions.get(claim["claim_id"], "확인 전")),
                    key=f"decide-{idx}",
                    horizontal=True,
                )

    done = sum(1 for v in ss.decisions.values() if v == "확인 완료")
    hold = sum(1 for v in ss.decisions.values() if v == "보류")
    c1, c2, c3 = st.columns(3)
    c1.metric("확인 완료", done)
    c2.metric("보류", hold)
    c3.metric("확인 전", len(ss.results) - done - hold)

    st.warning(
        "본 결과는 사전점검 참고자료입니다. 제품의 친환경성이나 광고의 법적 적합성을 보증하지 않으며, "
        "최종 게시 여부는 담당자가 결정합니다.",
        icon="⚠️",
    )

    record = {
        "검토일시": datetime.now().isoformat(timespec="seconds"),
        "자료_기준일": gl.EVALUATION_AS_OF,
        "광고_문구": ss.ad_text,
        "선택_제품": ss.product_ids,
        "claims": [
            {
                "claim_id": r["claim"]["claim_id"],
                "product_id": r["claim"]["product_id"],
                "claim_text": r["claim"]["claim_text"],
                "validation_rule_id": r["claim"]["validation_rule_id"],
                "검토_결과": label_of(r),
                "확인_상태": review_state_of(r),
                "담당자_확인": ss.decisions.get(r["claim"]["claim_id"], "확인 전"),
                "보충_횟수": len(r["history"]),
                "상세": r["state"].get("report") or r["state"].get("request"),
            }
            for r in ss.results
        ],
        "고지": gl.DISCLAIMER,
    }
    c1, c2 = st.columns(2)
    c1.download_button(
        "검토 기록 내려받기 (JSON)",
        data=json.dumps(record, ensure_ascii=False, indent=2, default=str),
        file_name=f"greenlens_review_{datetime.now():%Y%m%d_%H%M%S}.json",
        mime="application/json",
        width="stretch",
    )
    if c2.button("검토 Report로 돌아가기", width="stretch"):
        ss.stage = "review"
        st.rerun()


# ─────────────────────────────────────────────
# 일괄 스크리닝 — 감독기관용 1차 필터링
# 판정 엔진은 단건 검토와 완전히 같다. 훑는 범위만 다르다.
# ─────────────────────────────────────────────
SEVERITY = {"CONTRADICTED": 0, "INSUFFICIENT": 1, "PARTIALLY_SUPPORTED": 2, "SUPPORTED": 3}


def run_screening(rows: list[dict]) -> list[dict]:
    out = []
    bar = st.progress(0.0, text="스크리닝 중")
    for i, row in enumerate(rows, 1):
        ex = gl.extract_claims(row["primary_claim_text"], [row["product_id"]], use_llm=False)
        if ex["claims"]:
            claim = ex["claims"][0]
            session = [e for e in gl.SESSION_EVIDENCE_POOL.values()
                       if e["product_id"] == row["product_id"]]
            res = gl.assess(claim, session)
        else:
            claim = {}
            res = {"status": "INSUFFICIENT", "label": gl.STATUS_LABELS["INSUFFICIENT"],
                   "rationale": ["검증 가능한 환경성 주장을 찾지 못함"],
                   "review_state": "담당자 필수 확인"}
        out.append({**row, "status": res["status"], "label": res["label"],
                    "review_state": res["review_state"],
                    "reason": " / ".join(str(x) for x in res["rationale"])})
        bar.progress(i / len(rows), text=f"스크리닝 중 {i}/{len(rows)}")
    bar.empty()
    return sorted(out, key=lambda r: SEVERITY[r["status"]])


def screen_batch() -> None:
    st.subheader("일괄 스크리닝")
    st.caption("등록된 광고 문구를 한 번에 훑어 우선 검토 대상을 좁힙니다. "
               "판정 기준은 단건 검토와 동일하며, 여기서도 AI가 위반을 단정하지 않습니다.")

    catalog = gl.demo_catalog.fillna("")
    companies = ["전체"] + sorted(catalog["company_name"].unique())
    with st.container(border=True):
        pick = st.selectbox("대상 기업", companies)
        target = catalog if pick == "전체" else catalog[catalog["company_name"] == pick]
        st.caption(f"검토 대상 광고 문구 {len(target)}건")
        if st.button("스크리닝 실행", type="primary", width="stretch"):
            ss.screening = run_screening(target.to_dict("records"))
            st.rerun()

    results = ss.get("screening")
    if not results:
        return

    flagged = [r for r in results if r["status"] != "SUPPORTED"]
    must = [r for r in results if r["review_state"] == "담당자 필수 확인"]
    st.write("")
    cols = st.columns(4)
    cols[0].metric("검토한 문구", len(results))
    cols[1].metric("우선 검토 대상", len(flagged),
                   delta=f"{len(flagged) / len(results) * 100:.0f}%", delta_color="off")
    cols[2].metric("담당자 필수 확인", len(must))
    cols[3].metric("근거 확인", len(results) - len(flagged))

    st.caption(f"전체 {len(results)}건 중 {len(flagged)}건으로 좁혔습니다. "
               "나머지는 등록된 자료와 일치하지만, 법적 적합성을 보증하지는 않습니다.")
    st.divider()

    for n, row in enumerate(results):
        if row["status"] == "SUPPORTED":
            continue
        fg, bg = STATUS_STYLE[row["status"]]
        with st.container(border=True):
            left, right = st.columns([5, 1])
            with left:
                st.markdown(
                    f"**{row['product_name']}** "
                    f"<span style='color:#6b7280;font-size:0.8rem'>{row['company_name']}</span> "
                    + pill(row["label"], fg, bg)
                    + ("" if row["review_state"] != "담당자 필수 확인"
                       else " " + pill("필수 확인", "#374151", "#f3f4f6")),
                    unsafe_allow_html=True)
                st.caption(f"“{row['primary_claim_text']}”")
                st.caption(row["reason"])
            if right.button("상세 검토", key=f"drill-{n}", width="stretch"):
                ss["_pending"] = {"product_ids": [row["product_id"]],
                                  "ad_text": row["primary_claim_text"]}
                ss.mode = "단건 검토"
                ss.stage = "input"
                st.rerun()

    st.caption("‘상세 검토’를 누르면 해당 문구가 단건 검토로 넘어가며, "
               "근거·판단 기준·필요한 보완 자료를 건별로 확인할 수 있습니다.")


# ─────────────────────────────────────────────
if ss.mode == "일괄 스크리닝":
    screen_batch()
else:
    {"input": screen_input, "review": screen_review, "final": screen_final}[ss.stage]()
