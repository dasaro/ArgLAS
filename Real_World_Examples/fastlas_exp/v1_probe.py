#!/usr/bin/env python3
"""V1 reviewer probe: cross-arm identity & scoring single-path for unified_compare.py.
Checks: (1) fold identity/determinism/leak-freeness, (2) ILASP-vs-FastLAS example identity,
(3) scoring single-path + McNemar pairing alignment (recomputed vs smoke JSON),
(4) all-undec participants flow through every arm."""
import os, sys, json, re, hashlib
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
sys.path.insert(0, HERE)
import unified_compare as U
import discover_semantics as D
import fl_discover as G
from apples_to_apples import mcnemar

PHASE = "final"
OK = lambda name, cond, extra="": print(f"  [{'PASS' if cond else 'FAIL'}] {name} {extra}")

def cellkey(r):
    return (tuple(sorted(r["attacks"])), tuple(sorted(r["labels"].items())))

def commitkey(r):
    return (tuple(sorted(r["attacks"])), tuple(sorted(r["commit"].items())))

print("=" * 90)
print("(1) FOLD IDENTITY / DETERMINISM / LEAK-FREENESS")
print("=" * 90)
recs1 = U.load_pooled(PHASE)
folds1 = U.shared_folds(recs1, 5)
recs2 = U.load_pooled(PHASE)
folds2 = U.shared_folds(recs2, 5)

sig1 = [[(r["version"], r["pid"]) for r in f] for f in folds1]
sig2 = [[(r["version"], r["pid"]) for r in f] for f in folds2]
n_resp = sum(len(r["labels"]) for r in recs1)
print(f"  pool: {len(recs1)} participants, {n_resp} responses; fold sizes {[len(f) for f in folds1]}")
OK("load_pooled deterministic (order + content)",
   [(r["version"], r["pid"], cellkey(r)) for r in recs1] == [(r["version"], r["pid"], cellkey(r)) for r in recs2])
OK("shared_folds deterministic within-process", sig1 == sig2)
OK("n_responses == 495 (2022-faithful IndAF pool)", n_resp == 495, f"(got {n_resp})")

# leak-freeness at the declared (graph, full-labelling) cell level
cellsets = [set(cellkey(r) for r in f) for f in folds1]
straddle = 0
for i in range(len(cellsets)):
    for j in range(i + 1, len(cellsets)):
        straddle += len(cellsets[i] & cellsets[j])
OK("no (graph,labels) cell straddles folds", straddle == 0, f"(straddling cells: {straddle})")

# informational: commit-level straddle (labels differ only in undec pattern, commit identical)
commit_straddles = []
for fi in range(len(folds1)):
    test = folds1[fi]
    train = [r for j, f in enumerate(folds1) if j != fi for r in f]
    train_ck = set(commitkey(r) for r in train)
    hit = [r for r in test if commitkey(r) in train_ck]
    commit_straddles.append((len(hit), sum(len(r["labels"]) for r in hit)))
print(f"  INFO commit-key (graph,commit) straddle per fold (test recs whose exact positive "
      f"example appears in train): {commit_straddles}")

# cross-process determinism of the full fold->task pipeline
sub = """
import os, sys, hashlib
sys.path.insert(0, %r); sys.path.insert(0, %r)
import unified_compare as U, discover_semantics as D
recs = U.load_pooled("final"); folds = U.shared_folds(recs, 5)
test = folds[0]; train = [r for j, f in enumerate(folds) if j != 0 for r in f]
cells = U.dedup_weighted(train); negs, neg_w = U.shared_negatives(train, 150)
pos = [D.render_example("pos", f"p{i}", c["weight"], c["args"], c["attacks"], c["commit"]) for i, c in enumerate(cells)]
neg = [D.render_example("neg", f"n{j}", neg_w, ar, at, ng) for j, (ar, at, ng) in enumerate(negs)]
it = "\\n".join(pos + neg) + "\\n\\n" + D.BG + "\\n\\n" + U.MODES_MAXV1 + "\\n"
ft = U.fastlas_task(cells, negs, neg_w)
print(hashlib.sha256(it.encode()).hexdigest(), hashlib.sha256(ft.encode()).hexdigest())
""" % (os.path.dirname(HERE), HERE)
import subprocess
h1 = subprocess.run([sys.executable, "-c", sub], capture_output=True, text=True, timeout=300).stdout.strip()
h2 = subprocess.run([sys.executable, "-c", sub], capture_output=True, text=True, timeout=300).stdout.strip()
OK("cross-process byte-identical fold-0 tasks (ILASP+FastLAS sha256)", h1 == h2 and len(h1) > 0,
   f"\n        {h1}\n        {h2}")

