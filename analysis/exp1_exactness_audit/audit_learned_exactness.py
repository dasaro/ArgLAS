#!/usr/bin/env python3
"""Post-hoc exactness audit of the clean-label (NOISE=0.0) campaign hypotheses.

For every successfully learned theory H of the v2 campaign at noise 0.0
(semantics STB/ADM/CMP/PRF), decide whether H is EXACTLY extension-equivalent
to its target semantics on EVERY labelled digraph with <= NMAX (=4) arguments,
self-attacks included (2^1 + 2^4 + 2^9 + 2^16 = 66,066 frameworks).

Equivalence notion (the paper's own, for constraint-style presentations over
the guessing background, and the notion the complete-information MCC_FULL
surface probes): enumerate the answer sets of H + config/background_knowledge.lp
+ AF facts, keep only TOTAL labellings (every argument in or out), and compare
the resulting sets of in-extensions with the reference labelling sets computed
from the ASPARTIX-style encodings quoted in the manuscript.

PRF is the one semantics whose pipeline evaluation is NOT total-labelling
based (config/semantics_config.json: completion_rules=false, show in/1 only,
--heuristic=Domain --enum=domRec): the extension set the campaign scores is
the set of subset-maximal in-projections over ALL models of H + guessing
background, which is exactly what domRec realizes on bg_prf_learned.lp
(= background_knowledge.lp + a #heuristic directive; heuristics never change
the set of models, only which ones domRec enumeration keeps). The audit
therefore checks PRF under that pipeline-faithful convention as PRIMARY
(subset-maximal in-selection applied in Python on both sides: reference PRF
= subset-maximal elements of the ADM labelling set, i.e. the preferred
extensions), and additionally records the strict total-labelling variant as
a secondary column. Plain background_knowledge.lp is used as the guessing
background for all four semantics.

This is an empirical exhaustive comparison via ASP solving. No learning is
re-run; hypotheses are read from the committed campaign record
(data/exp1_v2/results/*/results_*.csv -> LEARNED_MODEL_FILENAME under
artifacts/final_synthetic_v2/train_output/).

Usage:
  python3 audit_learned_exactness.py build-cache [--workers 7]
  python3 audit_learned_exactness.py audit       [--workers 7]
  python3 audit_learned_exactness.py all         [--workers 7]

Outputs (in this directory):
  hypothesis_catalogue.csv  one row per distinct hypothesis (exact flag + one
                            minimal counterexample AF for non-exact ones)
  run_exactness.csv         one row per clean campaign run
  exactness_by_cell.csv     fraction exact per (semantics, f, p)
  summary.json              headline numbers
Reference cache (regenerable, not committed): --cache path, default in the
system temp dir.
"""
import argparse
import collections
import csv
import glob
import json
import os
import pickle
import sys
import tempfile
import time
from multiprocessing import Pool

import clingo

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTDIR = os.path.dirname(os.path.abspath(__file__))
NMAX = 4
SEMS = ("STB", "ADM", "CMP", "PRF")
DEFAULT_CACHE = os.path.join(tempfile.gettempdir(), "exp1_exactness_reference_cache.pkl")

# ASPARTIX-style reference encodings exactly as quoted in the manuscript
# (identical to config/ASPARTIX/{stable,admissible,complete}.lp modulo comments;
# cross-checked against those files at n<=3 by sanity_checks()).
DEFS = "defeated(X):-att(Y,X), in(Y).\nnot_defended(X):-att(Y,X), not defeated(Y).\n"
GUESS = "in(X):-not out(X), arg(X).\nout(X):-not in(X), arg(X).\n"
S_REF = {
    "STB": GUESS + DEFS + ":- in(X), in(Y), att(X,Y).\n:- out(X), not defeated(X).\n",
    "ADM": GUESS + DEFS + ":- in(X), in(Y), att(X,Y).\n:- in(X), not_defended(X).\n",
    "CMP": (GUESS + DEFS + ":- in(X), in(Y), att(X,Y).\n:- in(X), not_defended(X).\n"
            ":- out(X), not not_defended(X).\n"),
}

with open(os.path.join(REPO, "config", "background_knowledge.lp")) as fh:
    BG = fh.read()


# ---------------------------------------------------------------- AF universe
def af_order():
    """All (n, mask) for n=1..NMAX, minimal-first (n asc, #attacks asc, mask asc)."""
    order = []
    for n in range(1, NMAX + 1):
        masks = sorted(range(2 ** (n * n)), key=lambda m: (bin(m).count("1"), m))
        order.extend((n, m) for m in masks)
    return order


def af_facts(n, mask):
    pairs = [(i, j) for i in range(n) for j in range(n)]  # self-attacks included
    s = "".join(f"arg(a{i})." for i in range(n))
    s += "".join(f"att(a{i},a{j})." for k, (i, j) in enumerate(pairs) if mask >> k & 1)
    return s


