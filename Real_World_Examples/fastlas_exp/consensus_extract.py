#!/usr/bin/env python3
"""Extract the CONSENSUS learned rules across CV folds = the stable 'human semantics' signal,
dropping per-fold noise-fitting. For the base and the aux9 vocabularies: learn on each of the 5
leave-one-out train sets, canonicalize each rule (variable-blanked body-literal set, arg/1 guard
dropped), count folds each rule appears in, and report the rules that RECUR (>=3/5 folds).
Flushes to results/consensus.json.

MULTI-SEED MODE (--multiseed): re-run the whole 5-fold extraction at the four fold seeds already
used by aux9_robustness.py (SEEDS below), i.e. 4 seeds x 5 folds = 20 learned theories per
vocabulary, and aggregate canonical-rule recurrence out of 20. Per-seed results are cached to
results/consensus_seed{seed}.json (resume-safe); the aggregate goes to
results/consensus_multiseed.json. Use --seeds to restrict a process to a subset of seeds (so two
processes can split the work); --aggregate combines whatever per-seed caches exist."""
import argparse, json, os, re, time
from collections import Counter, defaultdict
import unified_compare as U
import aux9_combined as A9
import fl_discover as G

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results", "consensus.json")
OUT_MULTI = os.path.join(HERE, "results", "consensus_multiseed.json")
# the four fold seeds of the aux9 robustness table (aux9_robustness.SEEDS)
SEEDS = (20260703, 424242, 777, 20250101)


def canon(rule):
    r = rule.strip().rstrip(".")
    if ":-" not in r:
        return None
    _, body = r.split(":-", 1)
    lits = [x.strip() for x in re.split(r",(?![^()]*\))", body)]
    lits = [l for l in lits if l and not l.startswith("arg(")]     # drop the arg(V0) type guard
    return tuple(sorted(re.sub(r"\bV\d+\b", "V", l) for l in lits))  # blank vars -> group by structure


def run(phase="final", with_aux=True, seed=U.SEED):
    U.SEED = seed
    recs = U.load_pooled(phase)
    folds = U.shared_folds(recs, 5)
    per_fold, examples = [], {}
    for fi in range(len(folds)):
        train = [r for j, f in enumerate(folds) if j != fi for r in f]
        cells = U.dedup_weighted(train); negs, neg_w = U.shared_negatives(train, 150)
        task = A9.build_task(cells, negs, neg_w, with_aux=with_aux)
        rules = G.run_fastlas(task, mode="opl", timeout=250) or []
        keys = set()
        for rl in rules:
            k = canon(rl)
            if k:
                keys.add(k); examples.setdefault(k, rl)
        per_fold.append(keys)
        print(f"  [{'aux' if with_aux else 'base'} {phase}] fold {fi} learned {len(rules)} rules "
              f"({len(keys)} distinct)", flush=True)
    cnt = Counter()
    for ks in per_fold:
        for k in ks:
            cnt[k] += 1
    consensus = [{"folds": c, "rule": examples[k], "canon": " & ".join(k)}
                 for k, c in cnt.most_common() if c >= 3]
    return {"phase": phase, "with_aux": with_aux, "n_folds": len(folds), "seed": seed,
            "consensus_rules": consensus,
            "all_ranked": [{"folds": c, "rule": examples[k], "canon": " & ".join(k)}
                           for k, c in cnt.most_common()]}


# ---------------------------------------------------------------------------
# multi-seed aggregation: 4 seeds x 5 folds = 20 theories per vocabulary
# ---------------------------------------------------------------------------
def _seed_path(seed):
    return os.path.join(HERE, "results", f"consensus_seed{seed}.json")


