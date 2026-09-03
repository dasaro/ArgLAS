#!/usr/bin/env python3
"""Cross-check of the transcribed Cramer & Guillaume (2019) frameworks against the paper's
own semantics-prediction columns.

FIG2_PREDICTIONS below is a transcription of the Grounded / Preferred / CF2 columns of
Fig. 2 of arXiv:1902.10552 (W = white = strongly accepted, B = black = strongly rejected,
g = grey = weakly undecided), read from the figure independently of any computation.  The
script recomputes the same three statuses from the transcribed attack relations (ASPARTIX
encodings + skeptical projection, as in the Exp2 pipeline) and asserts equality on all 60
arguments.  (The figure's semi-stable / stage / stage2 columns are not checked: the
repository carries no encodings for them.)
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); RWE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(RWE, "scripts")); sys.path.insert(0, HERE)
import discover_semantics as D
from external_afs import CG2019, lower

FIG2_PREDICTIONS = """
1 WWW  2 BBB  3 WWW  4 WWW
5 ggg  6 ggg  7 ggg
8 ggg  9 ggg  10 ggg  11 ggB  12 ggW
13 gBg  14 gBg  15 gWg  16 gBg  17 gWg
18 ggg  19 ggg  20 ggg  21 ggg  22 gBB  23 gWW
24 ggg  25 ggg  26 ggg  27 ggg  28 ggg  29 ggg  30 ggg
31 WWW  32 BBB  33 BBB  34 BBB  35 WWW
36 WWW  37 BBB  38 WWW
39 ggg  40 ggg  41 gBB  42 gWW
43 ggg  44 ggg  45 ggg  46 ggg  47 ggg
48 ggg  49 ggg  50 ggg  51 ggg  52 ggg
53 ggg  54 ggg  55 ggg  56 ggg  57 ggg  58 ggg  59 gBg  60 gWg
"""
CODE = {"in": "W", "out": "B", "undec": "g"}
toks = FIG2_PREDICTIONS.split()
fig = {int(toks[i]): toks[i + 1] for i in range(0, len(toks), 2)}
assert len(fig) == 60

mism = []
for name, af0 in CG2019.items():
    af = lower(af0)
    for a in af["args"]:
        got = "".join(CODE[D.project(D.textbook_labellings(s, af["args"], af["att"]), af["args"], "skeptical")[a]]
                      for s in ("grounded", "preferred", "cf2"))
        if got != fig[af["num"][a]]:
            mism.append((name, a.upper(), af["num"][a], fig[af["num"][a]], got))
if mism:
    for m in mism:
        print("MISMATCH", m)
    sys.exit(1)
print("all 60 grounded/preferred/CF2 statuses recomputed from the transcribed AFs match Fig. 2: OK")
