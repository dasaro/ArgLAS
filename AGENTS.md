# AGENTS Guide: FabioExperimentsMacM4_codex

## Scope
This repository contains two related experiment tracks:

1. Synthetic Abstract Argumentation Framework (AAF) experiments:
- Generate random AAFs.
- Label extensions under semantics (ASPARTIX encodings used as ground truth).
- Learn hypotheses with ILASP.
- Evaluate learned hypotheses vs ASPARTIX via clingo.

2. Real-world labeled examples:
- Curated/versioned `.lp` datasets from human labels.
- ILASP tasks per version.
- Learned encodings per version.

---

## Authoritative References (Read-Only)
When editing ILASP/clingo-related code, treat these directories as authoritative and do not overwrite them:

- `ILASP_Reference/`:
  - Source of truth for ILASP syntax, semantics, mode declarations, and noisy/task semantics.
  - Key files include `ilasp_detailed_guide.md` and `ilasp_theory_semantics.md`.
- `clingo_reference/`:
  - Source of truth for clingo CLI usage and Python API usage.
  - Key files include `clingo_python_api_cheatsheet.md` and `clingo_extended_help.txt`.

Rule: use these folders to understand and amend code; never replace or modify reference files themselves.

---

## Repository Structure

### Core pipeline files (root)
- `generate_aafs.py`: generates random AAF `.lp` files using clingo Python API.
- `generate_extensions.py`: labels AAFs with positive/negative extensions under selected semantics.
- `generate_ilasp_task.py`: builds ILASP `.las` tasks from labeled files with optional noise inversion.
- `train_test.py`: runs ILASP, then tests learned hypotheses against ASPARTIX ground truth.
- `run_experiment_grid.py`: generic benchmark-grid launcher used by the CLI.
- `watch_experiment_grid.py`: generic watchdog/restart loop used by the CLI.
- `arglas/cli.py`: canonical CLI entrypoint.
- `validate_config.py`, `cleanup.py`: config checks and output cleanup.
- `test_semantics.py`, `check_aaf_satisfaction.py`: comparison/satisfaction utilities.

### Semantics and logic files
- `ASPARTIX/`: authoritative ground-truth semantics encodings used in experiments (`admissible.lp`, `complete.lp`, `stable.lp`, `grounded.lp`, `preferred.lp`, etc.).
- `background_knowledge.lp`: shared predicates/rules for ILASP task generation and evaluation.
- `mode_declarations.las`: ILASP mode bias declarations.
- `semantics_config.json`: maps semantics labels to ASPARTIX files and clingo args.
- `ilasp_config.json`: per-semantics ILASP CLI options.
- `batch_config.json`: experiment matrix settings.

### Data/output folders
- Generated artifact folders (`aafs/`, `labelled/`, `train/`, `train_output/`, `results/`, `logs/`, `plots/`, `benchmarks/`) are created on demand.
- For final benchmark runs, prefer setting `FABIO_ARTIFACTS_ROOT` so generated outputs live under a dedicated artifact root instead of cluttering the repository root.
- Historical generated trees and deprecated wrappers were archived in `backup/pre_final_cleanup_20260309_212003/`.

### Real-world track
- `Real_World_Examples/asp_files/version{A..G}/{pos,neg}`: curated labeled AAF examples.
- `Real_World_Examples/ilasp_tasks/version*.las`: ILASP tasks for each version.
- `Real_World_Examples/learned_encodings/version*.lp`: learned/selected encodings.
- `Real_World_Examples/extract_labeled_aafs.py`: generalized extraction script from Excel source (paper phases or explicit response columns).
- `Real_World_Examples/build_real_world_dataset.py`: end-to-end real-world builder (extract -> neg generation -> ILASP tasks -> learned encodings).
- `Real_World_Examples/neg_generator/versionE.lp`: negative-example generator/constraint program.

---

## Implemented Synthetic Pipeline

1. Generate AAFs
- `python3 generate_aafs.py Nmin Nmax M --output_dir aafs`
- Uses randomized clingo solving and uniqueness checks.

2. Label extensions
- `python generate_extensions.py --semantics <ADM|CMP|STB|GRD|PRF> --p_partial <float> ...`
- Loads semantics from `semantics_config.json`.
- Produces `labelled/labelled_<SEM>_<full|partial_p>/...`.

3. Build ILASP task
- `generate_ilasp_task.py` samples `n` positive + `n` negative files.
- Emits `#pos/#neg` examples, then appends `background_knowledge.lp` + `mode_declarations.las`.
- Supports noisy inversion via probability `p` and penalty via `@noise_factor`.

4. Train + test
- `train_test.py`:
  - Runs ILASP (`ILASP --version=4 ... -d <task>`).
  - Builds train/test split from example IDs in task.
  - Default publication protocol is a deterministic, class-balanced fixed hold-out:
    - `--test_set_policy fixed_balanced_holdout` is the default.
    - A fixed `test_examples_per_class` is computed once per run from the smallest feasible remainder after the largest training size in that run, unless explicitly overridden.
    - One balanced hold-out pool is reserved once per labelled dataset, and ILASP task generation is restricted to the complement of that pool.
    - This keeps both test size and test identities constant across all conditions within the run.
  - Transitional behavior is still available with `--test_set_policy balanced_remaining`, but should be treated as backward-compatibility mode rather than the default benchmark mode.
  - Legacy behavior is still available with `--test_set_policy all_remaining`.
  - Compares learned-model predictions to ASPARTIX predictions via clingo API.
  - Writes semicolon-delimited CSV results.