def run_seed(seed, phase="final"):
    """Both vocabularies at one fold seed; cached to results/consensus_seed{seed}.json."""
    path = _seed_path(seed)
    try:
        cached = json.load(open(path))
        if all(f"{phase}_{t}" in cached for t in ("base", "aux")):
            print(f"[seed {seed}] cached -> {path}", flush=True)
            return cached
    except Exception:
        cached = {}
    for with_aux in (False, True):
        tag = f"{phase}_{'aux' if with_aux else 'base'}"
        if tag in cached:
            continue
        t0 = time.time()
        cached[tag] = run(phase, with_aux, seed=seed)
        cached[tag]["secs"] = round(time.time() - t0)
        tmp = path + ".tmp"
        json.dump(cached, open(tmp, "w"), indent=1)
        os.replace(tmp, path)
        print(f"[seed {seed}] {tag} done ({cached[tag]['secs']}s)", flush=True)
    return cached


def aggregate(phase="final", seeds=SEEDS):
    """Combine per-seed caches -> recurrence counts out of len(seeds)*5 folds."""
    agg = {"phase": phase, "seeds": list(seeds), "n_folds_total": 0}
    for with_aux in (False, True):
        tag = f"{phase}_{'aux' if with_aux else 'base'}"
        cnt, examples, per_seed = Counter(), {}, {}
        n_folds_total = 0
        for seed in seeds:
            data = json.load(open(_seed_path(seed)))[tag]
            n_folds_total += data["n_folds"]
            per_seed[str(seed)] = {r["canon"]: r["folds"] for r in data["all_ranked"]}
            for r in data["all_ranked"]:
                cnt[r["canon"]] += r["folds"]
                examples.setdefault(r["canon"], r["rule"])
        agg["n_folds_total"] = n_folds_total
        agg[tag] = {
            "n_folds_total": n_folds_total,
            "all_ranked": [{"folds_of_total": c, "rule": examples[k], "canon": k,
                            "per_seed": {s: per_seed[s].get(k, 0) for s in per_seed}}
                           for k, c in cnt.most_common()]}
        agg[tag]["consensus_rules"] = [r for r in agg[tag]["all_ranked"]
                                       if r["folds_of_total"] >= n_folds_total // 2 + 1]
    tmp = OUT_MULTI + ".tmp"
    json.dump(agg, open(tmp, "w"), indent=1)
    os.replace(tmp, OUT_MULTI)
    return agg


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--multiseed", action="store_true",
                    help="run all --seeds then aggregate to consensus_multiseed.json")
    ap.add_argument("--seeds", default=",".join(str(s) for s in SEEDS),
                    help="comma list; lets two processes split the seeds")
    ap.add_argument("--aggregate", action="store_true",
                    help="only aggregate existing per-seed caches")
    a = ap.parse_args()
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)

    if a.multiseed or a.aggregate:
        seeds = tuple(int(s) for s in a.seeds.split(","))
        if not a.aggregate:
            for seed in seeds:
                run_seed(seed)
        agg = aggregate(seeds=SEEDS if a.aggregate else seeds)
        for tag in ("final_base", "final_aux"):
            n = agg[tag]["n_folds_total"]
            print(f"\n=== MULTI-SEED CONSENSUS ({tag}) — recurrence out of {n} folds ===", flush=True)
            for c in agg[tag]["all_ranked"]:
                print(f"  [{c['folds_of_total']:2d}/{n}]  {c['rule']}   per-seed {c['per_seed']}", flush=True)
        print(f"\n-> {OUT_MULTI}\nDONE", flush=True)
    else:
        res = {}
        for with_aux in (False, True):
            tag = f"final_{'aux' if with_aux else 'base'}"
            t0 = time.time()
            res[tag] = run("final", with_aux)
            res[tag]["secs"] = round(time.time() - t0)
            json.dump(res, open(OUT, "w"), indent=1)
            print(f"\n=== CONSENSUS ({tag}) — rules in >=3/5 folds ===", flush=True)
            for c in res[tag]["consensus_rules"]:
                print(f"  [{c['folds']}/5]  {c['rule']}", flush=True)
            print("", flush=True)
        print("DONE", flush=True)
