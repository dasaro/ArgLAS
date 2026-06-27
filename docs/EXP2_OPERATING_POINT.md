# Estimating the real-data operating point (Exp2 ← Exp1 bridge)

Methods note for placing the real-world dataset on the synthetic recovery surface of Exp1,
and for separating *idiosyncratic noise* (which Exp1 already quantifies the cost of) from
*model-mismatch* (humans not being a Dung semantics — the quantity Exp2 exists to measure).

## Rationale

Exp1 measures the pure learnability cost of two stressors — incomplete labels (`p`) and
per-argument noise (`q`) — for a target that **is** a Dung semantics. Real human judgement
is **not** a Dung semantics, so its recovery error decomposes as

```
Exp2_error  =  recovery_limit(p, q)        +   model_mismatch
               └ read off the Exp1 surface ┘     └ the Exp2 result ┘
```

To use this we must estimate the real data's `(p, q)` and, separately, the model-mismatch,
without ever calling the latter "noise".

## Data model

Each record is `(G, annotator, ℓ)`: an AAF `G` with `N` arguments and attack relation, plus
one annotator's labelling `ℓ` assigning each argument a status in `{in, out, undec, ⊥}`
(`⊥` = not shown to / not answered by the annotator). The real corpus is **multi-annotator**
(many participants label the same condition's AAF), which is what makes `q` identifiable.

**Three-valued handling.** Human `undec` ("undecided") is an *abstention from commitment*,
the natural analogue of a hidden label, so for the completeness/noise mapping we treat both
`undec` and `⊥` as non-commitments and call `{in, out}` the *commitments*. (`undec` is also
retained as a first-class status for a secondary 3-valued disagreement diagnostic, and it is
**not** treated as `out` — that conflation would inflate `p` and fabricate structure.)

## 1. Completeness `p`

Maps directly to Exp1's partial axis (which retains each in/out atom independently with
probability `p`). Per labelling on an AAF with `N` arguments:

> `p(ℓ) = #commitments(ℓ) / N`

Report the **distribution** (mean, median, IQR), not just the mean, and **stratify by `N`**
(recovery and the binding semantics both depend on graph size). The pooled mean `p̂` is the
coordinate used for surface lookup.

## 2. Idiosyncratic noise `q`

Identifiable only from inter-annotator disagreement. Exp1's noise is an iid per-argument flip
of a consistent base labelling; if two annotators each flip the truth with probability `q`,
they disagree on a committed argument with probability

> `D = 2q(1 − q)`   ⇒   **`q̂ = (1 − √(1 − 2D)) / 2`**

Estimate `D` by pooling pairwise disagreements over commitments: for each `(framework, arg)`
with `c_in` "in" and `c_out` "out" commitments, contribute `c_in·c_out` disagreeing pairs out
of `C(c_in+c_out, 2)` total. Then `D = Σ c_in·c_out / Σ C(c_in+c_out, 2)` and invert to `q̂`.
Bootstrap over **participants** for a CI. (`D > 0.5` cannot arise under the iid model —
anti-correlated annotators — so clamp and warn; the model is then inappropriate.)

*Single-annotator corpora*: `q` is **not identifiable from labels alone**. Collect a small
doubly-annotated subset (preferred), use test–retest, or fall back to
distance-to-nearest-consistent-labelling as an *upper bound*, explicitly flagged as
conflating noise with mismatch.

## 3. Model-mismatch (kept separate)

Measure the **consensus constraint-violation rate**: among arguments/labellings where
annotators agree, the fraction that violate a Dung constraint — primarily conflict-freeness
(an agreed labelling putting two mutually-attacking arguments both `in`), plus
admissibility/completeness if relevant to the target. Agreed-upon violations are irreducible
"humans ≠ Dung" and must be reported as a **separate** number; folding them into `q` would
over-state noise and under-state the Exp2 result.

## 4. Placement and validation

- Look up the Exp1 cell at `(p̂, q̂)` for the predicted recovery (per candidate semantics).
  Better: **re-run the synthetic pipeline at the measured `(p̂, q̂)`** and the real
  AAF-size distribution for an exact tailored baseline rather than the coarse 3×3 grid.
- **Check the size match**: Exp1 used `N ∈ [4, 8]`; the real conditions are `N ∈ {3, 4, 5}`.
  The simple-reinstatement set (`N=3`) is below the synthetic range — note the extrapolation
  or extend the synthetic generator to cover `N=3`.
- Headline output: `predicted_recovery(p̂, q̂) − achieved_Exp2 = ` the degree of
  human-non-Dung-ness, with a bootstrap CI.

## Pitfalls checklist

`undec`/`⊥` ≠ `out`; stratify by `N`; `q` needs multi-annotator data; bootstrap over
participants; keep consensus CF-violation strictly separate from `q`; mind the `N=3`
extrapolation below the synthetic range.
