#!/usr/bin/env python3
"""P3 probe 3: (A) hand-verify the report() Holm implementation against textbook step-down
Holm on synthetic p-vectors; (B) exact-binomial McNemar power table for small n."""
from math import comb

# ---------- exact two-sided binomial (same convention as apples_to_apples.binom_two_sided) ----------
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from apples_to_apples import mcnemar, binom_two_sided

# ---------- (A) Holm ----------
def report_holm(ps):
    """EXACT expression from report(): sorted ascending, SIG iff p*(m-i)<0.05, adj=min(1,p*(m-i))."""
    hs = sorted(enumerate(ps), key=lambda x: x[1])
    m = len(hs)
    return {v: ("SIG" if p * (m - i) < 0.05 else "ns", min(1, p * (m - i)))
            for i, (v, p) in enumerate(hs)}

def textbook_holm(ps, alpha=0.05):
    """Step-down Holm: reject while p_(i) <= alpha/(m-i); STOP at first failure.
    Adjusted p = cumulative max of min(1,(m-i)*p_(i))."""
    idx = sorted(range(len(ps)), key=lambda i: ps[i])
    m = len(ps)
    out, rejecting, cmax = {}, True, 0.0
    for rank, i in enumerate(idx):
        adj = min(1.0, (m - rank) * ps[i])
        cmax = max(cmax, adj)
        if ps[i] > alpha / (m - rank):
            rejecting = False
        out[i] = ("SIG" if rejecting else "ns", cmax)
    return out

vectors = [
    [0.001, 0.03, 0.04],                       # classic step-down violation case
    [0.008, 0.009, 0.04, 0.2, 0.5, 0.9, 1.0],  # 7 conditions like the harness
    [0.006, 0.012, 0.011, 0.049, 0.6, 1.0, 1.0],
    [0.02, 0.02],                              # ties
]
print("=== (A) Holm: report() vs textbook step-down ===")
any_diff = False
for ps in vectors:
    r, t = report_holm(ps), textbook_holm(ps)
    diffs = [i for i in r if r[i][0] != t[i][0] or abs(r[i][1] - t[i][1]) > 1e-12]
    print(f"p={ps}")
    for i in sorted(r):
        flag = "  <-- DIFF" if i in diffs else ""
        print(f"  H{i} raw={ps[i]:<6} report:{r[i][0]:>4} adj={r[i][1]:.4f} | textbook:{t[i][0]:>4} adj={t[i][1]:.4f}{flag}")
    any_diff |= bool(diffs)
print("VERDICT:", "report() Holm DEVIATES from step-down Holm" if any_diff else "identical")

# ---------- (B) power ----------
def power_two_sided(n, theta, alpha):
    """P(two-sided exact binomial p<=alpha) when successes ~ Bin(n, theta)."""
    return sum(comb(n, k) * theta**k * (1-theta)**(n-k)
               for k in range(n + 1) if n and binom_two_sided(min(k, n-k), n, 0.5) <= alpha)

print("\n=== (B) exact McNemar power (n_d = discordant pairs, theta = P(within wins | discordant)) ===")
print("minimum n_d for ANY possible rejection (all discordances one way):")
for alpha, tag in ((0.05, "alpha=0.05"), (0.05/7, "Holm worst rank alpha=0.05/7")):
    nmin = next(n for n in range(1, 40) if binom_two_sided(0, n, 0.5) <= alpha)
    print(f"  {tag}: n_d >= {nmin}  (p at n_d={nmin}, 0 losses: {binom_two_sided(0, nmin, 0.5):.5f})")
print(f"\n{'n_d':>5} | " + " ".join(f"th={t:.2f}a.05" for t in (0.65, 0.75, 0.85, 0.95))
      + " || " + " ".join(f"th={t:.2f}a.0071" for t in (0.75, 0.85, 0.95)))
for n in (4, 6, 8, 10, 15, 20, 30, 45, 60, 95):
    row = [power_two_sided(n, t, 0.05) for t in (0.65, 0.75, 0.85, 0.95)]
    row2 = [power_two_sided(n, t, 0.05/7) for t in (0.75, 0.85, 0.95)]
    print(f"{n:>5} | " + " ".join(f"{p:>10.3f}" for p in row) + " || " + " ".join(f"{p:>12.3f}" for p in row2))

print("\nContext: cell-arg pairs per condition = 15..95 (D/E=15, F=21, B=24, A=40, C=44, G=95);")
print("n_d is the DISCORDANT subset of those, e.g. 10-20% disagreement -> n_d ~ 2-19 per condition.")
