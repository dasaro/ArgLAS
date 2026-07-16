#!/usr/bin/env python3
"""aux10 -- LEAVE-ONE-CONDITION-OUT validation of the auxiliary-FEATURE-FAMILY SELECTION.

The aux9 combined vocabulary (reinstatement triple + top-2 degree-salience) was selected on the
full corpus -- the same corpus the +7.7 committed-only gain (Table tab:aux) is reported on.
This script re-runs the ENTIRE selection pipeline with each condition A-G held out:

  For each held-out condition v:
    (a) restrict the corpus to the other six conditions, with the per_condition_experiment.py
        TRANSFER identity guard (any training rec whose (graph,labelling) cell equals a test
        cell of v is removed -- D/E/F share graphs, naive LOCO leaks);
    (b) run the four family CVs (aux1 scc-cycle, aux2 degree-salience, aux3 reinstatement,
        aux4 reach-position) + the primitive baseline CV on that restricted set: leak-free
        5-fold cell CV at the canonical seed 20260703, reusing each family module's OWN
        build_task/predict (the audited in-corpus code paths) and the shared
        dedup/negatives/scoring from unified_compare / fl_discover;
    (c) apply the pre-existing selection rule: a family is selected iff its CV committed-only
        beats the primitive baseline's (strict >) AND its modeh-visible predicates actually
        appear in the learned theories.  The combined vocabulary is built from the selected
        families (families ordered by CV committed-only, predicates within a family ordered by
        learned-theory frequency), capped at 5 modeh-visible predicates as aux9 already does;
    (d) learn ONE combined-vocabulary theory on the six training conditions and score
        committed-only accuracy on the held-out condition v, paired against a
        primitive-vocabulary theory learned on the identical training set.

  Deviations from aux9's manual choices, made deterministic here:
    - within-family predicate ranking is PURE learned-theory frequency (aux9 additionally
      demoted `unattacked` on a subsumption argument despite its higher frequency);
    - family ranking is CV committed-only (desc), ties by fixed family order.

Everything flushes incrementally to results/aux10_loco.json (aux9_robustness style, resumable).
Run:  python3 aux10_loco_selection.py            # full run (two parallel stages)
      python3 aux10_loco_selection.py --report   # print summary from the results file
"""
import argparse, json, multiprocessing, os, re, sys, time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
sys.path.insert(0, HERE)
import discover_semantics as D
import fl_discover as G
import unified_compare as U
import aux1_scc_cycle as A1
import aux2_degree_salience as A2
import aux3_reinstatement as A3
import aux4_reachpos as A4
from apples_to_apples import mcnemar
import clingo

VERSIONS = ("A", "B", "C", "D", "E", "F", "G")
SEED = 20260703            # canonical fold seed (selection); U.SEED already == this
PHASE = "final"
CV_TIMEOUT = 150           # per-learn FastLAS cap in the family CVs (aux9_robustness value)
TR_TIMEOUT = 300           # per-learn cap for the two transfer theories (per_condition value)
THREADS = 4                # FastLAS threads per job (we run WORKERS jobs concurrently)
WORKERS = 5
CAP = 5                    # max modeh-visible aux predicates (aux9's OPL tractability cap)
OUT = os.path.join(HERE, "results", "aux10_loco.json")

FAMILIES = ("scc_cycle", "degree_salience", "reinstatement", "reachpos")
# modeh-visible predicates per family (fixed tie-break order = the family script's order)
FAM_PREDS = {
    "scc_cycle": ["mutual", "in_long_cycle"],
    "degree_salience": ["unattacked", "has_unattacked_attacker", "has_many_attackers"],
    "reinstatement": ["reinstated", "floating", "undefended_in"],
    "reachpos": ["reaches_cycle", "source", "sink", "attacked_by_source"],
}
# aux background blocks for the COMBINED builder; base = G._feat_bg(enrich=True) already
# defines attacked/attacker_not_out/defended/attacked_by_in/undec + reach/in_cycle, so the
# reachpos block drops its duplicate reach/in_cycle lines.
FAM_BG = {
    "scc_cycle": A1._AUX_MUTUAL + "\n" + A1._AUX_LONG,
    "degree_salience": A2._AUX_BG,
    "reinstatement": A3.AUX3_BG,
    "reachpos": "\n".join(l for l in A4._AUX_BG.splitlines()
                          if not l.startswith(("reach(", "in_cycle("))),
}


