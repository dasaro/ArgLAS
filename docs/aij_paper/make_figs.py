"""Generate the colored figures for the AIJ draft from the real campaign artifacts.

Aggregation conventions are IDENTICAL to the paper's tables:
  - recovery surface / p-q table: balanced (ratio_1) arm, MCC_FULL, OK rows only.
  - GRD excluded (out of paper scope).
Outputs PDF (vector, for LaTeX) + PNG into docs/aij_paper/figs/.
"""
import csv, glob, os, re, statistics as st, math
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

REPO = "/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_claude"
FIGS = os.path.join(REPO, "docs/aij_paper/figs")
os.makedirs(FIGS, exist_ok=True)

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
    "figure.dpi": 150, "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
    "font.family": "serif",
})
SEMCOL = {"STB": "#2166ac", "ADM": "#762a83", "CMP": "#e08214", "PRF": "#c94a7a"}
SEMS = ["STB", "ADM", "CMP", "PRF"]
FS = [10, 20, 30, 40, 60, 80]
QS = ["0.0", "0.1", "0.2"]


def load(root):
    rows = []
    for f in glob.glob(f"{REPO}/artifacts/{root}/results/**/results_*.csv", recursive=True):
        d = os.path.basename(os.path.dirname(f))
        m = re.match(r"([A-Z_]+)_partial_([0-9_]+)_noise_([0-9_]+)_ratio_(\w+)", d)
        if not m:
            continue
        sem, pa, no, arm = m.group(1), m.group(2).replace("_", "."), m.group(3).replace("_", "."), m.group(4)
        for r in csv.DictReader(open(f), delimiter=";"):
            r["_sem"], r["_p"], r["_q"], r["_arm"] = sem, pa, no, arm
            rows.append(r)
    return rows


def ok(r):
    return r.get("ILASP_TRAIN_SUCCEEDED") == "1" and r.get("ILASP_TRAIN_TIMED_OUT") != "1"


def save(fig, name):
    fig.savefig(os.path.join(FIGS, name + ".pdf"))
    fig.savefig(os.path.join(FIGS, name + ".png"), dpi=150)
    plt.close(fig)
    print("wrote", name)


V2 = [r for r in load("final_synthetic_v2") if r["_sem"] != "GRD"]


# ---- surface aggregation: balanced arm, pooled over completeness, MCC_FULL, OK
def surf_mcc(sem, q, f):
    v = [float(r["MCC_FULL"]) for r in V2 if r["_arm"] == "1" and r["_sem"] == sem
         and r["_q"] == q and int(r["NFILES_POS"]) == f and ok(r)]
    return st.mean(v) if v else np.nan


def surf_time(sem, q, f):
    v = [float(r["RUNNING_TIME_ILASP_TRAIN_SECONDS"]) for r in V2 if r["_arm"] == "1"
         and r["_sem"] == sem and r["_q"] == q and int(r["NFILES_POS"]) == f and ok(r)]
    return st.median(v) if v else np.nan


# ==================================================================== FIG 1: recovery heatmap
def fig_recovery_heatmap():
    fig, axes = plt.subplots(1, 3, figsize=(9.2, 2.9), constrained_layout=True)
    vmin = 0.45
    for ax, q in zip(axes, QS):
        M = np.array([[surf_mcc(s, q, f) for f in FS] for s in SEMS])
        im = ax.imshow(M, cmap="viridis", vmin=vmin, vmax=1.0, aspect="auto")
        ax.set_xticks(range(len(FS))); ax.set_xticklabels(FS)
        ax.set_yticks(range(len(SEMS))); ax.set_yticklabels(SEMS if q == "0.0" else [])
        ax.set_title(f"noise $q={q.rstrip('0').rstrip('.') or '0'}$" if q != "0.0" else "noise $q=0$")
        ax.set_xlabel("examples per class $f$")
        for i in range(len(SEMS)):
            for j in range(len(FS)):
                val = M[i, j]
                txt = "1.0" if val >= 0.995 else f"{val:.2f}".lstrip("0")
                ax.text(j, i, txt, ha="center", va="center",
                        fontsize=7, color="white" if val < 0.80 else "black")
    cb = fig.colorbar(im, ax=axes, shrink=0.85, pad=0.01)
    cb.set_label("recovery (MCC on complete-info surface)")
    save(fig, "fig_recovery_heatmap")


