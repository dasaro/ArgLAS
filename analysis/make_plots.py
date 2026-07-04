#!/usr/bin/env python3
"""Illustrative figures for the ArgLAS Exp1+Exp2 results. Outputs PNG+PDF to analysis/figs/."""
import json, os
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIGS = os.path.join(REPO, "analysis", "figs")
os.makedirs(FIGS, exist_ok=True)
EXP2 = os.path.join(REPO, "Real_World_Examples", "fastlas_exp", "results")

plt.rcParams.update({
    "font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 130, "savefig.bbox": "tight",
})
BLUE, ORANGE, GREEN, RED, GREY, PURPLE = "#2166ac", "#e08214", "#1b7837", "#b2182b", "#777777", "#762a83"


def save(fig, name):
    fig.savefig(os.path.join(FIGS, name + ".png"))
    fig.savefig(os.path.join(FIGS, name + ".pdf"))
    plt.close(fig)
    print("wrote", name)


# ---------------------------------------------------------------- fig 1: Exp1 two surfaces
rows = json.load(open(os.path.join(REPO, "analysis", "exp1_complete_info_rescore.json")))["rows"]
P = {"full": 1.0, "partial_0.75": 0.75, "partial_0.5": 0.5}

def mean_mcc(sem, ptok, q, surf):
    xs = [r[surf]["MCC"] for r in rows if r["sem"] == sem and r["ptok"] == ptok and r["noise"] == q]
    return sum(xs) / len(xs)

from matplotlib.lines import Line2D
fig, axes = plt.subplots(1, 3, figsize=(9.8, 3.4), sharey=True)
ps = [1.0, 0.75, 0.5]
ptoks = ["full", "partial_0.75", "partial_0.5"]
qc = {0.0: GREEN, 0.1: ORANGE, 0.2: RED}
for ax, sem in zip(axes, ("ADM", "CMP", "STB")):
    for q in (0.0, 0.1, 0.2):
        comp = [mean_mcc(sem, pt, q, "complete") for pt in ptoks]
        mat = [mean_mcc(sem, pt, q, "matched") for pt in ptoks]
        ax.fill_between(ps, mat, comp, color=qc[q], alpha=0.10, lw=0)   # shade the test-protocol gap
        ax.plot(ps, comp, "-o", color=qc[q], lw=2.0, ms=4)              # solid = true recovery
        ax.plot(ps, mat, ":s", color=qc[q], lw=1.3, ms=3.5, alpha=0.75, mfc="white")  # dotted = as reported
    ax.set_title(sem)
    ax.set_xticks(ps); ax.set_xticklabels(["1.0\n(full)", "0.75", "0.5"])
    ax.invert_xaxis(); ax.set_ylim(0, 1.02)
axes[0].set_ylabel("mean MCC (recovery)")
fig.text(0.5, -0.055, "fraction of labels shown ($p$)", ha="center", fontsize=10)
# annotate the gap once, on the CMP panel where it is largest
axes[1].annotate("gap = test-protocol\nhandicap (not a\nlearning loss)", xy=(0.5, 0.34), xytext=(0.62, 0.14),
                 fontsize=7.5, color=GREY, ha="center",
                 arrowprops=dict(arrowstyle="->", color=GREY, lw=0.8))
# TWO separate legends: colour = noise, line style = which test set
col_leg = [Line2D([], [], color=qc[q], lw=2.4, label=f"noise $q={q}$") for q in (0.0, 0.1, 0.2)]
sty_leg = [Line2D([], [], color="black", lw=2.0, ls="-", marker="o", ms=4,
                  label="graded on FULLY-labelled test cases  (true recovery)"),
           Line2D([], [], color="black", lw=1.3, ls=":", marker="s", ms=3.5, mfc="white",
                  label="graded on PARTIALLY-labelled test cases  (as originally reported)")]
leg1 = fig.legend(handles=col_leg, loc="lower center", ncol=3, frameon=False,
                  bbox_to_anchor=(0.5, -0.13), fontsize=8.5)
fig.legend(handles=sty_leg, loc="lower center", ncol=1, frameon=False,
           bbox_to_anchor=(0.5, -0.29), fontsize=8.5)
fig.add_artist(leg1)
fig.suptitle("Exp1: how well the learner recovers the target semantics\n"
             "(same learned theories, scored two ways)", y=1.06, fontsize=11)
save(fig, "fig1_exp1_two_surfaces")

# ---------------------------------------------------------------- fig 2: Exp1 f-curve (p<1)
fig, ax = plt.subplots(figsize=(4.4, 3.1))
fs = [10, 20, 30, 40]
for surf, col, lab, ls in (("complete", BLUE, "fully-labelled test (true recovery)", "-"),
                           ("matched", GREY, "partially-labelled test (as reported)", "--")):
    ys = []
    for f in fs:
        xs = [r[surf]["MCC"] for r in rows if r["f"] == f and r["ptok"] != "full"]
        ys.append(sum(xs) / len(xs))
    ax.plot(fs, ys, ls + "o", color=col, lw=1.8, ms=5, label=lab)
    for x, y in zip(fs, ys):
        ax.annotate(f"{y:.2f}", (x, y), textcoords="offset points", xytext=(0, 6), fontsize=8, color=col, ha="center")
