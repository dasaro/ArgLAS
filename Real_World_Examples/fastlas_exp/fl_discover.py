#!/usr/bin/env python3
"""Agnostic Exp2 semantics DISCOVERY on real human data, powered by FastLAS (30-600x faster than
ILASP -> the WIDER enriched feature space is now affordable). No target semantics is embedded.

Formulation (the S4/S2 verifier reframing that makes it OPL-fast):
  - A labelling is GIVEN as context facts (in/out/undec per arg) + the graph. Target-independent
    STRUCTURAL features (defended, attacked_by_in, undec, in_cycle, ...) are computed from it.
  - LEARN a target-independent constraint `violated :- body` over those features (FastLAS --opl).
    Positives = human labellings (violated EXCLUDED); negatives = the Hamming-1 shell (violated
    INCLUDED). Both SOFT (penalty) so a legal semantics that reproduces one boundary labelling is
    not FORBIDDEN (the H1-contamination lesson from the ILASP pipeline).
  - PREDICT by generate-and-constrain: 0{in}1/0{out}1 + features + learned `:- violated` + a
    reading (skeptical/credulous/grounded-of-survivors); project to one labelling per graph.
  - SCORE 3-valued vs held-out humans and vs every textbook semantics (apples-to-apples).

Everything reuses discover_semantics for loaders / textbook / project / metrics.
"""
import os, sys, subprocess, tempfile, time, argparse
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import discover_semantics as D
import clingo

# ---- target-independent feature background (computed from a GIVEN labelling) ----
_FEATS = """attacked(X) :- att(Y, X).
attacker_not_out(X) :- att(Y, X), not out(Y).
defended(X) :- arg(X), not attacker_not_out(X).
attacked_by_in(X) :- att(Y, X), in(Y).
undec(X) :- arg(X), not in(X), not out(X)."""
_FEATS_ENR = """reach(X, Y) :- att(X, Y).
reach(X, Z) :- att(X, Y), reach(Y, Z).
in_cycle(X) :- reach(X, X)."""

_MODEB = ["#modeb(in(var(arg))).", "#modeb(out(var(arg))).", "#modeb(undec(var(arg))).",
          "#modeb(defended(var(arg))).", "#modeb(attacked_by_in(var(arg))).",
          "#modeb(attacked(var(arg))).",
          "#modeb(not in(var(arg))).", "#modeb(not out(var(arg))).", "#modeb(not undec(var(arg))).",
          "#modeb(not defended(var(arg))).", "#modeb(not attacked_by_in(var(arg)))."]
_MODEB_ENR = ["#modeb(in_cycle(var(arg))).", "#modeb(not in_cycle(var(arg)))."]
_BIAS = ('#bias("penalty(1, head) :- in_head(X).").\n'
         '#bias("penalty(1, body(X)) :- in_body(X).").')


def _feat_bg(enrich):
    return _FEATS + ("\n" + _FEATS_ENR if enrich else "")


def _lab_ctx(args, attacks, lab):
    """context facts: graph + a GIVEN labelling (in/out; undec args get neither -> derived undec)."""
    f = [f"arg({a})." for a in args] + [f"att({s},{t})." for s, t in attacks]
    for a in args:
        if lab.get(a) == "in":
            f.append(f"in({a}).")
        elif lab.get(a) == "out":
            f.append(f"out({a}).")
    return " ".join(f)


# lean modeb = the 6 predicates the useful constraints actually need. Keeps the search space small
# enough for higher maxv (the full 11-predicate set explodes the candidate generation at maxv>=3).
_MODEB_LEAN = ["#modeb(in(var(arg))).", "#modeb(out(var(arg))).",
               "#modeb(defended(var(arg))).", "#modeb(attacked_by_in(var(arg))).",
               "#modeb(not in(var(arg))).", "#modeb(not out(var(arg)))."]


def build_learn_task(pos_labs, neg_labs, enrich=False, maxv=1, pos_w=100, neg_w=100, lean=False):
    """pos_labs / neg_labs: lists of (args, attacks, commit-dict). Learn `violated` s.t. positives
    are NOT violated and negatives ARE. Soft penalties (H1-safe). lean=True uses the 6-predicate
    modeb so maxv>=3 stays tractable."""
    mb = _MODEB_LEAN if lean else (_MODEB + (_MODEB_ENR if enrich else []))
    lines = [_feat_bg(enrich), "", "#modeh(violated)."] + mb
    lines += ["", _BIAS, f"#maxv({maxv}).", ""]
    for i, (ar, at, lab) in enumerate(pos_labs):     # human labelling: violated must be excluded
        w = f"@{pos_w}" if pos_w else ""
        lines.append(f"#pos(p{i}{w}, {{}}, {{violated}}, {{{_lab_ctx(ar, at, lab)}}}).")
    for j, (ar, at, lab) in enumerate(neg_labs):     # shell labelling: violated must be included
        w = f"@{neg_w}" if neg_w else ""
        lines.append(f"#pos(n{j}{w}, {{violated}}, {{}}, {{{_lab_ctx(ar, at, lab)}}}).")
    return "\n".join(lines) + "\n"


