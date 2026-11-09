from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from phrase_finder.errors import InputError
from phrase_finder.extract import extract
from phrase_finder.overlap import validate_n
from phrase_finder.results import MAX_DISPLAY_ROWS, limit_for_display

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

TEI_HEAD = '<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="T99n%04d"><teiHeader/>'


def write_doc(tmp_path, name, body, number=1):
    f = tmp_path / name
    f.write_text(
        TEI_HEAD % number + f"<text><body>{body}</body></text></TEI>", encoding="utf-8"
    )
    return f


# --- extract(): 파일·형식 오류 (prd.md 4장) ---


def test_파일이_없으면_경로와_함께_알린다(tmp_path):
    missing = tmp_path / "없는파일.xml"
    with pytest.raises(InputError, match="파일을 열 수 없습니다") as e:
        extract(missing)
    assert str(missing) in str(e.value)


def test_폴더를_지정해도_열_수_없다고_알린다(tmp_path):
    with pytest.raises(InputError, match="파일을 열 수 없습니다"):
        extract(tmp_path)


def test_xml이_아니면_형식_오류와_파일명(tmp_path):
    f = tmp_path / "깨짐.xml"
    f.write_text("이건 XML이 아닙니다", encoding="utf-8")
    with pytest.raises(InputError, match="CBETA P5 XML 형식이 아닌 것 같습니다: 깨짐.xml"):
        extract(f)


def test_xml이지만_TEI가_아니면_형식_오류(tmp_path):
    f = tmp_path / "other.xml"
    f.write_text("<root><body>甲乙丙</body></root>", encoding="utf-8")
    with pytest.raises(InputError, match="형식이 아닌 것 같습니다: other.xml"):
        extract(f)


def test_body가_없으면_형식_오류(tmp_path):
    f = tmp_path / "nobody.xml"
    f.write_text(TEI_HEAD % 1 + "</TEI>", encoding="utf-8")
    with pytest.raises(InputError, match="형식이 아닌 것 같습니다: nobody.xml"):
        extract(f)


def test_본문이_비어_있으면_알린다(tmp_path):
    f = write_doc(tmp_path, "empty.xml", '<lb n="0001a01"/><p>abc。 </p>')
    with pytest.raises(InputError, match="본문을 추출하지 못했습니다: empty.xml"):
        extract(f)


# --- N 범위 ---


@pytest.mark.parametrize("n", [3, 6, 30])
def test_n_범위_안은_통과(n):
    validate_n(n)


@pytest.mark.parametrize("n", [2, 0, -1, 31])
def test_n_범위_밖은_오류(n):
    with pytest.raises(InputError, match="N은 3에서 30 사이여야 합니다"):
        validate_n(n)


# --- 결과가 너무 많을 때 ---


def test_상한을_넘으면_길이_긴_순으로_자른다():
    rows = [{"구절": "x", "길이": i % 50, "A 위치": "", "B 위치": ""} for i in range(700)]
    full = pd.DataFrame(rows)
    shown = limit_for_display(full)
    assert len(shown) == MAX_DISPLAY_ROWS == 500
    assert shown["길이"].is_monotonic_decreasing
    # 잘려 나간 것 중에 보여 준 것보다 긴 구절은 없다
    dropped = full.drop(shown.index)
    assert len(dropped) == 200
    assert dropped["길이"].max() <= shown["길이"].min()


def test_상한_이하면_그대로():
    t = pd.DataFrame([{"구절": "x", "길이": 6, "A 위치": "", "B 위치": ""}] * 10)
    assert len(limit_for_display(t)) == 10


# --- 화면 (AppTest) ---


def app(path_a=None, path_b=None):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    if path_a is not None:
        at.text_input[0].set_value(path_a)
    if path_b is not None:
        at.text_input[1].set_value(path_b)
    at.button[0].click().run()
    assert not at.exception  # 어떤 경우에도 프로그램이 죽지 않는다
    return at


def test_화면_경로를_비우면_안내하고_실행하지_않는다(tmp_path):
    at = app(path_a="")
    assert [e.value for e in at.error] == ["문헌 A와 B를 모두 선택하세요."]
    assert len(at.dataframe) == 0


def test_화면_없는_파일(tmp_path):
    at = app(path_a=str(tmp_path / "nope.xml"))
    assert len(at.error) == 1
    assert "문헌 A" in at.error[0].value and "파일을 열 수 없습니다" in at.error[0].value
    assert len(at.dataframe) == 0


def test_화면_형식이_틀린_파일(tmp_path):
    bad = tmp_path / "bad.xml"
    bad.write_text("<<<", encoding="utf-8")
    at = app(path_b=str(bad))
    assert "문헌 B" in at.error[0].value and "bad.xml" in at.error[0].value


def test_화면_겹침이_없으면_오류가_아니라_안내(tmp_path):
    a = write_doc(tmp_path, "a.xml", '<lb n="0001a01"/><p>甲乙丙丁戊己庚辛</p>', 1)
    b = write_doc(tmp_path, "b.xml", '<lb n="0002a01"/><p>壬癸子丑寅卯辰巳</p>', 2)
    at = app(str(a), str(b))
    assert not at.error
    assert any("겹치는 구절이 없습니다" in i.value for i in at.info)


def test_화면_같은_파일이면_경고하고_실행은_한다(tmp_path):
    a = write_doc(tmp_path, "a.xml", '<lb n="0001a01"/><p>甲乙丙丁戊己庚辛</p>')
    at = app(str(a), str(a))
    assert any("같은 파일" in w.value for w in at.warning)
    assert any("1건" in s.value for s in at.subheader)


def test_화면_500건_초과는_상위_500건만_표시하고_안내(tmp_path):
    # 서로 겹치지 않는 6글자 구절 600개를 구분 글자로 이어 붙인다.
    def phrase(i):
        return "".join(chr(0x4E00 + i * 6 + k) for k in range(6))

    count = 600
    a_body = "".join(phrase(i) + chr(0x6000 + i) for i in range(count))
    b_body = "".join(phrase(i) + chr(0x7000 + i) for i in range(count))
    a = write_doc(tmp_path, "a.xml", f'<lb n="0001a01"/><p>{a_body}</p>', 1)
    b = write_doc(tmp_path, "b.xml", f'<lb n="0002a01"/><p>{b_body}</p>', 2)
    at = app(str(a), str(b))
    assert any("600건" in s.value for s in at.subheader)
    assert any("상위 500건" in w.value for w in at.warning)
    assert len(at.dataframe[0].value) == 500


@pytest.mark.skipif(not (DATA / "T45n1866.xml").exists(), reason="data/ 샘플 없음")
def test_화면_정상_실행은_오류도_경고도_없다():
    at = app()
    assert not at.error and not at.warning
    assert any("83건" in s.value for s in at.subheader)
