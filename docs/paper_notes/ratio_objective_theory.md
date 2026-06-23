# Ratio-Objective Theory Notes (ILASP, This Repository)

## 1) ILASP score and implementation constants

From ILASP noisy-task semantics:

\[
S(H,T)=|H|+\operatorname{pen}(H,T)
\]

In this repository, for noisy runs (`noise > 0`), each training example is emitted with weight `@100` (`--noise_factor=100`), so:

\[
S(H,T)=|H|+100\cdot U_{\text{obs}}
\]

where \(U_{\text{obs}}\) is the number of uncovered examples with respect to observed (possibly flipped) labels.

For `noise = 0`, examples are unweighted hard examples (no `@100`).

## 2) Expected score under symmetric label flips

Let:

- \(p\): label-flip probability used in task generation,
- \(N=N_+ + N_-\): number of training examples,
- \(E=FP+FN\): true classification error count w.r.t. clean labels.

Under i.i.d. symmetric flips:

\[
\mathbb{E}[U_{\text{obs}} \mid E] = pN + (1-2p)E
\]

thus

\[
\mathbb{E}[S] = |H| + 100\big(pN + (1-2p)E\big)
\]

and, for \(p<0.5\),

\[
E \approx \frac{S-|H|-100pN}{100(1-2p)}.
\]

## 3) Mapping score to FP/FN and F1

Define \(\rho=\frac{FP}{FN}\). Then:

\[
FN=\frac{E}{1+\rho}, \quad FP=\frac{\rho E}{1+\rho}, \quad TP=N_+-FN
\]

\[
F1=\frac{2TP}{2TP+FP+FN}.
\]

Substituting:

\[
F1(S,\rho)\approx
\frac{2\left(N_+ - \frac{E}{1+\rho}\right)}
{2N_+ + E\frac{\rho-1}{1+\rho}},
\quad
E=\frac{S-|H|-100pN}{100(1-2p)}.
\]

Important identifiability note: \(S\) alone gives \(FP+FN\), not \(FP\) and \(FN\) separately. One extra condition (for example \(\rho\)) is required.

## 4) How ratio `n_pos/n_neg` enters the objective

Let \(r=\frac{n_{pos}}{n_{neg}}\). Up to additive constants and global scale, minimizing \(S\) is equivalent to minimizing:

\[
L_r \propto r\cdot FNR + FPR.
\]

So `ratio` is an explicit FN-vs-FP cost trade-off parameter:

- larger \(r\): stronger pressure to reduce FN (typically more FP),
- smaller \(r\): stronger pressure to reduce FP (typically more FN).

The `100` penalty and \(p\) scale the objective but do not change this direction (for \(p<0.5\)).

## 5) Practical heuristic for F1-oriented ratio

A local first-order heuristic gives:

\[
r^* \approx \frac{2-F1}{F1}.
\]

Examples:

- \(F1=0.90 \Rightarrow r^*\approx 1.22\)
- \(F1=0.85 \Rightarrow r^*\approx 1.35\)
- \(F1=0.80 \Rightarrow r^*\approx 1.50\)

Use this as a prior for grid design, then select by held-out metrics and confidence intervals.

## 6) Limits and caveats for paper claims

- The derivation assumes symmetric independent label flips.
- ILASP search bias, finite samples, timeout truncation, and hypothesis-size effects (\(|H|\)) can shift empirical optima.
- Therefore:
  - theory is strongest for directional predictions and parameterization insight,
  - empirical estimates remain authoritative for final ratio selection.
