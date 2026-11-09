"""F3: 두 본문의 공통 구절을 N-gram으로 찾고, 이어지는 일치를 하나의 구간으로 병합한다.

입력은 extract()가 돌려준 본문 문자열이다. 반환하는 위치는 문자열 안의 글자 번호(0부터)이며,
원문 위치(쪽·단·줄)는 Extracted.positions[글자 번호]로 되돌릴 수 있다.
"""

from collections import defaultdict
from dataclasses import dataclass

from phrase_finder.errors import InputError
from phrase_finder.extract import BREAK


MIN_N, MAX_N = 3, 30


def validate_n(n: int) -> None:
    """화면에서 받은 최소 겹침 길이가 허용 범위(3~30)인지 확인한다."""
    if not MIN_N <= n <= MAX_N:
        raise InputError(f"N은 {MIN_N}에서 {MAX_N} 사이여야 합니다.")


@dataclass(frozen=True)
class Match:
    length: int  # 겹친 글자 수
    a_start: int  # 문헌 A 본문에서의 시작 글자 번호
    b_start: int  # 문헌 B 본문에서의 시작 글자 번호


def find_overlaps(text_a: str, text_b: str, n: int) -> list[Match]:
    """A와 B에서 n글자 이상 겹치는 구간을 모두 찾는다.

    같은 구절이 한쪽에 여러 번 나오면 위치 쌍마다 하나씩 돌려준다.
    결과는 (길이 내림차순, B 위치, A 위치) 순으로 정렬해 항상 같은 순서가 되게 한다.
    """
    if n < 1:
        raise ValueError("n은 1 이상이어야 합니다.")

    # A의 모든 n글자 조각의 위치 색인. 끊는 기호가 든 조각은 일치시키지 않는다.
    index: dict[str, list[int]] = defaultdict(list)
    for i in range(len(text_a) - n + 1):
        gram = text_a[i : i + n]
        if BREAK not in gram:
            index[gram].append(i)

    # 일치 쌍 (대각선 = A위치 - B위치, B위치, A위치)
    pairs: list[tuple[int, int, int]] = []
    for j in range(len(text_b) - n + 1):
        gram = text_b[j : j + n]
        for i in index.get(gram, ()):
            pairs.append((i - j, j, i))
    pairs.sort()

    # 같은 대각선에서 한 칸씩 이어지거나 겹치는 일치는 하나의 구간으로 합친다.
    runs: list[list[int]] = []  # [대각선, 첫 B위치, 마지막 B위치]
    for diagonal, j, _ in pairs:
        if runs and runs[-1][0] == diagonal and j <= runs[-1][2] + 1:
            runs[-1][2] = max(runs[-1][2], j)
        else:
            runs.append([diagonal, j, j])

    matches = [
        Match(length=last - first + n, a_start=first + diagonal, b_start=first)
        for diagonal, first, last in runs
    ]
    matches.sort(key=lambda m: (-m.length, m.b_start, m.a_start))
    return matches