def af_edges(n, mask):
    pairs = [(i, j) for i in range(n) for j in range(n)]
    return [pairs[k] for k in range(len(pairs)) if mask >> k & 1]


# ------------------------------------------------------------- ASP enumeration
def enum_models(prog, facts, show=("in/1",), extra_args=()):
    ctl = clingo.Control(["0", "--warn=none"] + list(extra_args))
    shows = "".join(f"#show {p}.\n" for p in show)
    # newline-join defensively: some encoding files lack a trailing newline,
    # which would otherwise glue the facts onto a trailing %-comment line
    ctl.add("base", [], prog + "\n" + facts + "\n" + shows)
    ctl.ground([("base", [])])
    out = []
    with ctl.solve(yield_=True) as handle:
        for m in handle:
            out.append(frozenset(str(a) for a in m.symbols(shown=True)))
    return out


def in_bitmask(model_atoms):
    b = 0
    for a in model_atoms:
        if a.startswith("in(a"):
            b |= 1 << int(a[4:-1])
    return b


def ref_in_sets(sem, facts):
    """Reference labelling set as frozenset of in-bitmasks (models are total)."""
    return frozenset(in_bitmask(m) for m in enum_models(S_REF[sem], facts))


def hyp_in_sets(hyp, n, facts):
    """Models of hyp + guessing background, as (total_in_sets, all_in_sets):
    in-bitmasks of the TOTAL labellings, and in-projections of ALL models."""
    total, allm = set(), set()
    for m in enum_models(BG + hyp, facts, show=("in/1", "out/1")):
        b = in_bitmask(m)
        allm.add(b)
        labelled = set()
        for a in m:
            labelled.add(int(a[4:-1]) if a.startswith("in(a") else int(a[5:-1]))
        if len(labelled) == n:  # total: every argument in or out
            total.add(b)
    return frozenset(total), frozenset(allm)


def subset_max(masks):
    return frozenset(m for m in masks
                     if not any(m != m2 and m | m2 == m2 for m2 in masks))


# ------------------------------------------------------------- reference cache
def _ref_worker(chunk):
    res = []
    for n, mask in chunk:
        facts = af_facts(n, mask)
        adm = ref_in_sets("ADM", facts)
        res.append(((n, mask), {
            "STB": ref_in_sets("STB", facts),
            "ADM": adm,
            "CMP": ref_in_sets("CMP", facts),
            "PRF": subset_max(adm),
        }))
    return res


def build_cache(cache_path, workers):
    order = af_order()
    print(f"[cache] computing reference labelling sets for {len(order)} AFs "
          f"(n<= {NMAX}, self-attacks included) with {workers} workers", flush=True)
    t0 = time.time()
    chunks = [order[i::workers * 8] for i in range(workers * 8)]
    ref = {}
    with Pool(workers) as pool:
        for part in pool.imap_unordered(_ref_worker, chunks):
            ref.update(part)
    assert len(ref) == len(order), (len(ref), len(order))
    with open(cache_path, "wb") as fh:
        pickle.dump({"order": order, "ref": ref}, fh, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"[cache] done in {time.time()-t0:.0f}s -> {cache_path} "
          f"({os.path.getsize(cache_path)/1e6:.1f} MB)", flush=True)
    return order, ref


# ---------------------------------------------------------------- sanity checks
def sanity_checks(order, ref):
    """Independent cross-checks of the reference cache on all n<=3 AFs (530)."""
    print("[sanity] cross-checking reference vs config/ASPARTIX encodings (n<=3)",
          flush=True)
    enc = {}
    for sem, fname in (("STB", "stable.lp"), ("ADM", "admissible.lp"),
                       ("CMP", "complete.lp"), ("PRF", "preferred.lp")):
        with open(os.path.join(REPO, "config", "ASPARTIX", fname)) as fh:
            enc[sem] = fh.read()
    small = [(n, m) for (n, m) in order if n <= 3]
    bad = 0
    for n, mask in small:
        facts = af_facts(n, mask)
        for sem in ("STB", "ADM", "CMP"):
            got = frozenset(in_bitmask(x) for x in enum_models(enc[sem], facts))
            if got != ref[(n, mask)][sem]:
                bad += 1
                print(f"[sanity] MISMATCH {sem} n={n} mask={mask}", flush=True)
        # PRF: ASPARTIX preferred.lp under its documented domRec call
        got = frozenset(in_bitmask(x) for x in enum_models(
            enc["PRF"], facts, extra_args=("--heuristic=Domain", "--enum=domRec")))
        if got != ref[(n, mask)]["PRF"]:
            bad += 1
            print(f"[sanity] MISMATCH PRF n={n} mask={mask}", flush=True)
    if bad:
        sys.exit(f"[sanity] FAILED: {bad} mismatches on n<=3")
    print(f"[sanity] OK on all {len(small)} AFs with n<=3 (4 semantics each)",
          flush=True)


