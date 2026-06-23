# Raw Data to Paper Mapping (for a clean rebuild)

## Goal
Map the paper protocol to `Raw_Data_original.xlsx` / `Raw_Data_Augmented.xlsx` so we can rebuild the real-world pipeline from first principles.

## 1) What the paper says vs what the files contain

### Participants and conditions

- Paper: 130 participants, 7 argument sets/conditions:
  - 3 simple-reinstatement sets,
  - 3 floating-reinstatement sets,
  - 1 3-cycle set.
- Data (`PART_B`) matches exactly:
  - unique participants: 130,
  - versions: `A..G`,
  - participants per version:
    - `A=20, B=20, C=20, D=15, E=15, F=15, G=25`,
  - total groups: 35, and 5 groups per version.

### AF size structure

- Paper:
  - Simple = 3 arguments,
  - Floating = 4 arguments,
  - 3-cycle = 5 arguments.
- Data (`PART_B` item counts by version):
  - `A/B/C`: items `A,B,C,D` (4 arguments) -> floating family.
  - `D/E/F`: items `A,B,C` (3 arguments) -> simple family.
  - `G`: items `A,B,C,D,E` (5 arguments) -> 3-cycle family.
- Data (`PART_A` relation counts by version) also matches ordered-pair counts:
  - `A/B/C`: 12 relations (4*3),
  - `D/E/F`: 6 relations (3*2),
  - `G`: 20 relations (5*4).

### Part A (draw attacks) phases

- Paper protocol: first individual -> group -> final individual (+ confidence).
- `PART_A` columns:
  - first individual: `1st_RESPONSE`, `1st_CONFIDENCE`,
  - group: `GROUP_RESPONSE`,
  - final individual: `2nd_RESPONSE`, `2nd_CONFIDENCE`,
  - agreement/follow-up: `INFLUENCE_GROUP`, `AGREEMENT`, `FOLLOW_GROUP`, `MIND_CHANGE`, `ATTACK_CHANGE`,
  - gold attack existence: `EXPECTED`, plus correctness flags.

### Part B (accept/reject/undecided) phases

- Paper protocol: first individual -> group -> final individual (+ confidence).
- `PART_B` columns:
  - first individual: `1st_RESPONSE`, `1st_CONFIDENCE`,
  - group: `GROUP_RESP`,
  - final individual: `2nd_RESPONSE`, `2nd_CONFIDENCE`,
  - theoretical labels for BaseAF: `EXP_GROUNDED`, `EXP_PREFERRED`, `EXP_CF2`,
  - computed predictor families:
    - `GROUP_PRED_*`,
    - `2nd_PRED_*`,
    - `MAJ_GRAPH_PRED_*`,
  - many precomputed correctness/difference columns.

## 2) Relationship between `Raw_Data_original.xlsx` and `Raw_Data_Augmented.xlsx`

- `Raw_Data_Augmented.xlsx` contains sheets: `PART_A`, `PART_B`, `Attacks`, `Labellings`.
- `PART_A` and `PART_B` in both files are byte-equivalent in content.
- `Attacks` and `Labellings` are derived sheets:
  - `Attacks` has same row order/count as `PART_A`.
  - `Labellings` has same row order/count as `PART_B`.

## 3) Exact derivation behavior in augmented sheets

### `Attacks` sheet derivation

- `ID = p{PARTICIPANT}_version{VERSION}` (row-wise from `PART_A`).
- `ATTACK` is populated iff `1st_RESPONSE == "Attack"`.
- Relation conversion:
  - `A_attacks_B` -> `att(a,b).`
  - generally: `X_attacks_Y` -> `att(x,y).`

So `Attacks` is explicitly based on **first personal Part A response**, not group/final response.

### `Labellings` sheet derivation

