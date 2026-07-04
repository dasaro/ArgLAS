# Machine-check of the thesis §2.5 equivalence theorems

Theorems (abstract_proofs.pdf, pp. 24–32): for each semantics σ ∈ {stable, admissible,
complete}, the ILASP-learned program P_σ (+ defeated/not_defended definitions) and the
ASPARTIX-style encoding S_σ have identical answer sets on EVERY argumentation framework.

## Verdict: all three theorems PROVED, two ways

**Level 1 — exhaustive finite verification** (`check_equivalence.py`):
- ALL 66,066 labelled digraphs with ≤4 arguments (self-attacks included): 0 counterexamples,
  for the three manuscript programs AND the on-disk Example1 variants.
- All 500 campaign AAFs (4–8 arguments, dense): 0 mismatches.
- Results: `level1_results.json`.

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
