#!/usr/bin/env python3
"""ONE-SEMANTICS-PER-CONDITION experiment (contextual-reasoning test), rock-solid edition.

DESIGN (pre-registered):
  Q: does each condition A-G have its own learnable semantics beyond one global theory?
  ARMS (identical held-out responses, identical scoring):
    WITHIN   - per-condition theory, leave-one-cell-out (LOCO) CV over the condition's
               distinct (graph, labelling) cells. Deterministic (no fold-seed variance).
    GLOBAL   - one pooled A-G theory from the leak-free 5-fold cell CV (U.shared_folds);
               a held-out cell is scored by the theory of the fold that holds it out.
    TRANSFER - leave-one-condition-out theory (train on the other six), with a cross-
               condition IDENTITY GUARD: any training rec whose cell equals a test cell of
               the held-out condition is removed (D/E/F share graphs!).
    + textbook semantics as anchors (cf2 pre-registered comparator).
  HYPOTHESES: H1 contextual: WITHIN > GLOBAL.  H2 transfer-gap: WITHIN > TRANSFER.
  METRICS: committed-only credulous (primary; chance 33.3% for 3-way guesser, 50% coin-flip),
           acc3 skeptical/credulous; paired exact-binomial McNemar per condition (+ pooled),
           Holm correction across the 7 per-condition H1 tests; cell-level McNemar robustness.
  RIGOUR: IndAF-final pool, all-undec kept; soft mass-balanced positives + negatives
          (Hamming-1 shell + drop-all totality negs) built from each arm's OWN train set only;
          every response tested exactly once per arm; synthetic grounded GATE through the
          exact LOCO machinery; per-condition CONSENSUS rules (>=50% of LOCO folds).
  VOCAB: aux9 combined (primary) + base (ablation).

Usage:
  python3 per_condition_experiment.py --gate            # synthetic gate only
  python3 per_condition_experiment.py --smoke           # condition D only, aux vocab
  python3 per_condition_experiment.py                   # full run (both vocabs)
Results stream to results/per_condition_experiment.json (incremental flush, resumable cache).
"""
import argparse, json, os, re, sys, time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts")); sys.path.insert(0, HERE)
import unified_compare as U
import aux9_combined as A9
import fl_discover as G
import discover_semantics as D
from apples_to_apples import mcnemar

VERSIONS = ("A", "B", "C", "D", "E", "F", "G")
GROUP = {"A": "FLOAT", "B": "FLOAT", "C": "FLOAT", "D": "SIMPLE", "E": "SIMPLE", "F": "SIMPLE", "G": "CYCLE"}
OUT = os.path.join(HERE, "results", "per_condition_experiment.json")
ARMS = ("within", "global", "transfer")
TB = D.TEXTBOOK
TIMEOUTS = {"within": 150, "global": 300, "transfer": 300}


def cell_key(r):
    return (tuple(sorted(r["attacks"])), tuple(sorted(r["labels"].items())))


def learn(train, with_aux, timeout):
    """Audited construction: deduped weighted positives + soft mass-balanced negatives
    (Hamming-1 + drop-all) from THIS train set only."""
    cells = U.dedup_weighted(train)
    negs, neg_w = U.shared_negatives(train, 150)
    task = A9.build_task(cells, negs, neg_w, with_aux=with_aux)
    t0 = time.time()
    rules = G.run_fastlas(task, mode="opl", timeout=timeout)
    return (rules or []), round(time.time() - t0, 1), rules is None


def canon(rule):
    r = rule.strip().rstrip(".")
    if ":-" not in r:
        return None
    _, body = r.split(":-", 1)
    lits = [x.strip() for x in re.split(r",(?![^()]*\))", body)]
    lits = [l for l in lits if l and not l.startswith("arg(")]
    return tuple(sorted(re.sub(r"\bV\d+\b", "V", l) for l in lits))


def _flush(state):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"; json.dump(state, open(tmp, "w"), indent=1); os.replace(tmp, OUT)


def _load():
    try:
        return json.load(open(OUT))
    except Exception:
        return {}