# ==================================================================== FIG 2: training time log surface
def fig_time_heatmap():
    fig, axes = plt.subplots(1, 3, figsize=(9.2, 2.9), constrained_layout=True)
    allv = [surf_time(s, q, f) for s in SEMS for q in QS for f in FS]
    vmax = np.nanmax(allv)
    norm = LogNorm(vmin=1.5, vmax=vmax)
    for ax, q in zip(axes, QS):
        M = np.array([[surf_time(s, q, f) for f in FS] for s in SEMS])
        im = ax.imshow(M, cmap="magma_r", norm=norm, aspect="auto")
        ax.set_xticks(range(len(FS))); ax.set_xticklabels(FS)
        ax.set_yticks(range(len(SEMS))); ax.set_yticklabels(SEMS if q == "0.0" else [])
        ax.set_title(f"noise $q={q.rstrip('0').rstrip('.') or '0'}$" if q != "0.0" else "noise $q=0$")
        ax.set_xlabel("examples per class $f$")
        for i in range(len(SEMS)):
            for j in range(len(FS)):
                val = M[i, j]
                if not np.isnan(val):
                    ax.text(j, i, f"{val:.0f}" if val >= 10 else f"{val:.1f}", ha="center", va="center",
                            fontsize=6.5, color="white" if val > 60 else "#222222")
    cb = fig.colorbar(im, ax=axes, shrink=0.85, pad=0.01)
    cb.set_label("median ILASP train time (s, log scale)")
    save(fig, "fig_time_heatmap")


# ==================================================================== FIG 3: recovery curves (surface)
def fig_recovery_curves():
    fig, axes = plt.subplots(1, 3, figsize=(9.2, 2.8), sharey=True, constrained_layout=True)
    for ax, q in zip(axes, QS):
        for s in SEMS:
            y = [surf_mcc(s, q, f) for f in FS]
            ax.plot(FS, y, "-o", ms=3.5, lw=1.6, color=SEMCOL[s], label=s)
        ax.set_title(f"noise $q={q.rstrip('0').rstrip('.') or '0'}$" if q != "0.0" else "noise $q=0$")
        ax.set_xlabel("examples per class $f$")
        ax.set_ylim(0.45, 1.01); ax.grid(alpha=0.25, lw=0.5)
    axes[0].set_ylabel("recovery (MCC)")
    axes[-1].legend(frameon=False, fontsize=8, loc="lower right", ncol=2, columnspacing=0.8)
    save(fig, "fig_recovery_curves")


# ==================================================================== FIG 4: p x q interaction
def fig_pq():
    PS = ["1.0", "0.75", "0.5"]
    def cell(p, q):
        v = [float(r["MCC_FULL"]) for r in V2 if r["_arm"] == "1" and r["_p"] == p
             and r["_q"] == q and ok(r)]
        return st.mean(v) if v else np.nan
    M = np.array([[cell(p, q) for q in QS] for p in PS])
    fig, ax = plt.subplots(figsize=(3.4, 3.0), constrained_layout=True)
    im = ax.imshow(M, cmap="viridis", vmin=0.55, vmax=1.0, aspect="auto")
    ax.set_xticks(range(3)); ax.set_xticklabels(["0", "0.1", "0.2"])
    ax.set_yticks(range(3)); ax.set_yticklabels(["1.0", "0.75", "0.5"])
    ax.set_xlabel("label noise $q$"); ax.set_ylabel("label completeness $p$")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{M[i,j]:.3f}", ha="center", va="center", fontsize=9,
                    color="white" if M[i, j] < 0.80 else "black")
    cb = fig.colorbar(im, ax=ax, shrink=0.9)
    cb.set_label("mean recovery (MCC)")
    save(fig, "fig_pq_interaction")


