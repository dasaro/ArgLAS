# Exp1 exactness audit (clean-label campaign hypotheses)

Post-hoc audit answering: *how many of the theories learned in the v2 campaign
at noise 0.0 are EXACTLY extension-equivalent to their target semantics — not
just behaviourally correct on the 200-item test sample?*

The check is an empirical exhaustive comparison via ASP solving: for every
labelled digraph with up to 4 arguments, self-attacks included
(2^1 + 2^4 + 2^9 + 2^16 = 66,066 frameworks), the extension set of each
learned theory over the guessing background (`config/background_knowledge.lp`)
is compared with the reference extension set from the ASPARTIX-style
encodings. No learning is re-run: hypotheses come from the committed campaign
record (`data/exp1_v2/results/*/results_*.csv` -> `LEARNED_MODEL_FILENAME`
under `artifacts/final_synthetic_v2/train_output/`; 1,080 clean runs, 206
distinct hypothesis texts: STB 48, ADM 21, CMP 94, PRF 43).

Equivalence notion per semantics (mirrors the pipeline's own evaluation
conventions in `config/semantics_config.json`):

- **STB / ADM / CMP** — sets of TOTAL labellings (every argument `in` or
  `out`) of H + guessing background must coincide with the reference.
- **PRF** (learned admissible core + fixed subset-maximal in-selection) —
  primary convention is pipeline-faithful: subset-maximal in-projections over
  ALL models of H + guessing background (exactly what
  `--heuristic=Domain --enum=domRec` realizes on `bg_prf_learned.lp`; the
  `#heuristic` directive never changes the set of models), compared against
  the preferred extensions (subset-maximal elements of the ADM reference
  set, derived in Python). A strict total-labelling variant is reported as a
  secondary column.

Non-exact hypotheses get one minimal counterexample AF (fewest arguments,
then fewest attacks).

## Files

- `audit_learned_exactness.py` — the audit (`python3 audit_learned_exactness.py
  all --workers 7`). Builds a reference-labelling cache for all 66,066 AFs
  once (regenerable; kept outside the repo, see `--cache`), cross-checks it
  against the `config/ASPARTIX/` encodings on all 530 AFs with n<=3 (PRF via
  the documented domRec call) before any hypothesis is audited, then checks
  the 206 distinct hypotheses in parallel.
- `hypothesis_catalogue.csv` — one row per distinct hypothesis: exact flag,
  counterexample (JSON), PRF strict-total secondary flag, hypothesis text.
- `run_exactness.csv` — one row per clean campaign run (semantics, f, p,
  MCC_FULL, hypothesis id, exact).
- `exactness_by_cell.csv` — fraction of exact runs per (semantics, f, p).
- `summary.json` — headline numbers used in the paper.