# --------------------------------------------------------------------- harvest
def harvest():
    """Clean-label campaign runs -> (rows, distinct hypotheses)."""
    rows = []
    pattern = os.path.join(REPO, "data", "exp1_v2", "results", "*", "results_*.csv")
    for path in sorted(glob.glob(pattern)):
        sem = os.path.basename(os.path.dirname(path)).split("_")[0]
        if sem not in SEMS:
            continue
        with open(path) as fh:
            for r in csv.DictReader(fh, delimiter=";"):
                if float(r["NOISE"]) != 0.0 or r["ILASP_TRAIN_SUCCEEDED"] != "1":
                    continue
                with open(r["LEARNED_MODEL_FILENAME"]) as mh:
                    text = " ".join(mh.read().split())
                rows.append({
                    "semantics": sem,
                    "f": int(r["NFILES_POS"]) + int(r["NFILES_NEG"]),
                    "p": float(r["P_PARTIAL"]),
                    "mcc_full": float(r["MCC_FULL"]) if r["MCC_FULL"] else None,
                    "model_file": r["LEARNED_MODEL_FILENAME"],
                    "hyp_text": text,
                })
    dist = collections.defaultdict(set)
    for row in rows:
        dist[row["semantics"]].add(row["hyp_text"])
    hyp_id = {}
    for sem in SEMS:
        for i, text in enumerate(sorted(dist[sem])):
            hyp_id[(sem, text)] = f"{sem}_{i:03d}"
    for row in rows:
        row["hyp_id"] = hyp_id[(row["semantics"], row["hyp_text"])]
    return rows, hyp_id


# ------------------------------------------------------------ exactness checks
_G = {}


def _check_init(cache_path):
    with open(cache_path, "rb") as fh:
        data = pickle.load(fh)
    _G["order"] = data["order"]
    _G["ref"] = data["ref"]
    _G["facts"] = {key: af_facts(*key) for key in data["order"]}


def _check_hypothesis(job):
    """Check one distinct hypothesis against the reference on every cached AF.

    Convention per semantics (see module docstring):
      STB/ADM/CMP: total labellings of H + guessing background.
      PRF primary: subset-maximal in-projections over ALL models (what the
                   pipeline's domRec evaluation scores);
      PRF secondary ('strict_total_*' fields): subset-maximal over the TOTAL
                   labellings only.
    Early exit on the first (minimal-first order) counterexample of the
    primary convention; the secondary flag is tracked until then.
    """
    hid, sem, hyp = job
    t0 = time.time()
    checked = 0
    primary_ce = None
    strict_exact = True if sem == "PRF" else None
    strict_ce = None
    for n, mask in _G["order"]:
        facts = _G["facts"][(n, mask)]
        total, allm = hyp_in_sets(hyp, n, facts)
        expected = _G["ref"][(n, mask)][sem]
        if sem == "PRF":
            got = subset_max(allm)
            strict_got = subset_max(total)
        else:
            got = total
            strict_got = None
        checked += 1

        def fmt(sets):
            return sorted(sorted(f"a{i}" for i in range(n) if b >> i & 1)
                          for b in sets)

        if sem == "PRF" and strict_exact and strict_got != expected:
            strict_exact = False
            strict_ce = {"n": n, "attacks": af_edges(n, mask),
                         "expected_in_sets": fmt(expected),
                         "learned_in_sets": fmt(strict_got)}
        if primary_ce is None and got != expected:
            primary_ce = {"n": n, "attacks": af_edges(n, mask),
                          "expected_in_sets": fmt(expected),
                          "learned_in_sets": fmt(got)}
        # early exit once every tracked convention has found its counterexample
        if primary_ce is not None and (sem != "PRF" or not strict_exact):
            break
    return {"hyp_id": hid, "exact": primary_ce is None, "n_afs_checked": checked,
            "counterexample": primary_ce, "strict_total_exact": strict_exact,
            "strict_total_counterexample": strict_ce,
            "secs": round(time.time() - t0, 1)}


