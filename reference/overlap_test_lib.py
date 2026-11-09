import collections
def overlaps(a, b, n):
    ta, tb_ = a[1], b[1]
    idx = collections.defaultdict(list)
    for i in range(len(ta) - n + 1):
        idx[ta[i:i+n]].append(i)
    matches = []
    for j in range(len(tb_) - n + 1):
        for i in idx.get(tb_[j:j+n], ()):
            matches.append((i - j, j, i))     # diagonal, posB, posA
    matches.sort()
    runs = []
    for d, j, i in matches:
        if runs and runs[-1][0] == d and j <= runs[-1][2] + 1:
            runs[-1][2] = max(runs[-1][2], j)
        else:
            runs.append([d, j, j])
    # run: diagonal d, start j, last start j2 -> length = j2 - j + n
    out = []
    for d, j, j2 in runs:
        out.append((j2 - j + n, j, j + d))   # length, posB, posA
    return out
