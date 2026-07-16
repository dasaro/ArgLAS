# sigma_H principle-profile audit

Exhaustive principle audit of the learned human semantics sigma_H (AIJ paper,
Section 8 "The learned theory"): the five-rule consensus verifier — the four
`final_base` consensus rules plus the aux smoke/fire rule
(`violated :- reinstated(X), has_many_attackers(X)`) — read directly from
`Real_World_Examples/fastlas_exp/results/consensus.json` (exactly the rule set
the paper's figure prints).

## What it does

`audit_sigma_h.py [NMAX=4]` enumerates ALL labelled digraphs with n<=NMAX
arguments (self-attacks included; 66,066 AFs at NMAX=4 — the same exhaustive
surface as `analysis/zlatina_theorems/check_equivalence.py`). Per AF it
computes sigma_H's legal labellings (clingo: the fl_discover generator `_GEN`
+ the `_FEATS`/`_FEATS_ENR`/`AUX9_BG` feature background + the five rules +
`:- violated.`) and the complete labellings (standard Caminada encoding), and
checks: totality, conflict-freeness, admissibility, reinstatement, the
legal-vs-complete relation (globally and on acyclic AFs), and directionality
(over accepted sets; failure implies sigma_H is not SCC-recursive). It also
runs two attribution ablations (drop rule 4; strict rule 1 without the
`attacked_by_in` exception) and re-checks the three stimulus graph shapes
(float A-C, chain D-F, 3-cycle G) from Experiment 2.

Feature/generator code is imported verbatim from
`Real_World_Examples/fastlas_exp/fl_discover.py` and `aux9_combined.py` —
nothing is re-implemented, so the audit exercises the exact programs the paper
learned and predicts with.

## Headline result (n<=4, 66,066 AFs, ~4 min)

- conflict-freeness FAILS (9,645 AFs; minimal witness a->b with both accepted);
  admissibility FAILS a fortiori (43,933 AFs); reinstatement FAILS (15,078 AFs);
  totality HOLDS up to n=3 but FAILS on 768 n=4 AFs (36 acyclic) — the graphs
  whose labellings all force full reinstatement of a multiply-attacked argument;
  directionality FAILS (2,346 AFs) hence sigma_H is not SCC-recursive.
- Attribution is exact: dropping rule 4 restores totality on all 66,066 AFs;
  removing rule 1's attacked_by_in exception restores conflict-freeness on all
  66,066 AFs.
- Every complete labelling is legal on 51,337/66,066 AFs (77.7%) and on all
  three experimental stimulus graphs; sigma_H is total on all three stimuli.

## Output

`Real_World_Examples/fastlas_exp/results/sigma_h_principle_audit.json` —
per-principle violated-AF/violated-labelling counts, lexicographically minimal
counterexamples, ablations, stimulus-graph checks.
