#!/usr/bin/env python3
"""Data-driven semantics DISCOVERY for the real-world (Exp2) study.

Goal: find the actual acceptance axioms humans follow per condition A-G, learned
agnostically (no target semantics) and PINNED by hard negatives, then validated on
held-out participants. This goes one step past the 2022 "compare to grounded/preferred/CF2"
analysis: the axioms are the output.

Principled choices
------------------
- Positives  : each participant's committed (in/out) final labelling, on their own AAF,
               soft-weighted (penalty, not hard) so dissenters are absorbed as noise.
- Negatives  : the EXHAUSTIVE Hamming-1 shell -- every single committed-arg flip of a
               positive that is not itself a positive labelling. These minimal
               perturbations are the hardest, most boundary-defining negatives and are
               what pin an otherwise under-determined theory (the reliable_negative run
               used farthest-Hamming negatives, which never constrain the boundary).
- Hypothesis : agnostic argumentation vocabulary (mode_declarations.las), shortest theory.
- Validation : k-fold over participants; the discovered theory predicts held-out labels
               (skeptical reading) and is compared head-to-head with grounded/preferred/
               stable. Defensible iff it is tight AND predicts >= the best textbook semantics.

Usage:
  python3 discover_semantics.py --versions A,B,C,D,E,F,G --mode discover
  python3 discover_semantics.py --versions A,B,C,D,E,F,G --mode cv --folds 5
"""
import argparse, glob, os, random, re, subprocess, sys, math, tempfile
from collections import defaultdict, Counter

import clingo

HERE = os.path.dirname(os.path.abspath(__file__))
RWE = os.path.dirname(HERE)
REPO = os.path.dirname(RWE)
BG = open(os.path.join(REPO, "config/background_knowledge.lp")).read().strip()
MODES = open(os.path.join(REPO, "config/mode_declarations.las")).read().strip()
# AGNOSTIC mode-bias enrichment (opt-in via env ARGLAS_ENRICH). The base vocabulary
# {in,out,arg,att,defeated,not_defended,supported} provably CANNOT express cf2-like behaviour on
# cyclic AFs (needs SCC/reachability). Two enrichment levers, both agnostic (structural graph
# properties, not semantics); off by default so the baseline is unaffected:
#   ARGLAS_ENRICH=cycle  -> add the UNARY derived predicate in_cycle(X) := X lies on a directed
#                           att-cycle (reach(X,X)). Cheap: one unary modeb (like defeated), tiny
#                           search-space growth, and it is exactly the SCC signal cf2 keys on
#                           (odd cycles commit). PREFERRED.
#   ARGLAS_ENRICH=reach  -> expose the full BINARY reach/2. Maximally expressive but explodes the
#                           search space (~2.4x) and TIMES OUT on the study conditions; kept only
#                           for reference. reach/2 stays in the background either way.
_enr = os.environ.get("ARGLAS_ENRICH", "")
if "cycle" in _enr or "reach" in _enr:
    BG += "\nreach(X, Y) :- att(X, Y).\nreach(X, Z) :- att(X, Y), reach(Y, Z)."
if "cycle" in _enr:
    BG += "\nin_cycle(X) :- reach(X, X)."
    MODES += "\n#modeb(in_cycle(var(arg)))."
if "reach" in _enr:
    MODES += "\n#modeb(reach(var(arg), var(arg)))."
# Prediction-time BG WITHOUT the 0{in}1/0{out}1 choice rules. Those choice rules are needed in
# the ILASP LEARNING task (so hypotheses can generate in/out), but at PREDICTION time they let
# clingo freely guess in/out -- inflating a learned theory's extension set (a grounded theory
# returns 3-15 labellings instead of 1) and fabricating conflicting credulous labellings. Solving
# the learned rules against BG_PREDICT makes the theory's entailed in/out/undec match the ASPARTIX
# encodings exactly (verified 38/38 graphs, all readings). Agnostic: embeds no textbook prior.
BG_PREDICT = "\n".join(ln for ln in BG.splitlines()
                       if "0{ in(X) }1" not in ln and "0{ out(X) }1" not in ln)
EXTRACT = os.path.join(RWE, "_tmp_extract_all2")
PHASE = "att_first__lab_first"  # headline = first-individual (most between-participant variance)
GRAPH = "own"                   # "own" = each participant's drawn graph; "gold" = canonical stimulus