def cell_key(r):  # == per_condition_experiment.cell_key
    return (tuple(sorted(r["attacks"])), tuple(sorted(r["labels"].items())))


def guarded_train(recs, v):
    """Six-condition training corpus for held-out v, with the TRANSFER identity guard
    (per_condition_experiment.py lines 125-136): drop any training rec whose cell equals a
    test cell of v (D/E/F share graphs)."""
    test_cells = {cell_key(r) for r in recs if r["version"] == v}
    train = [r for r in recs if r["version"] != v and cell_key(r) not in test_cells]
    n_guarded = sum(1 for r in recs if r["version"] != v and cell_key(r) in test_cells)
    return train, n_guarded


# ---------------- family adapters (the audited in-corpus code paths) ----------------
def fam_task(fam, cells, negs, neg_w):
    if fam == "base":
        return U.fastlas_task(cells, negs, neg_w, maxv=1, enrich=True)
    if fam == "scc_cycle":
        return A1.build_task(cells, negs, neg_w, "both", maxv=1)
    if fam == "degree_salience":
        return A2.build_task(cells, negs, neg_w, enrich=True, maxv=1, with_aux=True)
    if fam == "reinstatement":
        return A3.build_task(cells, negs, neg_w, maxv=1, enrich=True, with_aux=True)
    if fam == "reachpos":
        return A4.build_task(cells, negs, neg_w, maxv=1, enrich=True, aux=True)
    raise ValueError(fam)


def fam_predict(fam, rules, args, attacks, reading):
    if fam == "base":
        return G.predict(rules, args, attacks, reading, enrich=True)
    if fam == "scc_cycle":
        return A1.predict(rules, args, attacks, reading, "both")
    if fam == "degree_salience":
        return A2.predict(rules, args, attacks, reading, enrich=True, with_aux=True)
    if fam == "reinstatement":
        return A3.predict(rules, args, attacks, reading, enrich=True, with_aux=True)
    if fam == "reachpos":
        return A4.predict(rules, args, attacks, reading, enrich=True, aux=True)
    raise ValueError(fam)


# ---------------- combined-vocabulary builder (aux9 generalized) ----------------
def combined_bg(fams):
    blocks = [G._feat_bg(True)] + [FAM_BG[f] for f in FAMILIES if f in fams]
    seen, lines = set(), []
    for ln in "\n".join(blocks).splitlines():
        if ln.strip() and ln in seen:
            continue
        seen.add(ln)
        lines.append(ln)
    return "\n".join(lines)


def combined_task(cells, negs, neg_w, fams, preds, maxv=1):
    mb = list(G._MODEB) + list(G._MODEB_ENR)
    for p in preds:
        mb += [f"#modeb({p}(var(arg))).", f"#modeb(not {p}(var(arg)))."]
    lines = [combined_bg(fams), "", "#modeh(violated)."] + mb
    lines += ["", G._BIAS, f"#maxv({maxv}).", ""]
    for i, c in enumerate(cells):
        lines.append(f"#pos(p{i}@{c['weight']}, {{}}, {{violated}}, "
                     f"{{{G._lab_ctx(c['args'], c['attacks'], c['commit'])}}}).")
    for j, (ar, at, ng) in enumerate(negs):
        lines.append(f"#pos(n{j}@{neg_w}, {{violated}}, {{}}, {{{G._lab_ctx(ar, at, ng)}}}).")
    return "\n".join(lines) + "\n"


def combined_predict(rules, args, attacks, reading, fams):
    if not rules:
        return {a: "undec" for a in args}
    prog = "\n".join([G._GEN, combined_bg(fams)] + list(rules) + [":- violated."])
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


