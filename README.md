# ArgLAS — learning argumentation semantics as answer set programs

ArgLAS is a small, standalone Python program that **learns the acceptability
semantics of argumentation frameworks** from labelled examples, using
ILASP (Learning from Answer Sets). Given argumentation graphs encoded as ASP
facts (`arg/1`, `att/2`, optionally `support/2`), it labels them with a
reference semantics, builds an ILASP learning task, and induces an explicit,
inspectable logic program — which, for the standard semantics, is provably
equivalent to the textbook ASPARTIX encodings (Theorems 1–3 of the paper,
with full proofs in its Appendix A).

The core is deliberately brief: a dozen small Python modules in `arglas/` and a
handful of short config and `.lp` files in `config/`.

## Requirements

- Python ≥ 3.9 with `clingo` (installed automatically by pip)
- [`ILASP`](https://www.ilasp.com) 4.x on `PATH` (the campaigns used 4.4.1)
- optional, Experiment 2 and the demo's `--engine fastlas` toggle: `FastLAS` 2.1 on `PATH`
- optional, figures/baseline: `matplotlib`, `numpy`, `scikit-learn`, `networkx`

## Install & 60-second start

```bash
pip install -e .
arglas demo                    # generate AAFs -> label (STB) -> ILASP task -> learned program
arglas demo --semantics PRF    # same, for preferred
```

The demo generates 90 random AAFs, labels them with the ASPARTIX reference
semantics, builds a 20+20-example ILASP task, and prints the learned program —
about a minute end to end. (If FastLAS is on your `PATH`, `arglas demo
--engine fastlas` optionally runs the same demo with FastLAS instead of ILASP.)

## The four core commands

```bash
arglas generate-aafs 4 8 100 --output_dir aafs --seed 1     # random AAF pool
arglas label --input_dir aafs --base_output_dir labelled \
             --semantics STB --p_partial 1.0 --allow_empty  # oracle labelling
arglas build-task labelled/labelled_STB_full task.las 20 0.0 --semantics STB
arglas learn --semantics STB --partial 1.0 --f_values 20 --n_values 0.0 \
             --iterations 5 --base_output_dir labelled      # train/test harness
```

`arglas learn` evaluates with framework-disjoint grouped 5-fold CV
(`test_set_policy=grouped_kfold`, the default), the paper's protocol.
Valid `--semantics` names (defined in `config/semantics_config.json`):
`STB`, `ADM`, `CMP`, `PRF`, `GRD`, and the bipolar variants `BAF_STB`,
`BAF_ADM`, `BAF_CMP`.

## Input format

One argumentation framework per `.lp` file, as plain ASP facts — `arg/1`,
`att/2`, and (bipolar frameworks only) `support/2`; any symbolic constants
work as argument names:

```prolog
arg(a). arg(b). arg(c).
att(a,b).
att(b,c).
att(c,a).
support(a,c).            % optional; BAF_* semantics only
```

Filenames **must** match `aaf_<size>_<id>.lp` (e.g. `aaf_3_0.lp`) — the
harness parses the two numbers for framework-disjoint grouping.
`arglas generate-aafs` produces files in this shape already.

Semantics, encodings, and ILASP flags are configured in `config/semantics_config.json`
and `config/ilasp_config.json`; the learning background and mode bias are
`config/background_knowledge.lp` and `config/mode_declarations.las`; reference
encodings live in `config/ASPARTIX/`. Generated data goes under the directory
named by `FABIO_ARTIFACTS_ROOT` (default: the repo root).

## Repository layout

| dir | contents |
|---|---|
| `arglas/` | the standalone learner (10 modules + CLI) |
| `config/` | semantics/ILASP configs, learning backgrounds, mode bias, ASPARTIX encodings |
| `data/` | **committed experimental record**: all 4,065 result rows + generator pools behind the paper's synthetic experiments (see `data/README.md`) |
| `experiments/` | everything used to run the paper's campaigns: the benchmark grid, launchers, breadth generators, calibration scripts, `run_configs/` with pinned seeds |
| `analysis/` | equivalence-check labs (`zlatina_theorems/`), the non-LAS baseline (`tree_baseline/`), figure scripts |
| `Real_World_Examples/` | Experiment 2 (human-study re-analysis): `data/` vs `scripts/` vs `fastlas_exp/` (see its README) |
| `docs/` | the AIJ paper (`docs/aij_paper/`), specs, references, archived planning docs |

(`artifacts/`, `backup/`, `plots/`, `tmp/` are local, gitignored working areas —
as are the outputs the core commands create in the repo root by default:
`aafs/`, `labelled/`, `task.las`, `train/`, `train_output/`, `results/`, and
`demo_run/`. To keep a clone pristine, set `FABIO_ARTIFACTS_ROOT` to a
directory outside the repo and all generated data goes there instead.)

## Reproducing the paper

**In minutes (from the committed record — no learning re-run needed):**

```bash
python3 docs/aij_paper/make_figs.py                      # all paper figures, from data/
python3 analysis/make_plots.py                           # Exp1/Exp2 summary plots -> analysis/figs_regen/
python3 analysis/tree_baseline/tree_baseline.py          # §7 non-LAS baseline (~1 min) -> results_regen.json
python3 analysis/zlatina_theorems/check_equivalence.py 4 # Thm 1 equivalences -> level1_results_regen.json
cd docs/aij_paper && pdflatex aij_draft.tex              # the manuscript
```

The analysis re-runs write `*_regen` twins next to the committed records — diff them
to verify (for `make_plots.py` / `tree_baseline.py`, `--overwrite` replaces the
committed files instead). `check_equivalence.py` takes an optional positional bound:
`4` is the exhaustive 66,066-AF check behind the committed results; without it a
quick nmax=3 smoke run is performed.

**From scratch (days; deterministic seeds in `experiments/run_configs/`):**

```bash
nohup ./experiments/run_v2_campaign.sh &   # Experiment 1 (3,510 runs)
nohup ./experiments/run_v3_gap.sh &        # breadth campaigns (555 runs)
python3 -m arglas benchmark progress --config experiments/run_configs/final_synthetic_v2_pos50.json
```

Both launchers are stop/resume-safe (kill anytime; rerun to resume). The
n=10–12 regime is memory-heavy: use `experiments/run_large_safe.sh` (workers=1
+ memory watchdog).

## Correctness

The learned stable/admissible/complete encodings are proved equivalent to the
ASPARTIX references — on abstract, bipolar, and value-based frameworks — and the preferred
construction is proved correct; statements and full proofs are in the paper
(Section 4 and Appendix A). The scripts in `analysis/zlatina_theorems/`
independently re-check these equivalences on finite framework pools.