# Canonical GOLD BaseAF per condition, from PART_A EXPECTED (verified 0-ambiguity in the
# audit). att(X,Y) = X attacks Y. Gold track attaches every participant's labels to this
# shared graph, so a learned theory's commitments transfer across participants.
_FLOAT = (["a", "b", "c", "d"], [("b", "a"), ("c", "b"), ("c", "d"), ("d", "b"), ("d", "c")])
_SIMPLE = (["a", "b", "c"], [("b", "a"), ("c", "b")])
_CYCLE = (["a", "b", "c", "d", "e"], [("b", "a"), ("c", "b"), ("c", "d"), ("d", "b"), ("d", "e"), ("e", "b"), ("e", "c")])
GOLD = {"A": _FLOAT, "B": _FLOAT, "C": _FLOAT, "D": _SIMPLE, "E": _SIMPLE, "F": _SIMPLE, "G": _CYCLE}
ASPARTIX = {s: os.path.join(REPO, "ASPARTIX", f"{s}.lp")
            for s in ("grounded", "preferred", "stable", "complete", "cf2")}
TEXTBOOK = ("grounded", "preferred", "stable", "complete", "cf2")


def parse_lp(path):
    t = open(path).read()
    args = sorted(re.findall(r"arg\((\w+)\)", t))
    attacks = [(x, y) for x, y in re.findall(r"att\((\w+),(\w+)\)", t)]
    labels = {}
    for s, x in re.findall(r"\b(in|out|undec)\((\w+)\)", t):
        labels[x] = s
    return args, attacks, {a: labels.get(a) for a in args}


def committed(labels):
    return {a: s for a, s in labels.items() if s in ("in", "out")}


def load_recs(v, graph="gold", label_phase="final"):
    """Decoupled loader for the 2022-faithful comparison. graph selects the AF the
    semantics is applied to: 'gold' = the intended BaseAF, 'ind' = the participant's own
    final Part-A drawing (IndAF, att_final), 'group' = the group's Part-A drawing (GroupAF,
    att_group). label_phase selects the Part-B response (first/group/final). Keeps every
    participant with at least one label (incl. all-undecided), matching the paper's
    response-level counting."""
    gargs, gatt = GOLD[v]
    recs, seen = [], set()
    # gold: labels are att-source-independent and the AF is fixed, so UNION across att dirs
    # (so participants whose att_final drawing is all-NA are still counted -> pools all 500
    # responses, matching the paper). ind/group legitimately depend on the drawing.
    asrcs = ("final", "group", "first") if graph == "gold" else (("group",) if graph == "group" else ("final",))
    for asrc in asrcs:
        for f in sorted(glob.glob(os.path.join(EXTRACT, f"version{v}", f"att_{asrc}__lab_{label_phase}", "p*.lp"))):
            pid = os.path.basename(f)[:-3]
            if pid in seen:
                continue
            args, attacks, labels = parse_lp(f)
            if graph == "gold":
                args, attacks = list(gargs), [tuple(e) for e in gatt]
                labels = {a: labels.get(a) for a in gargs}
            lab = {a: s for a, s in labels.items() if s in CLASSES}
            if lab:
                seen.add(pid)
                recs.append({"pid": pid, "args": args, "attacks": attacks,
                             "commit": committed(labels), "labels": lab})
    return recs


def load_version(v):
    recs = []
    gargs, gatt = GOLD[v] if GRAPH == "gold" else (None, None)
    for f in sorted(glob.glob(os.path.join(EXTRACT, f"version{v}", PHASE, "p*.lp"))):
        args, attacks, labels = parse_lp(f)
        if GRAPH == "gold":
            args, attacks = gargs, gatt
            labels = {a: labels.get(a) for a in gargs}  # participant's labels on the shared gold graph
        c = committed(labels)
        if c:
            recs.append({"pid": os.path.basename(f)[:-3], "args": args, "attacks": attacks,
                         "commit": c, "labels": {a: s for a, s in labels.items() if s in CLASSES}})
    return recs


def render_example(etype, eid, weight, args, attacks, commit):
    # weight=None -> HARD example (must be satisfied/rejected); else soft with penalty.
    head = f"#{etype}({eid}, " if weight is None else f"#{etype}({eid}@{weight}, "
    incl, excl = [], []
    for a in args:
        s = commit.get(a)
        if s == "in":
            incl.append(f"in({a})"); excl.append(f"out({a})")
        elif s == "out":
            incl.append(f"out({a})"); excl.append(f"in({a})")
        else:  # uncommitted (undec / not labelled) -> exclude both
            excl.append(f"in({a})"); excl.append(f"out({a})")
    ctx = " ".join([f"arg({a})." for a in args] + [f"att({s},{t})." for s, t in attacks])
    return f"{head}{{{', '.join(incl)}}}, {{{', '.join(excl)}}}, {{{ctx}}})."


