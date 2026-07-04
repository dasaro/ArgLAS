#!/usr/bin/env python3
"""Extract the CONSENSUS learned rules across CV folds = the stable 'human semantics' signal,
dropping per-fold noise-fitting. For the base and the aux9 vocabularies: learn on each of the 5
leave-one-out train sets, canonicalize each rule (variable-blanked body-literal set, arg/1 guard
dropped), count folds each rule appears in, and report the rules that RECUR (>=3/5 folds).
Flushes to results/consensus.json."""
import json, os, re, time
from collections import Counter, defaultdict
import unified_compare as U
import aux9_combined as A9
import fl_discover as G

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "consensus.json")


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
    return {"phase": phase, "with_aux": with_aux, "n_folds": len(folds),
            "consensus_rules": consensus,
            "all_ranked": [{"folds": c, "rule": examples[k]} for k, c in cnt.most_common()]}


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
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
