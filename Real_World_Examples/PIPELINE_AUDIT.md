# Real World Examples Pipeline Audit

## Scope

This note reconstructs the currently implemented/available pipeline for `Real_World_Examples/` and highlights low-risk improvements.

## Reconstructed Pipeline (Current State)

1. **Raw data source**
   - `Raw_Data_original.xlsx` (plus auxiliary processed exports).

2. **Extraction script**
   - `extract_labeled_aafs.py`:
     - loads `PART_A` and `PART_B`,
     - supports version filtering (`A..G`, configurable),
     - supports configurable response sources for both parts:
       - paper phases (`first`, `group`, `final`) or
       - all detected response columns / explicit column names,
     - maps labels `accept/reject/undecided -> in/out/undec`,
     - persists per-participant `.lp` files by source-combination,
     - writes CSV/JSON manifests with paper-reference metadata and source provenance.

3. **Preprocessed table**
   - `Preprocessed_Data.csv` contains 130 rows (`p1..p130`) with:
     - `ID` (e.g., `p100_versionB`),
     - `ATTACK`,
     - `ARGS`,
     - `EXTENSION`.
   - Pos examples in `asp_files/version*/pos` match these preprocessed labels (for included IDs).

4. **Curated pos/neg ASP files**
   - `asp_files/version{A..G}/{pos,neg}/p*.lp` exist as the dataset used for ILASP tasks.
   - For versions A-F, `pos` is a subset of available preprocessed IDs.
   - `neg` generally includes all/most version IDs (plus class-specific curation).

5. **ILASP tasks**
   - `ilasp_tasks/version*.las` built from curated files as `#pos/#neg(...@100, ...)`.
   - `versionC.las` has 4 commented-out negative examples.
   - Tasks contain examples only (no appended background/mode declarations in-file).

6. **Learned theories**
   - Stored in `learned_encodings/version*.lp`.

7. **Evaluation utility**
   - `check_aaf_satisfaction.py` evaluates a selected encoding on a selected directory (currently hardcoded defaults).

## Negative-Example Findings

### A) `versionA..G` curated neg files are **not** "flip-one"

For overlapping IDs (`pos/pX.lp` and `neg/pX.lp` for same `pX`):

- argument and attack facts are identical,
- label assignment differs on **every argument**:
  - versionA/B/C: 4 label changes per pair,
  - versionD/E/F: 3 changes per pair,
  - versionG: 5 changes per pair.

So the current curated neg set is "full relabeling per same graph", not one-label perturbation.

### B) `versionE_special_neg.las` is generated from solver-output enumeration

- 9 positive examples are the same positives as `versionE.las`.
- 90 negative examples exactly match the first 90 answer sets in `neg_examples_experimental.lp`.
- `neg_examples_experimental.lp` is a captured clingo output trace (not a reusable generator script by itself).
- The underlying generator constraints are in `neg_generator/versionE.lp`.

## Reproducibility Gaps

1. A single reproducible builder is now available:
   - `build_real_world_dataset.py` can regenerate
     - extracted participant `.lp`,
     - `asp_files/version*/{pos,neg}`,
     - `ilasp_tasks/version*.las`,
     - `learned_encodings/version*.lp` (if ILASP enabled).

2. `extract_labeled_aafs.py` remains extraction-only by design:
   - ILASP task/training orchestration is delegated to `build_real_world_dataset.py`.

3. Class-construction provenance is implicit:
   - curated selection rules per version are not encoded in code/config,
   - negative-generation policy differs across artifacts (curated relabeling vs enumerated generator output).

## Recommended Low-Risk, High-Gain Improvements

1. **Create one canonical builder script**
   - e.g., `Real_World_Examples/build_real_world_dataset.py`
   - inputs: source CSV/XLSX + config JSON
   - outputs: `asp_files`, `ilasp_tasks`, provenance manifest.

2. **Add explicit negative strategy config**
   - `strategy: curated|flip_one|k_flip|constraint_enum`
   - deterministic seed + sample size + uniqueness constraints.

3. **Write provenance manifests**
   - per version: included IDs, source file hashes, strategy, seed, command.
   - prevents "silent drift" in curated sets.

4. **Normalize `.lp` formatting**
   - one atom per line (`arg/att/in/out/undec`) for diffability and parser robustness.

5. **Add consistency checks**
   - verify each `.las` example matches source `.lp`,
   - verify class counts and missing IDs,
   - detect commented examples and report.

6. **Promote `versionE_special_neg` generation to code**
   - replace reliance on `neg_examples_experimental.lp` snapshot with scripted clingo run over `neg_generator/versionE.lp`,
   - support deterministic, auditable selection (instead of "first N answer sets" only).

7. **CLI-ize evaluation**
   - parameterize `check_aaf_satisfaction.py` for input dir, semantics file, output path, and optional pos/neg split metrics.

## Quick Practical Conclusion

Your memory of "negative examples are synthesized by flip-one" does not match current artifacts.
Current data uses:

- curated full relabelings for versionA..G base tasks,
- enumerated constraint-based negatives for `versionE_special_neg`.