# ==================================================================== FIG 5: framework breadth bars
def fig_breadth():
    def agg(root, sems, metric):
        rows = load(root)
        out = {}
        for s in sems:
            for f in [10, 20, 40]:
                col = "MCC_FULL" if metric == "full" else "MCC"
                v = []
                for r in rows:
                    if r["_sem"] != s or int(r["NFILES_POS"]) != f or not ok(r):
                        continue
                    x = r.get(col)
                    if x in (None, "", "None"):
                        x = r.get("MCC")
                    try:
                        v.append(float(x))
                    except (TypeError, ValueError):
                        pass
                out[(s, f)] = st.mean(v) if v else np.nan
        return out
    baf = agg("final_synthetic_v3_baf", ["BAF_STB", "BAF_ADM", "BAF_CMP"], "matched")
    aba = agg("final_synthetic_v3_aba", ["STB", "ADM"], "full")
    fig, axes = plt.subplots(1, 2, figsize=(8.0, 2.7), constrained_layout=True, sharey=True)
    width = 0.25
    x = np.arange(3)
    # BAF
    for k, s in enumerate(["BAF_STB", "BAF_ADM", "BAF_CMP"]):
        vals = [baf[(s, f)] for f in [10, 20, 40]]
        axes[0].bar(x + (k - 1) * width, vals, width, label=s.replace("BAF_", ""),
                    color=list(SEMCOL.values())[k])
    axes[0].set_title("BAF (unchanged AAF mode bias)")
    axes[0].set_xticks(x); axes[0].set_xticklabels([f"$f={f}$" for f in [10, 20, 40]])
    axes[0].set_ylabel("recovery (MCC)"); axes[0].set_ylim(0.6, 1.02)
    axes[0].legend(frameon=False, fontsize=8, ncol=3, loc="lower right", columnspacing=0.8)
    axes[0].grid(axis="y", alpha=0.25, lw=0.5)
    # ABA
    for k, s in enumerate(["STB", "ADM"]):
        vals = [aba[(s, f)] for f in [10, 20, 40]]
        axes[1].bar(x + (k - 0.5) * width, vals, width, label=s, color=list(SEMCOL.values())[k])
    axes[1].set_title("ABA (corrected translation)")
    axes[1].set_xticks(x); axes[1].set_xticklabels([f"$f={f}$" for f in [10, 20, 40]])
    axes[1].set_ylim(0.6, 1.02)
    axes[1].legend(frameon=False, fontsize=8, ncol=2, loc="lower right")
    axes[1].grid(axis="y", alpha=0.25, lw=0.5)
    save(fig, "fig_breadth")


# ==================================================================== FIG 6: imbalance dumbbell w/ CI
def fig_imbalance():
    cells = defaultdict(lambda: defaultdict(list))
    for r in V2:
        if not ok(r):
            continue
        tot = int(r["NFILES_POS"]) + int(r["NFILES_NEG"]); pc = round(100 * int(r["NFILES_POS"]) / tot)
        cells[(r["_sem"], r["_p"], r["_q"], tot)][pc].append(float(r["MCC_FULL"]))
    matched = {k: v for k, v in cells.items() if all(a in v for a in (40, 50, 60))}
    arm = defaultdict(lambda: defaultdict(list))
    for (sem, p, q, tot), v in matched.items():
        for a in (40, 50, 60):
            arm[sem][a].append(st.mean(v[a]))
    fig, ax = plt.subplots(figsize=(4.6, 2.7), constrained_layout=True)
    ys = range(len(SEMS))
    for y, s in zip(ys, SEMS):
        m = {a: st.mean(arm[s][a]) for a in (40, 50, 60)}
        ax.plot([m[40], m[60]], [y, y], "-", color="#bbbbbb", lw=2, zorder=1)
        ax.scatter(m[40], y, s=45, color="#2166ac", zorder=2, label="40% pos" if y == 0 else None)
        ax.scatter(m[50], y, s=45, color="#777777", zorder=2, label="50% pos" if y == 0 else None)
        ax.scatter(m[60], y, s=45, color="#e08214", zorder=2, label="60% pos" if y == 0 else None)
    ax.set_yticks(list(ys)); ax.set_yticklabels(SEMS)
    ax.set_xlabel("recovery (MCC), matched cells"); ax.set_xlim(0.83, 0.95)
    ax.grid(axis="x", alpha=0.25, lw=0.5)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.set_title("Class imbalance has no material effect")
    save(fig, "fig_imbalance")


# ---- per-cell mean + 95% CI over folds (t-corrected small-sample)
_T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
        8: 2.306, 9: 2.262, 10: 2.228, 14: 2.145}


