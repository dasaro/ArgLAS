# Experiment 2 — learning the semantics humans use

Re-analysis of the Guillaume et al. (2022, PLOS ONE) human argumentation study with
ILASP and FastLAS. Scripts and data are separated:

| dir | contents |
|---|---|
| `data/` | the human-study source data: `Raw_Data_original.xlsx` (primary workbook), preprocessed/processed CSVs, and the source paper (`data/source_paper/pone.0273225.pdf`) |
| `scripts/` | the Exp2 pipeline: `extract_labeled_aafs.py` (xlsx → per-participant AAFs), `build_real_world_dataset.py` (end-to-end builder), `discover_semantics.py` (core ILASP discovery module), `apples_to_apples.py` (learned-vs-textbook comparison + McNemar), `cv_real_world_pos_only.py`, `run_discovery_cv.py`, and the four klingo comparison drivers |
| `fastlas_exp/` | the FastLAS/OPL protocol behind the paper's §7–8: scripts, `results/*.json` (tracked; read by `analysis/make_plots.py`), and the standalone `paper/exp2.tex` draft; see `fastlas_exp/README.md` |
| `asp_files/`, `ilasp_tasks/`, `learned_encodings/`, `neg_generator/` | curated derived data per study condition (versionA–G), kept at stable paths (referenced by comparison scripts) |
| `runs/`, `_tmp_extract_*` | regenerable outputs (gitignored). `_tmp_extract_all2/` is the extraction pool `discover_semantics.py` reads; regenerate with `python3 scripts/extract_labeled_aafs.py --output-dir _tmp_extract_all2` if absent |

Reproduction: the paper's Exp2 numbers come from the tracked `fastlas_exp/results/*.json`;
`python3 analysis/make_plots.py` (repo root) rebuilds the Exp2 figures from them in
seconds. Re-running the learning itself requires ILASP 4.4 and FastLAS 2.1 on PATH.
