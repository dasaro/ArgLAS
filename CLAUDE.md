# CLAUDE.md — working notes for coding agents

ArgLAS: learning argumentation semantics as answer set programs with ILASP.
Start with `README.md` (layout + reproduction) — this file adds agent-facing rules.

## Layout (post-reorganization, 2026-07)

- `arglas/` — the standalone learner package. Modules: `generate_aafs`,
  `generate_extensions` (oracle labelling), `generate_ilasp_task`, `train_test`
  (grouped-CV learn/eval harness), `solver_policy` / `solver_runtime`
  (semantics config + clingo), `ilasp_policy` (ILASP flags), `artifact_paths`
  (path resolution — read this first), `validate_config`, `cleanup`, `cli`, `demo`.
- `config/` — the only place semantics behavior lives: `semantics_config.json`,
  `ilasp_config.json`, `batch_config.json`, `background_knowledge.lp` (learning
  background: derived vocabulary + choice rules), `mode_declarations.las` (mode
  bias), `bg_nochoice_grd.lp` / `bg_prf_learned.lp` / `bg_baf.lp` (per-semantics
  learning backgrounds), `ASPARTIX/` (reference encodings incl. the proved BAF
  guess encodings).
- `experiments/` — campaign machinery (grid, watch/progress/plot, launchers,
  breadth generators, calibrations) + `run_configs/` (seeded). Scripts bootstrap
  `sys.path` so they run standalone from anywhere.
- `data/` — committed experimental record (results CSVs + generator pools). Do
  not regenerate into it; new runs go to `FABIO_ARTIFACTS_ROOT`.
- `analysis/` — verification labs and figure scripts. `zlatina_theorems/` is the
  three-level proof lab; `grd_prf_lab/` is the historical GRD/PRF formulation lab
  (needs local legacy artifacts to re-run); `tree_baseline/` the §7 baseline.
- `Real_World_Examples/` — Experiment 2; `data/` vs `scripts/` vs `fastlas_exp/`.
- `docs/` — `aij_paper/` (manuscript + `make_figs.py`), specs, `references/`
  (ILASP_Reference, clingo_reference, source PDFs), `archive/` (stale plans).

## Path resolution contract

`arglas.artifact_paths` is the single source of truth:
- `resolve_repo_path(x)` — config/encoding assets; relative names resolve
  against the repo root, then fall back to `config/`. So the short names in
  JSON configs ("background_knowledge.lp", "ASPARTIX/stable.lp") keep working.
- `resolve_artifact_path(x)` / `artifacts_root()` — generated data; honors
  `FABIO_ARTIFACTS_ROOT` (default: repo root). Campaign launchers set it per run.

## Working rules

1. For ILASP syntax/flags consult `docs/references/ILASP_Reference/`; for clingo,
   `docs/references/clingo_reference/`. Keep both unmodified.
2. Configure semantics behavior in `config/semantics_config.json` /
   `config/ilasp_config.json` — never hardcode per-semantics logic in scripts.
3. The publication evaluation protocol is `test_set_policy=grouped_kfold`
   (framework-disjoint K=5) with the complete-information test surface
   (`MCC_FULL`); the failure taxonomy (TIMED_OUT / UNSAT / ERROR) is first-class
   — never fold failures into scores.
4. Campaign runs are stop/resume-safe; resume by re-running the launcher.
   Never edit files the grid re-reads (config/*.json, arglas/*.py) while a
   campaign is running.
5. The n=10–12 dense regime is memory-heavy (single ILASP task peaks ~7–8 GB);
   keep `workers=1` there and use `experiments/run_large_safe.sh`.
6. Grounded (GRD) is configured and runnable but out of the paper's scope
   (dense pools starve its learning signal; noise breaks the definite core).
