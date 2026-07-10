"""Decision-tree (and logistic / majority) baseline for argument acceptability,
as a non-LAS, interpretable comparator for the ILASP/FastLAS approach.

The decision tree solves the PER-ARGUMENT acceptance task (the standard task GNN
baselines such as AGNN solve), NOT the labelling-level extension-membership task
that LAS solves — a tree predicts one label per argument and cannot represent the
set of extensions. We report credulous AND skeptical acceptance, because credulous
acceptance coincides for admissible/complete/preferred (a classical result), so the
per-semantics signal lives in: credulous-stable, skeptical-stable, skeptical-preferred,
skeptical-complete(=grounded), plus the shared credulous-admissible-family target.

Protocol matches the v2 campaign where it can: same 500-AAF pool, grouped 5-fold CV
(no framework leaks across train/test), same four semantics, same noise axis
q in {0,0.1,0.2} (training labels flipped at rate q; test on the clean oracle).
Purely structural features (no oracle labels leak in).

Records EVERYTHING to analysis/tree_baseline/: results.json (per-fold + aggregate
metrics), summary.md, feature_importances.json, and exported tree rules per target.
"""
import csv, glob, json, os, re, time, statistics as st
from collections import defaultdict
import numpy as np
import networkx as nx
import clingo
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.metrics import matthews_corrcoef, accuracy_score, precision_recall_fscore_support

REPO = "/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_claude"
OUT = os.path.join(REPO, "analysis/tree_baseline")
os.makedirs(os.path.join(OUT, "trees"), exist_ok=True)
POOL = sorted(glob.glob(os.path.join(REPO, "artifacts/final_synthetic_v2/aafs/aaf_*.lp")))
SEED = 20260312           # campaign test_sampling_seed, reused for fold + noise determinism
NOISES = [0.0, 0.1, 0.2]
N_FOLDS = 5

ENC = {s: open(os.path.join(REPO, f"ASPARTIX/{f}.lp")).read()
       for s, f in [("STB", "stable"), ("ADM", "admissible"),
                    ("CMP", "complete"), ("PRF", "preferred")]}
DOMREC = {"PRF"}          # preferred needs subset-maximal enumeration


def parse_aaf(path):
    args, atts = [], []
    for ln in open(path):
        ln = ln.strip()
        m = re.match(r"arg\((\w+)\)", ln)
        if m:
            args.append(m.group(1))
        m = re.match(r"att\((\w+),\s*(\w+)\)", ln)
        if m:
            atts.append((m.group(1), m.group(2)))
    return args, atts


def extensions(aaf_text, sem):
    """All in-sets of the sigma-extensions (via ASPARTIX + clingo)."""
    args = ["0", "--warn=none"] + (["--heuristic=Domain", "--enum-mode=domRec"] if sem in DOMREC else [])
    ctl = clingo.Control(args)
    ctl.add("base", [], aaf_text + "\n" + ENC[sem] + "\n#show in/1.")
    ctl.ground([("base", [])])
    exts = []
    with ctl.solve(yield_=True) as h:
        for m in h:
            exts.append(frozenset(str(a.arguments[0]) for a in m.symbols(shown=True)))
    return exts


def features(args, atts):
    """Purely-structural per-argument features (no oracle labels)."""
    n = len(args)
    G = nx.DiGraph(); G.add_nodes_from(args); G.add_edges_from(atts)
    attackers = defaultdict(set); attacked = defaultdict(set)
    for a, b in atts:
        attackers[b].add(a); attacked[a].add(b)
    unatt = {x for x in args if len(attackers[x]) == 0}
    scc_of = {}
    for comp in nx.strongly_connected_components(G):
        for x in comp:
            scc_of[x] = len(comp)
    # reachability from unattacked args (via attack edges)
    reach = set()
    for u in unatt:
        reach |= nx.descendants(G, u) | {u}
    dens = len(atts) / (n * (n - 1)) if n > 1 else 0.0
    feats = {}
    for x in args:
        ina, outa = attackers[x], attacked[x]
        n_unatt_att = len(ina & unatt)
        self_att = 1 if x in ina else 0
        defenders = set()               # 2-step: attackers of x's attackers
        for y in ina:
            defenders |= attackers[y]
        feats[x] = [
            n, len(atts), round(dens, 4),
            len(ina), len(outa),
            1 if len(ina) == 0 else 0,          # is_unattacked
            self_att,
            n_unatt_att,
            1 if n_unatt_att > 0 else 0,        # has_unattacked_attacker
            round(len(ina & unatt) / len(ina), 3) if ina else 0.0,  # frac attackers unattacked
            scc_of[x],
            1 if (scc_of[x] > 1 or self_att) else 0,   # in_cycle
            1 if x in reach else 0,             # reachable_from_unattacked
            len(defenders),                     # n 2-step defenders
            round(st.mean([len(attackers[y]) for y in ina]), 3) if ina else 0.0,  # mean attacker in-degree
        ]
    return feats