def pred_counts(preds, theories):
    """learned-theory frequency: number of rules (across CV theories) whose body uses the pred."""
    cnt = Counter()
    for th in theories:
        for rule in th:
            for p in preds:
                if re.search(rf"\b{p}\(", rule):
                    cnt[p] += 1
    return {p: cnt.get(p, 0) for p in preds}


def select(cvres):
    """The pre-existing selection rule, made deterministic. cvres: fam -> cv summary dict.
    Selected iff committed_only > base committed_only AND aux predicates appear in theories.
    Combined pred list: families by CV committed-only desc (tie: FAMILIES order), preds within
    a family by learned-theory frequency desc (tie: FAM_PREDS order), capped at CAP."""
    base_co = cvres["base"]["committed_only"]
    selected = [f for f in FAMILIES
                if cvres[f]["committed_only"] > base_co and cvres[f]["aux_used_any"]]
    order = sorted(selected, key=lambda f: (-cvres[f]["committed_only"], FAMILIES.index(f)))
    preds = []
    for f in order:
        pc = cvres[f]["pred_counts"]
        fam_order = sorted(FAM_PREDS[f], key=lambda p: (-pc[p], FAM_PREDS[f].index(p)))
        for p in fam_order:
            if len(preds) < CAP and p not in preds:
                preds.append(p)
    return {"base_co": base_co, "selected": order, "preds": preds}


# ---------------- stage 1: one family CV on one guarded six-condition corpus ----------------
def cv_job(job):
    v, fam = job
    recs = U.load_pooled(PHASE)
    train_all, n_guarded = guarded_train(recs, v)
    folds = G.cell_folds(train_all, 5, seed=SEED)
    conf = {rd: Counter() for rd in D.READINGS}
    theories, n_to, t0 = [], 0, time.time()
    for fi in range(len(folds)):
        test = folds[fi]
        train = [r for j, f in enumerate(folds) if j != fi for r in f]
        if not (train and test):
            continue
        cells = U.dedup_weighted(train)
        negs, neg_w = U.shared_negatives(train, 150)
        task = fam_task(fam, cells, negs, neg_w)
        rules = G.run_fastlas(task, mode="opl", timeout=CV_TIMEOUT, threads=THREADS)
        if rules is None:
            n_to += 1
            rules = []
        theories.append(rules)
        for r in test:
            for rd in D.READINGS:
                conf[rd] += D.score(fam_predict(fam, rules, r["args"], r["attacks"], rd),
                                    r["labels"])
    co, ncom = G.committed_only_acc(conf["credulous"])
    preds = FAM_PREDS.get(fam, [])
    pc = pred_counts(preds, theories)
    return {"heldout": v, "family": fam, "n_train": len(train_all), "n_guarded": n_guarded,
            "committed_only": round(co, 4), "n_committed": ncom,
            "skeptical_acc3": round(D.metrics_from_conf(conf["skeptical"])["acc3"], 4),
            "n_timeouts": n_to, "aux_used_any": any(n > 0 for n in pc.values()),
            "pred_counts": pc, "theories": theories,
            "secs": round(time.time() - t0, 1)}