print()
print("=" * 90)
print("(2) EXAMPLE IDENTITY: ILASP task vs FastLAS task, fold 0")
print("=" * 90)
test = folds1[0]
train = [r for j, f in enumerate(folds1) if j != 0 for r in f]
cells = U.dedup_weighted(train)
negs, neg_w = U.shared_negatives(train, 150)
print(f"  fold0: n_train={len(train)} n_cells={len(cells)} n_negs={len(negs)} neg_w={neg_w}")
smoke = json.load(open(os.path.join(HERE, "results", "unified_smoke.json")))
sm0 = smoke["final"]["folds"][0]
OK("fold-0 stats match the smoke-run harness record",
   (sm0["n_train"], sm0["n_cells"], sm0["n_negs"], sm0["neg_w"]) == (len(train), len(cells), len(negs), neg_w),
   f"(smoke: {sm0['n_train']},{sm0['n_cells']},{sm0['n_negs']},{sm0['neg_w']})")
pos_mass = 100 * len(train)
print(f"  mass balance: pos_mass={pos_mass}  neg_mass={neg_w*len(negs)}  ratio={neg_w*len(negs)/pos_mass:.4f}")

# dedup/shell args-consistency: does every rec merged into a key share the SAME args?
bad_args = 0
km = defaultdict(set)
for r in train:
    km[commitkey(r)].add(tuple(r["args"]))
bad_args = sum(1 for k, v in km.items() if len(v) > 1)
OK("every dedup cell has a unique args-set (no arbitrary representative)", bad_args == 0,
   f"({bad_args} keys with >1 distinct args-set)")

# build both tasks exactly as the harness does
ipos = [D.render_example("pos", f"p{i}", c["weight"], c["args"], c["attacks"], c["commit"]) for i, c in enumerate(cells)]
ineg = [D.render_example("neg", f"n{j}", neg_w, ar, at, ng) for j, (ar, at, ng) in enumerate(negs)]
itask = "\n".join(ipos + ineg) + "\n\n" + D.BG + "\n\n" + U.MODES_MAXV1 + "\n"
ftask = U.fastlas_task(cells, negs, neg_w)

EX_RE = re.compile(r"#(pos|neg)\((\w+)@(\d+), \{(.*?)\}, \{(.*?)\}, \{(.*?)\}\)\.\s*$")

def atoms(s):
    return [a.strip() for a in s.split(",") if a.strip()] if s.strip() else []

def parse_ctx(ctx):
    args = sorted(re.findall(r"\barg\((\w+)\)", ctx))
    atts = sorted(re.findall(r"\batt\((\w+),\s*(\w+)\)", ctx))
    lab = {}
    for m in re.finditer(r"(?<![\w])(in|out)\((\w+)\)", ctx):
        lab[m.group(2)] = m.group(1)
    return args, atts, lab

ilasp_ex = {}
for ln in itask.splitlines():
    m = EX_RE.match(ln)
    if not m:
        continue
    et, eid, w, incl, excl, ctx = m.groups()
    args, atts, _ = parse_ctx(ctx)
    lab = {}
    for a in atoms(incl):
        mm = re.match(r"(in|out)\((\w+)\)", a)
        lab[mm.group(2)] = mm.group(1)
    ilasp_ex[eid] = {"type": et, "w": int(w), "args": args, "atts": atts, "lab": lab,
                     "incl": set(atoms(incl)), "excl": set(atoms(excl))}

fl_ex = {}
for ln in ftask.splitlines():
    m = EX_RE.match(ln)
    if not m:
        continue
    et, eid, w, incl, excl, ctx = m.groups()
    args, atts, lab = parse_ctx(ctx)
    kind = "pos" if "violated" in excl else ("neg" if "violated" in incl else "??")
    fl_ex[eid] = {"type": kind, "w": int(w), "args": args, "atts": atts, "lab": lab}

n_ip = sum(1 for e in ilasp_ex.values() if e["type"] == "pos")
n_in = sum(1 for e in ilasp_ex.values() if e["type"] == "neg")
n_fp = sum(1 for e in fl_ex.values() if e["type"] == "pos")
n_fn = sum(1 for e in fl_ex.values() if e["type"] == "neg")
OK("counts: ILASP pos/neg == FastLAS pos/neg == cells/negs",
   n_ip == n_fp == len(cells) and n_in == n_fn == len(negs),
   f"(ILASP {n_ip}p/{n_in}n, FastLAS {n_fp}p/{n_fn}n, expected {len(cells)}p/{len(negs)}n)")

