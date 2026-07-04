#!/usr/bin/env python3
"""Overnight run: pooled NOPL maxv=2 with a generous per-fold cap, to test whether the wider
maxv=2 space helps the learner once it is given enough time (maxv=2+enrich times out at 240s).
Flushes per-fold so a partial night still yields usable data. Works through a priority list of
(phase, enrich) configs; whatever completes is saved. Results: results/overnight_nopl_maxv2.json.

  python3 overnight_nopl_maxv2.py            # default 90 min/fold cap, all 4 configs
  python3 overnight_nopl_maxv2.py --fold-cap 3600 --configs final:enr,final:plain
"""
import argparse, json, os, time
from collections import Counter
import fl_discover as G
import discover_semantics as D

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, "results")
PREDS = ("learned",) + D.TEXTBOOK


def _pool(phase):
    recs = []
    for v in ("A", "B", "C", "D", "E", "F", "G"):
        for r in G.load_own(v, phase):
            r["version"] = v
            recs.append(r)
    return recs


def _ser_conf(conf):
    # {(pred,reading): Counter{(h,p):n}} -> nested JSON-safe dict
    out = {}
    for (p, rd), c in conf.items():
        out.setdefault(p, {}).setdefault(rd, {})
        for (h, pr), n in c.items():
            out[p][rd][f"{h}>{pr}"] = n
    return out


def _metrics(conf, p, rd):
    c = conf[(p, rd)]
    co, tot = G.committed_only_acc(c)
    return {"acc3": round(D.metrics_from_conf(c)["acc3"], 4),
            "committed_only": round(co, 4), "n_committed": tot}


def run_config(phase, enrich, fold_cap, max_neg, out_path, state):
    tag = f"{phase}_{'enr' if enrich else 'plain'}"
    recs = _pool(phase)
    folds = G.cell_folds(recs, 5)
    conf = {(p, rd): Counter() for p in PREDS for rd in D.READINGS}
    meta = {"phase": phase, "enrich": enrich, "maxv": 2, "mode": "nopl", "n_examples": len(recs),
            "n_folds": len(folds), "fold_cap_s": fold_cap, "max_neg": max_neg,
            "folds": [], "status": "running"}
    state[tag] = meta
    for fi in range(len(folds)):
        test = folds[fi]; train = [r for j, f in enumerate(folds) if j != fi for r in f]
        negs = G.shell_of(train)
        if max_neg and len(negs) > max_neg:
            import random
            negs = [negs[i] for i in sorted(random.Random(20260703).sample(range(len(negs)), max_neg))]
        neg_w = max(1, round(100 * len(train) / len(negs))) if negs else 100
        task = G.build_learn_task(G.cells_from(train), negs, enrich=enrich, maxv=2, neg_w=neg_w)
        t0 = time.time()
        rules = G.run_fastlas(task, mode="nopl", timeout=fold_cap)
        dt = round(time.time() - t0, 1)
        timed_out = rules is None
        if rules is None:
            rules = []
        for r in test:
            for kind in PREDS:
                if kind == "learned":
                    for rd in D.READINGS:
                        conf[(kind, rd)] += D.score(G.predict(rules, r["args"], r["attacks"], rd, enrich), r["labels"])
                else:
                    labs = D.textbook_labellings(kind, r["args"], r["attacks"])
                    for rd in D.READINGS:
                        conf[(kind, rd)] += D.score(D.project(labs, r["args"], rd), r["labels"])
        meta["folds"].append({"fold": fi, "secs": dt, "n_rules": len(rules),
                              "timed_out": timed_out, "rules": rules})
        # running committed-only for learned + textbook after this fold
        meta["running"] = {p: _metrics(conf, p, "credulous") for p in PREDS}
        meta["conf"] = _ser_conf(conf)
        _flush(out_path, state)
        print(f"[{tag}] fold {fi+1}/{len(folds)} {dt}s rules={len(rules)}{' TIMEOUT' if timed_out else ''} "
              f"| learned committed-only={meta['running']['learned']['committed_only']} "
              f"cf2={meta['running']['cf2']['committed_only']}", flush=True)
    meta["status"] = "done"
    meta["final"] = {p: {rd: _metrics(conf, p, rd) for rd in D.READINGS} for p in PREDS}
    _flush(out_path, state)
    print(f"[{tag}] DONE. learned committed-only(cred)={meta['final']['learned']['credulous']['committed_only']} "
          f"vs cf2={meta['final']['cf2']['credulous']['committed_only']}", flush=True)


def _flush(path, state):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fold-cap", type=int, default=5400, help="per-fold FastLAS solving cap (s).")
    ap.add_argument("--max-neg", type=int, default=150)
    ap.add_argument("--configs", default="final:enr,final:plain,first:enr,first:plain")
    a = ap.parse_args()
    os.makedirs(OUTDIR, exist_ok=True)
    out_path = os.path.join(OUTDIR, "overnight_nopl_maxv2.json")
    state = {"started": time.strftime("%Y-%m-%d %H:%M"), "params": vars(a)}
    _flush(out_path, state)
    for spec in a.configs.split(","):
        phase, ek = spec.split(":")
        try:
            run_config(phase, ek == "enr", a.fold_cap, a.max_neg, out_path, state)
        except Exception as e:
            state[f"{phase}_{ek}"] = {"status": "error", "error": repr(e)}
            _flush(out_path, state)
            print(f"[{phase}:{ek}] ERROR {e!r}", flush=True)
    state["status"] = "ALL DONE"
    _flush(out_path, state)
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