# ---------------- stage 2: paired transfer learns + held-out scoring ----------------
def transfer_job(args_):
    v, fams, preds = args_
    recs = U.load_pooled(PHASE)
    train, n_guarded = guarded_train(recs, v)
    test = [r for r in recs if r["version"] == v]
    cells = U.dedup_weighted(train)
    negs, neg_w = U.shared_negatives(train, 150)
    t0 = time.time()
    arms = {}
    # primitive arm
    b_rules = G.run_fastlas(U.fastlas_task(cells, negs, neg_w, maxv=1, enrich=True),
                            mode="opl", timeout=TR_TIMEOUT, threads=THREADS)
    b_to = b_rules is None
    b_rules = b_rules or []
    # combined arm (== primitive if nothing was selected)
    if preds:
        c_rules = G.run_fastlas(combined_task(cells, negs, neg_w, fams, preds),
                                mode="opl", timeout=TR_TIMEOUT, threads=THREADS)
        c_to = c_rules is None
        c_rules = c_rules or []
    else:
        c_rules, c_to = list(b_rules), b_to

    def pred_of(arm, r, rd):
        if arm == "combined" and preds:
            return combined_predict(c_rules, r["args"], r["attacks"], rd, fams)
        rules = c_rules if arm == "combined" else b_rules
        return G.predict(rules, r["args"], r["attacks"], rd, enrich=True)

    conf = {(arm, rd): Counter() for arm in ("base", "combined") for rd in D.READINGS}
    paired = {"base": [], "combined": []}   # per committed response, credulous correctness
    pkeys = []
    for r in test:
        pc = {}
        for arm in ("base", "combined"):
            for rd in D.READINGS:
                p = pred_of(arm, r, rd)
                conf[(arm, rd)] += D.score(p, r["labels"])
                if rd == "credulous":
                    pc[arm] = p
        for a_, h in r["labels"].items():
            if h in ("in", "out"):
                pkeys.append((cell_key(r), a_))
                for arm in ("base", "combined"):
                    paired[arm].append(1 if pc[arm].get(a_, "undec") == h else 0)
    for arm in ("base", "combined"):
        co, ncom = G.committed_only_acc(conf[(arm, "credulous")])
        arms[arm] = {"committed_only": round(co, 4), "n_committed": ncom,
                     "rules": (c_rules if arm == "combined" else b_rules),
                     "timed_out": (c_to if arm == "combined" else b_to)}
    return {"heldout": v, "selected": fams, "preds": preds, "n_train": len(train),
            "n_guarded": n_guarded, "arms": arms,
            "paired": paired, "pair_keys": [list(map(str, k)) for k in pkeys],
            "delta": round(arms["combined"]["committed_only"] - arms["base"]["committed_only"], 4),
            "secs": round(time.time() - t0, 1)}


# ---------------- state / report ----------------
def _load():
    try:
        return json.load(open(OUT))
    except Exception:
        return {"cv": {}, "transfer": {}}


def _flush(state):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    json.dump(state, open(tmp, "w"), indent=1)
    os.replace(tmp, OUT)