def hard_shell(commit):
    """Exhaustive Hamming-1 hard negatives around a human labelling. Two kinds, both
    needed to PIN the theory: (1) FLIP a committed arg in<->out (forces the right value);
    (2) DROP a committed arg to undecided (forces commitment, not just forbids the wrong
    value). Without the drops the learner forbids 'out' but never forces 'in', so the
    skeptical reading abstains everywhere (observed)."""
    out = []
    for a, s in commit.items():
        flipped = dict(commit)
        flipped[a] = "out" if s == "in" else "in"
        out.append(flipped)
        dropped = dict(commit)
        del dropped[a]  # a becomes undecided (excluded from both in and out)
        out.append(dropped)
    return out


def build_task(recs, weight=100, neg_weight=100, max_neg=None):
    # neg_weight=100 (soft) is the AGNOSTIC default: the Hamming-1 shell is a PENALTY, not a hard
    # exclusion, so a correct semantics that happens to re-derive one boundary labelling pays a
    # cost instead of being made UNSAT. Pass neg_weight=None to restore the old (contaminating)
    # hard negatives. On known-grounded synthetic data this lifts recovery under noise from ~0.27
    # (hard) back to ~0.80 (soft), matching an oracle that peeks at the truth.
    pos_keys = {(tuple(sorted(r["attacks"])), tuple(sorted(r["commit"].items()))) for r in recs}
    pos = [render_example("pos", f"p{i}", r.get("weight", weight), r["args"], r["attacks"], r["commit"])
           for i, r in enumerate(recs)]
    seen = set()
    negs = []
    for r in recs:
        for neg in hard_shell(r["commit"]):
            key = (tuple(sorted(r["attacks"])), tuple(sorted(neg.items())))
            if key in pos_keys or key in seen:
                continue
            seen.add(key)
            negs.append((r["args"], r["attacks"], neg))
    if max_neg and len(negs) > max_neg:  # deterministic sample to keep ILASP tractable
        negs = [negs[i] for i in sorted(random.Random(20260627).sample(range(len(negs)), max_neg))]
    neg_lines = [render_example("neg", f"n{j}", neg_weight, ar, at, ng) for j, (ar, at, ng) in enumerate(negs)]
    return "\n".join(pos + neg_lines) + "\n\n" + BG + "\n\n" + MODES + "\n", len(recs), len(neg_lines)


def run_ilasp(task_text, timeout=300):
    with tempfile.NamedTemporaryFile("w", suffix=".las", delete=False) as f:
        f.write(task_text); path = f.name
    try:
        out = subprocess.run(["ILASP", "--version=4", "-d", path], capture_output=True,
                             text=True, timeout=timeout).stdout
    except subprocess.TimeoutExpired:
        return ["% TIMEOUT"]
    finally:
        os.unlink(path)
    rules = [ln.strip() for ln in out.splitlines()
             if ln.strip().endswith(".") and ("V1" in ln or "V2" in ln or ":-" in ln)
             and not ln.strip().startswith("%")]
    return rules


def _solve(program, args, attacks, shows):
    facts = "".join(f"arg({a}). " for a in args) + "".join(f"att({s},{t}). " for s, t in attacks)
    ctl = clingo.Control(["0", "--warn=none"])
    ctl.add("base", [], program + "\n" + facts + "\n" + "".join(f"#show {s}/1.\n" for s in shows))
    ctl.ground([("base", [])])
    models = []
    def on_model(m):
        d = {s: frozenset(str(x.arguments[0]) for x in m.symbols(shown=True) if x.name == s) for s in shows}
        models.append(d)
    ctl.solve(on_model=on_model)
    return models


def learned_labellings(rules, args, attacks):
    """Full labellings entailed by the learned theory, using its OWN in/out atoms; undec=neither.
    Solves against BG_PREDICT (no free in/out guessing) so the entailed labellings match the
    ASPARTIX convention rather than being inflated by BG's choice rules. Fallback: a constraint-
    only theory that RELIES on guessing (e.g. ':- supported(X), not in(X).' with no in-rule) is
    UNSAT without the choice rules -- there we solve against full BG plus conflict-freeness, which
    still drops the spurious in-attacks-in extensions the raw choice rules inject."""
    body = "\n".join(rules)
    models = _solve(BG_PREDICT + "\n" + body + "\n", args, attacks, ("in", "out"))
    if not models:
        models = _solve(BG + "\n:- in(X), in(Y), att(X, Y).\n" + body + "\n", args, attacks, ("in", "out"))
    return [{a: ("in" if a in m["in"] else "out" if a in m["out"] else "undec") for a in args} for m in models]


