#!/usr/bin/env python3
"""Tables for the three targeted re-runs (experiments/RERUNS.md) -> rerun_tab_{baf,prf,seedb}.tex.

  data/baf_anchor      BAF x p{1,.5} x q{0,.1} x f{20,60}, 5 folds   (tab:bafanchor)
  data/self_prf_recap  PRF self-attacking pool, q=.1, cap 14,000 s    (tab:prfrecap)
  data/seedB           second master seed, vs data/exp1_v2 balanced   (tab:seedb)

Aggregation follows make_figs.py: per-cell mean of MCC_FULL over folds that completed
(timeouts excluded and counted), worst fold in parentheses.
"""
import csv, glob, os, statistics as st, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

def load(name):
    rows = []
    for f in glob.glob(f"{ROOT}/data/{name}/results/**/results_*.csv", recursive=True):
        d = os.path.basename(os.path.dirname(f))
        sem, ratio = d.split("_partial_")[0], d.split("_ratio_")[1]
        for r in csv.DictReader(open(f), delimiter=";"):
            r["SEM"], r["RATIO"] = sem, ratio
            r["TO"] = r["ILASP_TRAIN_TIMED_OUT"] == "1"
            r["KEY"] = (sem, float(r["P_PARTIAL"]), float(r["NOISE"]), int(r["NFILES_POS"]))
            rows.append(r)
    return rows

def cells(rows):
    d = defaultdict(list)
    for r in rows: d[r["KEY"]].append(r)
    return d

def stat(rs):
    ok = [float(r["MCC_FULL"]) for r in rs if not r["TO"] and r["MCC_FULL"]]
    return (st.mean(ok), min(ok), len(ok), len(rs)) if ok else (None, None, 0, len(rs))

def fmt(rs):
    m, w, n, N = stat(rs)
    if m is None: return "--"
    s = f"{m:.2f} ({w:.2f})"
    return s + (f"\\,[{n}/{N}]" if n < N else "")

out = []
files = {}
# ---------------------------------------------------------------- BAF anchor
baf = cells(load("baf_anchor"))
nto = sum(r["TO"] for rs in baf.values() for r in rs)
out.append(r"""\begin{table}[t]
\centering
\footnotesize
\setlength{\tabcolsep}{4pt}
\caption{BAF anchor under label incompleteness and noise (complete-information
MCC, mean over five folds, worst fold in parentheses; $80$ test instances per
class; the unchanged AAF mode bias over $B_{\mathrm{BAF}}$; same $500$-BAF pool
as Table~\ref{tab:breadth}). A bracket $[k/5]$ marks a cell with $k$ completions
within the $3{,}500$\,s cap; every other cell completed $5/5$ (%d of %d runs
timed out).}
\label{tab:bafanchor}
\begin{tabular}{lcccccccc}
\toprule
& \multicolumn{2}{c}{$p{=}1.0,\ q{=}0$} & \multicolumn{2}{c}{$p{=}0.5,\ q{=}0$}
& \multicolumn{2}{c}{$p{=}1.0,\ q{=}0.1$} & \multicolumn{2}{c}{$p{=}0.5,\ q{=}0.1$}\\
\cmidrule(lr){2-3}\cmidrule(lr){4-5}\cmidrule(lr){6-7}\cmidrule(lr){8-9}
BAF & $f{=}20$ & $f{=}60$ & $f{=}20$ & $f{=}60$ & $f{=}20$ & $f{=}60$ & $f{=}20$ & $f{=}60$\\
\midrule""" % (nto, sum(len(rs) for rs in baf.values())))
for sem in ["BAF_STB", "BAF_ADM", "BAF_CMP"]:
    row = [sem.replace("BAF_", "")]
    for p, q in [(1.0, 0.0), (0.5, 0.0), (1.0, 0.1), (0.5, 0.1)]:
        for f in (20, 60):
            row.append(fmt(baf[(sem, p, q, f)]))
    out.append(" & ".join(row) + r"\\")
out.append(r"\bottomrule\end{tabular}\end{table}")
files["rerun_tab_baf.tex"], out = out, []