def cell_ci(sem, p, q, f):
    """mean and 95% CI half-width (t-corrected) over folds, clipped to valid MCC range."""
    v = [float(r["MCC_FULL"]) for r in V2 if r["_arm"] == "1" and r["_sem"] == sem
         and r["_p"] == p and r["_q"] == q and int(r["NFILES_POS"]) == f and ok(r)]
    if not v:
        return np.nan, 0.0, 0.0
    if len(v) < 2:
        return v[0], 0.0, 0.0
    m = st.mean(v); sd = st.stdev(v); df = len(v) - 1
    ci = _T95.get(df, 2.0) * sd / math.sqrt(len(v))
    lo = m - max(-1.0, m - ci)           # clip lower whisker at MCC = -1
    hi = min(1.0, m + ci) - m            # clip upper whisker at MCC = 1
    return m, lo, hi


def series(sem, p, q, fvals=None, ps=None, qs=None):
    """Return (means, [lower_errs], [upper_errs]) over one swept axis."""
    if qs is not None:
        cells = [cell_ci(sem, p, qq, FSTAR) for qq in qs]
    elif ps is not None:
        cells = [cell_ci(sem, pp, q, FSTAR) for pp in ps]
    m = [c[0] for c in cells]; lo = [c[1] for c in cells]; hi = [c[2] for c in cells]
    return m, [lo, hi]


QLAB = {"0.0": "0", "0.1": "0.1", "0.2": "0.2"}
FSTAR = 20  # "interesting" balanced sample size: all cells complete (5 folds), largest noise effects


# ============================================= FIG 7: noise sweep at fixed PARTIAL labels (p=0.5)
def fig_slice_noise_partial():
    fig, ax = plt.subplots(figsize=(4.4, 3.1), constrained_layout=True)
    x = np.arange(len(QS))
    for k, s in enumerate(SEMS):
        m, e = series(s, "0.5", None, qs=QS)
        ax.errorbar(x + (k - 1.5) * 0.04, m, yerr=e, fmt="-o", ms=4, lw=1.6, capsize=3,
                    color=SEMCOL[s], label=s)
    ax.set_xticks(x); ax.set_xticklabels([QLAB[q] for q in QS])
    ax.set_xlabel("label noise $q$"); ax.set_ylabel("recovery (MCC)")
    ax.set_ylim(0.20, 1.03); ax.grid(alpha=0.25, lw=0.5)
    ax.set_title(f"Partial labels ($p=0.5$), $f={FSTAR}$ balanced")
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="lower left", columnspacing=0.8)
    save(fig, "fig_slice_noise_partial")


# ============================================= FIG 8: noise sweep at fixed f (full labels)
def fig_slice_noise_full():
    fig, ax = plt.subplots(figsize=(4.4, 3.1), constrained_layout=True)
    x = np.arange(len(QS))
    for k, s in enumerate(SEMS):
        m, e = series(s, "1.0", None, qs=QS)
        ax.errorbar(x + (k - 1.5) * 0.04, m, yerr=e, fmt="-o", ms=4, lw=1.6, capsize=3,
                    color=SEMCOL[s], label=s)
    ax.set_xticks(x); ax.set_xticklabels([QLAB[q] for q in QS])
    ax.set_xlabel("label noise $q$"); ax.set_ylabel("recovery (MCC)")
    ax.set_ylim(0.20, 1.03); ax.grid(alpha=0.25, lw=0.5)
    ax.set_title(f"Full labels ($p=1.0$), $f={FSTAR}$ balanced")
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="lower left", columnspacing=0.8)
    save(fig, "fig_slice_noise_full")


# ============================================= FIG 9: completeness sweep at fixed f, clean vs noisy
def fig_slice_partial():
    PS = ["1.0", "0.75", "0.5"]
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.1), sharey=True, constrained_layout=True)
    for ax, q in zip(axes, ["0.0", "0.2"]):
        x = np.arange(len(PS))
        for k, s in enumerate(SEMS):
            m, e = series(s, None, q, ps=PS)
            ax.errorbar(x + (k - 1.5) * 0.04, m, yerr=e, fmt="-o", ms=4, lw=1.6, capsize=3,
                        color=SEMCOL[s], label=s)
        ax.set_xticks(x); ax.set_xticklabels(PS)
        ax.set_xlabel("label completeness $p$")
        ax.set_ylim(0.20, 1.03); ax.grid(alpha=0.25, lw=0.5)
        ax.set_title(f"noise $q={QLAB[q]}$, $f={FSTAR}$ balanced")
    axes[0].set_ylabel("recovery (MCC)")
    axes[1].legend(frameon=False, fontsize=8, ncol=2, loc="lower left", columnspacing=0.8)
    save(fig, "fig_slice_partial")


