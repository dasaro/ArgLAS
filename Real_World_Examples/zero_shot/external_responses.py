"""Published aggregate human responses for the external stimuli (zero-shot evaluation).

CG2019_MAJORITY: Cramer & Guillaume (2019), technical report arXiv:1902.10552, Fig. 2 --
the MAJORITY final individual response per argument (numbered 1..60 as in the figure) for
the three participant groups the authors report: all 61 participants, the 49 'coherent'
participants, and the 27 'coherent non-grounded' participants.  Transcribed from the
majority-response squares of the figure (white=accept, black=reject, grey=undecided);
argument 59 has no unique majority among all participants (reject and undecided tied,
as the text states) and is marked 'tie'.  Independently re-transcribed by three blind
readers (see zero_shot_verification.json).

CG2018_PCT: Cramer & Guillaume (2018, COMMA), Fig. 4 -- percentage of final individual
responses per argument (accept / reject / undecided), pooled over the three thematic
contexts; read off the bar chart to about +-3 points (N = 45 / 60 / 25 participants for
simple / floating / 3-cycle reinstatement).  The majority category is unambiguous.
"""
GROUPS = ("all", "coherent", "nongrounded")
_A, _R, _U, _T = "accept", "reject", "undecided", "tie"
_rows = """
1 A A A
2 R R R
3 U U U
4 A A A
5 U U U
6 U U U
7 U U U
8 U U U
9 U U U
10 U U U
11 R U R
12 U U A
13 U U U
14 U U U
15 U U U
16 U U U
17 U U U
18 U U U
19 U U U
20 U U U
21 U U U
22 U U R
23 U U A
24 U U U
25 U U U
26 U U U
27 U U U
28 U U U
29 U U R
30 U U A
31 A A A
32 R R R
33 R R R
34 R R R
35 U U U
36 A A A
37 R R R
38 U U U
39 U U U
40 U U U
41 R R R
42 U A A
43 U U U
44 U U U
45 U U U
46 U U U
47 U U U
48 U U U
49 U U U
50 U U U
51 U U R
52 U U A
53 U U U
54 U U U
55 U U U
56 U U U
57 U U U
58 U U U
59 T U R
60 U U A
"""
_code = {"A": _A, "R": _R, "U": _U, "T": _T}
CG2019_MAJORITY = {int(l.split()[0]): dict(zip(GROUPS, (_code[c] for c in l.split()[1:])))
                   for l in _rows.strip().splitlines()}
assert len(CG2019_MAJORITY) == 60

CG2018_PCT = {
    "simple":   {"A": {_A: 58, _R: 16, _U: 27}, "B": {_A: 4, _R: 78, _U: 18}, "C": {_A: 69, _R: 0, _U: 31}},
    "floating": {"A": {_A: 83, _R: 2, _U: 15}, "B": {_A: 2, _R: 93, _U: 5},
                 "C": {_A: 7, _R: 13, _U: 80}, "D": {_A: 23, _R: 0, _U: 77}},
    "cycle3":   {"A": {_A: 52, _R: 40, _U: 8}, "B": {_A: 24, _R: 60, _U: 16}, "C": {_A: 32, _R: 8, _U: 60},
                 "D": {_A: 16, _R: 24, _U: 60}, "E": {_A: 44, _R: 8, _U: 48}},
}
CG2018_N = {"simple": 45, "floating": 60, "cycle3": 25}
