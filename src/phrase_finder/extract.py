"""F1: CBETA P5 XML에서 본문 한자와 글자별 위치(대정장 쪽·단·줄)를 추출한다.

규칙의 근거는 prd.md 3-3, 3-5절.
"""

from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

TEI = "{http://www.tei-c.org/ns/1.0}"
CB = "{http://www.cbeta.org/ns/1.0}"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"

# 글자를 읽는 요소 (이 요소 안에서만 텍스트를 모은다)
READ_TAGS = {TEI + "p", TEI + "l", TEI + "head"}
# 본문 안에서도 텍스트를 읽지 않는 요소 (협주, 교감 표지, 권 제목, 저자 표기 등)
SKIP_TAGS = {
    TEI + "note",
    TEI + "anchor",
    TEI + "byline",
    CB + "jhead",
    CB + "docNumber",
    CB + "mulu",
}
# 읽지 않는 구역 (T45n1868의 후대 발문 등)
SKIP_DIV_TYPES = {"w"}

# 특수 한자를 대응시킬 수 없을 때 넣는 끊는 기호.
# 이 기호는 한자가 아니므로 N-gram 일치가 이 자리를 가로지르지 못한다.
BREAK = ""


@dataclass
class Extracted:
    doc_id: str  # 예: "T45n1866"
    title: str
    text: str  # 한자 + 끊는 기호만 남긴 본문 (F2 정규화 이전)
    positions: list[str | None]  # text의 각 글자가 속한 줄 번호 (예: "0477a06")
    div_types: dict[str, int] = field(default_factory=dict)  # <cb:div> type별 개수

    def __post_init__(self) -> None:
        # 글자와 위치가 어긋나면 이후 모든 위치가 틀어지므로 항상 검사한다.
        if len(self.text) != len(self.positions):
            raise ValueError("본문 글자 수와 위치 수가 다릅니다.")


def is_han(ch: str) -> bool:
    """CJK 통합한자(확장 A~G 포함)와 호환한자인지."""
    o = ord(ch)
    return (
        0x4E00 <= o <= 0x9FFF
        or 0x3400 <= o <= 0x4DBF
        or 0x20000 <= o <= 0x323AF
        or 0xF900 <= o <= 0xFAFF
        or 0x2F800 <= o <= 0x2FA1F
    )


def _gaiji_map(root: etree._Element) -> dict[str, str]:
    """teiHeader의 charDecl에서 특수 한자 ID → 글자. unicode 우선, 없으면 normal_unicode."""
    result: dict[str, str] = {}
    for char in root.iter(TEI + "char"):
        char_id = char.get(XML_ID)
        mappings = {m.get("type"): (m.text or "").strip() for m in char.findall(TEI + "mapping")}
        for kind in ("unicode", "normal_unicode"):
            value = mappings.get(kind, "")
            if value.startswith("U+"):
                result[char_id] = chr(int(value[2:], 16))
                break
    return result


def _first_text(root: etree._Element, path: str) -> str:
    node = root.find(path)
    return "".join(node.itertext()).strip() if node is not None else ""


def extract(path: str | Path) -> Extracted:
    root = etree.parse(str(path)).getroot()
    gaiji = _gaiji_map(root)
    body = root.find(f".//{TEI}body")
    if body is None:
        raise ValueError("<body>를 찾을 수 없습니다.")

    chars: list[str] = []
    positions: list[str | None] = []
    div_types: dict[str, int] = {}
    current_lb: list[str | None] = [None]  # 가장 최근에 나온 <lb>의 n

    def emit(text: str | None, active: bool) -> None:
        if not active or not text:
            return
        for ch in text:
            if is_han(ch):
                chars.append(ch)
                positions.append(current_lb[0])

    def walk(el: etree._Element, in_read: bool, skipping: bool) -> None:
        tag = el.tag
        if isinstance(tag, str):
            if tag == CB + "div":
                kind = el.get("type", "")
                div_types[kind] = div_types.get(kind, 0) + 1
            skip_here = (
                skipping
                or tag in SKIP_TAGS
                or (tag == CB + "div" and el.get("type") in SKIP_DIV_TYPES)
            )
            read_here = in_read or tag in READ_TAGS
            active = read_here and not skip_here

            if tag == TEI + "lb":
                # 제외한 요소 안의 <lb>도 위치 추적에는 반영한다.
                current_lb[0] = el.get("n")
            elif tag == TEI + "g":
                if active:
                    ref = (el.get("ref") or "").lstrip("#")
                    mapped = gaiji.get(ref, "")
                    chars.append(mapped if mapped and is_han(mapped) else BREAK)
                    positions.append(current_lb[0])
            else:
                emit(el.text, active)
                for child in el:
                    walk(child, read_here, skip_here)
        # 주석·처리 지시문 등 문자열 태그가 아닌 노드도 tail은 부모 상태를 따른다.
        emit(el.tail, in_read and not skipping)

    for child in body:
        walk(child, False, False)

    return Extracted(
        doc_id=root.get(XML_ID, ""),
        title=_first_text(root, f".//{TEI}titleStmt/{TEI}title"),
        text="".join(chars),
        positions=positions,
        div_types=div_types,
    )
