import sys, collections
sys.path.insert(0, '/home/claude/proto')
from extract2 import extract
from overlap_test_lib import overlaps

A = extract('/mnt/user-data/uploads/92613d9e-T45n1866.xml')
B = extract('/mnt/user-data/uploads/7840a59a-T45n1868.xml')
N = 6

# Test 1: self-comparison -> one run on diagonal 0 covering the whole text
for name, X in (('T45n1866', A), ('T45n1868', B)):
    runs = overlaps(X, X, N)
    full = [r for r in runs if r[0] == len(X[1]) and r[1] == 0 and r[2] == 0]
    print(f'[1 self] {name}: full-length diagonal run found = {len(full) == 1}')

# Test 2: planted passage -> found with correct positions
a0 = 12000
planted = A[1][a0:a0 + 20]
m = 3000
Bt = B[1][:m] + planted + B[1][m:]
Bp = B[2][:m] + A[2][a0:a0 + 20] + B[2][m:]
Bx = (B[0], Bt, Bp, B[3])
runs = overlaps(A, Bx, N)
hit = [r for r in runs if r[1] <= m and r[1] + r[0] >= m + 20 and r[2] <= a0 and r[2] + r[0] >= a0 + 20]
print('[2 plant] planted 20 chars found:', bool(hit),
      '| reported A pos', Bx[2][m], '== source', A[2][a0], ':', Bx[2][m] == A[2][a0])

# Test 3: negative control (shuffled text keeps characters but breaks sequences)
import random
random.seed(0)
chars = list(B[1]); random.shuffle(chars)
Bs = (B[0], ''.join(chars), [None]*len(chars), B[3])
for n in (6, 8):
    r = overlaps(A, Bs, n)
    cov = sum(x[0] for x in r)
    print(f'[3 shuffled] N={n}: runs={len(r)}')
