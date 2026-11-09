"""문헌 공통 구절 찾기 — Streamlit 화면. 실행: uv run streamlit run app.py"""

import streamlit as st

from phrase_finder.extract import extract
from phrase_finder.overlap import find_overlaps
from phrase_finder.results import build_table

DEFAULT_N = 6  # F6(N 조절 UI) 전까지는 고정

st.set_page_config(page_title="문헌 공통 구절 찾기", layout="wide")
st.title("문헌 공통 구절 찾기")
st.caption("CBETA P5 XML 문헌 두 개에서 겹치는 한문 구절을 찾아 대정장 위치와 함께 보여 줍니다.")

col_a, col_b = st.columns(2)
path_a = col_a.text_input("문헌 A (XML 파일 경로)", value="data/T45n1866.xml")
path_b = col_b.text_input("문헌 B (XML 파일 경로)", value="data/T45n1868.xml")


def describe(label: str, doc) -> str:
    divs = ", ".join(f"{t or '(없음)'}×{c}" for t, c in doc.div_types.items())
    return f"**{label}** {doc.doc_id} {doc.title} — 추출 {len(doc.text):,}자 / 구역(cb:div): {divs or '없음'}"


if st.button("실행", type="primary"):
    with st.spinner("문헌을 읽고 겹치는 구절을 찾는 중입니다..."):
        doc_a = extract(path_a)
        doc_b = extract(path_b)
        matches = find_overlaps(doc_a.text, doc_b.text, DEFAULT_N)
        table = build_table(doc_a, doc_b, matches)

    st.markdown(describe("A", doc_a))
    st.markdown(describe("B", doc_b))
    st.caption("구역 type이 w인 부분(후대 발문 등)은 비교에서 제외했습니다.")
    st.subheader(f"결과: {len(table):,}건 (최소 겹침 길이 N={DEFAULT_N})")
    st.dataframe(table, width="stretch", hide_index=True)