- `ID = p{PARTICIPANT}_version{VERSION}` (row-wise from `PART_B`).
- one row per `(ID, arg)` where `arg` is the `ITEM` letter lowercased.
- `EXTENSION` is exactly mapped from `1st_RESPONSE`:
  - `Accept -> in`
  - `Reject -> out`
  - `Undecided -> undec`

So positive labels in augmented data come from **first personal Part B response**.

### `NEGATIVE` column semantics

- `NEGATIVE` is **not** a participant response column.
- Empirical property: for each `ID`, every argument label differs from `EXTENSION` (full relabel, not one-argument flip).
  - changed labels per ID:
    - 4 for 4-arg versions (`A/B/C`),
    - 3 for 3-arg versions (`D/E/F`),
    - 5 for 5-arg version (`G`).
- This matches the current `asp_files/version*/neg` artifacts (same full relabel pattern).
- Generation mechanism is not encoded by a tracked script in repo.

## 4) Important caveats for rebuild

1. Paper text mentions 5-point confidence ratings; dataset confidence values are `1..4` in practice.
2. `PART_A` includes `2nd_RESPONSE == "NA"` in 20 rows (must be handled explicitly).
3. `extract_labeled_aafs.py` now provides a generalized extraction layer:
   - no hardcoded version (selectable via `--versions`),
   - supports paper phases (`first/group/final`) and response-column selectors,
   - persists per-participant `.lp` outputs and extraction manifests.
4. Current neg generation provenance is incomplete in code; treat `NEGATIVE` as legacy artifact unless regenerated with an explicit policy.

## 5) Recommended reliable rebuild (from scratch)

Use `Raw_Data_original.xlsx` as source of truth, and make derivations explicit/configurable.
Reference implementation: `Real_World_Examples/build_real_world_dataset.py` (uses `extract_labeled_aafs.py`).

### Stage 0: Ingestion and normalization

- Parse `PART_A`, `PART_B`.
- Normalize case and labels:
  - attacks: `Attack/No_attack`,
  - labels: `Accept/Reject/Undecided`.
- Create stable participant key:
  - `pid = p{PARTICIPANT}_version{VERSION}`.

### Stage 1: Build AF graphs (configurable response source)

- Choose attack source via config:
  - `partA_source = paper(first|group|final) | all_response_columns | explicit_column_list`.
- Convert `RELATION` rows into `att/2` facts based on chosen phase.

### Stage 2: Build labelings (configurable response source)

- Choose label source via config:
  - `partB_source = paper(first|group|final) | all_response_columns | explicit_column_list`.
- Convert responses to `in/out/undec`.
- Emit one labeling per `pid`.

### Stage 3: Generate positive `.lp`

- For each `pid`, emit:
  - all `arg/1`,
  - all selected `att/2`,
  - selected `in/out/undec`.

### Stage 4: Generate negative `.lp` with explicit policy

- Make this a required config parameter:
  - `negative_policy = legacy_augmented | flip_one_arg | relabel_all_args_random | model_based`.
- For reproducibility:
  - fixed seed,
  - deterministic sampling,
  - provenance log for each `pid`.

### Stage 5: Build ILASP tasks

- Deterministically convert `{pos,neg}` `.lp` files into `#pos/#neg`.
- Append `background_knowledge.lp` + `mode_declarations.las` in one canonical builder.

### Stage 6: Validation gates

- Count checks:
  - participants/version,
  - AF sizes/version,
  - rows/sheet invariants.
- Structural checks:
  - each `pid` has complete labels for all its args,
  - no malformed atoms,
  - task examples match source `.lp`.
- Reproducibility checks:
  - hash inputs,
  - store config + seed + command in manifest.

## 6) Minimal mapping summary

- `PART_A` = attack elicitation process data (all phases).
- `PART_B` = acceptability process data (all phases + semantics predictor fields).
- `Attacks` (augmented) = deterministic projection of `PART_A` first personal phase.
- `Labellings` (augmented) = deterministic projection of `PART_B` first personal phase + synthetic `NEGATIVE`.