ax.set_xlabel("training examples per class (f)"); ax.set_ylabel("mean MCC (partial-info cells, p<1)")
ax.set_xticks(fs); ax.set_ylim(0.4, 1.0)
ax.set_title("Exp1: learning curve is still rising at f=40")
ax.legend(frameon=False, fontsize=8.5, loc="lower right")
save(fig, "fig2_exp1_fcurve")

# ---------------------------------------------------------------- fig 3: Exp2 unified comparison
uni = json.load(open(os.path.join(EXP2, "unified_final.json")))
arm_lab = [("cf2", "CF2"), ("preferred", "preferred"), ("stable", "stable"), ("complete", "complete"),
           ("grounded", "grounded"), ("fastlas_nopl", "FastLAS NOPL"), ("fastlas_opl", "FastLAS OPL"),
           ("ilasp_maxv1", "ILASP maxv=1")]
fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.4), sharex=True)
for ax, phase, ttl in ((axes[0], "final", "final (post-deliberation)"), (axes[1], "first", "first (initial)")):
    t = uni[phase]["table"]
    ys = range(len(arm_lab))
    vals = [t[a]["credulous"]["committed_only"] for a, _ in arm_lab]
    cols = [PURPLE if a == "cf2" else (GREY if a in ("preferred", "stable", "complete", "grounded") else BLUE)
            for a, _ in arm_lab]
    ax.barh(list(ys), vals, color=cols, height=0.62)
    for y, v in zip(ys, vals):
        ax.text(v + 0.012, y, f"{v:.2f}", va="center", fontsize=8)
    ax.set_yticks(list(ys)); ax.set_yticklabels([l for _, l in arm_lab], fontsize=9)
    ax.axvline(0.5, color=RED, lw=1, ls=":", label="coin-flip (50%)")
    ax.axvline(1 / 3, color=GREY, lw=1, ls=":", label="3-way guess (33%)")
    ax.set_xlim(0, 1.05); ax.invert_yaxis(); ax.set_title(ttl)
    ax.set_xlabel("committed-only accuracy")
axes[0].legend(frameon=False, fontsize=8, loc="lower right")
fig.suptitle("Exp2: learned semantics vs textbook (IndAF pool, n=495, leak-free)", y=1.02)
save(fig, "fig3_exp2_unified")

# ---------------------------------------------------------------- fig 4: aux predicate gains
rob = json.load(open(os.path.join(EXP2, "aux9_robustness.json")))
seeds = ["20260703", "424242", "777", "20250101"]
fig, ax = plt.subplots(figsize=(4.6, 3.2))
pairs = [(rob[s + "_base"]["committed_only"], rob[s + "_aux"]["committed_only"]) for s in seeds]
# dodge the delta labels vertically by rank of the aux endpoint so they never collide
order = sorted(range(len(pairs)), key=lambda i: pairs[i][1])
ylab = {i: min(p[1] for p in pairs) + rank * 0.022 for rank, i in enumerate(order)}
for i, (b, a) in enumerate(pairs):
    ax.plot([0, 1], [b, a], "-o", color=BLUE, lw=1.5, ms=5, alpha=0.85)
    ax.annotate(f"+{(a - b) * 100:.1f}", (1.05, ylab[i]), fontsize=8, color=BLUE, va="center")
ax.axhline(0.797, color=PURPLE, lw=1.4, ls="--")
ax.text(0.02, 0.807, "CF2 = 0.80", color=PURPLE, fontsize=8.5)
ax.axhline(0.5, color=RED, lw=1, ls=":"); ax.text(0.02, 0.508, "coin-flip", color=RED, fontsize=8)
ax.set_xticks([0, 1]); ax.set_xticklabels(["base vocabulary", "+ aux predicates\n(reinstatement + salience)"])
ax.set_xlim(-0.15, 1.35); ax.set_ylim(0.45, 0.85)
ax.set_ylabel("committed-only accuracy")
ax.set_title("Exp2: auxiliary predicates help at every fold seed")
save(fig, "fig4_exp2_aux_gains")

# ---------------------------------------------------------------- fig 5: per-condition contextual test
pc = json.load(open(os.path.join(EXP2, "per_condition_experiment.json")))["final_aux"]["conditions"]
conds = ["A", "B", "C", "D", "E", "F", "G"]
grp = {"A": "float", "B": "float", "C": "float", "D": "simple", "E": "simple", "F": "simple", "G": "cycle"}
arms = [("within", BLUE, "WITHIN (own condition)"), ("global", ORANGE, "GLOBAL (pooled)"),
        ("transfer", GREEN, "TRANSFER (other six)"), ("cf2", PURPLE, "CF2")]
fig, ax = plt.subplots(figsize=(8.2, 3.3))
w = 0.2
for k, (arm, col, lab) in enumerate(arms):
    xs = [i + (k - 1.5) * w for i in range(len(conds))]
    ys = [pc[c]["table"][arm]["credulous"]["committed_only"] for c in conds]
    ax.bar(xs, ys, width=w * 0.92, color=col, label=lab)
ax.axhline(0.5, color=RED, lw=1, ls=":")
ax.set_xticks(range(len(conds)))
ax.set_xticklabels([f"{c}\n({grp[c]})" for c in conds], fontsize=9)
ax.set_ylabel("committed-only accuracy"); ax.set_ylim(0, 1.05)
ax.set_title("Exp2: contextual-reasoning test — one pooled semantics beats seven specialised ones")
ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper right")
save(fig, "fig5_exp2_contextual")

print("all figures ->", FIGS)