def textbook_labellings(kind, args, attacks):
    """Standard complete labelling of each textbook extension (in-set): out = attacked
    by in, undec = rest. (ASPARTIX encodings emit only in/1.)"""
    insets = [m["in"] for m in _solve(open(ASPARTIX[kind]).read(), args, attacks, ("in",))]
    if kind == "preferred":
        # preferred.lp needs --heuristic=Domain --enum=domRec for subset-maximality; under
        # plain clingo it returns the COMPLETE extensions (incl. {}), which makes skeptical-
        # preferred collapse to grounded. Recover preferred = the subset-MAXIMAL in-sets.
        insets = [s for s in insets if not any(s < t for t in insets)]
    labs = []
    for s in insets:
        att_out = {y for (x, y) in attacks if x in s}
        labs.append({a: ("in" if a in s else "out" if a in att_out else "undec") for a in args})
    return labs


READINGS = ("skeptical", "credulous", "grounded")
_ORDER = {"in": 0, "out": 1, "undec": 2}


def project(labs, args, reading):
    """Turn a set of labellings into one predicted labelling. Applied SYMMETRICALLY to
    learned and textbook predictors. Three readings:
      - skeptical : commit only where ALL extensions agree (cautious; under-commits).
      - credulous : plurality label across extensions, ties broken toward commitment
                    (in/out over undec) -- matches the credulous human reasoning mode.
      - grounded  : the labelling of the subset-MINIMAL in-set (grounded-of-learned;
                    a single deterministic, more-committal-than-skeptical extension)."""
    if not labs:
        return {a: "undec" for a in args}
    if reading == "grounded":
        lab = min(labs, key=lambda l: (sum(1 for a in args if l.get(a) == "in"),
                                       tuple(sorted(a for a in args if l.get(a) == "in"))))
        return {a: lab.get(a, "undec") for a in args}
    pred = {}
    for a in args:
        vals = [l.get(a, "undec") for l in labs]
        if reading == "skeptical":
            pred[a] = vals[0] if len(set(vals)) == 1 else "undec"
        else:  # credulous: plurality, ties toward commitment then 'in'
            cnt = Counter(vals)
            pred[a] = max(cnt, key=lambda x: (cnt[x], -_ORDER[x]))
    return pred


def predict_labellings(kind, args, attacks, rules=None):
    return learned_labellings(rules, args, attacks) if kind == "learned" else textbook_labellings(kind, args, attacks)


CLASSES = ("in", "out", "undec")


def score(pred, human_labels):
    """3-valued confusion over ALL human-labelled args (in/out/undec), Counter[(h,p)]."""
    conf = Counter()
    for a, h in human_labels.items():
        conf[(h, pred.get(a, "undec"))] += 1
    return conf


def mcc(tp, fp, tn, fn):
    d = math.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
    return ((tp*tn-fp*fn)/d) if d else float("nan")


def metrics_from_conf(conf):
    total = sum(conf.values())
    acc3 = sum(conf[(c, c)] for c in CLASSES) / total if total else float("nan")
    f1s = []
    for c in CLASSES:
        tp = conf[(c, c)]
        fp = sum(conf[(h, c)] for h in CLASSES if h != c)
        fn = sum(conf[(c, p)] for p in CLASSES if p != c)
        if tp + fp + fn == 0:  # class absent from BOTH gold and prediction -> not scorable; excluding
            continue           # it avoids deflating macroF1 (e.g. all-committed data with no undec)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    io_total = sum(conf[(h, p)] for h in ("in", "out") for p in CLASSES)
    committed = sum(conf[(h, p)] for h in ("in", "out") for p in ("in", "out"))
    return {"acc3": acc3, "macroF1": (sum(f1s) / len(f1s)) if f1s else float("nan"),
            "commit_rate": committed / io_total if io_total else float("nan"),
            "mcc_committed": mcc(conf[("in", "in")], conf[("out", "in")], conf[("out", "out")], conf[("in", "out")]),
            "n_args": total}


def modal_aaf(recs):
    c = Counter(tuple(sorted(r["attacks"])) for r in recs)
    attacks = [tuple(x) for x in c.most_common(1)[0][0]]
    args = sorted({a for r in recs for a in r["args"]})
    return args, attacks


