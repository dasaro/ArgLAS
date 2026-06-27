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
import argparse, glob, os, re, subprocess, sys, math, tempfile
from collections import defaultdict, Counter

import clingo

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BG = open(os.path.join(REPO, "background_knowledge.lp")).read().strip()
MODES = open(os.path.join(REPO, "mode_declarations.las")).read().strip()
EXTRACT = os.path.join(HERE, "_tmp_extract_all2")
PHASE = "att_first__lab_first"  # headline = first-individual (most between-participant variance)
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


def load_version(v):
    recs = []
    for f in sorted(glob.glob(os.path.join(EXTRACT, f"version{v}", PHASE, "p*.lp"))):
        args, attacks, labels = parse_lp(f)
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


def build_task(recs, weight=100):
    pos_keys = {(tuple(sorted(r["attacks"])), tuple(sorted(r["commit"].items()))) for r in recs}
    lines = []
    for i, r in enumerate(recs):
        lines.append(render_example("pos", f"p{i}", weight, r["args"], r["attacks"], r["commit"]))
    seen = set()
    j = 0
    for r in recs:
        for neg in hard_shell(r["commit"]):
            key = (tuple(sorted(r["attacks"])), tuple(sorted(neg.items())))
            if key in pos_keys or key in seen:
                continue
            seen.add(key)
            lines.append(render_example("neg", f"n{j}", None, r["args"], r["attacks"], neg))  # HARD boundary
            j += 1
    return "\n".join(lines) + "\n\n" + BG + "\n\n" + MODES + "\n", len(recs), j


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
    """Full labellings of BG+learned theory, using the theory's OWN in AND out atoms
    (the predictor fix: do NOT re-derive out from attacks). undec = neither."""
    prog = BG + "\n" + "\n".join(rules) + "\n"
    labs = []
    for m in _solve(prog, args, attacks, ("in", "out")):
        labs.append({a: ("in" if a in m["in"] else "out" if a in m["out"] else "undec") for a in args})
    return labs


def textbook_labellings(kind, args, attacks):
    """Standard complete labelling of each textbook extension (in-set): out = attacked
    by in, undec = rest. (ASPARTIX encodings emit only in/1.)"""
    insets = [m["in"] for m in _solve(open(ASPARTIX[kind]).read(), args, attacks, ("in",))]
    labs = []
    for s in insets:
        att_out = {y for (x, y) in attacks if x in s}
        labs.append({a: ("in" if a in s else "out" if a in att_out else "undec") for a in args})
    return labs


def skeptical_project(labs, args):
    """Same cautious reading for EVERY predictor (kills the evaluation asymmetry): an
    argument is predicted in/out only if all labellings agree, else undecided."""
    if not labs:
        return {a: "undec" for a in args}
    pred = {}
    for a in args:
        vals = {l.get(a, "undec") for l in labs}
        pred[a] = next(iter(vals)) if len(vals) == 1 else "undec"
    return pred


def predict(kind, args, attacks, rules=None):
    labs = learned_labellings(rules, args, attacks) if kind == "learned" else textbook_labellings(kind, args, attacks)
    return skeptical_project(labs, args), len(labs)


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
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    io_total = sum(conf[(h, p)] for h in ("in", "out") for p in CLASSES)
    committed = sum(conf[(h, p)] for h in ("in", "out") for p in ("in", "out"))
    return {"acc3": acc3, "macroF1": sum(f1s) / len(f1s),
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
    args, attacks = modal_aaf(recs)
    pred, n_ext = predict("learned", args, attacks, rules)
    n_commit = sum(1 for a in args if pred[a] in ("in", "out"))
    return {"v": v, "n_part": len(recs), "npos": npos, "nneg": nneg, "rules": rules,
            "n_ext": n_ext, "skeptical_commit": f"{n_commit}/{len(args)}", "modal_attacks": attacks}


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
    conf = {p: Counter() for p in preds}
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
                    pred, _ = predict(kind, r["args"], r["attacks"], rules if kind == "learned" else None)
                    conf[kind] += score(pred, r["labels"])
        if on_progress:
            on_progress(fi + 1, k)
    res = {"v": v, "k": k, "n_part": len(recs), "ilasp_timeouts": timeouts}
    for kind in preds:
        res[kind] = metrics_from_conf(conf[kind])
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--versions", default="A,B,C,D,E,F,G")
    ap.add_argument("--mode", choices=("discover", "cv"), default="discover")
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--phase", choices=("first", "final", "group"), default="first",
                    help="response phase: first-individual (headline), final-individual, or group.")
    ap.add_argument("--ilasp-timeout", type=int, default=1800, help="per-fold ILASP timeout (s).")
    args = ap.parse_args(argv)
    global PHASE
    PHASE = {"first": "att_first__lab_first", "final": "att_final__lab_final", "group": "att_group__lab_group"}[args.phase]
    versions = [x.strip() for x in args.versions.split(",") if x.strip()]
    if args.mode == "discover":
        for v in versions:
            r = discover(v, ilasp_timeout=args.ilasp_timeout)
            print(f"\n===== Condition {v}  (n={r['n_part']} participants; {r['npos']} pos / {r['nneg']} hard-neg) =====")
            print(f"  tightness: {r['n_ext']} extensions on modal AAF; skeptical commits {r['skeptical_commit']} args")
            print("  DISCOVERED AXIOMS:")
            for rule in (r["rules"] or ["(empty)"]):
                print(f"    {rule}")
    else:
        print(f"{'cond':<5}{'predictor':<11}{'macroF1':<9}{'acc3':<8}{'commit':<8}{'MCC_io':<8}")
        for v in versions:
            r = cv(v, args.folds, ilasp_timeout=args.ilasp_timeout)
            for kind in ("learned",) + TEXTBOOK:
                m = r[kind]
                print(f"{v:<5}{kind:<11}{m['macroF1']:<9.3f}{m['acc3']:<8.3f}{m['commit_rate']:<8.3f}{m['mcc_committed']:<8.3f}")
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