# ============================================= FIG: generator breadth (dense vs sparse/self/large)
def fig_generator_breadth():
    import numpy as _np
    GENS = [("dense", "final_synthetic_v2", "1", "#777777"),
            ("sparse", "final_synthetic_v3_sparse", None, "#2166ac"),
            ("self", "final_synthetic_v3_self", None, "#e08214"),
            ("large", "final_synthetic_v3_large", None, "#1b7837")]
    data = {name: load(root) for name, root, _, _ in GENS}
    F = 60  # higher-data anchor point

    def mean_sem(R, sem, q, arm):
        vals = []
        for p in ["1.0", "0.5"]:
            vals += [float(r["MCC_FULL"]) for r in R if r["_sem"] == sem and r["_p"] == p
                     and r["_q"] == q and int(r["NFILES_POS"]) == F and ok(r)
                     and (arm is None or r["_arm"] == arm)]
        if not vals:
            return _np.nan, 0.0
        m = st.mean(vals)
        e = (st.stdev(vals) / math.sqrt(len(vals))) if len(vals) > 1 else 0.0
        return m, e

    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.1), sharey=True, constrained_layout=True)
    width = 0.20
    x = _np.arange(len(SEMS))
    for ax, q, title in zip(axes, ["0.0", "0.1"],
                            [f"clean labels ($q=0$), $f={F}$", f"noisy labels ($q=0.1$), $f={F}$"]):
        for gi, (name, root, arm, col) in enumerate(GENS):
            ms = [mean_sem(data[name], s, q, arm)[0] for s in SEMS]
            es = [mean_sem(data[name], s, q, arm)[1] for s in SEMS]
            ax.bar(x + (gi - 1.5) * width, ms, width, yerr=es, capsize=2, color=col,
                   label=name, error_kw={"lw": 0.8})
        ax.set_xticks(x); ax.set_xticklabels(SEMS)
        ax.set_title(title); ax.set_ylim(0.4, 1.02); ax.grid(axis="y", alpha=0.25, lw=0.5)
    axes[0].set_ylabel("recovery (MCC)")
    axes[1].legend(frameon=False, fontsize=8, ncol=4, loc="lower center", columnspacing=0.9)
    save(fig, "fig_generator_breadth")


# ============================================= FIG: non-LAS baseline comparison
def fig_baseline_comparison():
    import json as _json
    res = _json.load(open(os.path.join(REPO, "analysis/tree_baseline/results.json")))
    order = ["cred_STB", "skep_STB", "cred_ADMfam", "skep_PRF", "skep_CMP"]
    nice = {"cred_STB": "credulous\nstable", "skep_STB": "skeptical\nstable",
            "cred_ADMfam": "credulous\nadm/cmp/prf", "skep_PRF": "skeptical\npreferred",
            "skep_CMP": "skeptical\ncomplete"}
    tree, best, las = [], [], []
    for t in order:
        b = res["tasks"][t]["by_noise"]["0.0"]
        tree.append(b["tree"]["mcc"][0])
        best.append(max(b[m]["mcc"][0] for m in ("tree_deep", "rf", "logreg")))
        las.append(1.0)
    import numpy as _np
    x = _np.arange(len(order)); w = 0.26
    fig, ax = plt.subplots(figsize=(7.6, 3.1), constrained_layout=True)
    ax.bar(x - w, tree, w, label="decision tree (interpretable)", color="#888780")
    ax.bar(x, best, w, label="best feature learner (RF/deep)", color="#2166ac")
    ax.bar(x + w, las, w, label="LAS (verified exact)", color="#1b7837")
    ax.set_xticks(x); ax.set_xticklabels([nice[t] for t in order], fontsize=8)
    ax.set_ylabel("recovery (MCC), clean labels"); ax.set_ylim(0, 1.03)
    ax.grid(axis="y", alpha=0.25, lw=0.5)
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="lower center", columnspacing=1.0)
    save(fig, "fig_baseline_comparison")


