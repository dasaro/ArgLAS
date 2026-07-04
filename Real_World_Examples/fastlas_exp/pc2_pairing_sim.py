#!/usr/bin/env python3
"""P3 probe 2: verify pairing/index alignment + cell-level dedupe of per_condition_experiment
by running the REAL run_vocab loop with stubbed learner/predictor, then recomputing paired
arrays and McNemar counts independently from first principles."""
import sys, os, hashlib, json
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import per_condition_experiment as pce
import unified_compare as U
import aux9_combined as A9
import discover_semantics as D
from apples_to_apples import mcnemar

SCRATCH = "/private/tmp/claude-501/-Users-fdasaro-Desktop-Zlatina-FabioExperimentsMacM4-claude/b944494f-f629-4bf2-b8ab-90204d85f7ef/scratchpad"
os.makedirs(SCRATCH, exist_ok=True)

# ---- stubs: deterministic, arm-distinguishing ----
_learn_calls = [0]
def fake_learn(train, with_aux, timeout):
    _learn_calls[0] += 1
    return ([f"in(V) :- rule{_learn_calls[0]}(V)."], 0.0, False)

def fake_predict(rules, args, attacks, reading, enrich=True, with_aux=True):
    out = {}
    for a in args:
        h = hashlib.md5(repr((tuple(rules), a, tuple(sorted(attacks)), reading)).encode()).hexdigest()
        out[a] = ("in", "out", "undec")[int(h, 16) % 3]
    return out

pce.learn = fake_learn
A9.predict = fake_predict
pce.A9.predict = fake_predict
pce._flush = lambda state: None          # do NOT touch the live results file
pce.OUT = os.path.join(SCRATCH, "pc2_state.json")

state = {}
st = pce.run_vocab(state, "final", True, ("D", "B"))   # B has max cell multiplicity 8

# ---- independent recomputation ----
recs = U.load_pooled("final")
byv = defaultdict(list)
for r in recs:
    byv[r["version"]].append(r)
folds = U.shared_folds(recs, 5)
fold_of = {}
for fi, f in enumerate(folds):
    for r in f:
        fold_of[pce.cell_key(r)] = fi

ok = True
for v in ("D", "B"):
    cst = st["conditions"][v]
    vrecs = byv[v]
    cells = sorted({pce.cell_key(r) for r in vrecs})
    # expected paired arrays, rebuilt from scratch in an INDEPENDENT loop shape
    exp = {arm: [] for arm in ("within", "global", "transfer", "cf2")}
    exp_keys = []
    for ci, ck in enumerate(cells):
        w_rules = cst["loco"][str(ci)]["rules"]
        g_rules = st["global_theories"][str(fold_of[ck])]["rules"]
        t_rules = st["transfer_theories"][v]["rules"]
        for r in vrecs:
            if pce.cell_key(r) != ck:
                continue
            pw = fake_predict(w_rules, r["args"], r["attacks"], "credulous")
            pg = fake_predict(g_rules, r["args"], r["attacks"], "credulous")
            pt = fake_predict(t_rules, r["args"], r["attacks"], "credulous")
            pc2 = D.project(D.textbook_labellings("cf2", r["args"], r["attacks"]), r["args"], "credulous")
            for a, h in r["labels"].items():
                exp_keys.append((ck, a))
                exp["within"].append(1 if pw.get(a, "undec") == h else 0)
                exp["global"].append(1 if pg.get(a, "undec") == h else 0)
                exp["transfer"].append(1 if pt.get(a, "undec") == h else 0)
                exp["cf2"].append(1 if pc2.get(a, "undec") == h else 0)
    n_resp_args = sum(len(r["labels"]) for r in vrecs)
    got = cst["paired"]
    lens = {arm: len(got[arm]) for arm in got}
    print(f"[{v}] response-arg pairs expected={n_resp_args}  stored lens={lens}")
    for arm in exp:
        match = got[arm] == exp[arm]
        print(f"[{v}] paired[{arm}] elementwise match: {match}")
        ok &= match
    # cell-level dedupe: independent computation using FIRST rec of each cell AND using
    # a DIFFERENT representative (last rec) -> both must give identical b/c (determinism)
    for h1, (x, y) in {"H1_within_vs_global": ("within", "global"),
                       "H2_within_vs_transfer": ("within", "transfer")}.items():
        stored = cst["tests"][h1]["credulous_cell"]
        for pick in ("first", "last"):
            bc = Counter()
            for ck in cells:
                cell_recs = [r for r in vrecs if pce.cell_key(r) == ck]
                r = cell_recs[0] if pick == "first" else cell_recs[-1]
                rules = {"within": cst["loco"][str(cells.index(ck))]["rules"],
                         "global": st["global_theories"][str(fold_of[ck])]["rules"],
                         "transfer": st["transfer_theories"][v]["rules"]}
                px = fake_predict(rules[x], r["args"], r["attacks"], "credulous")
                py = fake_predict(rules[y], r["args"], r["attacks"], "credulous")
                for a, h in r["labels"].items():
                    cx = 1 if px.get(a, "undec") == h else 0
                    cy = 1 if py.get(a, "undec") == h else 0
                    if cx and not cy: bc["b"] += 1
                    if cy and not cx: bc["c"] += 1
            agree = (bc["b"], bc["c"]) == (stored["n1_only"], stored["n2_only"])
            print(f"[{v}] {h1} cell-level ({pick} rec): b={bc['b']} c={bc['c']} vs stored "
                  f"({stored['n1_only']},{stored['n2_only']}) match={agree}")
            ok &= agree
    # response-level vs cell-level inflation on this stub run
    rl = cst["tests"]["H1_within_vs_global"]["credulous"]
    cl = cst["tests"]["H1_within_vs_global"]["credulous_cell"]
    print(f"[{v}] H1 response-level b/c={rl['n1_only']}/{rl['n2_only']} p={rl['p']}  "
          f"cell-level b/c={cl['n1_only']}/{cl['n2_only']} p={cl['p']}")
print("\nALL CHECKS PASS" if ok else "\nMISMATCH FOUND")
