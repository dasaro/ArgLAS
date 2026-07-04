#!/usr/bin/env python3
"""V2 reviewer probe: synthetic recovery gate THROUGH the unified_compare harness.

Replace human labels with clean textbook labels (skeptical projection) on the REAL pooled
IndAF graphs, then push them through the EXACT run_phase fold machinery (dedup_weighted ->
shared_negatives -> ilasp_fold / fastlas_fold -> predict_arm -> D.score) and check each
learner arm recovers the semantics: skeptical acc3 >= 0.95 on held-out cell-folds (k=2).
"""
import os, sys, time, json
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import unified_compare as U
import discover_semantics as D
import fl_discover as G

TIMEOUTS = {"ilasp": 240, "opl": 60, "nopl": 240}


def synth_recs(phase, sem):
    """Same shape as U.load_pooled output, but labels = skeptical projection of the
    textbook `sem` labellings of each participant's real IndAF graph."""
    recs = U.load_pooled(phase)
    cache = {}
    out = []
    for r in recs:
        key = (tuple(sorted(r["args"])), tuple(sorted(map(tuple, r["attacks"]))))
        if key not in cache:
            labs = D.textbook_labellings(sem, r["args"], r["attacks"])
            cache[key] = (D.project(labs, r["args"], "skeptical"), len(labs))
        lab, next_ = cache[key]
        labels = {a: lab.get(a, "undec") for a in r["args"]}
        out.append({"pid": r["pid"], "version": r.get("version"),
                    "args": r["args"], "attacks": r["attacks"],
                    "labels": labels, "commit": D.committed(labels)})
    return out, cache


def gate(sem, arms, k=2, max_neg=150):
    recs, cache = synth_recs("final", sem)
    # diagnostics on the distinct graphs
    n_ext = Counter(next_ for (_, next_) in cache.values())
    lab_dist = Counter(l for r in recs for l in r["labels"].values())
    print(f"\n########## GATE sem={sem} arms={arms} ##########")
    print(f"recs={len(recs)} distinct_graphs={len(cache)} responses={sum(len(r['labels']) for r in recs)}")
    print(f"extensions-per-graph histogram (n_labellings -> n_graphs): {dict(sorted(n_ext.items()))}")
    print(f"synthetic label distribution: {dict(lab_dist)}")
    folds = U.shared_folds(recs, k)
    print(f"cell-folds: k={len(folds)} sizes={[len(f) for f in folds]}")
    conf = {a: Counter() for a in list(arms) + ["textbook_" + sem]}
    per_fold = []
    for fi in range(len(folds)):
        test = folds[fi]
        train = [r for j, f in enumerate(folds) if j != fi for r in f]
        cells = U.dedup_weighted(train)
        negs, neg_w = U.shared_negatives(train, max_neg)
        print(f"\n-- fold {fi}: train={len(train)} test={len(test)} cells={len(cells)} "
              f"negs={len(negs)} neg_w={neg_w}")
        rules_by = {}
        finfo = {"fold": fi, "arms": {}}
        for arm in arms:
            t0 = time.time()
            if arm == "ilasp_maxv1":
                rules, to = U.ilasp_fold(cells, negs, neg_w, TIMEOUTS["ilasp"])
            elif arm == "fastlas_opl":
                rules, to = U.fastlas_fold(cells, negs, neg_w, "opl", TIMEOUTS["opl"])
            else:
                rules, to = U.fastlas_fold(cells, negs, neg_w, "nopl", TIMEOUTS["nopl"])
            rules_by[arm] = rules
            secs = round(time.time() - t0, 1)
            finfo["arms"][arm] = {"secs": secs, "timed_out": to, "rules": rules}
            print(f"   {arm}: {secs}s timed_out={to} rules:")
            for rl in (rules or ["(EMPTY)"]):
                print(f"      {rl}")
        fold_conf = {a: Counter() for a in conf}
        for r in test:
            for arm in arms:
                p = U.predict_arm(arm, rules_by[arm], r["args"], r["attacks"], "skeptical")
                fold_conf[arm] += D.score(p, r["labels"])
            p = U.predict_arm(sem, None, r["args"], r["attacks"], "skeptical")
            fold_conf["textbook_" + sem] += D.score(p, r["labels"])
        for a in conf:
            conf[a] += fold_conf[a]
            m = D.metrics_from_conf(fold_conf[a])
            print(f"   fold-{fi} heldout {a}: acc3={m['acc3']:.4f} (n={m['n_args']})")
        per_fold.append(finfo)
    print(f"\n== POOLED HELD-OUT (sem={sem}) ==")
    results = {}
    for a in conf:
        m = D.metrics_from_conf(conf[a])
        co, ncom = G.committed_only_acc(conf[a])
        gate_ok = m["acc3"] >= 0.95
        results[a] = {"acc3": round(m["acc3"], 4), "committed_only": round(co, 4),
                      "n": m["n_args"], "gate": ("PASS" if gate_ok else "FAIL")}
        print(f"  {a:<18} acc3={m['acc3']:.4f} committedOnly={co:.4f} (n={m['n_args']}, "
              f"n_comm={ncom}) GATE(>=0.95): {'PASS' if gate_ok else 'FAIL'}")
        errs = {f"{h}>{p}": n for (h, p), n in conf[a].items() if h != p}
        if errs:
            print(f"     errors: {errs}")
    return {"sem": sem, "results": results, "folds": per_fold}


def stable_representability_check():
    """Is stable representable at maxv=1 in the ILASP space? Verify the candidate theory
    in(X):-arg(X),not defeated(X). out(X):-defeated(X). reproduces stable labellings exactly
    through D.learned_labellings (BG_PREDICT path) on every distinct pooled graph."""
    print("\n########## STABLE REPRESENTABILITY (maxv=1, 2-body) ##########")
    theory = ["in(V1) :- arg(V1); not defeated(V1).", "out(V1) :- defeated(V1)."]
    recs = U.load_pooled("final")
    graphs = {}
    for r in recs:
        graphs[(tuple(sorted(r["args"])), tuple(sorted(map(tuple, r["attacks"]))))] = (r["args"], r["attacks"])
    ok = bad = 0
    for (ka, kt), (args, attacks) in sorted(graphs.items()):
        want = sorted(tuple(sorted(l.items())) for l in D.textbook_labellings("stable", args, attacks))
        got = sorted(tuple(sorted(l.items())) for l in D.learned_labellings(theory, args, attacks))
        if want == got:
            ok += 1
        else:
            bad += 1
            if bad <= 3:
                print(f"  MISMATCH on att={kt}: stable={want} theory={got}")
    print(f"  candidate maxv=1 theory reproduces stable labellings on {ok}/{ok+bad} distinct graphs")
    return ok, bad


if __name__ == "__main__":
    t0 = time.time()
    out = {}
    out["grounded"] = gate("grounded", ("ilasp_maxv1", "fastlas_opl", "fastlas_nopl"), k=2)
    ok, bad = stable_representability_check()
    out["stable_repr"] = {"ok": ok, "bad": bad}
    out["stable"] = gate("stable", ("ilasp_maxv1",), k=2)
    with open(os.path.join(HERE, "v2_gate_results.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(f"\ntotal {time.time()-t0:.0f}s -> v2_gate_results.json")
