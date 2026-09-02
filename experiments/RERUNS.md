# Targeted re-runs (post status-audit, 2026-07-17)

Three self-contained re-runs recommended by the round-3 review and the 2026-07-17 status
audit (`docs/aij_paper/review_round3_todo.md`). None is a campaign re-run: the judge panel
was unanimous that a fresh full campaign (~6–7 days) would orphan the four derived records
that address the v2 learned models by filename. These are the cheap, high-value additions.

Everything goes through one launcher, `experiments/run_reruns.sh`. Every run is
stop/resume-safe (kill any time; rerun the identical command to resume), writes only under
`artifacts/` (never `data/`), and is memory-safe at `workers=7` — all three stay at
`n ≤ 8` arguments, far from the 7–8 GB tasks of the `n=10–12` regime.

## The three runs

| command | what it settles | runs | expected wall-clock | worst case |
|---|---|---|---|---|
| `baf-anchor` | Bipolar frameworks under **partial labels and noise** (p∈{1,.5}, q∈{0,.1}, f∈{20,60}); today BAF/ABA are clean-label-only, and the breadth caption had to be scoped accordingly. On the committed `data/v3_baf` pool. | 120 | 2–4 h | ~8 h (all 60 noisy runs at the cap) |
| `self-prf-recap` | Whether the PRF self-attack "boundary" is an **accuracy floor or a compute frontier**: the four q=0.1 cells whose reported 0.71/0.42 rest on 2/10 and 6/10 completions, re-run at a **4× cap (14,000 s)** with the identical pool and seeds. | 20 | several hours | ~12 h (20 tasks, ≤7 concurrent, up to 14,000 s each) |
| `seedb` | A **between-realization replicate** of the uncensored headline cells with a fresh pool draw and fresh seeds (master 20260901): the clean balanced arm (360 runs) + the uncensored q=0.2 buy-back cells at p≥0.75, f∈{10,80} (80 runs). Can only tighten error bars, never change a conclusion. | 440 | 1–2 h | ~6 h |

Priority if time is short: `self-prf-recap` (the only re-run whose omission limits what a
referee can conclude), then `baf-anchor`, then `seedb`.

## Before you start (once, on a fresh machine)

```bash
pip install -e .              # arglas + clingo
which ILASP                   # ILASP 4.x must be on PATH (the campaigns used 4.4.1)
python3 -m arglas batch validate
```

## Running

Smoke-test first (one cell, two folds, separate `*_smoke` root, a couple of minutes):

```bash
./experiments/run_reruns.sh baf-anchor smoke
./experiments/run_reruns.sh self-prf-recap smoke
./experiments/run_reruns.sh seedb smoke
```

Then launch detached, one at a time (the launcher refuses to overlap grids — they share
the 7 workers and the pipeline files, which must not be edited while a grid runs):

```bash
nohup ./experiments/run_reruns.sh self-prf-recap > self_prf_recap.out 2>&1 &
nohup ./experiments/run_reruns.sh baf-anchor     > baf_anchor.out     2>&1 &   # after the first finishes
nohup ./experiments/run_reruns.sh seedb          > seedb.out          2>&1 &
./experiments/run_reruns.sh status                # row counts + whether a grid is running
```

If the machine restarts or you kill a run, rerun the same command: completed rows are
skipped at row granularity, pools are reused. Note the one resume caveat inherited from the
grid: a row that **timed out** is recorded as done and is not retried — which is exactly why
`self-prf-recap` runs in its own root at its own cap rather than resuming `data/v3_self`.

## When a run finishes

```bash
./experiments/run_reruns.sh collect self_prf_recap   # -> data/self_prf_recap/{results,aafs,train_output,README.md}
./experiments/run_reruns.sh collect baf_anchor
./experiments/run_reruns.sh collect seedB
git add data/<name> && git commit
```

`collect` copies the per-fold results, the exact framework pool, and `train_output/` (the
learned programs that `LEARNED_MODEL_FILENAME` points at — commit them; the exactness,
hard-negative and transfer audits need them). Then fold the numbers into the paper:

- **self-prf-recap** → Section 5.4 "Under noise the regimes separate" and the Limitations
  sentence on PRF/self-attacks. Built-in check: the 8 runs that completed within 3,500 s in
  `data/v3_self` (PRF q=0.1: p=0.5 f=20 ×3, p=1.0 f=20 ×3, p=0.5 f=60 ×1, p=1.0 f=60 ×1) use
  identical pools and seeds and must reproduce their `MCC_FULL` exactly; the 12 previously
  censored runs are the new information. Report either the recovered accuracy or the new
  timeout count — both are cleaner claims than the current one.
- **baf-anchor** → `tab:breadth`/`fig:breadth` and the Limitations clause "bipolar and ABA
  breadth arms are clean-label, complete-information runs only". Aggregate on `MCC_FULL`
  (populated at p=0.5 now that the sibling-pool bug is fixed) with the same conventions as
  `docs/aij_paper/make_figs.py`.
- **seedb** → one footnote number in Section 5.2: how far the cell means moved between the
  two realizations (compare against `data/exp1_v2`, balanced arm, same cells). Add it to
  Appendix B via `make_appendix_tables.py` if you want the full table.

## Configs (all seeds pinned)

| config | root | pool | seeds |
|---|---|---|---|
| `run_configs/v3_baf_anchor.json` | `artifacts/final_synthetic_v3_baf_anchor` | copied from `data/v3_baf/aafs` | same as v3 (master 20260309) |
| `run_configs/v3_self_prf_recap.json` | `artifacts/final_synthetic_v3_self_prf_recap` | copied from `data/v3_self/aafs` | identical to `v3_breadth_self` |
| `run_configs/seedB_clean.json`, `seedB_noisy.json` | `artifacts/final_synthetic_seedB` (shared) | generated, seed 20260901 | master 20260901, label 20260902, task 20260903, test 20260904 |

The smoke mode derives a one-cell/two-fold variant of the real config on the fly (lowest
`p` so the complete-information sibling pool is exercised), so there is a single source of
truth per experiment.