# ---------------------------------------------------------------- PRF recap
rec, old = cells(load("self_prf_recap")), cells([r for r in load("v3_self") if r["SEM"] == "PRF"])
out.append(r"""
\begin{table}[t]
\centering
\footnotesize
\caption{Preferred on the self-attacking pool at $q{=}0.1$, re-run at four times
the training cap ($14{,}000$\,s) on the identical frameworks, seeds and ILASP
tasks as the breadth arm (\S\ref{sec:exp1breadth}). Complete-information MCC,
mean over the folds that completed (worst fold in parentheses), with
completions out of five in brackets; the last column is the mean ILASP
training time over all five folds, timed-out folds counted at the cap.}
\label{tab:prfrecap}
\begin{tabular}{llccccr}
\toprule
& & \multicolumn{2}{c}{cap $3{,}500$\,s (breadth arm)} & \multicolumn{2}{c}{cap $14{,}000$\,s (re-run)}\\
\cmidrule(lr){3-4}\cmidrule(lr){5-6}
$p$ & $f$ & MCC & compl. & MCC & compl. & mean train (s)\\
\midrule""")
for p in (1.0, 0.5):
    for f in (20, 60):
        k = ("PRF", p, 0.1, f)
        om, ow, on, oN = stat(old[k]); nm, nw, nn, nN = stat(rec[k])
        t = st.mean(float(r["RUNNING_TIME_ILASP_TRAIN_SECONDS"]) for r in rec[k])
        o = f"{om:.2f} ({ow:.2f})" if om is not None else "--"
        n = f"{nm:.2f} ({nw:.2f})" if nm is not None else "--"
        out.append(f"{p} & {f} & {o} & {on}/{oN} & {n} & {nn}/{nN} & {t:,.0f}\\\\")
out.append(r"\bottomrule\end{tabular}\end{table}")
files["rerun_tab_prf.tex"], out = out, []

# ---------------------------------------------------------------- seed B
sb, v2 = cells(load("seedB")), cells([r for r in load("exp1_v2") if r["RATIO"] == "1"])
deltas = {k: stat(rs)[0] - stat(v2[k])[0] for k, rs in sb.items() if k in v2}
out.append(r"""
\begin{table}[t]
\centering
\footnotesize
\caption{Second realization of the dense campaign (a fresh $500$-framework pool,
noise masks and test draw under master seed $20260901$; $%d$ runs, all completed)
against the balanced arm of the main grid on the same $%d$ cells
($p\in\{1,0.75,0.5\}$, $q{=}0$, $f\in\{10,\dots,80\}$; $p\in\{1,0.75\}$,
$q{=}0.2$, $f\in\{10,80\}$). $\Delta$ is the seed-B minus main-grid difference
in per-cell mean complete-information MCC.}
\label{tab:seedb}
\begin{tabular}{lcrrrr}
\toprule
semantics & $q$ & cells & mean $\Delta$ & mean $|\Delta|$ & max $|\Delta|$ (cell)\\
\midrule""" % (sum(len(rs) for rs in sb.values()), len(deltas)))
for sem in ["STB", "ADM", "CMP", "PRF"]:
    for q in (0.0, 0.2):
        ks = [k for k in deltas if k[0] == sem and k[2] == q]
        if not ks: continue
        worst = max(ks, key=lambda k: abs(deltas[k]))
        out.append(f"{sem} & {q} & {len(ks)} & {st.mean(deltas[k] for k in ks):+.3f} & "
                   f"{st.mean(abs(deltas[k]) for k in ks):.3f} & {deltas[worst]:+.3f} ($p{{=}}{worst[1]},f{{=}}{worst[3]}$)\\\\")
allk = list(deltas)
worst = max(allk, key=lambda k: abs(deltas[k]))
out.append(r"\midrule")
out.append(f"all & & {len(allk)} & {st.mean(deltas.values()):+.3f} & {st.mean(abs(d) for d in deltas.values()):.3f} & "
           f"{deltas[worst]:+.3f} ({worst[0]}, $p{{=}}{worst[1]},q{{=}}{worst[2]},f{{=}}{worst[3]}$)\\\\")
out.append(r"\bottomrule\end{tabular}\end{table}")

files["rerun_tab_seedb.tex"] = out
for name, lines in files.items():
    open(os.path.join(HERE, name), "w").write("\n".join(l for l in lines if l.strip() or True).lstrip("\n") + "\n")
# console summary for the prose
big = sorted((abs(d), k) for k, d in deltas.items() if abs(d) > 0.05)
print(f"seedB: {len(deltas)} cells, mean d {st.mean(deltas.values()):+.4f}, median |d| {st.median(abs(d) for d in deltas.values()):.3f}, >0.05: {len(big)} -> {[k for _,k in big]}")
print("f=10 share among >0.05:", sum(1 for _,k in big if k[3]==10), "; q=0.2 share:", sum(1 for _,k in big if k[2]==0.2))
for f in (20, 60):
    o = [float(r["MCC_FULL"]) for p in (1.0,0.5) for r in old[("PRF",p,0.1,f)] if not r["TO"]]
    n = [float(r["MCC_FULL"]) for p in (1.0,0.5) for r in rec[("PRF",p,0.1,f)] if not r["TO"]]
    print(f"PRF recap pooled f={f}: old {st.mean(o):.3f} ({len(o)}/10) -> new {st.mean(n):.3f} ({len(n)}/10); worst-case floor new {sum(n)/10:.3f}")
print("BAF worst noisy cells:", {k: round(stat(rs)[0],3) for k,rs in baf.items() if k[2]==0.1 and stat(rs)[0] and stat(rs)[0]<0.9})
