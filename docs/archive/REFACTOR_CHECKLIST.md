# Refactor Checklist

This checklist is intended to be executed in order, with validation after each step.

Scope:
- Synthetic benchmark orchestration
- Artifact layout
- Evaluation/reporting pipeline
- Label/evaluation consistency

Out of scope for the first pass:
- Real-world pipeline redesign
- ILASP/ASPARTIX theory changes not required for correctness
- Re-running historical benchmarks except as validation

Read-only references:
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/ILASP_Reference`
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/clingo_reference`

## Safety Rules

- Do not modify the active benchmark while a long-running job is still needed.
- Do not overwrite historical outputs.
- Keep resume semantics intact at every step.
- Keep existing CSV schemas backward-readable.
- After each phase, run a smoke test before proceeding.

## Phase 0: Freeze And Inventory

Goal:
- Establish a clean starting point and avoid editing against unknown runtime state.

Steps:
- [ ] Record active launcher, watcher, worker, and ILASP processes.
- [ ] Record the active output roots for `results`, `train`, `train_output`, and `logs`.
- [ ] Snapshot current script entrypoints:
  - `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/run_prf_full_grid_ratio1_parallel3.zsh`
  - `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/run_prf_noise0_ratio1_parallel3.zsh`
  - `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/watch_prf_full_grid_ratio1_parallel3.py`
  - `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/watch_prf_noise0_ratio1_parallel3.py`
  - `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/train_test.py`
  - `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/generate_extensions.py`
- [ ] Record current known issues:
  - stale lock/pid files
  - runner/watcher duplication
  - timeout-heavy results flattening metrics
  - PRF label/evaluation mismatch

Validation:
- [ ] A short audit note exists with current process IDs and active paths.
- [ ] No files have been moved yet.

Stop if:
- A benchmark is still running and must not be interrupted.

## Phase 1: Establish Minimal Repo Hygiene

Goal:
- Make the repository manageable before structural edits.

Steps:
- [ ] Create a `.gitignore` that ignores:
  - `.venv/`
  - `.venv311/`
  - `__pycache__/`
  - `.DS_Store`
  - `.vscode/`
  - generated artifact trees:
    - `logs/`
    - `plots/`
    - `results/`
    - `train/`
    - `train_output/`
    - `tmp/`
    - `_old_results/`
    - zipped result bundles
- [ ] Confirm that source/config/reference files remain visible.
- [ ] If desired, create an initial git commit before refactor work starts.

Files:
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/.gitignore`

Validation:
- [ ] `git status --short` shows source files cleanly and does not drown in artifacts.

Stop if:
- Important source files are accidentally ignored.

## Phase 2: Separate Source From Artifacts

Goal:
- Stop further sprawl in the repository root.

Target layout:
- `artifacts/logs`
- `artifacts/results`
- `artifacts/train`
- `artifacts/train_output`
- `artifacts/plots`
- `artifacts/tmp`

Steps:
- [ ] Introduce a single artifact-root setting, defaulting to current paths for backward compatibility.
- [ ] Add path resolution helpers so scripts can compute:
  - logs dir
  - results dir
  - train dir
  - train_output dir
  - plots dir
  - tmp dir
- [ ] Make new runs write to the new artifact root.
- [ ] Keep legacy roots readable during migration.
- [ ] Do not move historical files yet unless explicitly archiving.

Files likely touched:
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/train_test.py`
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/plot_partial_grid.py`
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/plot_collected_accuracies.py`
- launcher/watcher scripts

Validation:
- [ ] A smoke run writes all generated files under the configured artifact root.
- [ ] Old result directories can still be read by plotting and replay scripts.

Stop if:
- Resume logic depends on hardcoded root paths that have not been migrated.

## Phase 3: Replace Forked Launchers With One Generic Runner

Goal:
- Remove near-duplicate `run_*.zsh` scripts and centralize orchestration logic.

Target:
- one generic launcher script, parameterized by config

Recommended shape:
- `run_experiment_grid.zsh`
- config via env vars or a JSON/YAML/TOML file

Parameters to support:
- semantics
- partial list
- noise list
- ratio / `f_values` / `f_neg_values`
- totals
- iterations
- workers
- output prefix / run id
- timeouts
- evaluation policy
- overwrite/resume mode

Steps:
- [ ] Extract shared logic from:
  - `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/run_prf_full_grid_ratio1_parallel3.zsh`
  - `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/run_prf_noise0_ratio1_parallel3.zsh`
  - `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/run_grd_noise0_ratio1_parallel3.zsh`
- [ ] Remove semantics-specific or grid-specific assumptions from the runner body.
- [ ] Ensure logs, lock files, and worker logs derive from a run-id rather than script filename.
- [ ] Preserve resume behavior.

