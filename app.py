"""문헌 공통 구절 찾기 — Streamlit 화면. 실행: uv run streamlit run app.py"""

from pathlib import Path

import streamlit as st

from phrase_finder.errors import InputError
from phrase_finder.extract import extract
from phrase_finder.overlap import find_overlaps, validate_n
from phrase_finder.results import MAX_DISPLAY_ROWS, build_table, limit_for_display

DEFAULT_N = 6  # F6(N 조절 UI) 전까지는 고정

st.set_page_config(page_title="문헌 공통 구절 찾기", layout="wide")
st.title("문헌 공통 구절 찾기")
st.caption("CBETA P5 XML 문헌 두 개에서 겹치는 한문 구절을 찾아 대정장 위치와 함께 보여 줍니다.")

col_a, col_b = st.columns(2)
path_a = col_a.text_input("문헌 A (XML 파일 경로)", value="data/T45n1866.xml").strip()
path_b = col_b.text_input("문헌 B (XML 파일 경로)", value="data/T45n1868.xml").strip()


def describe(label: str, doc) -> str:
    divs = ", ".join(f"{t or '(없음)'}×{c}" for t, c in doc.div_types.items())
    return f"**{label}** {doc.doc_id} {doc.title} — 추출 {len(doc.text):,}자 / 구역(cb:div): {divs or '없음'}"


def load(label: str, path: str):
    try:
        return extract(path)
    except InputError as exc:
        raise InputError(f"문헌 {label}: {exc}") from exc


def run() -> None:
    validate_n(DEFAULT_N)
    if not path_a or not path_b:
        raise InputError("문헌 A와 B를 모두 선택하세요.")
    if Path(path_a).resolve() == Path(path_b).resolve():
        st.warning("문헌 A와 B가 같은 파일입니다. 자기 자신과 비교하면 본문 전체가 겹침으로 나옵니다.")

    with st.spinner("문헌을 읽고 겹치는 구절을 찾는 중입니다..."):
        doc_a = load("A", path_a)
        doc_b = load("B", path_b)
        matches = find_overlaps(doc_a.text, doc_b.text, DEFAULT_N)
        table = build_table(doc_a, doc_b, matches)

    st.markdown(describe("A", doc_a))
    st.markdown(describe("B", doc_b))
    st.caption("구역 type이 w인 부분(후대 발문 등)은 비교에서 제외했습니다.")

    if table.empty:
        st.info(f"겹치는 구절이 없습니다. N을 줄여 보세요. (현재 N={DEFAULT_N})")
        return

    st.subheader(f"결과: {len(table):,}건 (최소 겹침 길이 N={DEFAULT_N})")
    if len(table) > MAX_DISPLAY_ROWS:
        st.warning(
            f"전체 {len(table):,}건 중 길이가 긴 순으로 상위 {MAX_DISPLAY_ROWS}건만 표시했습니다. "
            "N을 올리면 결과를 줄일 수 있습니다."
        )
    st.dataframe(limit_for_display(table), width="stretch", hide_index=True)


if st.button("실행", type="primary"):
    try:
        run()
    except InputError as exc:
        st.error(str(exc))
