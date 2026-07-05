# v3 gap experiments — generator breadth (G) + framework breadth (F)

Two experiments that close the external-validity gaps flagged by the Exp1 bias audit and
required by the AIJ outline (`docs/aij_outline/`, §5.4): every v2 claim currently rests on
**one generator regime** (n=4..8, dense `s~U[n, n(n-1)]`, no self-attacks), and learning is
demonstrated **only on AAF** while the paper claims a unifying framework across
AAF/BAF/ABA/VAF. Designed to launch **immediately after the v2 campaign finishes, on the
same 7-worker infrastructure**, with the same resume/skip semantics, dual-surface
evaluation and failure taxonomy.

**Total: 615 rows** (G: 540, F: 75). Estimated wall-clock: **~3–6 days** sequential
(F first: hours; G-sparse/self: ~0.5–1 day each; G-large: 1–2.5 days — see §6 risks).

**Ground rule:** while v2 is running, *nothing it reads may change* (grid subprocesses
re-load `*.py`, `semantics_config.json`, `ilasp_config.json`, `background_knowledge.lp`
at every fold). Everything staged now is inert new files; the four small patches in §4 are
applied only after v2's final row. `run_v3_gap.sh` refuses to start until both conditions
hold (no live grid process + patches applied).

---

## 1. Experiment G — generator-breadth sweep

**Question.** Do the v2 recovery headlines survive under different graph regimes, or are
they an artifact of one dense generator?

**Design.** Three regimes, each an independent AAF pool + the same anchor slice of the v2
grid. The anchor slice (2×2×2 per semantics) is chosen to make regime deltas readable at
matched coordinates against v2, not to re-map the whole surface:

| axis | values | rationale |
|---|---|---|
| semantics | ADM, CMP, STB, PRF (+ GRD noise-free) | as v2 (GRD×noise exclusion carries over) |
| partial `p` | 1.0, 0.5 | endpoints of the v2 range |
| noise `q` | 0.0, 0.1 | clean + the v2 "binding constraint" level |
| examples/class `f` | 20, 60 | pre/post the v2 knee |
| proportions | 50/50 only | proportions were second-order in v2; don't re-cross |
| folds | K=5 grouped CV | as v2 |

Rows per regime: (4·2·2·2 + 1·2·1·2) cells × 5 folds = **180**; three regimes = **540**.

**Regimes** (config: `run_configs/v3_breadth_{sparse,self,large}[_grd].json`):

1. **G-sparse** — attack count `s ~ U[n, 2n]` instead of `U[n, n(n-1)]` (attack/argument
   ratio 1–2, the regime of most benchmark and human-authored graphs). Pool seed 20260801.
2. **G-self** — self-attacks permitted: guess over all ordered pairs incl. `X=Y`,
   `s ~ U[n, n²]`. The encodings are already verified for self-attacks (the 66,066-AF
   exhaustive sweep includes them). Pool seed 20260802.
3. **G-large** — `n ∈ {10,11,12}`, 60 AAFs/size, v2 density. Stresses oracle enumeration
   and ILASP grounding rather than semantics. Pool seed 20260803.

Sampling seeds (`test_sampling_seed` 20260312 etc.) are kept identical to v2 on purpose:
the pools differ by construction, and keeping the sampling machinery fixed makes regime
deltas attributable to the generator alone.

**ETA arithmetic.** Per regime, 80 rows at q=0.1 are the only slow ones (STB/PRF can hit
the 3500 s train cap): worst case 80×3500 s / 7 workers ≈ 11 h + fast rows ≈ few hours.
G-large adds labelling and grounding overhead (see §6, R1).

**Analysis deliverable.** One Δ-table + one figure per regime: `MCC_FULL` (complete-info
surface) at the 36 matched cells vs the v2 values, with bootstrap CIs over folds. Claim
template for the paper: *"headline X persists in sparse/self-attack/larger regimes (Δ ≤ ε)"*
or an honest boundary statement where it does not.