mism = []
for eid, ie in ilasp_ex.items():
    fe = fl_ex.get(eid)
    if fe is None:
        mism.append((eid, "missing in FastLAS")); continue
    if ie["w"] != fe["w"]:
        mism.append((eid, f"weight {ie['w']} vs {fe['w']}"))
    if ie["args"] != fe["args"]:
        mism.append((eid, f"args {ie['args']} vs {fe['args']}"))
    if ie["atts"] != fe["atts"]:
        mism.append((eid, f"atts {ie['atts']} vs {fe['atts']}"))
    if ie["lab"] != fe["lab"]:
        mism.append((eid, f"labelling {ie['lab']} vs {fe['lab']}"))
    if ie["type"] != fe["type"]:
        mism.append((eid, f"polarity {ie['type']} vs {fe['type']}"))
OK("per-example identity (weight, graph, labelling, polarity) across ALL examples",
   not mism, f"({len(mism)} mismatches)" + ("".join(f"\n        {x}" for x in mism[:10])))

# ILASP CDPI internal consistency: excl encodes exactly 'opposite of committed' + 'both for undec'
bad_excl = []
for eid, ie in ilasp_ex.items():
    want_excl = set()
    for a in ie["args"]:
        s = ie["lab"].get(a)
        if s == "in":
            want_excl.add(f"out({a})")
        elif s == "out":
            want_excl.add(f"in({a})")
        else:
            want_excl.add(f"in({a})"); want_excl.add(f"out({a})")
    if ie["excl"] != want_excl:
        bad_excl.append(eid)
OK("ILASP incl/excl == the same 3-valued labelling constraint (undec = neither)", not bad_excl,
   f"({len(bad_excl)} bad)")

# semantic diff of 10 sampled examples
print("\n  --- semantic diff, 10 sampled examples (ILASP CDPI vs FastLAS violated-in-context) ---")
sample = [f"p{i}" for i in (0, 10, 22, 44)] + [f"n{j}" for j in (0, 25, 60, 99, 120, 149)]
for eid in sample:
    ie, fe = ilasp_ex[eid], fl_ex[eid]
    same = ie["lab"] == fe["lab"] and ie["args"] == fe["args"] and ie["atts"] == fe["atts"] and ie["w"] == fe["w"]
    labstr = ",".join(f"{a}:{ie['lab'].get(a,'undec')}" for a in ie["args"])
    print(f"    {eid:<5} w={ie['w']:<6} graph={len(ie['args'])}args/{len(ie['atts'])}atts  "
          f"lab[{labstr}]  ILASP({ie['type']}: incl={sorted(ie['incl'])} excl-count={len(ie['excl'])}) "
          f"== FastLAS({'{}->{violated}' if fe['type']=='pos' else '{violated}->{}'})  {'SAME' if same else 'DIFF'}")

print()
print("=" * 90)
print("(3) SCORING SINGLE-PATH + McNEMAR PAIRING (recompute fold 0 with the smoke rules)")
print("=" * 90)
rules_by_arm = {a: sm0["arms"][a]["rules"] for a in U.LEARNERS}
conf = {(a, rd): Counter() for a in U.ARMS for rd in U.READINGS}
paired = {(a, rd): [] for a in U.ARMS for rd in ("skeptical", "credulous")}
seq = {(a, rd): [] for a in U.ARMS for rd in ("skeptical", "credulous")}
for r in test:
    preds = {}
    for arm in U.ARMS:
        for rd in U.READINGS:
            p = U.predict_arm(arm, rules_by_arm.get(arm), r["args"], r["attacks"], rd)
            conf[(arm, rd)] += D.score(p, r["labels"])
            if rd in ("skeptical", "credulous"):
                preds[(arm, rd)] = p
    for a_, h in r["labels"].items():
        for arm in U.ARMS:
            for rd in ("skeptical", "credulous"):
                paired[(arm, rd)].append(1 if preds[(arm, rd)].get(a_, "undec") == h else 0)
                seq[(arm, rd)].append((r["version"], r["pid"], a_))

ref = seq[(U.ARMS[0], "skeptical")]
align = all(seq[k] == ref for k in seq)
OK("paired sequences index-aligned across ALL arms (same (cond,pid,arg) order)", align,
   f"(len={len(ref)}, arms x readings checked: {len(seq)})")