def report(state):
    print("\n========== aux10 LOCO selection validation ==========")
    tally = Counter()
    print(f"  {'held':<5}{'base':>7}" + "".join(f"{f[:9]:>11}" for f in FAMILIES)
          + "   selected -> preds")
    for v in VERSIONS:
        row = {f: state["cv"].get(f"{v}_{f}") for f in ("base",) + FAMILIES}
        if any(r is None for r in row.values()):
            continue
        sel = select({f: row[f] for f in row})
        for f in sel["selected"]:
            tally[f] += 1
        marks = {f: ("*" if f in sel["selected"] else "") for f in FAMILIES}
        print(f"  {v:<5}{row['base']['committed_only']:>7.3f}"
              + "".join(f"{row[f]['committed_only']:>10.3f}{marks[f]:<1}" for f in FAMILIES)
              + f"  {'+'.join(sel['selected']) or '(none)'} -> {','.join(sel['preds'])}")
    print("  selection tally /7: " + ", ".join(f"{f}:{tally.get(f,0)}" for f in FAMILIES))
    rows = [state["transfer"].get(v) for v in VERSIONS]
    rows = [r for r in rows if r]
    if not rows:
        return
    print(f"\n  {'held':<5}{'n_com':>6}{'base':>8}{'combined':>10}{'delta':>8}   preds")
    for r in rows:
        print(f"  {r['heldout']:<5}{r['arms']['base']['n_committed']:>6}"
              f"{r['arms']['base']['committed_only']:>8.3f}"
              f"{r['arms']['combined']['committed_only']:>10.3f}{r['delta']:>+8.3f}   "
              + ",".join(r["preds"]))
    deltas = [r["delta"] for r in rows]
    print(f"  mean per-condition delta: {sum(deltas)/len(deltas):+.4f} "
          f"(range {min(deltas):+.3f} .. {max(deltas):+.3f})")
    # pooled committed-only + McNemar (response-level and cell-level deduped)
    pooled = {"base": [], "combined": []}
    keys = []
    for r in rows:
        pooled["base"] += r["paired"]["base"]
        pooled["combined"] += r["paired"]["combined"]
        keys += [tuple(k) for k in r["pair_keys"]]
    nb = sum(pooled["base"]); nc = sum(pooled["combined"]); n = len(pooled["base"])
    print(f"  pooled committed-only: base {nb/n:.4f} combined {nc/n:.4f} "
          f"(delta {nc/n-nb/n:+.4f}, n={n})")
    def mcn(a1, a2):
        b = sum(1 for x, y in zip(a1, a2) if y and not x)   # combined-only correct
        c_ = sum(1 for x, y in zip(a1, a2) if x and not y)  # base-only correct
        return b, c_, (1.0 if b == c_ == 0 else mcnemar(b, c_))
    b, c_, p = mcn(pooled["base"], pooled["combined"])
    print(f"  pooled McNemar (response-level): combined-only {b} / base-only {c_} p={p:.4f}")
    first = {}
    for i, k in enumerate(keys):
        first.setdefault(k, i)
    ix = sorted(first.values())
    b, c_, p = mcn([pooled["base"][i] for i in ix], [pooled["combined"][i] for i in ix])
    print(f"  pooled McNemar (cell-level dedup): combined-only {b} / base-only {c_} p={p:.4f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="summarize existing results only")
    ap.add_argument("--workers", type=int, default=WORKERS)
    a = ap.parse_args()
    state = _load()
    if a.report:
        report(state)
        return
    ctx = multiprocessing.get_context("spawn")
    # ---- stage 1: 7 x 5 family/baseline CVs on the guarded six-condition corpora ----
    jobs = [(v, fam) for v in VERSIONS for fam in ("base",) + FAMILIES
            if f"{v}_{fam}" not in state["cv"]]
    print(f"stage 1: {len(jobs)} CV jobs (cached {35 - len(jobs)})", flush=True)
    if jobs:
        with ProcessPoolExecutor(max_workers=a.workers, mp_context=ctx) as ex:
            futs = {ex.submit(cv_job, j): j for j in jobs}
            for fu in as_completed(futs):
                r = fu.result()
                state["cv"][f"{r['heldout']}_{r['family']}"] = r
                _flush(state)
                print(f"  [cv -{r['heldout']} {r['family']}] co={r['committed_only']:.4f} "
                      f"aux_used={r['aux_used_any']} TO={r['n_timeouts']} ({r['secs']}s)",
                      flush=True)
    # ---- stage 2: per held-out condition, selection -> paired transfer learns ----
    jobs2 = []
    for v in VERSIONS:
        if v in state["transfer"]:
            continue
        cvres = {f: state["cv"][f"{v}_{f}"] for f in ("base",) + FAMILIES}
        sel = select(cvres)
        jobs2.append((v, sel["selected"], sel["preds"]))
    print(f"stage 2: {len(jobs2)} transfer jobs (cached {7 - len(jobs2)})", flush=True)
    if jobs2:
        with ProcessPoolExecutor(max_workers=a.workers, mp_context=ctx) as ex:
            futs = {ex.submit(transfer_job, j): j for j in jobs2}
            for fu in as_completed(futs):
                r = fu.result()
                state["transfer"][r["heldout"]] = r
                _flush(state)
                print(f"  [transfer -{r['heldout']}] base={r['arms']['base']['committed_only']:.4f} "
                      f"combined={r['arms']['combined']['committed_only']:.4f} "
                      f"delta={r['delta']:+.4f} preds={','.join(r['preds']) or '(none)'} "
                      f"({r['secs']}s)", flush=True)
    report(state)
    print("\nDONE", flush=True)


if __name__ == "__main__":
    main()
