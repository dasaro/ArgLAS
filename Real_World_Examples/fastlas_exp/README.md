# FastLAS experiments for argumentation semantics learning

Goal: use local FastLAS 2.1.0 (`/usr/local/bin/FastLAS`) — much faster than ILASP at the cost of
representability — to learn per-condition acceptance semantics over a WIDER search space in far
less time than ILASP (which times out on the soft-neg-optimised / enriched space, 74–135 s/call).

## RESULT (2026-07-02): SOLVED — 4 working formulations, all clingo-verified, all ≫ faster than ILASP

Every strategy recovers grounded EXACTLY on all distinct condition-D graphs (independently
clingo-verified against the reference `{in:-supported. out:-defeated.}`), 30–600× faster than ILASP.

| # | Formulation | Best mode / time | Learned theory |
|---|---|---|---|
| **S4** | **OPL VERIFIER** — labelling GIVEN in context, learn a target-independent `violated` | **OPL 0.22 s** (NOPL 1.17 s, identical) | `violated:-attacked_by_in(X),not out(X).`  `violated:-defended(X),not in(X).` |
| **S2** | **CONSTRAINTS-ONLY** — labelling as context facts, learn `false:-body` pruning constraints | **OPL 0.27 s** (NOPL 0.61 s) | `false:-supported(X),not in(X).`  `false:-defeated(X),not out(X).` |
| **S1** | **FEATURES-AS-FACTS** — precompute supported/defeated as context facts, learn in/out defs | NOPL 0.56 s (OPL 0.06 s, pos-only) | `in(X):-supported(X).`  `out(X):-defeated(X).` |
| **S3** | **aaai-style LATENT** — observed `ok/bad` legality over given `lab/2`, latent `just_in/out` | NOPL 2.2 s (OPL UNSAT) | `just_in(X):-supported(X).`  `just_out(X):-defeated(X).` |

Winning files: `s4_task2.las`, `s2_gadgets.las`, `s1_M_feats_det_flip.las`, `s3_grounded.las`
(+ each strategy's generator/verifier `sN_*.py`).

## The unifying insight (why OPL kept failing, and the fix)
FastLAS-OPL **cannot use body features that depend on the predicate being learned.** The faithful
Dung task learns `in`/`out` whose features (`supported`/`defeated`) are themselves defined from
`in`/`out` → recursive → FastLAS drops them from the candidate space → OPL-UNSAT / att-only collapse.
**Every working formulation resolves this identically: make the labelling/features GIVEN INPUT
(context facts) instead of the derived target.** Then the features are ground EDB, not target-IDB,
and the search space is intact.
- S4/S2: give the full labelling as context, learn a *verifier*/*constraints* over it.
- S1: precompute the features as context facts, learn the in/out *definitions*.
- S3: give the labelling as `lab/2`, learn the latent operator behind observed legality (the
  `aaai_2020_task` "learn `valid_move` behind observed `valid`" pattern).

## OPL vs NOPL — the verdict (answers the core question)
- The **direct "learn in/out with recursive features"** task is **OPL-UNSAT** (feature/target coupling).
- **Reframed** (verifier S4 / constraints S2 / features-as-facts S1), the task becomes **OPL-able and
  OPL is 2–6× FASTER than NOPL with byte-identical results.** ⇒ **Use OPL** (S4 verifier @0.22 s or
  S2 constraints @0.27 s) for the least-time-consuming pipeline.
- **NOPL** is the correct fallback whenever the formulation keeps choice/recursion in the target, or
  needs hard `#neg` pinning (S1-with-negs, S3). NOPL also fast (0.56–2.2 s).

## Representability cost (honest caveats for the paper)
1. FastLAS learns **COMPLETE-labelling constraints**, not grounded directly. **Grounded = learned-
   complete + minimality**, and minimality is a non-local property NOT expressible as local
   constraints — recovered by a FIXED `#minimize{1,X:in(X);1,X:out(X)}` at deploy time, or a
   precomputed minimality-aware feature (matches the `arglas-grd-learnability` note). For **STABLE**
   (the Exp2 bridge target) this issue does not arise → the plain formulation transfers directly.
2. FastLAS grammar rejects `:` conditional literals in background (use `not_supported`+negation).
3. Learns normal rules + constraints (via `#modeh(false)`), not choice rules.

## Recommended pipeline for Exp2
FastLAS-**OPL** learns the legality verifier / complete-constraints in ~0.2–0.3 s; a fixed
generate-step (`0{in}1;0{out}1` + `:- violated.`/learned-constraints + `#minimize`/`#maximize undec`)
reconstructs the semantics. 30–600× faster than ILASP ⇒ the enriched/wider search space (reach,
in_cycle, higher maxv) that ILASP could not afford is now tractable. NEXT: (a) scale to STB/CF2 and
the cyclic condition G (the CF2 case ILASP timed out on); (b) run the real noisy human-data learning.

## Core files
- `fl_build.py` — shared generator (det/choice variants, enrichment, shell negatives, grounded_cells).
- `run_probe.py` — OPL/NOPL probe driver. `sN_*` — per-strategy tasks, generators, verifiers.