def run_fastlas(task, mode="opl", timeout=120, threads=8):
    with tempfile.NamedTemporaryFile("w", suffix=".las", delete=False) as f:
        f.write(task); path = f.name
    try:
        p = subprocess.run(["FastLAS", f"--{mode}", "--timeout", str(timeout), "--threads", str(threads), path],
                           capture_output=True, text=True, timeout=timeout + 90)
        out = p.stdout
    except subprocess.TimeoutExpired:
        out = "__WALL_TIMEOUT__"
    finally:
        os.unlink(path)
    if "__WALL_TIMEOUT__" in out or "UNSATISFIABLE" in out:
        return None if "UNSAT" not in out else []
    rules = [ln.strip() for ln in out.splitlines()
             if ln.strip().endswith(".") and (":-" in ln or ln.strip().startswith("violated"))
             and not ln.strip().startswith("%")]
    return rules


# ---- prediction: generate-and-constrain with the learned `violated` rules ----
_GEN = """0 { in(X) } 1 :- arg(X).
0 { out(X) } 1 :- arg(X).
:- in(X), out(X)."""


def predict(rules, args, attacks, reading, enrich=False):
    if not rules:  # empty/UNSAT/degenerate theory: it learned NO structure -> honest prediction is
        return {a: "undec" for a in args}  # all-undec, NOT the all-in credulous artifact of 3^n models
    prog = "\n".join([_GEN, _feat_bg(enrich)] + list(rules) + [":- violated."])
    facts = "".join(f"arg({a}). " for a in args) + "".join(f"att({s},{t}). " for s, t in attacks)
    ctl = clingo.Control(["0", "--warn=none"])
    ctl.add("base", [], prog + "\n" + facts + "\n#show in/1.\n#show out/1.\n")
    ctl.ground([("base", [])])
    labs = []
    def on_model(m):
        ins = {str(x.arguments[0]) for x in m.symbols(shown=True) if x.name == "in"}
        ous = {str(x.arguments[0]) for x in m.symbols(shown=True) if x.name == "out"}
        labs.append({a: ("in" if a in ins else "out" if a in ous else "undec") for a in args})
    ctl.solve(on_model=on_model)
    return D.project(labs, args, reading)


def load_own(v, phase):
    """Own-graph loader that KEEPS all-undecided participants (the 2022 paper counts them). Same
    as discover_semantics.load_version but with the `if lab:` guard instead of `if c:` (which
    dropped all-undec humans -> biased the comparison toward committal semantics). Graph and labels
    are from the SAME phase (self-consistent; = 2022 IndAF only at phase=final)."""
    import glob, os
    D.PHASE = {"first": "att_first__lab_first", "final": "att_final__lab_final",
               "group": "att_group__lab_group"}[phase]
    D.GRAPH = "own"
    recs = []
    for f in sorted(glob.glob(os.path.join(D.EXTRACT, f"version{v}", D.PHASE, "p*.lp"))):
        args, attacks, labels = D.parse_lp(f)
        lab = {a: s for a, s in labels.items() if s in D.CLASSES}
        if lab:  # keep participants with ANY label, including all-undecided
            recs.append({"pid": os.path.basename(f)[:-3], "args": args, "attacks": attacks,
                         "commit": D.committed(labels), "labels": lab})
    return recs


def cell_folds(recs, k, seed=20260703):
    """Leak-free CV: partition by DISTINCT (graph, full-labelling) cell so no held-out cell can be
    in train (participant-folds leaked 61% of held-out responses). Mirrors apples_to_apples.cell_folds."""
    from collections import defaultdict
    cells = defaultdict(list)
    for r in recs:
        cells[(tuple(sorted(r["attacks"])), tuple(sorted(r["labels"].items())))].append(r)
    keys = sorted(cells)
    kk = min(k, len(keys))
    if kk < 2:
        return None  # degenerate: <2 distinct cells -> no honest split
    folds = [[] for _ in range(kk)]
    for i, key in enumerate(keys):
        folds[(i * 7 + seed) % kk].extend(cells[key])
    return [f for f in folds if f]