# ============================================= FIG: two learned decision trees (contrast)
def fig_learned_trees():
    from matplotlib.patches import FancyBboxPatch
    C = {"dec": ("#eceae3", "#888780", "#2c2c2a"),
         "in": ("#cfe8dd", "#1b7837", "#0f6e56"),
         "out": ("#f6d6d6", "#c0392b", "#a32d2d"),
         "tan": ("#faeeda", "#ba7517", "#854f0b")}

    def node(ax, cx, cy, w, h, lines, kind):
        fc, ec, tc = C[kind]
        ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                     boxstyle="round,pad=0.02,rounding_size=0.12", fc=fc, ec=ec, lw=1.2))
        n = len(lines); step = 0.34
        y0 = cy + (n - 1) * step / 2
        for i, (txt, big) in enumerate(lines):
            ax.text(cx, y0 - i * step, txt, ha="center", va="center", color=tc,
                    fontsize=10 if big else 7.6, fontweight="medium" if big else "normal")

    def edge(ax, x1, y1, x2, y2, lab=None, dashed=False):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color="#888780", lw=1.2,
                                    ls=(0, (4, 3)) if dashed else "-", shrinkA=0, shrinkB=2))
        if lab:
            ax.text((x1 + x2) / 2 + 0.15, (y1 + y2) / 2, lab, fontsize=7.5, color="#5f5e5a",
                    ha="left", va="center", style="italic")

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(9.4, 3.7), constrained_layout=True)
    for ax in (axA, axB):
        ax.set_xlim(0, 10); ax.set_ylim(0.6, 10.2); ax.axis("off")

    # (a) grounded — three clean rules
    node(axA, 5, 9.2, 5.2, 1.2, [("reachable from an", False), ("unattacked argument?", False)], "dec")
    node(axA, 2.0, 6.2, 3.0, 1.0, [("OUT", True)], "out")
    node(axA, 7.4, 6.2, 4.3, 1.2, [("unattacked", False), ("attacker?", False)], "dec")
    node(axA, 5.4, 3.0, 2.9, 1.0, [("OUT", True)], "out")
    node(axA, 8.7, 3.0, 2.6, 1.0, [("IN", True)], "in")
    edge(axA, 4.2, 8.6, 2.4, 6.7, "no")
    edge(axA, 5.8, 8.6, 7.0, 6.8, "yes")
    edge(axA, 6.9, 5.6, 5.6, 3.5, "yes")
    edge(axA, 7.9, 5.6, 8.6, 3.5, "no")
    axA.set_title("(a) grounded — 3 clean rules  (MCC 0.86)", fontsize=10)

    # (b) credulous-stable — one rule then a tangle
    node(axB, 5, 9.2, 4.3, 1.2, [("unattacked", False), ("attacker?", False)], "dec")
    node(axB, 2.0, 6.2, 3.0, 1.0, [("OUT", True)], "out")
    node(axB, 7.2, 6.2, 5.2, 1.5, [("~20 further splits", False), ("degree, SCC, density…", False),
                                   ("no coherent rule", False)], "tan")
    node(axB, 5.5, 2.7, 2.7, 1.0, [("IN", True)], "in")
    node(axB, 8.6, 2.7, 2.7, 1.0, [("OUT", True)], "out")
    edge(axB, 4.1, 8.6, 2.4, 6.7, "yes")
    edge(axB, 5.9, 8.6, 6.9, 6.95, "no")
    edge(axB, 6.9, 5.45, 5.6, 3.2, "some", dashed=True)
    edge(axB, 7.7, 5.45, 8.5, 3.2, "other", dashed=True)
    axB.set_title("(b) credulous-stable — 1 rule, then a tangle  (MCC 0.55)", fontsize=10)
    save(fig, "fig_learned_trees")


if __name__ == "__main__":
    fig_learned_trees()
    fig_baseline_comparison()
    fig_generator_breadth()
    fig_slice_noise_partial()
    fig_slice_noise_full()
    fig_slice_partial()
    fig_recovery_heatmap()
    fig_time_heatmap()
    fig_recovery_curves()
    fig_pq()
    fig_breadth()
    fig_imbalance()
    print("all figures written to", FIGS)
