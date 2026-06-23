# ArgLAS Finalization Audit

## Implemented

ArgLAS now has a real CLI entrypoint:
- `arglas generate-aafs`
- `arglas label`
- `arglas build-task`
- `arglas learn`
- `arglas benchmark run`
- `arglas benchmark watch`
- `arglas benchmark replay`
- `arglas batch validate`
- `arglas batch cleanup`
- `arglas batch label`
- `arglas batch learn`
- `arglas batch pipeline`

Implementation files:
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/arglas/cli.py`
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/arglas/__main__.py`
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/pyproject.toml`

CLI routing is now in place for maintained benchmark entrypoints:
- benchmark wrappers call `arglas benchmark run`
- watcher wrappers call `arglas benchmark watch`
- legacy batch wrappers call `arglas batch ...`
- benchmark worker processes spawned by the generic runner now call `arglas learn`
- benchmark label generation spawned by the generic runner now calls `arglas label`

Validated during this pass:
- editable install succeeded with `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/.venv/bin/python -m pip install -e .`
- `arglas --help` works
- delegated help works:
  - `arglas learn --help`
  - `arglas benchmark run --help`
- one real learning smoke test succeeded through the CLI:
  - semantics `ADM`
  - partial `0.8`
  - `n_pos=n_neg=5`
  - `noise=0.0`
  - `iterations=1`
  - output root `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/tmp/arglas_cli_smoke`
- benchmark dry run succeeded through the CLI:
  - `arglas benchmark run --config run_configs/prf_noise0_ratio1_parallel3.json`
  - with `DRY_RUN=1 WORKERS=1 ITERATIONS=1`
- batch config validation succeeded through the CLI:
  - `arglas batch validate --config batch_config.json`
- synthetic label-generation/evaluation alignment smoke passed after the P1 fix:
  - semantics `PRF`
  - partial `0.5`
  - `100` AAFs
  - generated files: `473`
  - `pos_bad=0`
  - `neg_bad=0`

P1 has been fixed in:
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/solver_runtime.py`
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/generate_extensions.py`
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/generate_ilasp_task.py`
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/train_test.py`

## Remaining Issues Before Final Validation

### P2. Packaging is validated for editable repo-local use, not for a standalone wheel/sdist deployment
Current state:
- `pip install -e .` works
- the CLI works from the repository and uses the repository tree as the source of ASP/JSON assets
- no standalone distribution test was done for installed assets outside the repo checkout

Impact:
- current support level is: repo-local, editable-install workflow
- if the goal is PyPI-style or wheel-only distribution, asset packaging still needs explicit hardening

Recommendation before final validation:
- if final scope is repo-local usage, no action is required
- if final scope is distribution outside the repo, package static assets explicitly and test a clean install in a separate directory

### P2. The generic watcher is improved but still process-table based
Current state:
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/watch_experiment_grid.py` now restarts via `arglas benchmark run` and matches workers using run-specific train path markers
- it still determines health from `ps` output plus lock files rather than from an explicit heartbeat/state channel

Impact:
- acceptable for current unattended repo-local runs
- still less robust than a persisted worker-state protocol

Recommendation before final validation:
- acceptable to keep for now unless long unattended benchmark supervision is part of the final claim
- otherwise add a small state file / heartbeat per run

### P3. Legacy config fields and wrappers remain for compatibility
Current state:
- `run_configs/*.json` still contain `launcher_script`, which is now effectively legacy metadata
- several legacy shell scripts remain in the tree, though the maintained ones now delegate to `arglas`

Impact:
- low technical risk
- mild maintenance noise

Recommendation before final validation:
- optional cleanup only
- remove or deprecate unused config fields once the final workflow is frozen

## Final Validation Readiness

Ready now for:
- CLI-first repo-local usage
- running learning tasks through `arglas`
- running maintained benchmark configs through `arglas benchmark ...`
- synthetic reruns under a shared strict oracle stack

Not fully ready yet for:
- standalone distribution outside the repository checkout without an additional packaging pass
