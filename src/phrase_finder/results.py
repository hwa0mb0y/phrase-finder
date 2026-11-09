"""F4: 겹침 탐지 결과를 화면에 보여 줄 표로 바꾼다.

구절은 정규화본이 아니라 원문 글자 그대로, 위치는 대정장 쪽·단·줄로 표시한다.
"""

import pandas as pd

from phrase_finder.extract import Extracted
from phrase_finder.overlap import Match

COLUMNS = ["구절", "길이", "A 위치", "B 위치"]
UNKNOWN_LOCATION = "(위치 불명)"


MAX_DISPLAY_ROWS = 500  # prd.md 4장: 화면에 보여 주는 최대 건수


def limit_for_display(table: pd.DataFrame) -> pd.DataFrame:
    """결과가 너무 많으면 길이가 긴 순으로 상위 MAX_DISPLAY_ROWS건만 남긴다."""
    return table.sort_values("길이", ascending=False, kind="stable").head(MAX_DISPLAY_ROWS)


def format_location(doc: Extracted, start: int, length: int) -> str:
    """본문 글자 범위 [start, start+length)의 원문 위치.

    예: 'T45n1866 0505a22' (한 줄 안), 'T45n1866 0505a22 ~ 0505b03' (줄·쪽을 넘을 때).
    """
    first = doc.positions[start]
    last = doc.positions[start + length - 1]
    if first is None or last is None:
        return f"{doc.doc_id} {UNKNOWN_LOCATION}"
    if first == last:
        return f"{doc.doc_id} {first}"
    return f"{doc.doc_id} {first} ~ {last}"


def build_table(a: Extracted, b: Extracted, matches: list[Match]) -> pd.DataFrame:
    """겹침 한 건이 표의 한 줄이 된다. 같은 구절이 여러 곳에 있으면 위치 쌍마다 한 줄."""
    rows = [
        {
            "구절": b.text[m.b_start : m.b_start + m.length],
            "길이": m.length,
            "A 위치": format_location(a, m.a_start, m.length),
            "B 위치": format_location(b, m.b_start, m.length),
        }
        for m in matches
    ]
    return pd.DataFrame(rows, columns=COLUMNS)