**Acceptance criteria.**
- Pool sanity (checked before launching the learning grid): density within the regime's
  range; G-self pools contain self-attacks (expected ~n/(n+1) share of AAFs at s≥n… report
  observed count), G-sparse/G-large contain none; all pools deduplicated (generator
  guarantees uniqueness).
- ≥ 98% of rows end in a terminal state other than ERROR (TIMED_OUT and UNSAT are
  legitimate recorded outcomes, as in v2).
- Every v2-vs-regime comparison cell has all 5 folds present.

## 2. Experiment F — framework breadth (BAF + ABA learning cells)

**Question.** Does the *learning* pipeline — not just the verified encodings — work beyond
AAF? This turns the unifying-framework claim from "verified equivalences" into
"demonstrated end-to-end learning" for two more framework families.

### F1 — BAF cells (45 rows)

The elegant part: **the hypothesis space does not change at all** — the verified BAF
learned encodings use exactly the AAF mode bias (`in/out/arg/defeated/not_defended`);
only the background changes (`defeat/2` extended through support). This is precisely the
paper's unifying-framework story, now as a learning experiment.

- **Pool:** 500 BAFs (n=4..8, 100/size, seed 20260804) via `generate_bafs.py` — the v2 AAF
  generator + support facts sampled among non-attack ordered pairs, `|support| ~ U[0, n]`,
  att∩support = ∅ (Cayrol & Lagasquie-Schiex convention), cycles allowed (the closure rule
  handles them). Files keep the `aaf_<n>_<i>.lp` naming so the grid works unchanged.
- **Oracles (labelling):** `ASPARTIX/baf_{stable,admissible,complete}.lp` — guess-style
  encodings + support closure + support-extended defeat, byte-for-byte the formulations
  machine-verified in `analysis/zlatina_theorems/check_baf.py` (3,256 BAFs, 0 CE) and
  proved by anthem+Vampire (`analysis/zlatina_theorems/anthem/baf2_*`). Already
  cross-checked against the verified learned encodings on smoke BAFs.
- **Learning background:** `bg_baf.lp` = `background_knowledge.lp` + closure + the two
  support-defeat rules, with `supported/1` redefined the thesis-§4.3 way. **GRD-BAF is out
  of scope** for exactly this reason: the AAF grounded target uses the *other* `supported/1`
  ("all attackers out") — a semantics clash to resolve in follow-up work, not here.
- **Grid:** BAF_STB/BAF_ADM/BAF_CMP × p=1.0 × q=0 × f∈{10,20,40} × 5 folds = 45 rows
  (`run_configs/v3_baf.json`; artifact root `artifacts/final_synthetic_v3_baf`).
  Clean-and-complete labels only: the robustness surface is Experiment G's job; F answers
  the qualitative "does it learn the right theory" question.
- **ILASP:** default `--version=4` (no `ilasp_config.json` entry needed; the choice-rule
  background is the standard regime, unlike no-choice GRD).

**Acceptance:** `MCC_FULL ≥ 0.99` at f=40 for all three semantics; learned hypotheses
answer-set-equivalent to the verified targets on the holdout BAFs (spot-check with the
`check_baf.py` machinery); support facts present in labelled pool files (guarded by patch
§4.3 — today `generate_extensions.py` would silently drop them).

### F2 — ABA cells (30 rows)

End-to-end test of the **corrected** ABA→AAF translation feeding the standard pipeline —
the full "unifying" path: ABA → (fixed per-root translation) → AAF pool → label → learn →
dual-surface eval. Uses the exhaustive reference construction (`ref_arguments`/
`ref_attacks` from `analysis/zlatina_theorems/check_aba_transform.py`), which the lab
validated ≡ the fixed per-root domRec program on 500/500 random flat ABAs — the *published*
step-1 program drops arguments (worklist item 1.1) and is not used.

- **Pool:** 300 translated AAFs (3–12 arguments) from random flat ABAs (4–7 atoms, ≤8
  rules, 2–4 assumptions), seed 20260805, via `translate_abas.py`. Each instance ships with
  an `aba_source_*.txt` sidecar recording the source ABA and the argument table, so learned
  theories remain traceable to assumption-level structure. Translated pools organically
  contain self-attacks (an assumption attacking itself via its own contrary) — a free
  robustness bonus.
