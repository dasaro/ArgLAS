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
ASPARTIX = {s: os.path.join(REPO, "ASPARTIX", f"{f}.lp")
            for s, f in [("grounded", "grounded"), ("preferred", "preferred"), ("stable", "stable")]}


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
    for f in sorted(glob.glob(os.path.join(EXTRACT, f"version{v}", "att_final__lab_final", "p*.lp"))):
        args, attacks, labels = parse_lp(f)
        c = committed(labels)
        if c:
            recs.append({"pid": os.path.basename(f)[:-3], "args": args,
                         "attacks": attacks, "commit": c})
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


def enumerate_insets(program, args, attacks, show="in"):
    facts = "".join(f"arg({a}). " for a in args) + "".join(f"att({s},{t}). " for s, t in attacks)
    ctl = clingo.Control(["0", "--warn=none"])
    ctl.add("base", [], program + "\n" + facts + f"\n#show {show}/1.\n")
    ctl.ground([("base", [])])
    models = []
    ctl.solve(on_model=lambda m: models.append(
        frozenset(str(s.arguments[0]) for s in m.symbols(shown=True) if s.name == show)))
    return models


def labelling_from_inset(inset, args, attacks):
    """Standard complete labelling of an in-set: out = attacked by in; undec = rest."""
    out = {y for (x, y) in attacks if x in inset}
    return {a: ("in" if a in inset else "out" if a in out else "undec") for a in args}


def skeptical(insets, args, attacks):
    if not insets:
        return {a: "undec" for a in args}
    labs = [labelling_from_inset(s, args, attacks) for s in insets]
    pred = {}
    for a in args:
        vals = {l[a] for l in labs}
        pred[a] = vals.pop() if len(vals) == 1 else "undec"
    return pred


def predictor_program(kind, theory_rules=None):
    if kind == "learned":
        return BG + "\n" + "\n".join(theory_rules) + "\n"
    return open(ASPARTIX[kind]).read()


def score(pred_labels, human_commit):
    tp = fp = tn = fn = commit = total = 0
    for a, h in human_commit.items():
        total += 1
        p = pred_labels.get(a, "undec")
        if p in ("in", "out"):
            commit += 1
            if p == "in" and h == "in": tp += 1
            elif p == "in" and h == "out": fp += 1
            elif p == "out" and h == "out": tn += 1
            elif p == "out" and h == "in": fn += 1
    return tp, fp, tn, fn, commit, total


def mcc(tp, fp, tn, fn):
    d = math.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
    return ((tp*tn-fp*fn)/d) if d else float("nan")


def modal_aaf(recs):
    c = Counter(tuple(sorted(r["attacks"])) for r in recs)
    attacks = [tuple(x) for x in c.most_common(1)[0][0]]
    args = sorted({a for r in recs for a in r["args"]})
    return args, attacks


def discover(v):
    recs = load_version(v)
    task, npos, nneg = build_task(recs)
    rules = run_ilasp(task)
    args, attacks = modal_aaf(recs)
    insets = enumerate_insets(predictor_program("learned", rules), args, attacks)
    pred = skeptical(insets, args, attacks)
    n_commit = sum(1 for a in args if pred[a] in ("in", "out"))
    return {"v": v, "n_part": len(recs), "npos": npos, "nneg": nneg, "rules": rules,
            "n_ext": len(insets), "skeptical_commit": f"{n_commit}/{len(args)}", "modal_attacks": attacks}


def make_folds(recs, k, seed=20260627):
    order = sorted(range(len(recs)), key=lambda i: recs[i]["pid"])
    folds = [[] for _ in range(k)]
    for idx, i in enumerate(order):
        folds[(idx * 7 + seed) % k].append(recs[i])
    return folds


def cv(v, k=5):
    recs = load_version(v)
    if len(recs) < k:
        k = max(2, len(recs))
    folds = make_folds(recs, k)
    acc = {p: [0, 0, 0, 0, 0, 0] for p in ("learned", "grounded", "preferred", "stable")}
    for fi in range(k):
        test = folds[fi]
        train = [r for j, f in enumerate(folds) if j != fi for r in f]
        if not train or not test:
            continue
        task, _, _ = build_task(train)
        rules = run_ilasp(task)
        for r in test:
            for kind in acc:
                prog = predictor_program("learned", rules) if kind == "learned" else predictor_program(kind)
                insets = enumerate_insets(prog, r["args"], r["attacks"])
                pred = skeptical(insets, r["args"], r["attacks"])
                tp, fp, tn, fn, commit, total = score(pred, r["commit"])
                a = acc[kind]
                a[0] += tp; a[1] += fp; a[2] += tn; a[3] += fn; a[4] += commit; a[5] += total
    res = {"v": v, "k": k, "n_part": len(recs)}
    for kind, a in acc.items():
        tp, fp, tn, fn, commit, total = a
        correct = tp + tn
        res[kind] = {"acc_on_committed": (correct / commit) if commit else float("nan"),
                     "MCC": mcc(tp, fp, tn, fn),
                     "commit_rate": (commit / total) if total else float("nan")}
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--versions", default="A,B,C,D,E,F,G")
    ap.add_argument("--mode", choices=("discover", "cv"), default="discover")
    ap.add_argument("--folds", type=int, default=5)
    args = ap.parse_args(argv)
    versions = [x.strip() for x in args.versions.split(",") if x.strip()]
    if args.mode == "discover":
        for v in versions:
            r = discover(v)
            print(f"\n===== Condition {v}  (n={r['n_part']} participants; {r['npos']} pos / {r['nneg']} hard-neg) =====")
            print(f"  tightness: {r['n_ext']} extensions on modal AAF; skeptical commits {r['skeptical_commit']} args")
            print("  DISCOVERED AXIOMS:")
            for rule in (r["rules"] or ["(empty)"]):
                print(f"    {rule}")
    else:
        print(f"{'cond':<5}{'pred':<11}{'acc/committed':<15}{'MCC':<9}{'commit_rate':<12}")
        for v in versions:
            r = cv(v, args.folds)
            for kind in ("learned", "grounded", "preferred", "stable"):
                m = r[kind]
                print(f"{v:<5}{kind:<11}{m['acc_on_committed']:<15.3f}{m['MCC']:<9.3f}{m['commit_rate']:<12.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
