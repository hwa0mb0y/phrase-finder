import re
from lxml import etree

T = '{http://www.tei-c.org/ns/1.0}'
CB = '{http://www.cbeta.org/ns/1.0}'
XML = '{http://www.w3.org/XML/1998/namespace}'
SKIP = {T+'note', T+'anchor', T+'byline', CB+'jhead', CB+'docNumber', CB+'mulu'}
SKIP_DIV_TYPES = {'w'}

def is_han(ch):
    o = ord(ch)
    return (0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF or 0x20000 <= o <= 0x2FFFF
            or 0xF900 <= o <= 0xFAFF or 0x2F800 <= o <= 0x2FA1F)

def gaiji_map(root):
    m = {}
    for c in root.iter(T+'char'):
        cid = c.get(XML+'id')
        maps = {x.get('type'): x.text for x in c.findall(T+'mapping')}
        for k in ('unicode', 'normal_unicode'):
            if k in maps:
                m[cid] = chr(int(maps[k][2:], 16)); break
    return m

def extract(path):
    root = etree.parse(path).getroot()
    gm = gaiji_map(root)
    body = root.find('.//'+T+'body')
    chars, pos = [], []
    st = {'lb': None}
    divtypes = {}
    def emit(text, skipping):
        if skipping: return
        for ch in text:
            if is_han(ch):
                chars.append(ch); pos.append(st['lb'])
    def walk(e, skipping):
        tag = e.tag
        if not isinstance(tag, str):
            if e.tail: emit(e.tail, skipping_parent[0])
            return
    # iterative-safe recursive walker
    def rec(e, skipping):
        tag = e.tag
        if isinstance(tag, str):
            if tag == CB+'div':
                divtypes[e.get('type')] = divtypes.get(e.get('type'), 0) + 1
            here = skipping or tag in SKIP or (tag == CB+'div' and e.get('type') in SKIP_DIV_TYPES)
            if tag == T+'lb': st['lb'] = e.get('n')
            elif tag == T+'g' and not here:
                ref = (e.get('ref') or '')[1:]
                chars.append(gm.get(ref, '')); pos.append(st['lb'])
            else:
                emit(e.text or '', here)
                for c in e: rec(c, here)
        if e.tail: emit(e.tail, skipping)
    for c in body: rec(c, False)
    return root.get(XML+'id'), ''.join(chars), pos, divtypes