def run_vocab(state, phase, with_aux, versions, gate_labels=None):
    """One full 3-arm experiment for one vocabulary. gate_labels='grounded' swaps every human
    labelling for the clean textbook-grounded labelling (synthetic gate through the same code)."""
    vtag = ("aux" if with_aux else "base") + ("_GATE" if gate_labels else "")
    key = f"{phase}_{vtag}"
    st = state.setdefault(key, {"phase": phase, "with_aux": with_aux, "gate": bool(gate_labels),
                                "conditions": {}, "learn_log": []})
    recs = U.load_pooled(phase)
    if gate_labels:  # replace labels with the clean generating semantics
        clean = []
        for r in recs:
            labs = D.textbook_labellings(gate_labels, r["args"], r["attacks"])
            lab = D.project(labs, r["args"], "skeptical")
            commit = {a: s for a, s in lab.items() if s in ("in", "out")}
            clean.append({**r, "labels": dict(lab), "commit": commit})
        recs = clean
    byv = defaultdict(list)
    for r in recs:
        byv[r["version"]].append(r)

    # ---- GLOBAL arm: pooled 5-fold cell CV theories (cache per vocab) ----
    folds = U.shared_folds(recs, 5)
    fold_of = {}
    for fi, f in enumerate(folds):
        for r in f:
            fold_of[cell_key(r)] = fi
    if "global_theories" not in st:
        st["global_theories"] = {}
    for fi in range(len(folds)):
        if str(fi) in st["global_theories"]:
            continue
        train = [r for j, f in enumerate(folds) if j != fi for r in f]
        rules, secs, to = learn(train, with_aux, TIMEOUTS["global"])
        st["global_theories"][str(fi)] = {"rules": rules, "secs": secs, "timed_out": to}
        print(f"[{key}] GLOBAL fold {fi}: {len(rules)}r {secs}s{' !TO' if to else ''}", flush=True)
        _flush(state)

    # ---- TRANSFER arm: leave-one-condition-out theories with identity guard ----
    if "transfer_theories" not in st:
        st["transfer_theories"] = {}
    for v in versions:
        if v in st["transfer_theories"]:
            continue
        test_cells = {cell_key(r) for r in byv[v]}
        train = [r for r in recs if r["version"] != v and cell_key(r) not in test_cells]
        rules, secs, to = learn(train, with_aux, TIMEOUTS["transfer"])
        st["transfer_theories"][v] = {"rules": rules, "secs": secs, "timed_out": to,
                                      "n_guarded": sum(1 for r in recs if r["version"] != v and cell_key(r) in test_cells)}
        print(f"[{key}] TRANSFER -{v}: {len(rules)}r {secs}s guard={st['transfer_theories'][v]['n_guarded']}"
              f"{' !TO' if to else ''}", flush=True)
        _flush(state)

    # ---- WITHIN arm (LOCO) + scoring of all arms on the SAME held-out responses ----
    for v in versions:
        # cache hit only if scored under the CURRENT schema (paired_cell added by the P3 audit)
        if v in st["conditions"] and st["conditions"][v].get("done") and "paired_cell" in st["conditions"][v]:
            continue
        if v in st["conditions"]:
            st["conditions"][v].pop("done", None)  # re-score (LOCO learns stay cached)
        vrecs = byv[v]
        cells = sorted({cell_key(r) for r in vrecs})
        cst = st["conditions"].setdefault(v, {"type": GROUP[v], "n_recs": len(vrecs),
                                              "n_cells": len(cells), "loco": {}})
        conf = {(arm, rd): Counter() for arm in ARMS + TB for rd in D.READINGS}
        paired = {arm: [] for arm in ARMS + TB}   # credulous per-response correctness
        pairedS = {arm: [] for arm in ARMS + TB}  # skeptical
        pkeys = []
        for ci, ck in enumerate(cells):
            lk = str(ci)
            test = [r for r in vrecs if cell_key(r) == ck]
            if lk not in cst["loco"]:
                train = [r for r in vrecs if cell_key(r) != ck]
                if not train:
                    cst["loco"][lk] = {"rules": [], "secs": 0, "timed_out": False, "empty_train": True}
                else:
                    rules, secs, to = learn(train, with_aux, TIMEOUTS["within"])
                    cst["loco"][lk] = {"rules": rules, "secs": secs, "timed_out": to}
                _flush(state)
            w_rules = cst["loco"][lk]["rules"]
            g_rules = st["global_theories"][str(fold_of[ck])]["rules"]
            t_rules = st["transfer_theories"][v]["rules"]
            arm_rules = {"within": w_rules, "global": g_rules, "transfer": t_rules}
            for r in test:
                preds_c, preds_s = {}, {}
                for arm in ARMS:
                    for rd in D.READINGS:
                        p = A9.predict(arm_rules[arm], r["args"], r["attacks"], rd, with_aux=with_aux) \
                            if arm_rules[arm] else {a: "undec" for a in r["args"]}
                        conf[(arm, rd)] += D.score(p, r["labels"])
                        if rd == "credulous":
                            preds_c[arm] = p
                        elif rd == "skeptical":
                            preds_s[arm] = p
                for tb in TB:
                    labs = D.textbook_labellings(tb, r["args"], r["attacks"])
                    for rd in D.READINGS:
                        p = D.project(labs, r["args"], rd)
                        conf[(tb, rd)] += D.score(p, r["labels"])
                        if rd == "credulous":
                            preds_c[tb] = p
                        elif rd == "skeptical":
                            preds_s[tb] = p
                for a_, h in r["labels"].items():
                    pkeys.append((ck, a_))
                    for arm in ARMS + TB:
                        paired[arm].append(1 if preds_c[arm].get(a_, "undec") == h else 0)
                        pairedS[arm].append(1 if preds_s[arm].get(a_, "undec") == h else 0)
        # per-condition table
        table = {}
        for arm in ARMS + TB:
            row = {}
            for rd in D.READINGS:
                c = conf[(arm, rd)]
                co, ncom = G.committed_only_acc(c)
                row[rd] = {"acc3": round(D.metrics_from_conf(c)["acc3"], 4),
                           "committed_only": (round(co, 4) if co == co else None), "n_committed": ncom}
            table[arm] = row

        def mcn(a1, a2, keys=None):
            if keys is not None:  # cell-level dedupe
                first = {}
                for i, k in enumerate(pkeys):
                    first.setdefault(k, i)
                ix = sorted(first.values())
                a1 = [a1[i] for i in ix]; a2 = [a2[i] for i in ix]
            b = sum(1 for x, y in zip(a1, a2) if x and not y)
            c_ = sum(1 for x, y in zip(a1, a2) if y and not x)
            return {"n1_only": b, "n2_only": c_, "p": (1.0 if b == c_ == 0 else round(mcnemar(b, c_), 6))}

        tests = {}
        for h, (x, y) in {"H1_within_vs_global": ("within", "global"),
                          "H2_within_vs_transfer": ("within", "transfer"),
                          "within_vs_cf2": ("within", "cf2"),
                          "global_vs_cf2": ("global", "cf2")}.items():
            tests[h] = {"credulous": mcn(paired[x], paired[y]),
                        "credulous_cell": mcn(paired[x], paired[y], keys=True),
                        "skeptical": mcn(pairedS[x], pairedS[y])}
        # consensus rules across LOCO folds (>= half)
        cnt, ex = Counter(), {}
        for lk, rec in cst["loco"].items():
            seen = set()
            for rl in rec["rules"]:
                k = canon(rl)
                if k and k not in seen:
                    seen.add(k); cnt[k] += 1; ex.setdefault(k, rl)
        half = max(2, (len(cells) + 1) // 2)
        cst["consensus_rules"] = [{"folds": c, "of": len(cells), "rule": ex[k]}
                                  for k, c in cnt.most_common() if c >= half]
        cst["table"] = table
        cst["tests"] = tests
        cst["paired"] = {arm: paired[arm] for arm in ARMS + ("cf2",)}
        # cell-deduped paired vectors (one unit per (cell,arg); predictions are deterministic per
        # cell, so duplicates carry no information) -> the PRIMARY confirmatory unit (P3 audit:
        # response-level exact-binomial inflates effective n ~2x via within-cell duplication).
        first = {}
        for i, k in enumerate(pkeys):
            first.setdefault(k, i)
        ix = sorted(first.values())
        cst["paired_cell"] = {arm: [paired[arm][i] for i in ix] for arm in ARMS + ("cf2",)}
        cst["done"] = True
        _flush(state)
        w, g, t = (table[a]["credulous"]["committed_only"] for a in ARMS)
        print(f"[{key}] {v} ({GROUP[v]}, {len(cells)} cells): committed-only "
              f"within={w} global={g} transfer={t} cf2={table['cf2']['credulous']['committed_only']} "
              f"| H1 p={tests['H1_within_vs_global']['credulous']['p']}", flush=True)
    return st


def holm_stepdown(named_ps, alpha=0.05):
    """Proper step-down Holm: sort ascending, reject while p_(i) <= alpha/(m-i), STOP at the
    first failure; adjusted p = cumulative max of min(1, (m-i)*p). (P3 audit fix.)"""
    hs = sorted(named_ps, key=lambda x: x[1])
    m = len(hs)
    out, rejecting, cmax = {}, True, 0.0
    for i, (name, p) in enumerate(hs):
        cmax = max(cmax, min(1.0, (m - i) * p))
        if rejecting and p <= alpha / (m - i):
            out[name] = ("SIG", cmax)
        else:
            rejecting = False
            out[name] = ("ns", cmax)
    return out


def report(state, phase, vtag):
    key = f"{phase}_{vtag}"
    st = state.get(key)
    if not st:
        return
    print(f"\n########## {key} ##########")
    print(f"  {'cond':<5}{'type':<8}{'cells':>6}{'within':>9}{'global':>9}{'transfer':>9}{'cf2':>7}"
          f"   H1 cell(w/g) p    H2 cell(w/t) p")
    h1ps = []
    pooled_cell = {arm: [] for arm in ARMS + ("cf2",)}
    for v in VERSIONS:
        c = st["conditions"].get(v)
        if not c or not c.get("done"):
            continue
        tb = c["table"]
        vals = [tb[a]["credulous"]["committed_only"] for a in ("within", "global", "transfer", "cf2")]
        # PRIMARY = cell-level (deduped) tests; direction-gated Holm below
        t1 = c["tests"]["H1_within_vs_global"]["credulous_cell"]
        t2 = c["tests"]["H2_within_vs_transfer"]["credulous_cell"]
        # direction gate: H1 is directional (within>global) -> a reversal cannot count as support
        h1ps.append((v, t1["p"] if t1["n1_only"] > t1["n2_only"] else 1.0))
        for arm in pooled_cell:
            pooled_cell[arm].extend(c.get("paired_cell", {}).get(arm, []))
        print(f"  {v:<5}{GROUP[v]:<8}{c['n_cells']:>6}"
              + "".join(f"{(x if x is not None else float('nan')):>9.3f}" for x in vals)
              + f"   {t1['n1_only']}/{t1['n2_only']} p={t1['p']:<9} {t2['n1_only']}/{t2['n2_only']} p={t2['p']}")
    if h1ps:
        hol = holm_stepdown(h1ps)
        print("  Holm(step-down, cell-level, direction-gated) H1 within>global: "
              + ", ".join(f"{v}:{hol[v][0]}(adj p={hol[v][1]:.3f})" for v, _ in sorted(h1ps)))
    def pooled_mcn(x, y):
        b = sum(1 for a, b_ in zip(pooled_cell[x], pooled_cell[y]) if a and not b_)
        c_ = sum(1 for a, b_ in zip(pooled_cell[x], pooled_cell[y]) if b_ and not a)
        return f"{b}/{c_} p={(mcnemar(b, c_) if (b or c_) else 1.0):.4f}"
    if any(pooled_cell.values()):
        print(f"  POOLED (cell-level): within-vs-global {pooled_mcn('within','global')} · "
              f"within-vs-transfer {pooled_mcn('within','transfer')} · within-vs-cf2 {pooled_mcn('within','cf2')}")
    print("  [caveats: H1 is CONSERVATIVE (WITHIN trains on 5-8x less data than GLOBAL); "
          "cell-level power is low for D/E/B/F (few cells) - only G and marginally A/C are powered; "
          "WITHIN gate ceilings from degenerate LOCO structure: B~0.875 D~0.692 E~0.0 F~0.733]")
    for v in VERSIONS:
        c = st["conditions"].get(v, {})
        if c.get("consensus_rules"):
            print(f"  consensus[{v}]: " + " | ".join(f"[{r['folds']}/{r['of']}] {r['rule']}"
                                                     for r in c["consensus_rules"][:4]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="final")
    ap.add_argument("--gate", action="store_true", help="synthetic grounded gate only")
    ap.add_argument("--smoke", action="store_true", help="condition D only, aux vocab")
    a = ap.parse_args()
    state = _load()
    if a.gate:
        run_vocab(state, a.phase, True, VERSIONS, gate_labels="grounded")
        report(state, a.phase, "aux_GATE")
    elif a.smoke:
        run_vocab(state, a.phase, True, ("D",))
        report(state, a.phase, "aux")
    else:
        for with_aux in (True, False):
            run_vocab(state, a.phase, with_aux, VERSIONS)
            report(state, a.phase, "aux" if with_aux else "base")
    print("\nDONE", flush=True)
