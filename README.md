# ArgLAS

ArgLAS is a CLI-first tool for learning abstract argumentation semantics with ILASP and benchmarking the learned theories against ASPARTIX/clingo ground truth.

The repository is prepared for final benchmark runs around a small stable surface:
- reusable CLI entrypoints for learning and benchmarking
- core Python modules used by the CLI
- benchmark JSON configs in `run_configs/`
- references, curated real-world data, and documentation

Historical artifacts and deprecated wrappers were archived under:
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/backup/pre_final_cleanup_20260309_212003`

## Install

ArgLAS is intended to be used from this repository with a clingo-enabled Python environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

Runtime prerequisites:
- `ILASP` available on `PATH`
- `clingo` importable from the active Python interpreter

Recommended for clean benchmark runs:

```bash
export FABIO_ARTIFACTS_ROOT="$PWD/artifacts/final_benchmark"
mkdir -p "$FABIO_ARTIFACTS_ROOT"
```

## Main CLI

```bash
arglas --help
```

Core commands:
- `arglas generate-aafs ...`
- `arglas label ...`
- `arglas build-task ...`
- `arglas learn ...`
- `arglas benchmark run ...`
- `arglas benchmark watch ...`
- `arglas benchmark replay ...`
- `arglas batch validate ...`
- `arglas batch cleanup ...`
- `arglas batch label ...`
- `arglas batch learn ...`
- `arglas batch pipeline ...`

## Typical Learning Workflow

1. Generate AAFs

```bash
arglas generate-aafs 4 8 100 --output_dir aafs
```

2. Label them under a semantics

```bash
arglas label \
  --semantics ADM \
  --p_partial 0.8 \
  --input_dir aafs \
  --base_output_dir labelled \
  --allow_empty
```

3. Run a learning task

```bash
arglas learn \
  --semantics ADM \
  --partial 0.8 \
  --f_values 10 20 30 \
  --f_neg_values 10 20 30 \
  --n_values 0.0 \
  --iterations 1 \
  --base_output_dir labelled \
  --train_dir train \
  --train_output_dir train_output \
  --results_dir results/ADM_partial_0_8_noise_0_0_ratio_1 \
  --no_prefix
```

Default publication protocol:
- deterministic fixed balanced hold-out test set
- full `in/1,out/1` exact model-set matching

Legacy evaluation is still available explicitly through:
- `--test_set_policy balanced_remaining`
- `--test_set_policy all_remaining`
- `--eval_match_policy existential_acceptance`

## Benchmark Grids

Benchmarks should be launched through JSON configs and the benchmark CLI.

Run a grid:

```bash
arglas benchmark run --config run_configs/prf_noise0_ratio1_parallel3.json
```

Watch and auto-restart a grid:

```bash
arglas benchmark watch --config run_configs/prf_noise0_ratio1_parallel3.json
```

Replay archived learned models through the current evaluator:

```bash
arglas benchmark replay \
  --archive_root backup/pre_final_cleanup_20260309_212003/artifacts/_old_results/prf_full_grid_ratio1_before_full_exact_model_20260307_014741 \
  --semantics PRF \
  --output_root benchmarks/replays/prf_old_models_replayed_full_exact
```

## Batch Config Pipeline

The `batch_config.json` workflow is also routed through the CLI.

```bash
arglas batch validate --config batch_config.json
arglas batch label --config batch_config.json
arglas batch learn --config batch_config.json
arglas batch pipeline --config batch_config.json
```

Older shell wrappers were archived in the backup tree and should not be used for new runs.

## Repository References

Do not modify these directories when editing ILASP/clingo logic:
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/ILASP_Reference`
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/clingo_reference`

## Current Status

The CLI entrypoint is in place and benchmark launchers are routed through it. See:
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/arglas/cli.py`
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/docs/ARGLAS_FINALIZATION_AUDIT.md`
- `/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_codex/docs/WORKSPACE_LAYOUT.md`