- **Grid:** plain STB/ADM (unchanged `semantics_config` entries — these are AAF instances)
  × p=1.0 × q=0 × f∈{10,20,40} × 5 folds = 30 rows (`run_configs/v3_aba.json`; root
  `artifacts/final_synthetic_v3_aba`; no `aaf_generation` block — the launcher pre-populates
  the pool, and the grid's "dir exists" path takes over).

**Acceptance:** `MCC_FULL ≥ 0.99` at f=40 for both semantics; translation preflight = the
generator's built-in dedup/size gates plus one manual spot-check of an `aba_source` sidecar
against `check_aba_transform.py --fix` output.

---

## 3. Files staged NOW (inert — nothing the running v2 campaign reads)

| file | role | tested |
|---|---|---|
| `generate_bafs.py` | BAF pool generator (AAF gen + support facts) | smoke-run: pools OK |
| `translate_abas.py` | random flat ABAs → corrected-translation AAF pool + sidecars | smoke-run: 8/8 OK |
| `ASPARTIX/baf_{stable,admissible,complete}.lp` | F1 labelling oracles | ≡ verified learned encodings on smoke BAFs |
| `bg_baf.lp` | F1 learning background (B_BAF) | formulation from verified lab |
| `run_configs/v3_breadth_{sparse,self,large}.json` (+`_grd`) | Experiment G configs | schema = v2 configs |
| `run_configs/v3_{baf,aba}.json` | Experiment F configs | schema = v2 configs |
| `run_configs/v3_smoke_breadth.json` | post-patch smoke (new generator flags, 1 cell, 2 folds) | — |
| `run_v3_gap.sh` | sequential launcher; guards + pool generation + resume | guards verified to refuse pre-patch |

## 4. Deferred patches — apply ONLY after v2 completes (~30 min total, then smoke)

### 4.1 `generate_aafs.py` — density preset + self-attacks

Extend `generate_random_aafs(...)` with `density_preset="v2"` and
`allow_self_attacks=False` keyword args, and the parser with matching options:

```python
# template: drop "X != Y" when self-attacks are allowed
asp_program_template = """
arg(1..{n}).
{{ att(X,Y) : arg(X), arg(Y){neq} }} = {s}.
"""
# inside generate_random_aafs:
neq = "" if allow_self_attacks else ", X != Y"
max_att = n * n if allow_self_attacks else n * (n - 1)
if density_preset == "sparse":
    s = rng.randint(n, min(2 * n, max_att))
else:  # "v2" — unchanged default
    s = rng.randint(n, max_att)
# parser:
parser.add_argument("--density-preset", choices=["v2", "sparse"], default="v2")
parser.add_argument("--allow_self_attacks", "--allow-self-attacks",
                    action="store_true", dest="allow_self_attacks")
```

Backward-compatible: defaults reproduce v2 byte-for-byte (same rng call sequence for the
v2 preset — verify by regenerating one v2-seed AAF and diffing).

### 4.2 `run_experiment_grid.py` — `ensure_aafs` plumbing (after the `--seed` args)

```python
        density_preset = self.aaf_generation.get("density_preset")
        if density_preset:
            cmd += ["--density-preset", str(density_preset)]
        if self.aaf_generation.get("allow_self_attacks"):
            cmd += ["--allow_self_attacks"]
```

(Also fold the two new keys into the `[GEN ]` log line for auditability.)

### 4.3 `generate_extensions.py` — carry support facts into labelled files

`extract_arguments_attacks` (lines 15–19) keeps only `arg(`/`att(` lines, and the writers
(lines ~161/184) emit `args + atts + labels` — support facts would be **silently dropped**,
making F1 labels wrong w.r.t. the BAF oracle that produced them. Patch: add a third
extracted list with prefix `support(` and include it in both writes:

```python
FRAMEWORK_FACT_PREFIXES = ("arg(", "att(", "support(")
# extract: framework_facts = [l.strip() for l in lines if l.strip().startswith(FRAMEWORK_FACT_PREFIXES)]
# writes:  f.write("\n".join(framework_facts + ext_atoms) + "\n")
```

No behaviour change for AAF pools (they contain no `support(` lines). The ILASP task
builder needs **no** change: `generate_ilasp_task.parse_lp_instance` already passes every
non-label fact into the CDPI context. `train_test.py`'s bare-AAF strip
(lines 1265/1347) only fires for `eval_on_bare_aaf` semantics (GRD) — out of F1's scope;
optionally unify it on the same constant for hygiene.

### 4.4 `semantics_config.json` — BAF entries (additive)

```json
"BAF_STB": {
  "file": "ASPARTIX/baf_stable.lp",
  "clingo_args": [],
  "learn_heuristics": false,
  "learn_background_file": "bg_baf.lp",
  "background_file": { "train_test_learned": "bg_baf.lp" }
},
"BAF_ADM": { "file": "ASPARTIX/baf_admissible.lp", "clingo_args": [], "learn_heuristics": false,
  "learn_background_file": "bg_baf.lp", "background_file": { "train_test_learned": "bg_baf.lp" } },
"BAF_CMP": { "file": "ASPARTIX/baf_complete.lp", "clingo_args": [], "learn_heuristics": false,
  "learn_background_file": "bg_baf.lp", "background_file": { "train_test_learned": "bg_baf.lp" } }
```

Everything else inherits the global stage defaults exactly as ADM/CMP/STB do (oracles are
self-contained, so ground-truth stages need no background; completion rules on the learned
side operate on `arg/in/out` and are framework-agnostic). Mode bias file: **unchanged**.

## 5. Runbook (after v2's "ALL v2 CONFIGS DONE")

```
1. git checkout -b feat/v3-gap-experiments
2. Apply patches §4.1–§4.4; commit.
3. ./run_v3_gap.sh smoke          # generator flags → pool → label → learn → eval, 1 cell
4. Pool sanity spot-checks (§1 acceptance; density/self-attack counts).
5. nohup ./run_v3_gap.sh > v3_gap.out 2>&1 &
6. Monitor as for v2 (campaign_progress.py works per artifact root).
   Stop/resume: kill + rerun the same command — completed rows are skipped.
```

## 6. Risks and pre-committed responses

- **R1 (G-large labelling/learning cost).** Extension enumeration (esp. ADM/PRF) and ILASP
  grounding grow steeply with n. Mitigation: the launcher runs each regime's cheap `_grd`
  config first — its `ensure_aafs` + labelling stage doubles as the regime's preflight. If
  labelling n=12 exceeds ~2 h or ADM/PRF rows blow past the train cap wholesale, drop
  `nmax` to 11 (regenerate with the same seed; the claim "larger frameworks" survives) and
  note the boundary honestly in the paper.
- **R2 (sparse pools under-constraining ILASP).** At `s≈n` many arguments are unattacked;
  positives may under-determine the theory at f=20. That is a *finding* (sample-efficiency
  depends on graph density), not a failure — report it against the same-f v2 cells.
- **R3 (BAF `supported/1` clash).** Documented in `bg_baf.lp`; GRD-BAF excluded from F1.
  If a reviewer asks: the fix is a renamed predicate in B_BAF, a deliberate follow-up.
- **R4 (ABA pools too easy).** Translated AAFs are small (3–12 args) and attack-sparse; if
  f=40 saturates trivially, the interesting number is the smallest f reaching MCC 1.0 —
  report that instead of a flat ceiling row.
- **R5 (accidental v2 interference).** All v3 artifact roots are fresh directories;
  the launcher's process guard + patch guard make early launch a hard error, not a hazard.

## 7. Paper hooks (AIJ outline cross-references)

- §5.4 "Breadth": G Δ-tables + F recovery table = the two exhibits.
- §3 (unifying framework): F1's "same hypothesis space, different background" sentence.
- §4 (mechanized correctness): F1 oracles are the *proved* encodings — labelling and
  verification share one artifact; F2 operationalizes the *corrected* translation.