FEATNAMES = ["n_args", "n_atts", "att_density", "in_deg", "out_deg", "is_unattacked",
             "self_attack", "n_unatt_attackers", "has_unatt_attacker", "frac_att_unatt",
             "scc_size", "in_cycle", "reachable_from_unatt", "n_defenders", "mean_attacker_indeg"]


def acceptance(exts, args):
    """credulous (union) and skeptical (intersection) in-sets; None if undefined."""
    if not exts:
        return set(), None       # credulous empty; skeptical undefined (no extension)
    cred = set().union(*exts)
    skep = set(exts[0])
    for e in exts[1:]:
        skep &= e
    return cred, skep


# ---- build the dataset: per-argument feature rows + targets, grouped by framework
print("computing features + oracle acceptance over", len(POOL), "frameworks ...")
rows_X, rows_group = [], []
targets = defaultdict(list)   # target_name -> list aligned with rows_X (label or None)
t0 = time.time()
for gi, path in enumerate(POOL):
    args, atts = parse_aaf(path)
    feats = features(args, atts)
    acc = {}
    for sem in ["STB", "ADM", "CMP", "PRF"]:
        exts = extensions(open(path).read(), sem)
        acc[sem] = acceptance(exts, args)
    for x in args:
        rows_X.append(feats[x]); rows_group.append(gi)
        cred_STB, skep_STB = acc["STB"]
        cred_ADMfam, _ = acc["ADM"]            # credulous adm = cmp = prf
        _, skep_PRF = acc["PRF"]
        _, skep_CMP = acc["CMP"]               # skeptical complete = grounded
        targets["cred_STB"].append(1 if x in cred_STB else 0)
        targets["skep_STB"].append((1 if x in skep_STB else 0) if skep_STB is not None else None)
        targets["cred_ADMfam"].append(1 if x in cred_ADMfam else 0)
        targets["skep_PRF"].append((1 if x in skep_PRF else 0) if skep_PRF is not None else None)
        targets["skep_CMP"].append((1 if x in skep_CMP else 0) if skep_CMP is not None else None)
    if (gi + 1) % 100 == 0:
        print(f"  {gi+1}/{len(POOL)}  ({time.time()-t0:.0f}s)")
X = np.array(rows_X, dtype=float); groups = np.array(rows_group)
print(f"dataset: {len(X)} argument rows from {len(POOL)} frameworks, {X.shape[1]} features, {time.time()-t0:.0f}s")


def flip(y, q, rng):
    if q <= 0:
        return y
    mask = rng.random(len(y)) < q
    return np.where(mask, 1 - y, y)


def evaluate(target_name):
    y_all = np.array([v if v is not None else -1 for v in targets[target_name]])
    keep = y_all >= 0                     # drop rows where target is undefined
    Xk, yk, gk = X[keep], y_all[keep], groups[keep]
    base_rate = float(yk.mean())
    n_kept, n_frames = len(yk), len(set(gk.tolist()))
    gkf = GroupKFold(n_splits=N_FOLDS)
    out = {"target": target_name, "n_rows": n_kept, "n_frameworks": n_frames,
           "base_rate_accepted": round(base_rate, 4), "by_noise": {}}
    fi_accum = np.zeros(X.shape[1])
    exported = False
    MODELS = ["tree", "tree_deep", "rf", "logreg", "majority"]
    for q in NOISES:
        per = {m: defaultdict(list) for m in MODELS}
        per.update({"tree_depth": [], "tree_leaves": [], "train_time_s": []})
        for fold, (tr, te) in enumerate(gkf.split(Xk, yk, gk)):
            rng = np.random.default_rng(SEED + fold + int(q * 100))
            ytr = flip(yk[tr], q, rng)
            # (1) interpretable decision tree (depth 6)
            t1 = time.time()
            dt = DecisionTreeClassifier(max_depth=6, min_samples_leaf=20,
                                        class_weight="balanced", random_state=SEED)
            dt.fit(Xk[tr], ytr)
            per["train_time_s"].append(time.time() - t1)
            for metr, val in metrics(yk[te], dt.predict(Xk[te])).items():
                per["tree"][metr].append(val)
            per["tree_depth"].append(int(dt.get_depth())); per["tree_leaves"].append(int(dt.get_n_leaves()))
            fi_accum += dt.feature_importances_
            # (2) deeper tree (fair-strength, less interpretable)
            dtd = DecisionTreeClassifier(max_depth=12, min_samples_leaf=5,
                                         class_weight="balanced", random_state=SEED)
            dtd.fit(Xk[tr], ytr)
            for metr, val in metrics(yk[te], dtd.predict(Xk[te])).items():
                per["tree_deep"][metr].append(val)
            # (3) random forest (strongest typical feature learner)
            rf = RandomForestClassifier(n_estimators=200, max_depth=None, min_samples_leaf=3,
                                        class_weight="balanced", random_state=SEED, n_jobs=-1)
            rf.fit(Xk[tr], ytr)
            for metr, val in metrics(yk[te], rf.predict(Xk[te])).items():
                per["rf"][metr].append(val)
            # (4) logistic regression (linear reference)
            lr = LogisticRegression(max_iter=500, class_weight="balanced")
            try:
                lr.fit(Xk[tr], ytr); lp = lr.predict(Xk[te])
            except Exception:
                lp = np.zeros_like(yk[te])
            for metr, val in metrics(yk[te], lp).items():
                per["logreg"][metr].append(val)
            # (5) majority-class floor
            maj = int(round(ytr.mean()))
            for metr, val in metrics(yk[te], np.full_like(yk[te], maj)).items():
                per["majority"][metr].append(val)
            # export one representative tree (clean, fold 0)
            if q == 0.0 and fold == 0 and not exported:
                with open(os.path.join(OUT, "trees", f"{target_name}.txt"), "w") as fh:
                    fh.write(f"# Decision tree for {target_name} (clean, fold 0)\n")
                    fh.write(f"# base rate accepted = {base_rate:.3f}\n\n")
                    fh.write(export_text(dt, feature_names=FEATNAMES))
                exported = True
        out["by_noise"][str(q)] = {
            model: {metr: [round(np.mean(v), 4), round(np.std(v), 4)] for metr, v in per[model].items()}
            for model in MODELS}
        out["by_noise"][str(q)]["tree_depth_mean"] = round(np.mean(per["tree_depth"]), 1)
        out["by_noise"][str(q)]["tree_leaves_mean"] = round(np.mean(per["tree_leaves"]), 1)
        out["by_noise"][str(q)]["train_time_s_mean"] = round(np.mean(per["train_time_s"]), 3)
    out["feature_importance"] = {FEATNAMES[i]: round(float(fi_accum[i] / (N_FOLDS * len(NOISES))), 4)
                                 for i in range(X.shape[1])}
    return out