OK("paired length == fold-0 held-out responses", len(ref) == sum(len(r['labels']) for r in test),
   f"({len(ref)} vs {sum(len(r['labels']) for r in test)})")

# compare recomputed confusions vs the harness-written smoke JSON (same single path?)
jconf = smoke["final"]["conf"]
diffs = []
for (arm, rd), c in conf.items():
    jc = {tuple(k.split(">")): v for k, v in jconf[f"{arm}|{rd}"].items()}
    if dict(c) != jc:
        diffs.append((arm, rd, dict(c), jc))
OK("recomputed confusions IDENTICAL to harness smoke output for all 8 arms x 3 readings",
   not diffs, f"({len(diffs)} diffs)" + "".join(f"\n        {d[0]}|{d[1]}:\n          mine={d[2]}\n          json={d[3]}" for d in diffs[:4]))

# McNemar recompute vs harness
best_tb = max(D.TEXTBOOK, key=lambda a: D.metrics_from_conf(conf[(a, "skeptical")])["acc3"])
print(f"  best textbook (skeptical acc3): {best_tb} (harness said {smoke['final']['table']['_best_textbook_skeptical']})")
mc_ok = True
for arm in U.LEARNERS:
    for rd in ("skeptical", "credulous"):
        a1, a2 = paired[(arm, rd)], paired[(best_tb, rd)]
        b = sum(1 for x, y in zip(a1, a2) if x and not y)
        c_ = sum(1 for x, y in zip(a1, a2) if y and not x)
        p = round(mcnemar(b, c_), 6)
        jm = smoke["final"]["table"][arm][f"mcnemar_{rd}_vs_{best_tb}"]
        match = (jm["learner_only"], jm["textbook_only"], jm["p"]) == (b, c_, p)
        mc_ok &= match
        print(f"    {arm:<13}|{rd:<10} b={b:<3} c={c_:<3} p={p:<9} harness: b={jm['learner_only']} c={jm['textbook_only']} p={jm['p']}  {'MATCH' if match else 'MISMATCH'}")
OK("McNemar discordant counts + p reproduce the harness exactly", mc_ok)

print()
print("=" * 90)
print("(4) ALL-UNDEC PARTICIPANTS FLOW")
print("=" * 90)
au = [r for r in recs1 if not r["commit"] and r["labels"]]
print(f"  all-undec participants in pool: {len(au)}: {[(r['version'], r['pid']) for r in au]}")
OK("all-undec participants kept in the pool", len(au) > 0)
infolds = sum(1 for f in folds1 for r in f if not r["commit"])
OK("all of them land in folds (none dropped by cell_folds)", infolds == len(au), f"({infolds}/{len(au)})")
au_train0 = [r for r in train if not r["commit"]]
au_test0 = [r for r in test if not r["commit"]]
print(f"  fold0: {len(au_train0)} all-undec in train, {len(au_test0)} in test")
au_cells = [i for i, c in enumerate(cells) if not c["commit"]]
print(f"  all-undec dedup cells in fold-0 train: {[(f'p{i}', cells[i]['weight']) for i in au_cells]}")
if au_cells:
    i = au_cells[0]
    print(f"    ILASP  : {ipos[i]}")
    flline = [ln for ln in ftask.splitlines() if ln.startswith(f"#pos(p{i}@")][0]
    print(f"    FastLAS: {flline}")
OK("hard_shell({}) contributes ZERO negatives (no crash)", D.hard_shell({}) == [])
# do all-undec recs contribute negs via shell_of? (they shouldn't)
negs_from_au = 0
for r in au_train0:
    negs_from_au += len(D.hard_shell(r["commit"]))
OK("all-undec train recs add no shell negatives", negs_from_au == 0)
# test-side scoring: all-undec test recs are scored (their labels counted) in every arm
if au_test0:
    n_au_resp = sum(len(r["labels"]) for r in au_test0)
    got = sum(1 for (v, pid, a_) in ref if any(r["pid"] == pid and r["version"] == v for r in au_test0))
    OK("all-undec test responses present in the paired/scored stream", got == n_au_resp,
       f"({got}/{n_au_resp})")
else:
    print("  (no all-undec rec in fold-0 test; checking other folds)")
    for fi in range(1, len(folds1)):
        au_t = [r for r in folds1[fi] if not r["commit"]]
        if au_t:
            print(f"    fold {fi} test would hold {len(au_t)} all-undec recs -> scored via same loop")
            break
print("\ndone.")