5. Batch orchestration
- `arglas benchmark run --config ...` is the default benchmark entrypoint.
- `arglas benchmark watch --config ...` is the default watchdog entrypoint.
- `arglas batch ...` exposes the older `batch_config.json` workflow through the CLI.

---

## Historical Artifacts

Historical synthetic outputs, intermediate plots, logs, and deprecated wrappers were moved to:

- `backup/pre_final_cleanup_20260309_212003/`

The archive manifest is:

- `backup/pre_final_cleanup_20260309_212003/MANIFEST.md`

The active repository surface is intentionally clean so the final benchmark can be launched from scratch.

---

## Real-World Track: What Is Already Prepared

### Labeled ASP files by version
- versionA: pos 17, neg 20
- versionB: pos 14, neg 20
- versionC: pos 17, neg 19
- versionD: pos 11, neg 13
- versionE: pos 9, neg 12
- versionF: pos 12, neg 14
- versionG: pos 25, neg 25

### ILASP tasks in `Real_World_Examples/ilasp_tasks`
- `versionA.las`: 17 pos, 20 neg
- `versionB.las`: 14 pos, 20 neg
- `versionC.las`: 17 pos, 15 neg (some neg lines commented out)
- `versionD.las`: 11 pos, 13 neg
- `versionE.las`: 9 pos, 12 neg
- `versionE_special_neg.las`: 9 pos, 90 neg (augmented negatives)
- `versionF.las`: 12 pos, 14 neg
- `versionG.las`: 25 pos, 25 neg

### Learned encodings in `Real_World_Examples/learned_encodings`
- versionA/B/C/D/E: single-rule hypotheses.
- versionE_special_neg: 4-rule hypothesis.
- versionF/G: 2-rule hypotheses.

### Data extraction script
- `Real_World_Examples/extract_labeled_aafs.py` reads Excel sheets (`Raw_Data_original.xlsx`) directly via XLSX XML parsing and maps labels (`accept/reject/undecided`) to `in/out/undec`.

---

## Operational Notes and Caveats

1. Current `batch_config.json` now lists only `PRF` in `"semantics"`, but repository outputs include historical runs for ADM/CMP/STB and partial PRF.
2. GRD labeling currently has no negative examples in `labelled_GRD_*`; this blocks ILASP task creation in the current `generate_ilasp_task.py` flow (requires both POS and NEG).
3. `generate_ilasp_task.py` fails fast when not enough POS/NEG examples exist.
4. Real-world `.lp` files contain formatting artifacts like adjacent atoms (`arg(d).att(b,a).`), which are still parseable ASP but should be normalized if regenerating data.
5. `extract_labeled_aafs.py` has no pandas dependency (XLSX is parsed directly).
6. New synthetic runs should be generated from scratch under the current oracle/runtime split; do not reuse older labelled synthetic datasets from the backup archive.
7. `supported/1` is now defined in `background_knowledge.lp` and matches the ASPARTIX-style “all attackers are out” shorthand.
8. Historical CSVs in the backup archive may have been produced with older evaluation protocols (`all_remaining` or `balanced_remaining`). New benchmark runs should use the fixed hold-out protocol by default.

---

## Default Evaluation Protocol

For synthetic benchmarks, the default and publication-facing evaluation mode is:

1. Train on the requested sampled set (`n_pos`, `n_neg`) as usual.
2. Reserve a deterministic balanced hold-out pool before any training-task sampling.
3. Sample training only from the complement of that hold-out pool.
4. Test on that same fixed hold-out pool for every condition in the run.

Concrete rules:
- Default `train_test.py` mode is `--test_set_policy fixed_balanced_holdout`.
- Default `--test_examples_per_class` is auto-resolved once per run from the smallest feasible held-out class size after accounting for the largest requested training size in that run.
- For cross-semantics comparisons where identical absolute test size matters, pass an explicit `--test_examples_per_class`.
- Use `--test_set_policy balanced_remaining` only to reproduce the earlier balanced-on-remainder protocol.
- Use `--test_set_policy all_remaining` only to reproduce or compare against legacy results.

Rationale:
- Synthetic labelled pools are often semantically imbalanced (e.g. many more NEG than POS files for PRF/STB/GRD).
- Evaluating on all remaining files preserves that prevalence and can materially bias raw accuracy.
- A fixed balanced hold-out makes accuracy and F1 more defensible for publication while also keeping the tested instances identical across conditions.

---

## Recommended Working Rules for Future Edits

1. For ILASP syntax/semantics changes, consult `ILASP_Reference/` first.
2. For clingo CLI or Python API behavior, consult `clingo_reference/` first.
3. Keep `ILASP_Reference/` and `clingo_reference/` unmodified.
4. Use `semantics_config.json` and `ilasp_config.json` as central configuration points instead of hardcoding semantics behavior in scripts.
5. Preserve the existing output directory contract (`aafs`, `labelled`, `train`, `train_output`, `results`) to keep batch scripts interoperable.
