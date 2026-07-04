#!/usr/bin/env python3
"""Exp1 complete-information rescoring (audit follow-up).

The corrected campaign's test items inherit the partial-label regime: at p<1 the held-out
instances are themselves partially labelled, so the reported surface conflates the LEARNING
limit with a harder TEST-item type (audit finding E2; rescoring identical models on complete
items raised MCC +0.13..+0.28 in spot checks). This driver re-scores every archived learned
model on BOTH test regimes with the exact campaign machinery (train_test functions, same fold
seed 20260312, fold=ITERATION, 100/class, full_exact_model):

  matched  : the fold test set from the SAME partial pool the campaign used
             -> must reproduce the stored TP/FP/TN/FN EXACTLY (built-in validation)
  complete : the fold test set drawn from labelled_<SEM>_full (complete-information items)
             -> the recovery-limit surface the Exp1->Exp2 bridge should read

Usage:
  python3 exp1_rescore_complete_info.py --validate     # 6 rows, assert matched == stored
  python3 exp1_rescore_complete_info.py                # full run (534 successful rows)
Results: analysis/exp1_complete_info_rescore.json (incremental flush; resumable cache).
"""
import argparse, csv, glob, json, os, sys, time
from multiprocessing import Pool

REPO = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(REPO, "artifacts", "final_synthetic_corrected_20260625")
OUT = os.path.join(REPO, "analysis", "exp1_complete_info_rescore.json")
FOLD_SEED = 20260312
K = 5
PER_CLASS = 100
sys.path.insert(0, REPO)
import train_test as T


def load_rows():
    rows = []
    for path in sorted(glob.glob(os.path.join(ART, "results", "*", "results_*.csv"))):
        for r in csv.DictReader(open(path), delimiter=";"):
            task = r["ILASP_TASK_FILENAME"]
            # semantics/partial token from the task path component e.g. "STB_partial_0.5" / "CMP_full"
            comp = os.path.basename(os.path.dirname(task))
            sem = comp.split("_")[0]
            ptok = comp[len(sem) + 1:]                     # "full" or "partial_0.5"
            rows.append({
                "sem": sem, "ptok": ptok,
                "noise": float(r["NOISE"]), "f": int(r["NFILES_POS"]),
                "iteration": int(r["ITERATION"]),
                "model": r["LEARNED_MODEL_FILENAME"],
                "succeeded": r["ILASP_TRAIN_SUCCEEDED"] in ("1", "True", "true"),
                "stored": {k2: int(r[k2]) for k2 in ("TP", "FP", "TN", "FN")},
                "stored_mcc": float(r["MCC"]),
                "key": f"{sem}|{ptok}|{r['NOISE']}|{r['NFILES_POS']}|{r['ITERATION']}",
            })
    return rows


def make_runtimes():
    cfgp = T.resolve_repo_path("semantics_config.json")
    cfg = T.load_semantics_config(cfgp)
    rt = {}
    for sem in ("ADM", "CMP", "STB"):
        entry = T.get_semantics_entry(cfg, sem)
        rt[sem] = {
            "asp_file": T.resolve_repo_path(entry["file"]),
            "l_args": T.get_clingo_args(cfg, sem, stage="train_test_learned"),
            "g_args": T.get_clingo_args(cfg, sem, stage="train_test_ground_truth"),
            "l_bg": (lambda v: T.resolve_repo_path(v) if v else None)(T.get_background_file(cfg, stage="train_test_learned")),
            "g_bg": (lambda v: T.resolve_repo_path(v) if v else None)(T.get_background_file(cfg, stage="train_test_ground_truth")),
            "l_comp": T.get_completion_rules_enabled(cfg, stage="train_test_learned", semantics=sem),
            "g_comp": T.get_completion_rules_enabled(cfg, stage="train_test_ground_truth", semantics=sem),
            "l_show": T.get_show_predicates(cfg, stage="train_test_learned"),
            "g_show": T.get_show_predicates(cfg, stage="train_test_ground_truth"),
            "bare": T.get_eval_on_bare_aaf(cfg, sem),
        }
    return rt


_RT = None  # per-worker runtime cache


