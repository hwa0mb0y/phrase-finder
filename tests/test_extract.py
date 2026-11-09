from pathlib import Path

import pytest

from phrase_finder.extract import BREAK, extract

DATA = Path(__file__).resolve().parent.parent / "data"

TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xmlns:cb="http://www.cbeta.org/ns/1.0" xml:id="T99n0001">
<teiHeader>
  <fileDesc><titleStmt><title>시험 문헌</title></titleStmt></fileDesc>
  <encodingDesc><charDecl>
    <char xml:id="CB00001"><charProp/><mapping type="unicode">U+4E00</mapping></char>
    <char xml:id="CB00002"><mapping type="normal_unicode">U+4E8C</mapping></char>
    <char xml:id="CB00003"><mapping type="unicode">U+4E09</mapping>
                           <mapping type="normal_unicode">U+56DB</mapping></char>
  </charDecl></encodingDesc>
</teiHeader>
<text><body>%s</body><back><div><p>背後注</p></div></back></text>
</TEI>"""


def run(tmp_path, body):
    f = tmp_path / "t.xml"
    f.write_text(TEMPLATE % body, encoding="utf-8")
    return extract(f)


def test_기본_추출과_줄_위치(tmp_path):
    r = run(tmp_path, '<pb n="0001a"/><lb n="0001a01"/><p>天地，玄黃。<lb n="0001a02"/>宇宙</p>')
    assert r.doc_id == "T99n0001"
    assert r.title == "시험 문헌"
    assert r.text == "天地玄黃宇宙"
    assert r.positions == ["0001a01"] * 4 + ["0001a02"] * 2


def test_back과_header는_읽지_않는다(tmp_path):
    r = run(tmp_path, '<lb n="0001a01"/><p>甲乙</p>')
    assert r.text == "甲乙"


def test_제외_요소는_텍스트만_건너뛴다(tmp_path):
    body = (
        '<cb:div type="jing"><lb n="0001a01"/>'
        "<cb:docNumber>號號</cb:docNumber>"
        "<cb:jhead>卷題</cb:jhead>"
        "<p>甲<note place='inline'>協注</note>乙<anchor n='x'/>丙</p>"
        "</cb:div>"
    )
    assert run(tmp_path, body).text == "甲乙丙"


def test_제외_요소_안의_lb도_위치에_반영된다(tmp_path):
    body = (
        '<lb n="0001a01"/><p>甲</p>'
        '<byline>著者<lb n="0001a02"/>名</byline>'
        "<p>乙</p>"
    )
    r = run(tmp_path, body)
    assert r.text == "甲乙"
    assert r.positions == ["0001a01", "0001a02"]


def test_note_안의_lb도_위치에_반영된다(tmp_path):
    body = '<lb n="0001a01"/><p>甲<note><lb n="0001a02"/>注</note>乙</p>'
    r = run(tmp_path, body)
    assert r.text == "甲乙"
    assert r.positions == ["0001a01", "0001a02"]


def test_후대_발문_구역_w는_제외한다(tmp_path):
    body = (
        '<cb:div type="jing"><lb n="0001a01"/><p>本文</p></cb:div>'
        '<cb:div type="w"><lb n="0001a02"/><p>跋文</p></cb:div>'
    )
    r = run(tmp_path, body)
    assert r.text == "本文"
    assert r.div_types == {"jing": 1, "w": 1}


def test_p_l_head_밖의_텍스트는_읽지_않는다(tmp_path):
    body = '<lb n="0001a01"/>떠돌이字<head>題</head><lg><l>偈頌</l></lg><trailer>尾</trailer>'
    assert run(tmp_path, body).text == "題偈頌"


def test_한자가_아닌_문자는_모두_버린다(tmp_path):
    body = '<lb n="0001a01"/><p>甲　乙\n丙abc123（丁）。「戊」</p>'
    assert run(tmp_path, body).text == "甲乙丙丁戊"


def test_특수한자_unicode가_normal_unicode보다_우선한다(tmp_path):
    body = (
        '<lb n="0001a01"/><p><g ref="#CB00001"/><g ref="#CB00002"/><g ref="#CB00003"/></p>'
    )
    assert run(tmp_path, body).text == "一二三"


def test_특수한자를_못_찾으면_끊는_기호를_넣고_위치도_맞춘다(tmp_path):
    body = '<lb n="0001a01"/><p>甲<g ref="#CB99999"/>乙<lb n="0001a02"/>丙</p>'
    r = run(tmp_path, body)
    assert r.text == f"甲{BREAK}乙丙"
    assert len(r.positions) == len(r.text)
    assert r.positions == ["0001a01"] * 3 + ["0001a02"]


def test_gaiji가_없는_문헌도_오류없이_동작한다(tmp_path):
    f = tmp_path / "t.xml"
    f.write_text(
        '<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="T99n0002"><teiHeader/>'
        '<text><body><lb n="0001a01"/><p>甲乙</p></body></text></TEI>',
        encoding="utf-8",
    )
    assert extract(f).text == "甲乙"


def test_같은_입력이면_같은_결과(tmp_path):
    body = '<lb n="0001a01"/><p>甲乙<g ref="#CB00001"/></p>'
    a, b = run(tmp_path, body), run(tmp_path, body)
    assert (a.text, a.positions) == (b.text, b.positions)


# --- 실제 샘플 (data/는 git에 없으므로 없으면 건너뜀) ---

needs_data = pytest.mark.skipif(not (DATA / "T45n1866.xml").exists(), reason="data/ 샘플 없음")


@needs_data
def test_샘플_T45n1866():
    r = extract(DATA / "T45n1866.xml")
    assert r.doc_id == "T45n1866"
    assert len(r.text) == 42364  # prd.md 3-5절 참조값
    assert len(r.positions) == len(r.text)
    assert all(p is not None for p in r.positions)
    assert "" not in r.text  # 샘플의 gaiji 1건은 normal_unicode로 해결됨
    assert not any(0xE000 <= ord(c) <= 0xF8FF for c in r.text)  # 사설 영역 문자 없음


@needs_data
def test_샘플_T45n1868():
    r = extract(DATA / "T45n1868.xml")
    assert r.doc_id == "T45n1868"
    assert len(r.text) == 6481
    assert r.positions[0].startswith("0514a")
    assert r.positions[-1] <= "0518c15"
    assert "w" in r.div_types and "jing" in r.div_types


@needs_data
def test_샘플_후대_발문은_본문에_없다():
    # T45n1868의 발문(<cb:div type="w">)에는 편자 楊文會의 기록이 있다.
    r = extract(DATA / "T45n1868.xml")
    assert "楊文會" not in r.text
