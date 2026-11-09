from pathlib import Path

import pytest

from phrase_finder.extract import Extracted, extract
from phrase_finder.overlap import Match, find_overlaps
from phrase_finder.results import COLUMNS, UNKNOWN_LOCATION, build_table, format_location

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def doc(doc_id, text, positions):
    return Extracted(doc_id=doc_id, title="", text=text, positions=positions)


def test_한_줄_안의_위치는_하나만_적는다():
    d = doc("T99n0001", "甲乙丙", ["0001a01"] * 3)
    assert format_location(d, 0, 3) == "T99n0001 0001a01"


def test_줄을_넘으면_시작과_끝을_적는다():
    d = doc("T99n0001", "甲乙丙丁", ["0001a01", "0001a01", "0001a02", "0001a02"])
    assert format_location(d, 1, 2) == "T99n0001 0001a01 ~ 0001a02"


def test_쪽을_넘는_위치():
    d = doc("T99n0001", "甲乙", ["0001c29", "0002a01"])
    assert format_location(d, 0, 2) == "T99n0001 0001c29 ~ 0002a01"


def test_위치를_모르면_조용히_넘어가지_않고_표시한다():
    d = doc("T99n0001", "甲乙", [None, None])
    assert UNKNOWN_LOCATION in format_location(d, 0, 2)


def test_구절은_B본문_원문_그대로_표시한다():
    a = doc("T99n0001", "子乙丙丁戊", ["0001a01"] * 5)
    b = doc("T99n0002", "乙丙丁", ["0002a05"] * 3)
    t = build_table(a, b, find_overlaps(a.text, b.text, 3))
    assert list(t.columns) == COLUMNS
    assert t.iloc[0].to_dict() == {
        "구절": "乙丙丁",
        "길이": 3,
        "A 위치": "T99n0001 0001a01",
        "B 위치": "T99n0002 0002a05",
    }


def test_같은_구절이_여러_곳이면_위치_쌍마다_한_줄():
    a = doc("T99n0001", "乙丙丁甲乙丙丁", ["0001a01"] * 3 + ["0001a02"] * 4)
    b = doc("T99n0002", "乙丙丁", ["0002a01"] * 3)
    t = build_table(a, b, find_overlaps(a.text, b.text, 3))
    assert len(t) == 2
    assert set(t["A 위치"]) == {"T99n0001 0001a01", "T99n0001 0001a02"}


def test_결과가_없으면_빈_표():
    a, b = doc("T99n0001", "甲乙丙", ["x"] * 3), doc("T99n0002", "丁戊己", ["y"] * 3)
    t = build_table(a, b, [])
    assert t.empty and list(t.columns) == COLUMNS


needs_data = pytest.mark.skipif(not (DATA / "T45n1866.xml").exists(), reason="data/ 샘플 없음")


@needs_data
def test_샘플_최장_구간의_표시():
    a, b = extract(DATA / "T45n1866.xml"), extract(DATA / "T45n1868.xml")
    t = build_table(a, b, find_overlaps(a.text, b.text, 6))
    first = t.iloc[0]
    assert first["구절"] == "云以一佛土滿十方十方入一亦無餘世界本相亦不壞"
    assert first["길이"] == 22
    assert first["A 위치"].startswith("T45n1866 0505a22")
    assert first["B 위치"].startswith("T45n1868 0517b19")
    assert len(t) == 83


@needs_data
def test_화면_실행_흐름():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not at.exception
    assert len(at.text_input) == 2
    at.button[0].click().run()
    assert not at.exception
    assert any("83건" in s.value for s in at.subheader)
    assert any("T45n1868" in m.value and "6,481" in m.value for m in at.markdown)
    assert any("jing" in m.value for m in at.markdown)
