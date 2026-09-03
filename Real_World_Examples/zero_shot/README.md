# Zero-shot (out-of-corpus) check of the learned human semantics σ_H

σ_H — the consensus acceptance policy learned from the Guillaume et al. (2022) corpus (paper,
Section "The Semantics People Follow") — is frozen here as a standalone clingo program and
applied, unchanged, to the stimuli and published aggregate responses of independent studies.
No learning run, no parameter, no fitting: evaluation only.

| file | role |
|---|---|
| `sigma_h_frozen.lp` | σ_H as a labelling verifier: generator + feature/auxiliary backgrounds reproduced verbatim from the learning code, and the five consensus rules audited in `../fastlas_exp/results/sigma_h_principle_audit.json`. Frozen and tagged (`sigma-h-frozen-20260903`) **before** any external data was scored. `clingo 0 sigma_h_frozen.lp af.lp` enumerates the legal labellings. |
| `check_frozen.py` | asserts that the frozen program still equals the audited rule set and backgrounds |
| `verify_external_afs.py` | recomputes the grounded / preferred / CF2 status of all 60 arguments from the transcribed attack relations and asserts equality with a transcription of the semantics-prediction columns of Fig. 2 of the 2019 report |
| `zero_shot_verification.json` | the blind re-transcriptions (three readers for the Fig. 2 majority squares, two for the attack relations, two for the 2018 bar chart) and the reconciliation against the committed files: zero discrepancies |
| `external_afs.py` | the external stimulus frameworks: the 12 AFs / 60 arguments of Cramer & Guillaume (2019, JELIA; technical report arXiv:1902.10552), derived from the natural-language argument sets in its appendix and cross-checked against the semantics-prediction columns of its Fig. 2 (`verify_external_afs.py`: all 60 statuses for grounded/preferred/CF2 match); the 3 AFs of Cramer & Guillaume (2018, COMMA); the 2 AFs of Rahwan et al. (2010) |
| `external_responses.py` | the published aggregate responses: per-argument MAJORITY response of the three participant groups of the 2019 study (transcribed from Fig. 2 of the technical report; independently re-transcribed by three blind readers, `zero_shot_verification.json`), and the per-argument response percentages of the 2018 study (read off its Fig. 4 to about ±3 points) |
| `zero_shot_eval.py` | the evaluation: per-argument agreement with the majority response (acc3, Cohen's κ, committed-only accuracy, commit precision; catalogue semantics under the papers' own justification status; σ_H under the skeptical and the in-corpus credulous projection; a predictor with no labelling/extension on a framework is scored as making no prediction there), the verifier's native labelling-level question (is the whole-framework majority labelling admitted?), a permissiveness control, the two frozen predictions of the paper on their acyclic instances (floating/cyclic reinstatement listed apart), and the rule-4 ablation. Self-tests guard the review findings. Writes `zero_shot_results.json`. |
| `zero_shot_results.json` | the committed record read by `docs/aij_paper/make_zero_shot_table.py` |

Run: `python3 Real_World_Examples/zero_shot/zero_shot_eval.py` (seconds; needs the `clingo` Python module).

Scope note: the 2018 study uses the same three graph shapes as the 2022 corpus (simple /
floating / 3-cycle reinstatement) with independent participants and materials; the 2019
study's twelve frameworks are new shapes (3–8 arguments). Both come from the same research
group as the 2022 corpus. Rahwan et al. (2010) and Bezou-Vrakatseli et al. (2025) report
graded (7-point) confidence rather than three-valued judgements and are used only
directionally.