Validation:
- [ ] PRF noise=0 smoke run works through the generic launcher.
- [ ] GRD noise=0 smoke run works through the same generic launcher.
- [ ] Existing completed CSVs are skipped correctly.

Stop if:
- The generic runner still needs script-specific condition matching logic.

## Phase 4: Replace Forked Watchers With One Generic Watcher

Goal:
- Supervise runs by declared run-id/config, not by copied regexes.

Target:
- one generic watcher script, parameterized by run-id and expected grid

Steps:
- [ ] Extract shared logic from:
  - `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/watch_prf_full_grid_ratio1_parallel3.py`
  - `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/watch_prf_noise0_ratio1_parallel3.py`
  - `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/watch_grd_noise0_ratio1_parallel3.py`
- [ ] Match launcher, workers, and ILASP children using run-id/path prefix, not broad PRF regexes.
- [ ] Make lock/pid handling robust to stale files.
- [ ] Log restart reasons clearly.
- [ ] Ensure the watcher can distinguish:
  - launcher active
  - workers active
  - ILASP active
  - all dead

Validation:
- [ ] Kill a worker manually in a smoke test and confirm restart behavior.
- [ ] Kill the launcher and confirm the watcher restarts only the correct run.
- [ ] Confirm unrelated runs are not counted as healthy.

Stop if:
- Watcher health checks still rely on semantics-only matching.

## Phase 5: Align Synthetic Label Generation With Evaluation

Goal:
- Use the same semantics stack for label generation and evaluation.

Current issue:
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/generate_extensions.py` verifies examples against plain semantics only.
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/train_test.py` evaluates with:
  - `background_knowledge.lp`
  - completion rules
  - stage-specific clingo args
  - stage-specific `#show`

Steps:
- [ ] Introduce a shared solver helper for:
  - label generation
  - learned evaluation
  - ground-truth evaluation
- [ ] Make `generate_extensions.py` use the same stage-aware stack as the evaluation ground truth.
- [ ] Re-audit PRF labeled datasets.
- [ ] Regenerate affected datasets if mismatch persists.

Files likely touched:
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/generate_extensions.py`
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/solver_policy.py`
- possibly a new shared solver utility

Validation:
- [ ] Oracle-vs-oracle exact-match smoke test reaches 100%.
- [ ] Previously mismatched PRF positives are reduced to zero or explicitly explained.

Stop if:
- Label generation and evaluation still produce different answers for the same labeled file.

## Phase 6: Make Reporting Separate Failures From Learned Quality

Goal:
- Avoid presenting timeout baselines as model behavior.

Steps:
- [ ] Add reporting splits:
  - all rows
  - success-only rows
  - timeout/failure rates
- [ ] Update plots to show timeout rate alongside accuracy/F1.
- [ ] Ensure partial plots and comparison plots use explicit labels.
- [ ] Keep legacy metrics available for backward comparison.

Files likely touched:
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/train_test.py`
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/plot_partial_grid.py`
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/compare_test_protocols.py`
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/compare_live_vs_replayed_exact.py`

Validation:
- [ ] A timeout-heavy PRF slice no longer looks like a legitimate accuracy plateau without an explicit timeout warning.

Stop if:
- Main plots still collapse timeout rows into the same view without annotation.

## Phase 7: Add A Minimal Test Harness

Goal:
- Prevent regressions while refactoring orchestration.

Recommended tests:
- [ ] Oracle-vs-oracle exact evaluation smoke test
- [ ] Resume test with partially filled CSV
- [ ] Stale lock recovery test
- [ ] Watcher restart test
- [ ] Generic launcher PRF smoke run
- [ ] Generic launcher GRD smoke run

Validation:
- [ ] Tests can be run from a single command.

Stop if:
- The generic runner/watcher cannot be validated without ad hoc manual inspection.

## Phase 8: Deprecate Legacy Entry Points

Goal:
- Reduce confusion and stop future drift.

Steps:
- [ ] Mark old runner/watcher scripts as deprecated.
- [ ] Replace their bodies with thin wrappers or remove them after migration.
- [ ] Update `AGENTS.md` with the new canonical orchestration path.

Validation:
- [ ] There is one obvious way to launch and one obvious way to watch a benchmark.

## Recommended Execution Order

1. Phase 1
2. Phase 2
3. Phase 3
4. Phase 4
5. Phase 7 smoke tests for orchestration
6. Phase 5
7. Phase 6
8. Phase 8

## Definition Of Done

- One generic runner
- One generic watcher
- Artifact root configurable and not polluting repo root
- Synthetic labeling consistent with evaluation
- Reporting separates failures from learned quality
- Minimal smoke/regression tests exist
- `AGENTS.md` points to the canonical workflow
