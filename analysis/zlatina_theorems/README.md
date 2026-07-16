# Machine-check of the thesis §2.5 equivalence theorems

Theorems (abstract_proofs.pdf, pp. 24–32): for each semantics σ ∈ {stable, admissible,
complete}, the ILASP-learned program P_σ (+ defeated/not_defended definitions) and the
ASPARTIX-style encoding S_σ have identical answer sets on EVERY argumentation framework.

## Verdict: all three theorems PROVED, two ways

**Level 1 — exhaustive finite verification** (`check_equivalence.py`):
- ALL 66,066 labelled digraphs with ≤4 arguments (self-attacks included): 0 counterexamples,
  for the three manuscript programs AND the on-disk Example1 variants.
- All 500 campaign AAFs (4–8 arguments, dense): 0 mismatches.
- Results: `level1_results.json` (committed; produced with `check_equivalence.py 4`).
  Re-runs write `level1_results_regen.json` so the committed record is never clobbered;
  without the positional NMAX the script does a quick nmax=3 smoke check.

**Level 2 — first-order proof** (`prove_completion_equiv.py`):
- All six programs are TIGHT (syntactic positive-dependency check in the script), so by
  Fages' theorem answer sets = models of the Clark completion.
- Each theorem reduces to Comp(P) ⇔ Comp(S) as a first-order validity over ALL domains;
  Z3 4.16 proves both directions of all three (plus the Example1 stable variant) in
  milliseconds. Assumption inherited from the thesis: every domain element has an arg fact.

## Bonus findings
- The on-disk `Example1/stable_learned.lp` (`in :- arg, not defeated`) differs from the
  manuscript's program (`in :- arg, not out`) — both are proved equivalent to S_STB, so
  the discrepancy is harmless (state both, one proof).
- Manuscript errata: §2.5.2/§2.5.3 closing lines read "A ∈ AS(P∪F) iff A ∈ AS(P∪F)"
  (second P should be S); the self-attack case (X=Y) is not addressed explicitly in the
  manual proofs but is covered by the exhaustive check here.

## Full-thesis verification (Final_Year_Project_Report.pdf, 2026-07-05)

| claim | thesis status | machine-check verdict |
|---|---|---|
| Thm 4.1.1–4.1.3 (AAF learned ≡ ASPARTIX, +10 lemmas) | proved | **PROVED** (66,066 AFs + Z3/Fages) |
| §4.1.5 GRD heuristic encoding + domRec = grounded | unproved, empirical | **HOLDS** (66,066 AFs + 500 campaign, 0 CE) |
| §4.1.6 PRF heuristic encoding + domRec = preferred | unproved, empirical | **HOLDS** (same; NB: domRec is SUBSET-minimality — the thesis prose says "minimal number", fix wording) |
| §4.3 BAF learned ≡ guess-encodings w/ BAF background | proofs omitted | **HOLDS** (3,256 BAFs incl. exhaustive n=2, 0 CE) |
| §4.5 unified background specializes to AAF/BAF/VAF | informal | **HOLDS** (1,800 randomized checks, 0 CE) |
| §4.2 ABA→AAF step 2 (attack rule) | by example | **HOLDS** (500 random flat ABAs, 0 CE) |
| **§4.2 ABA→AAF step 1 (argument enumeration)** | by example | **FAILS** — domRec with mixed assume/root heuristics drops arguments whenever fact-derivable roots exist (378/500 frameworks; minimal CE: rules={s1.}, A={s0} → misses ({s0}⊢s0)). The thesis's Example 2.2.3 has no fact rules, which is why it worked there. |

**Fix (validated 500/500):** run step 1 once per candidate root with the root pinned
(`:- not holds(root)`) and domRec over `assume` only — this enumerates exactly the
subset-minimal supports per root (`check_aba_transform.py --fix`).

Scripts: `check_heuristic_encodings.py`, `check_baf.py`, `check_unified.py`,
`check_aba_transform.py`.
