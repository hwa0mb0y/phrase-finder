import random
from pathlib import Path

import pytest

from phrase_finder.extract import BREAK, extract
from phrase_finder.overlap import Match, find_overlaps

DATA = Path(__file__).resolve().parent.parent / "data"


# --- 작은 예제 ---


def test_기본_일치_하나():
    assert find_overlaps("甲乙丙丁戊", "己乙丙丁庚", 3) == [Match(3, 1, 1)]


def test_n보다_짧은_일치는_찾지_않는다():
    assert find_overlaps("甲乙丙", "丁乙丙", 3) == []


def test_연속한_일치는_하나로_병합된다():
    # 공통 구절 "乙丙丁戊己" (5자)가 n=3 조각 세 개로 잡히지만 구간은 하나여야 한다.
    assert find_overlaps("甲乙丙丁戊己庚", "辛乙丙丁戊己壬", 3) == [Match(5, 1, 1)]


def test_같은_구절이_여러_곳에_있으면_위치_쌍마다_하나씩():
    a = "乙丙丁" + "甲" + "乙丙丁"  # A에 두 번
    b = "子乙丙丁子"  # B에 한 번
    assert find_overlaps(a, b, 3) == [Match(3, 0, 1), Match(3, 4, 1)]


def test_양쪽에_반복되면_모든_조합이_나온다():
    assert len(find_overlaps("乙丙丁甲乙丙丁", "乙丙丁子乙丙丁", 3)) == 4


def test_끊는_기호가_든_조각은_일치시키지_않는다():
    a = f"甲乙{BREAK}丙丁"
    b = f"戊乙{BREAK}丙己"  # 끊는 기호까지 똑같지만 가로지르면 안 된다
    assert find_overlaps(a, b, 3) == []


def test_끊는_기호_옆의_일치는_정상으로_찾는다():
    a = f"甲乙丙丁{BREAK}戊"
    b = f"己乙丙丁{BREAK}庚"
    assert find_overlaps(a, b, 3) == [Match(3, 1, 1)]


def test_빈_문자열과_짧은_입력():
    assert find_overlaps("", "甲乙丙", 3) == []
    assert find_overlaps("甲乙丙", "", 3) == []
    assert find_overlaps("甲乙", "甲乙", 3) == []


def test_n이_1_미만이면_오류():
    with pytest.raises(ValueError):
        find_overlaps("甲", "甲", 0)


def test_결과는_길이_내림차순():
    a = "甲乙丙丁戊" + "己" + "庚辛壬"
    b = "庚辛壬" + "子" + "甲乙丙丁戊"
    lengths = [m.length for m in find_overlaps(a, b, 3)]
    assert lengths == sorted(lengths, reverse=True) == [5, 3]


# --- 실제 샘플 (prd.md 3-4절 1단계 검증) ---

needs_data = pytest.mark.skipif(not (DATA / "T45n1866.xml").exists(), reason="data/ 샘플 없음")


@pytest.fixture(scope="module")
def docs():
    return extract(DATA / "T45n1866.xml"), extract(DATA / "T45n1868.xml")


@needs_data
@pytest.mark.parametrize("which", [0, 1])
def test_검증1_자기_비교는_전체_길이_구간_하나(docs, which):
    d = docs[which]
    full = [m for m in find_overlaps(d.text, d.text, 6) if m.a_start == m.b_start]
    assert Match(len(d.text), 0, 0) in full
    # 위치 차이 0인 구간 중 전체를 덮는 것은 정확히 하나
    assert sum(m.length == len(d.text) for m in full) == 1


@needs_data
def test_검증2_구절_심기(docs):
    a, b = docs
    a0, m = 12000, 3000
    planted = a.text[a0 : a0 + 20]
    b_text = b.text[:m] + planted + b.text[m:]
    hits = [
        x
        for x in find_overlaps(a.text, b_text, 6)
        if x.b_start <= m
        and x.b_start + x.length >= m + 20
        and x.a_start <= a0
        and x.a_start + x.length >= a0 + 20
    ]
    assert hits
    # 보고된 A 위치가 원래 위치와 같다 (심은 자리 m에 대응하는 A 글자 번호)
    h = hits[0]
    assert h.a_start + (m - h.b_start) == a0
    assert a.positions[a0] == a.positions[h.a_start + (m - h.b_start)]


@needs_data
@pytest.mark.parametrize("n", [6, 8])
def test_검증3_글자를_섞으면_겹침이_없다(docs, n):
    a, b = docs
    chars = list(b.text)
    random.Random(0).shuffle(chars)
    assert find_overlaps(a.text, "".join(chars), n) == []


@needs_data
def test_검증5_재현성(docs):
    a, b = docs
    first = find_overlaps(a.text, b.text, 6)
    assert all(find_overlaps(a.text, b.text, 6) == first for _ in range(2))


def _coverage(matches, size):
    covered = set()
    for m in matches:
        covered.update(range(m.b_start, m.b_start + m.length))
    return len(covered) / size


@needs_data
@pytest.mark.parametrize(
    "n, count, ratio",
    [(4, 695, 20.3), (6, 83, 7.2), (8, 32, 4.5), (10, 12, 2.3), (14, 4, 1.1)],
)
def test_검증8_참조_시험값(docs, n, count, ratio):
    a, b = docs  # A=T45n1866, B=T45n1868 (prd.md 3-4절 표)
    matches = find_overlaps(a.text, b.text, n)
    assert len(matches) == count
    assert round(_coverage(matches, len(b.text)) * 100, 1) == ratio


@needs_data
def test_참조_최장_구간_22자(docs):
    a, b = docs
    top = find_overlaps(a.text, b.text, 6)[0]
    assert top.length == 22
    assert b.text[top.b_start : top.b_start + 22] == "云以一佛土滿十方十方入一亦無餘世界本相亦不壞"
    assert b.positions[top.b_start] == "0517b19"
    assert a.positions[top.a_start] == "0505a22"
