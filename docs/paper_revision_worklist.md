# Claims diff & revision worklist — arXiv 2310.12309v2 → journal submission

Diff of every claim in *"A Unifying Framework for Learning Argumentation Semantics"*
(Mileva, Bikakis, D'Asaro, Law, Russo; arXiv v2, Mar 2025) against the machine-verification
and experimental results in this repository (commits `53ffc8a`…`3b807da` + the v2 campaign).
Evidence pointers are to `analysis/zlatina_theorems/` unless stated.

> **SCOPING DECISION (2026-07-07): grounded (GRD) is dropped from the paper entirely.**
> On the dense v2 generator the grounded extension is empty ~69% of the time (starving the
> learning signal), and GRD is fragile to label noise (no ILASP version — 2/2i/3/4 —
> recovers the correct program under noise). The paper now studies **four** semantics:
> stable, admissible, complete, preferred. Items below that concern GRD are struck through
> or annotated `[GRD — DROPPED]`; kept only as internal record / possible future work
> ("grounded under a signal-bearing graph distribution"). See `docs/aij_outline/` and
> [[arglas-v2-campaign-results]].

---

## 1. REQUIRED corrections (must fix before any resubmission)

**1.1 §3.2 / Listing 11 — the ABA Step-1 program is incorrect. [CRITICAL]**
The argument-construction program (assume/root choices + Domain heuristics + domRec)
*drops arguments* whenever any root is derivable without assumptions: 378/500 random flat
ABA frameworks affected; minimal counterexample `R={s1.}, A={s0}` misses the assumption-
argument `({s0} ⊢ s0)`. The paper's running example has no fact rules, which is why it
works there. **Fix (validated 500/500):** run Step 1 once per candidate root with the root
pinned (`:- not holds(root)`) and domRec over `assume` only. Rewrite §3.2 accordingly;
Listing 12 (Step 2) is verified correct as-is (500/500).
*Evidence:* `check_aba_transform.py` (+ `--fix`).

**1.2 Footnote 3 — `clingo -n 1` contradicts the enumeration described.**
The text requires enumerating *all* domRec answer sets (five arguments in the example);
`-n 1` returns one. Should be `-n 0` (and will change again with fix 1.1).

**1.3 "Table 13" → Table 1.** Leftover thesis numbering.

**1.4 Abstract overclaim.** "our framework outperforms existing argumentation solvers" —
Fig. 1 itself shows ASPARTIX ahead on preferred. Soften to match Fig. 1 (wins on
admissible/stable, parity on complete/grounded, behind on preferred).

---

## 2. Strengthenings of existing claims (verification now in hand)

**2.1 Theorem 1 (adm/cmp/stb ≡ ASPARTIX).** Currently: in-text proof for admissible only,
rest deferred to "fuller report". Now verifiable three independent ways:
(i) exhaustively on all 66,066 AFs with ≤4 arguments incl. self-attacks + 500 campaign AAFs
(0 counterexamples); (ii) via Clark completion + Fages (tight programs) discharged by Z3;
(iii) **fully automatically by anthem 2 + Vampire (~250 ms each)** — external
program-to-program equivalence in the published io-programs framework.
*Add a "Mechanized verification" subsection + artifact links; this is a novel contribution
in its own right (verified learned encodings).*
*Evidence:* `check_equivalence.py`, `prove_completion_equiv.py`, `anthem/`.

**2.2 Preferred (Listing 8) — currently NO theorem.** `[GRD — DROPPED from this item;
preferred retained.]` Theorem 1 covers {stb,adm,cmp}; for **preferred** we can now state:
*machine-checked on all 66,066 AFs n≤4 + 500 campaign AAFs, zero counterexamples*
(`check_heuristic_encodings.py`). Note: the arXiv's AS* definition (subset-minimal
projection) is correct — the thesis's "minimal number" wording was already fixed; keep the
subset-minimality language. (Grounded's exhaustive certificate still holds but is not
reported, since grounded is out of the paper.)
*Optionally add the honest caveat that no first-order proof exists for these two (heuristic
semantics are outside anthem's fragment) — the exhaustive check is the certificate.*

**2.3 BAF equivalence — NEW theorems, previously not even claimed.** The paper only
observes the learned BAF solutions coincide with AAF's. We now have **anthem+Vampire
proofs** of learned ≡ guess-encodings for BAF stable/admissible/complete via the
shared-input closure reduction (supp ⊇ support, supp∘support ⊆ supp; proofs 384/344/515 ms;
instantiation at the actual closure + clingo-validated reformulation, 2,400 checks), plus
3,256-BAF exhaustive confirmation of the original formulation. *Add as Theorem 2.*
*Evidence:* `anthem/baf2_*`, `anthem/README.md`, `check_baf.py`.

**2.4 §3.1 background simplifications (B → B_AAF/B_BAF/B_VAF).** Stated informally;
now verified (1,800 randomized checks, 0 mismatches — `check_unified.py`). One sentence.

---

## 3. New contributions to add (from this project)

**3.1 Robustness campaign (the big one).** The paper's evaluation uses small *manually
engineered* example sets and clean labels — the obvious reviewer question is "what if the
examples are sampled and imperfect?" The v2 campaign answers it: recovery surfaces for
**four semantics** (stb/adm/cmp/prf) over label completeness {1.0, 0.75, 0.5} × label
noise {0, 0.1, 0.2} × examples-per-class {10…80} × three pos/neg proportions, grouped K=5
CV, dual-surface evaluation (matched vs complete-information test — the latter is the honest
recovery number), all leak-free and reproducible from a pinned commit. **Campaign complete
(3510 rows):** near-perfect recovery (≈1.00) at full information once f≥30; noise (amplified
by partial labels) is the binding constraint and is bought back with more examples (not
saturated by sample size alone); class imbalance is a null (spread ≤0.026 over 40/50/60%
positive); all failures are timeouts under noise (0 UNSAT, 0 error).
*`[GRD — DROPPED]`* grounded is excluded from the campaign figures (see scoping banner).

**3.2 PRF made properly learnable at scale.** The `--learn-heuristics` route works on the
paper's small hand-crafted tasks but fails at campaign scale (our post-mortem: the flag is
costly and the eval-side domRec args were the historical failure). Working formulation for
**preferred**: an admissible/complete core + a fixed symmetric subset-maximality convention
(`#heuristic in(X).[1,true]` with `domRec` on both sides), recovering preferred at
MCC 0.996 through the real pipeline; separate stable-shortcut via divergent
(preferred≠stable) positives. *Evidence:* `analysis/grd_prf_lab/` (preferred track).
`[GRD — DROPPED]` the grounded routes (no-choice definite core; "grounded = complete + a
learnable weak constraint") are removed from the paper; retained in the repo as future work.

**3.3 ILASP 4.4.1 spurious-UNSAT bug** `[GRD — DROPPED from paper]` (minimal 2-positive
repro at `analysis/grd_prf_lab/g1_definite_core/tasks/_diag_core.las`). Since it only
manifests on no-choice/definite GRD tasks, it leaves the paper with GRD. Keep as a courtesy
upstream report to Mark Law (ILASP co-author), not a paper contribution.

**3.4 FastLAS comparison (optional).** Learning the same semantics 30–600× faster via the
verifier reframing (`Real_World_Examples/fastlas_exp/README.md`) — include if the venue
rewards a systems dimension, otherwise hold for a separate note.

**3.5 Repository refresh.** The paper's reproducibility link (github.com/dasaro/ArgLAS)
should gain: the verification lab, the fixed ABA programs, the campaign configs + launcher,
and the anthem artifacts.

---

## 4. Consistency / positioning items

- §1 "prove that the learned programs are equivalent to ASPARTIX encodings" — scope to
  {adm, cmp, stb} + point to the new BAF theorems and the exhaustive preferred check.
- §2.2 heuristic-statement semantics (AS*): correct as written; keep subset-minimal wording.
- Related work refresh 2023→2026 (learning argumentation semantics, NeSy approaches,
  anthem line of work for the verification angle).
- Decide framing of the human-data study (Exp2, `fastlas_exp/paper/exp2.tex`) — recommend a
  *separate* companion paper; cite as ongoing work in §5.
- Venue: TPLP (fits ILASP+anthem+ASP audience; no page pressure for proofs) or AIJ;
  if conference, KR/IJCAI with appendix.

## 5. Suggested revised structure

1. Introduction (+ verification as an explicit contribution bullet)
2. Background (as-is + AS* + brief io-programs/anthem)
3. The unifying framework (as-is; fixed ABA §3.2)
4. **Correctness, mechanized** (Thm 1 + new BAF Thm 2 + preferred exhaustive certificate +
   the ABA bug story as a case for mechanized checking)
5. Learnability at scale (v2 campaign surfaces, four semantics; preferred formulation)
6. Evaluation vs solvers and DL (existing §4, refreshed numbers + fixes 1.2–1.4)
7. Conclusion

---

*Everything in §§1–2 is actionable today; §3.1 waits on the campaign (running). The single
gating item for submission readiness is campaign completion + its figures.*