def discover(v, ilasp_timeout=300):
    recs = load_version(v)
    task, npos, nneg = build_task(recs)
    rules = run_ilasp(task, timeout=ilasp_timeout)
    args, attacks = (GOLD[v] if GRAPH == "gold" else modal_aaf(recs))
    labs = predict_labellings("learned", args, attacks, rules)
    cred = project(labs, args, "credulous")
    n_commit = sum(1 for a in args if cred[a] in ("in", "out"))
    return {"v": v, "n_part": len(recs), "npos": npos, "nneg": nneg, "rules": rules,
            "n_ext": len(labs), "credulous_commit": f"{n_commit}/{len(args)}", "graph": GRAPH}


def make_folds(recs, k, seed=20260627):
    order = sorted(range(len(recs)), key=lambda i: recs[i]["pid"])
    folds = [[] for _ in range(k)]
    for idx, i in enumerate(order):
        folds[(idx * 7 + seed) % k].append(recs[i])
    return folds


def cv(v, k=5, ilasp_timeout=300, on_progress=None):
    recs = load_version(v)
    if len(recs) < k:
        k = max(2, len(recs))
    folds = make_folds(recs, k)
    preds = ("learned",) + TEXTBOOK
    conf = {(p, rd): Counter() for p in preds for rd in READINGS}
    timeouts = 0
    for fi in range(k):
        test = folds[fi]
        train = [r for j, f in enumerate(folds) if j != fi for r in f]
        if train and test:
            rules = run_ilasp(build_task(train)[0], timeout=ilasp_timeout)
            if rules == ["% TIMEOUT"]:
                timeouts += 1
            for r in test:
                for kind in preds:
                    labs = predict_labellings(kind, r["args"], r["attacks"], rules if kind == "learned" else None)
                    for rd in READINGS:
                        conf[(kind, rd)] += score(project(labs, r["args"], rd), r["labels"])
        if on_progress:
            on_progress(fi + 1, k)
    res = {"v": v, "k": k, "n_part": len(recs), "ilasp_timeouts": timeouts}
    for kind in preds:
        res[kind] = {rd: metrics_from_conf(conf[(kind, rd)]) for rd in READINGS}
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--versions", default="A,B,C,D,E,F,G")
    ap.add_argument("--mode", choices=("discover", "cv"), default="discover")
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--phase", choices=("first", "final", "group"), default="first",
                    help="response phase: first-individual (headline), final-individual, or group.")
    ap.add_argument("--ilasp-timeout", type=int, default=1800, help="per-fold ILASP timeout (s).")
    ap.add_argument("--graph", choices=("own", "gold"), default="own",
                    help="own = each participant's drawn graph; gold = shared canonical stimulus.")
    ap.add_argument("--reading", choices=READINGS, default="credulous",
                    help="reading shown in the cv table (all three are computed regardless).")
    args = ap.parse_args(argv)
    global PHASE, GRAPH
    PHASE = {"first": "att_first__lab_first", "final": "att_final__lab_final", "group": "att_group__lab_group"}[args.phase]
    GRAPH = args.graph
    versions = [x.strip() for x in args.versions.split(",") if x.strip()]
    if args.mode == "discover":
        for v in versions:
            r = discover(v, ilasp_timeout=args.ilasp_timeout)
            print(f"\n===== Condition {v}  (n={r['n_part']} participants; {r['npos']} pos / {r['nneg']} hard-neg; graph={r['graph']}) =====")
            print(f"  tightness: {r['n_ext']} extensions; credulous commits {r['credulous_commit']} args")
            print("  DISCOVERED AXIOMS:")
            for rule in (r["rules"] or ["(empty)"]):
                print(f"    {rule}")
    else:
        rd = args.reading
        print(f"graph={GRAPH} phase={args.phase} reading={rd} (macroF1 / commit_rate)")
        print(f"{'cond':<5}{'predictor':<11}{'macroF1':<9}{'acc3':<8}{'commit':<8}{'MCC_io':<8}")
        for v in versions:
            r = cv(v, args.folds, ilasp_timeout=args.ilasp_timeout)
            for kind in ("learned",) + TEXTBOOK:
                m = r[kind][rd]
                print(f"{v:<5}{kind:<11}{m['macroF1']:<9.3f}{m['acc3']:<8.3f}{m['commit_rate']:<8.3f}{m['mcc_committed']:<8.3f}")
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
