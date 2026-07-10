# Workspace Layout

## Active Surface

The final benchmark should be run from these top-level paths only:

- `arglas/`: CLI package
- `run_experiment_grid.py`, `watch_experiment_grid.py`: generic benchmark engine
- `generate_aafs.py`, `generate_extensions.py`, `generate_ilasp_task.py`, `train_test.py`
- `solver_policy.py`, `solver_runtime.py`, `ilasp_policy.py`, `artifact_paths.py`
- `run_configs/`: benchmark configs
- `ASPARTIX/`, `ILASP_Reference/`, `clingo_reference/`
- `Real_World_Examples/`
- `semantics_config.json`, `ilasp_config.json`, `batch_config.json`
- `background_knowledge.lp`, `mode_declarations.las`, `generate_aafs.lp`

## Archived Material

Historical artifacts, deprecated wrappers, and old analysis helpers were archived under:

- `backup/pre_final_cleanup_20260309_212003`

See:

- `backup/pre_final_cleanup_20260309_212003/MANIFEST.md`

## Benchmark Output Policy

For new final runs, use a dedicated artifact root instead of repopulating the repository root:

```bash
export FABIO_ARTIFACTS_ROOT="$PWD/artifacts/final_benchmark"
mkdir -p "$FABIO_ARTIFACTS_ROOT"
```

This keeps generated AAFs, labelled data, tasks, learned theories, results, plots, logs, and temporary files outside the code surface.