def cells_from(recs):
    return [(r["args"], r["attacks"], r["commit"]) for r in recs]


def shell_of(recs):
    pos_keys = {(tuple(sorted(r["attacks"])), tuple(sorted(r["commit"].items()))) for r in recs}
    seen, negs = set(), []
    for r in recs:
        for neg in D.hard_shell(r["commit"]):
            key = (tuple(sorted(r["attacks"])), tuple(sorted(neg.items())))
            if key in pos_keys or key in seen:
                continue
            seen.add(key)
            negs.append((r["args"], r["attacks"], neg))
    return negs


def cv(v, phase="first", k=5, enrich=False, mode="opl", maxv=1, timeout=120, max_neg=None,
       lean=False, balance_neg=True):
    """Leak-free, all-undec-kept CV. balance_neg down-weights the shell so total neg penalty mass
    approx equals pos mass (removes the up-to-6.4:1 imbalance). Returns per-reading confusions so
    the caller can pool across conditions and compute committed-only accuracy."""
    recs = load_own(v, phase)
    folds = cell_folds(recs, k)
    preds = ("learned",) + D.TEXTBOOK
    conf = {(p, rd): Counter() for p in preds for rd in D.READINGS}
    n_to = n_empty = n_scored_folds = 0
    if folds is None:  # <2 distinct cells: cannot split without leakage -> report degenerate
        return {"v": v, "phase": phase, "n_part": len(recs), "degenerate": True,
                "conf": conf, "fastlas_timeouts": 0, "empty_folds": 0}
    for fi in range(len(folds)):
        test = folds[fi]; train = [r for j, f in enumerate(folds) if j != fi for r in f]
        if not (train and test):
            continue
        n_scored_folds += 1
        negs = shell_of(train)
        if max_neg and len(negs) > max_neg:
            import random
            negs = [negs[i] for i in sorted(random.Random(20260703).sample(range(len(negs)), max_neg))]
        neg_w = max(1, round(100 * len(train) / len(negs))) if (balance_neg and negs) else 100
        task = build_learn_task(cells_from(train), negs, enrich=enrich, maxv=maxv, lean=lean, neg_w=neg_w)
        rules = run_fastlas(task, mode=mode, timeout=timeout)
        if rules is None:          # wall timeout
            n_to += 1; rules = []
        elif rules == []:          # SAT-empty / UNSAT: learned no structure (now counted, not silent)
            n_empty += 1
        for r in test:
            for kind in preds:
                if kind == "learned":
                    for rd in D.READINGS:
                        conf[(kind, rd)] += D.score(predict(rules, r["args"], r["attacks"], rd, enrich), r["labels"])
                else:
                    labs = D.textbook_labellings(kind, r["args"], r["attacks"])
                    for rd in D.READINGS:
                        conf[(kind, rd)] += D.score(D.project(labs, r["args"], rd), r["labels"])
    res = {"v": v, "phase": phase, "n_part": len(recs), "n_folds": n_scored_folds,
           "fastlas_timeouts": n_to, "empty_folds": n_empty, "mode": mode, "enrich": enrich,
           "conf": conf, "degenerate": False}
    for kind in preds:
        res[kind] = {rd: D.metrics_from_conf(conf[(kind, rd)]) for rd in D.READINGS}
    return res