def audit(cache_path, workers):
    rows, hyp_id = harvest()
    n_runs = len(rows)
    hyps = sorted({(row["hyp_id"], row["semantics"], row["hyp_text"]) for row in rows})
    per_sem = collections.Counter(h[1] for h in hyps)
    print(f"[audit] {n_runs} clean runs, {len(hyps)} distinct hypotheses "
          f"({dict(per_sem)})", flush=True)

    t0 = time.time()
    results = {}
    with Pool(workers, initializer=_check_init, initargs=(cache_path,)) as pool:
        for i, res in enumerate(pool.imap_unordered(_check_hypothesis, hyps), 1):
            results[res["hyp_id"]] = res
            print(f"[audit] {i}/{len(hyps)} {res['hyp_id']} "
                  f"{'EXACT' if res['exact'] else 'NON-EXACT'} "
                  f"({res['n_afs_checked']} AFs, {res['secs']}s)", flush=True)
    print(f"[audit] all checks done in {(time.time()-t0)/60:.1f} min", flush=True)

    # ---- outputs
    hyp_runs = collections.Counter(row["hyp_id"] for row in rows)
    text_of = {hid: text for hid, _sem, text in hyps}
    with open(os.path.join(OUTDIR, "hypothesis_catalogue.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["hyp_id", "semantics", "n_runs", "exact", "n_afs_checked",
                    "strict_total_exact", "counterexample_json",
                    "strict_total_counterexample_json", "hypothesis_text"])
        for hid, sem, _text in hyps:
            res = results[hid]
            w.writerow([hid, sem, hyp_runs[hid], int(res["exact"]),
                        res["n_afs_checked"],
                        "" if res["strict_total_exact"] is None
                        else int(res["strict_total_exact"]),
                        json.dumps(res["counterexample"]) if res["counterexample"] else "",
                        json.dumps(res["strict_total_counterexample"])
                        if res["strict_total_counterexample"] else "",
                        text_of[hid]])

    with open(os.path.join(OUTDIR, "run_exactness.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["semantics", "f", "p", "mcc_full", "hyp_id", "exact", "model_file"])
        for row in sorted(rows, key=lambda r: (r["semantics"], r["f"], r["p"],
                                               r["model_file"])):
            w.writerow([row["semantics"], row["f"], row["p"], row["mcc_full"],
                        row["hyp_id"], int(results[row["hyp_id"]]["exact"]),
                        os.path.relpath(row["model_file"], REPO)])

    cell = collections.defaultdict(lambda: [0, 0])
    for row in rows:
        key = (row["semantics"], row["f"], row["p"])
        cell[key][0] += 1
        cell[key][1] += int(results[row["hyp_id"]]["exact"])
    with open(os.path.join(OUTDIR, "exactness_by_cell.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["semantics", "f", "p", "n_runs", "n_exact", "frac_exact"])
        for (sem, f, p), (tot, ex) in sorted(cell.items()):
            w.writerow([sem, f, p, tot, ex, round(ex / tot, 4)])

    def frac(sel):
        sel = list(sel)
        ex = sum(int(results[row["hyp_id"]]["exact"]) for row in sel)
        return {"n": len(sel), "exact": ex,
                "frac": round(ex / len(sel), 4) if sel else None}

    summary = {
        "n_afs": len(af_order()),
        "nmax": NMAX,
        "n_clean_runs": n_runs,
        "n_distinct_hypotheses": len(hyps),
        "distinct_per_semantics": dict(per_sem),
        "distinct_exact": sum(int(r["exact"]) for r in results.values()),
        "distinct_exact_per_semantics": {
            sem: sum(int(results[hid]["exact"]) for hid, s, _t in hyps if s == sem)
            for sem in SEMS},
        "runs_overall": frac(rows),
        "runs_per_semantics": {sem: frac(r for r in rows if r["semantics"] == sem)
                               for sem in SEMS},
        "runs_f_ge_30": frac(r for r in rows if r["f"] >= 30),
        "runs_mcc_full_1": frac(r for r in rows if r["mcc_full"] == 1.0),
        "runs_f_ge_30_per_semantics": {
            sem: frac(r for r in rows if r["semantics"] == sem and r["f"] >= 30)
            for sem in SEMS},
        "prf_strict_total_distinct_exact": sum(
            1 for hid, s, _t in hyps
            if s == "PRF" and results[hid]["strict_total_exact"]),
    }
    with open(os.path.join(OUTDIR, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1)
    print(json.dumps(summary, indent=1), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["build-cache", "audit", "all"], nargs="?",
                    default="all")
    ap.add_argument("--workers", type=int, default=7)
    ap.add_argument("--cache", default=DEFAULT_CACHE)
    ap.add_argument("--skip-sanity", action="store_true")
    args = ap.parse_args()

    if args.mode in ("build-cache", "all"):
        order, ref = build_cache(args.cache, args.workers)
        if not args.skip_sanity:
            sanity_checks(order, ref)
    if args.mode in ("audit", "all"):
        if not os.path.exists(args.cache):
            sys.exit(f"cache not found: {args.cache} (run build-cache first)")
        audit(args.cache, args.workers)


if __name__ == "__main__":
    main()