def _score(model_file, input_dir, test_files, rt):
    tp = fp = tn = fn = 0
    for tf in test_files:
        test_path = os.path.join(input_dir, tf)
        assert not rt["bare"], "bare-AAF eval not expected for ADM/CMP/STB"
        pred = T.run_learned_model_with_api(model_file, test_path, rt["l_bg"],
                                            clingo_args=rt["l_args"], completion_rules=rt["l_comp"],
                                            show_predicates=rt["l_show"])
        gt = T.run_ground_truth_with_api(rt["asp_file"], test_path, rt["g_bg"],
                                         clingo_args=rt["g_args"], completion_rules=rt["g_comp"],
                                         show_predicates=rt["g_show"])
        _, a, b, c, d = T.evaluate_model_sets(pred, gt, "full_exact_model")
        tp += a; fp += b; tn += c; fn += d
    return {"TP": tp, "FP": fp, "TN": tn, "FN": fn,
            "MCC": round(T.matthews_corrcoef(tp, fp, tn, fn), 6)}


def rescore_row(row):
    global _RT
    if _RT is None:
        _RT = make_runtimes()
    rt = _RT[row["sem"]]
    t0 = time.time()
    matched_dir = os.path.join(ART, "labelled", f"labelled_{row['sem']}_{row['ptok']}")
    full_dir = os.path.join(ART, "labelled", f"labelled_{row['sem']}_full")
    folds = T.build_grouped_folds(matched_dir, K, fold_seed=FOLD_SEED)
    test_aafs = folds[row["iteration"] - 1][1]
    out = {"key": row["key"], "stored": row["stored"], "stored_mcc": row["stored_mcc"],
           "sem": row["sem"], "ptok": row["ptok"], "noise": row["noise"], "f": row["f"],
           "iteration": row["iteration"]}
    for tag, d in (("matched", matched_dir), ("complete", full_dir)):
        tfs = T.build_grouped_balanced_test(d, test_aafs, PER_CLASS,
                                            fold_seed=FOLD_SEED, fold_index=row["iteration"])
        out[tag] = _score(row["model"], d, tfs, rt)
    out["matched_reproduces_stored"] = all(out["matched"][k2] == row["stored"][k2]
                                           for k2 in ("TP", "FP", "TN", "FN"))
    out["secs"] = round(time.time() - t0, 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true", help="6 rows only, assert matched==stored")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    rows = [r for r in load_rows() if r["succeeded"]]
    print(f"{len(rows)} successful rows to rescore (of 540)", flush=True)
    done = {}
    if os.path.exists(OUT):
        done = {r["key"]: r for r in json.load(open(OUT)).get("rows", [])}
        print(f"resuming: {len(done)} cached", flush=True)
    if a.validate:
        # one row per (semantics x partial-regime sample), incl. a p=1.0 row (delta must be ~0)
        pick, seen = [], set()
        for r in rows:
            kk = (r["sem"], r["ptok"])
            if kk not in seen:
                seen.add(kk); pick.append(r)
        rows = pick[:6]
        print(f"VALIDATE mode: {len(rows)} rows: {[r['key'] for r in rows]}", flush=True)
    todo = [r for r in rows if r["key"] not in done]
    results = list(done.values())
    t0 = time.time()
    with Pool(a.workers) as pool:
        for i, res in enumerate(pool.imap_unordered(rescore_row, todo)):
            results.append(res)
            ok = "OK " if res["matched_reproduces_stored"] else "MISMATCH!"
            print(f"[{len(results)}/{len(rows)}] {res['key']}  matched={ok} "
                  f"mcc {res['stored_mcc']:.3f} -> complete {res['complete']['MCC']:.3f}  ({res['secs']}s)",
                  flush=True)
            if len(results) % 10 == 0 or len(results) == len(rows):
                json.dump({"rows": results}, open(OUT + ".tmp", "w"), indent=1)
                os.replace(OUT + ".tmp", OUT)
    json.dump({"rows": results}, open(OUT + ".tmp", "w"), indent=1)
    os.replace(OUT + ".tmp", OUT)
    n_bad = sum(1 for r in results if not r["matched_reproduces_stored"])
    print(f"\nDONE in {time.time()-t0:.0f}s. matched-reproduction failures: {n_bad}/{len(results)}", flush=True)
    if a.validate and n_bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