def pooled_cv(phase="final", k=5, enrich=True, mode="nopl", maxv=2, timeout=300,
              max_neg=150, lean=False, balance_neg=True, versions=("A", "B", "C", "D", "E", "F", "G")):
    """FULL CLEVER task: pool every participant's own-graph labelling across all conditions into ONE
    example set and learn ONE cross-condition verifier theory per fold (NOPL, enriched, best params).
    Leak-free POOLED cell-folds (no held-out (graph,labelling) cell in train). This is the FastLAS
    analog of the ILASP pooled result. Returns pooled per-reading confusions + the fold theories."""
    recs = []
    for v in versions:
        for r in load_own(v, phase):
            r["version"] = v
            recs.append(r)
    folds = cell_folds(recs, k)  # keys on (attacks, labels) -> cells are per (graph,labelling), pooled
    preds = ("learned",) + D.TEXTBOOK
    conf = {(p, rd): Counter() for p in preds for rd in D.READINGS}
    n_to = n_empty = 0
    theories = []
    for fi in range(len(folds)):
        test = folds[fi]; train = [r for j, f in enumerate(folds) if j != fi for r in f]
        if not (train and test):
            continue
        negs = shell_of(train)
        if max_neg and len(negs) > max_neg:
            import random
            negs = [negs[i] for i in sorted(random.Random(20260703).sample(range(len(negs)), max_neg))]
        neg_w = max(1, round(100 * len(train) / len(negs))) if (balance_neg and negs) else 100
        task = build_learn_task(cells_from(train), negs, enrich=enrich, maxv=maxv, lean=lean, neg_w=neg_w)
        rules = run_fastlas(task, mode=mode, timeout=timeout)
        if rules is None:
            n_to += 1; rules = []
        elif rules == []:
            n_empty += 1
        theories.append(rules)
        for r in test:
            for kind in preds:
                if kind == "learned":
                    for rd in D.READINGS:
                        conf[(kind, rd)] += D.score(predict(rules, r["args"], r["attacks"], rd, enrich), r["labels"])
                else:
                    labs = D.textbook_labellings(kind, r["args"], r["attacks"])
                    for rd in D.READINGS:
                        conf[(kind, rd)] += D.score(D.project(labs, r["args"], rd), r["labels"])
    return {"phase": phase, "n_examples": len(recs), "n_folds": len(folds), "mode": mode,
            "enrich": enrich, "maxv": maxv, "fastlas_timeouts": n_to, "empty_folds": n_empty,
            "conf": conf, "theories": theories, "preds": preds}


def committed_only_acc(conf):
    """acc3 restricted to human-committed (in/out) responses -> strips free undec->undec matches."""
    tot = sum(c for (h, p), c in conf.items() if h in ("in", "out"))
    cor = sum(c for (h, p), c in conf.items() if h in ("in", "out") and h == p)
    return (cor / tot) if tot else float("nan"), tot


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--versions", default="D")
    ap.add_argument("--phase", default="first", choices=("first", "final", "group"))
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--mode", default="opl", choices=("opl", "nopl"))
    ap.add_argument("--enrich", action="store_true")
    ap.add_argument("--maxv", type=int, default=1)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--max-neg", type=int, default=None)
    ap.add_argument("--lean", action="store_true")
    a = ap.parse_args()
    preds = ("learned",) + D.TEXTBOOK
    pooled = {(p, rd): Counter() for p in preds for rd in D.READINGS}   # response-weighted pool
    print(f"FastLAS discovery (LEAK-FREE cell-folds, all-undec kept) · phase={a.phase} mode={a.mode} "
          f"enrich={a.enrich} maxv={a.maxv} lean={a.lean}")
    for v in a.versions.split(","):
        t0 = time.time()
        r = cv(v, phase=a.phase, k=a.folds, enrich=a.enrich, mode=a.mode, maxv=a.maxv,
               timeout=a.timeout, max_neg=a.max_neg, lean=a.lean)
        if r.get("degenerate"):
            print(f"\n=== {v} (n={r['n_part']}) DEGENERATE (<2 distinct cells) — skipped ===")
            continue
        for key, c in r["conf"].items():
            pooled[key] += c
        lo, _ = committed_only_acc(r["conf"][("learned", "credulous")])
        print(f"\n=== {v} (n={r['n_part']}, folds={r['n_folds']}, {r['fastlas_timeouts']}to/{r['empty_folds']}empty, "
              f"{time.time()-t0:.0f}s) ===")
        print(f"  {'pred':<10}{'credAcc3':<10}{'cred_committedOnly':<20}{'skeptAcc3':<11}")
        for kind in preds:
            co, _ = committed_only_acc(r["conf"][(kind, "credulous")])
            print(f"  {kind:<10}{r[kind]['credulous']['acc3']:<10.3f}{co:<20.3f}{r[kind]['skeptical']['acc3']:<11.3f}")
    # ---- pooled, response-weighted (apples-to-apples with the 2022 %correct) ----
    print(f"\n===== POOLED (response-weighted, n={sum(pooled[('learned','credulous')].values())}) =====")
    print(f"  {'pred':<10}{'credAcc3':<10}{'cred_committedOnly':<20}{'skeptAcc3':<11}{'skept_committedOnly':<12}")
    for kind in preds:
        cc, _ = committed_only_acc(pooled[(kind, "credulous")])
        sc, _ = committed_only_acc(pooled[(kind, "skeptical")])
        ca = D.metrics_from_conf(pooled[(kind, "credulous")])["acc3"]
        sa = D.metrics_from_conf(pooled[(kind, "skeptical")])["acc3"]
        print(f"  {kind:<10}{ca:<10.3f}{cc:<20.3f}{sa:<11.3f}{sc:<12.3f}")
    print("  (chance: acc3 33.3% · committed-only 2-class 50%)")