def metrics(y_true, y_pred):
    p, r, f, _ = precision_recall_fscore_support(y_true, y_pred, average="binary",
                                                 zero_division=0, labels=[0, 1])
    return {"acc": accuracy_score(y_true, y_pred),
            "mcc": matthews_corrcoef(y_true, y_pred) if len(set(y_true)) > 1 else 0.0,
            "precision": p, "recall": r, "f1": f}


TASKS = ["cred_STB", "skep_STB", "cred_ADMfam", "skep_PRF", "skep_CMP"]
results = {"config": {"pool": len(POOL), "arg_rows": int(len(X)), "features": FEATNAMES,
                      "noises": NOISES, "n_folds": N_FOLDS, "seed": SEED,
                      "tree_params": "max_depth=6,min_samples_leaf=20,class_weight=balanced"},
           "tasks": {}}
for tname in TASKS:
    print("evaluating", tname, "...")
    results["tasks"][tname] = evaluate(tname)

json.dump(results, open(os.path.join(OUT, "results.json"), "w"), indent=1)
json.dump({t: results["tasks"][t]["feature_importance"] for t in TASKS},
          open(os.path.join(OUT, "feature_importances.json"), "w"), indent=1)

# ---- readable summary
with open(os.path.join(OUT, "summary.md"), "w") as fh:
    fh.write("# Decision-tree acceptability baseline (per-argument task)\n\n")
    fh.write(f"Pool: {len(POOL)} AAFs, {len(X)} argument rows, grouped {N_FOLDS}-fold CV. "
             "Tree = CART (max_depth 6). Metric MCC (mean over folds). Noise q flips training "
             "labels; test on clean oracle.\n\n")
    fh.write("| target | base rate | model | q=0 MCC | q=0.1 MCC | q=0.2 MCC | (q=0 acc) |\n")
    fh.write("|---|---|---|---|---|---|---|\n")
    for t in TASKS:
        r = results["tasks"][t]
        for model in ("tree", "tree_deep", "rf", "logreg", "majority"):
            row = [f"{r['by_noise'][str(q)][model]['mcc'][0]:.3f}" for q in NOISES]
            acc0 = f"{r['by_noise']['0.0'][model]['acc'][0]:.3f}"
            fh.write(f"| {t if model=='tree' else ''} | {r['base_rate_accepted'] if model=='tree' else ''} "
                     f"| {model} | {row[0]} | {row[1]} | {row[2]} | {acc0} |\n")
    fh.write("\n_Best feature learner per target (q=0 MCC): "
             + "; ".join(f"{t} {max(('tree_deep','rf','logreg'), key=lambda m: results['tasks'][t]['by_noise']['0.0'][m]['mcc'][0])}="
                         f"{max(results['tasks'][t]['by_noise']['0.0'][m]['mcc'][0] for m in ('tree_deep','rf','logreg')):.3f}"
                         for t in TASKS) + "._\n")
    fh.write("\n## Interpretation\n")
    fh.write("- The tree solves per-argument credulous/skeptical acceptance (the AGNN task), NOT the "
             "labelling-level extension-membership task LAS solves; it cannot represent the set of extensions.\n")
    fh.write("- LAS recovers the exact semantics on clean data (Thm 1 + the recovery surface), so its "
             "argument-level acceptance is ~1.0 by construction — the gap to the tree's MCC is the baseline's cost.\n")
print("\nDONE. Wrote results.json, feature_importances.json, summary.md, trees/ to", OUT)
