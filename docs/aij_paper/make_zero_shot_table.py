#!/usr/bin/env python3
"""tab:zeroshot from Real_World_Examples/zero_shot/zero_shot_results.json (frozen sigma_H,
out-of-corpus check on Cramer & Guillaume 2019)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "..", "..", "Real_World_Examples", "zero_shot", "zero_shot_results.json")))
G = [("all", "all ($61$)"), ("coherent", "coherent ($49$)"), ("nongrounded", "coh.\\ non-grounded ($27$)")]
P = [("grounded", "grounded"), ("preferred", "preferred"), ("cf2", "CF2"),
     ("sigma_h/skeptical", "$\\sigma_H$, skeptical"), ("sigma_h/credulous", "$\\sigma_H$, credulous")]
ncom = {g: R["cg2019"][f"{g}|grounded"]["n_committed"] for g, _ in G}
L = []
L.append(r"""\begin{table}[t]
\centering
\scriptsize
\setlength{\tabcolsep}{2.5pt}
\caption{Out-of-corpus check of the frozen $\sigma_H$ on the twelve stimulus
frameworks ($60$ arguments) of \citet{cramer2019jelia}, against the published
majority response of each participant group. Top, per argument: acc$_3$ is
three-valued agreement (its all-undecided baseline is the share of
``undecided'' majorities); ``committed'' is agreement on the arguments whose
majority response is accept or reject ($n_c$ in the header); ``commits'' is the
number of arguments on which the predictor itself commits, with its precision.
Grounded and complete coincide.
Catalogue semantics are read under the papers' own justification status
(strongly accepted / strongly rejected / weakly undecided $=$ skeptical
projection); $\sigma_H$ under the skeptical projection of its legal labellings
and under the credulous (plurality) projection used in corpus. Argument~59 is
tied among all participants and excluded there; on framework~7 $\sigma_H$
admits no labelling at all and its five arguments are excluded from the
$\sigma_H$ rows ($n{=}54$ or $55$). Bottom, per framework: is the whole-framework
majority labelling admitted --- a legal labelling of $\sigma_H$, a grounded /
preferred / CF2 labelling of the catalogue --- out of $12$ frameworks ($11$ for
the all-participants group); ``space'' is the mean fraction of the $3^n$
labellings a verifier admits.}
\label{tab:zeroshot}
\resizebox{\linewidth}{!}{%
\begin{tabular}{l""" + "ccc" * len(G) + r"""}
\toprule
& """ + " & ".join(f"\\multicolumn{{3}}{{c}}{{{lab}, $n_c{{=}}{ncom[g]}$}}" for g, lab in G) + r"""\\
""" + " ".join(f"\\cmidrule(lr){{{2+3*i}-{4+3*i}}}" for i in range(len(G))) + r"""
predictor & """ + " & ".join("acc$_3$ & comm. & commits" for _ in G) + r"""\\
\midrule""")
for key, lab in P:
    cells = []
    for g, _ in G:
        r = R["cg2019"][f"{g}|{key}"]
        prec = "--" if r["n_predictor_committed"] == 0 else f"{r['commit_precision']:.2f}"
        cells.append(f"{r['acc3']:.2f} & {r['acc_committed']:.2f} & {r['n_predictor_committed']} ({prec})")
    L.append(f"{lab} & " + " & ".join(cells) + r"\\")
L.append("all-undecided baseline & " + " & ".join(f"{R['cg2019_all_undec_baseline'][g]:.2f} & 0.00 & 0 (--)" for g, _ in G) + r"\\")
L.append(r"\midrule")
L.append(r"\multicolumn{" + str(1 + 3 * len(G)) + r"}{l}{\emph{majority labelling admitted (out of 12 / 11 frameworks)}}\\")
adm = R["cg2019_admission"]; perm = R["cg2019_permissiveness"]
def count(g, key):
    rows = [a for a in adm if a["group"] == g and a["labelling"] != "tie"]
    return sum(1 for a in rows if a[key]), len(rows)
space = {k: sum(v[k] / 3 ** v["n"] for v in perm.values()) / len(perm) for k in ("sigma_H", "grounded", "preferred", "cf2")}
for key, lab, sk in (("grounded", "grounded", "grounded"), ("preferred", "preferred", "preferred"), ("cf2", "CF2", "cf2"), ("legal", "$\\sigma_H$", "sigma_H")):
    cells = []
    for g, _ in G:
        k, n = count(g, key)
        cells.append(f"\\multicolumn{{3}}{{c}}{{{k}/{n}}}")
    L.append(f"{lab} (space {100*space[sk]:.1f}\\%) & " + " & ".join(cells) + r"\\")
L.append(r"\bottomrule\end{tabular}}\end{table}")
open(os.path.join(HERE, "zero_shot_tab.tex"), "w").write("\n".join(L) + "\n")
print("\n".join(L[-12:]))
