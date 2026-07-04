#!/usr/bin/env python3
"""Part C: build PRF expressibility ILASP tasks.

C-i  : pipeline-style encoding (EMPTY exclusions) + complete-not-preferred hard
       negatives -> demonstrate structural UNSAT (encoding-level, independent of
       the hypothesis space).
C-ii : exact-pinning encoding (exclusions = in/out atoms of the negative's undec
       args, which pins the EXACT labelling) + the same hard negatives -> the
       real expressibility test.

Grouped split: seeded shuffle of the 500 campaign AAFs, 80% train / 20% test.
Training examples come only from train AAFs (hard AAFs = preferred != complete).
"""
import json
import os
import random
import re

REPO = "/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_claude"
LAB = os.path.join(REPO, "analysis/grd_prf_lab/p2_prf_alt")
AAF_DIR = os.path.join(REPO, "artifacts/final_synthetic_corrected_20260625/aafs")

SPLIT_SEED = 0
TRAIN_FRAC = 0.8
N_HARD_TRAIN_AAFS = 20


def load_aaf(name):
    args, atts = [], []
    for line in open(os.path.join(AAF_DIR, name)):
        line = line.strip()
        if line.startswith("arg("):
            args.append(line[4:-2])
        elif line.startswith("att("):
            m = re.match(r"att\((\w+),(\w+)\)\.", line)
            atts.append((m.group(1), m.group(2)))
    return args, atts


def labelling_from_inset(in_atoms, args, atts):
    """in_atoms like ['in(2)', 'in(3)'] -> (ins, outs, undecs) over arg names."""
    ins = {re.match(r"in\((\w+)\)", a).group(1) for a in in_atoms}
    outs = {b for (a, b) in atts if a in ins}
    undec = [x for x in args if x not in ins and x not in outs]
    return sorted(ins), sorted(outs), sorted(undec)


def example(kind, ex_id, ins, outs, undec, args, atts, pin_exact):
    inc = [f"in({x})" for x in ins] + [f"out({x})" for x in outs]
    exc = []
    if pin_exact:
        for z in undec:
            exc.append(f"in({z})")
            exc.append(f"out({z})")
    ctx = " ".join([f"arg({x})." for x in args] + [f"att({a},{b})." for a, b in atts])
    return (f"#{kind}({ex_id}, {{{', '.join(inc)}}}, "
            f"{{{', '.join(exc)}}}, {{{ctx}}}).")


def build_task(aaf_names, per_aaf, pin_exact, max_neg_per_aaf=6):
    lines = []
    for name in aaf_names:
        stem = name[:-3]
        args, atts = load_aaf(name)
        prf = {frozenset(s) for s in map(tuple, per_aaf[name]["prf"])}
        cmp_sets = {frozenset(s) for s in map(tuple, per_aaf[name]["cmp"])}
        for i, s in enumerate(sorted(prf, key=sorted)):
            ins, outs, undec = labelling_from_inset(s, args, atts)
            lines.append(example("pos", f"{stem}_P{i}", ins, outs, undec,
                                 args, atts, pin_exact))
        hard = sorted(cmp_sets - prf, key=sorted)[:max_neg_per_aaf]
        for i, s in enumerate(hard):
            ins, outs, undec = labelling_from_inset(s, args, atts)
            lines.append(example("neg", f"{stem}_N{i}", ins, outs, undec,
                                 args, atts, pin_exact))
    return lines


def main():
    per_aaf = json.load(open(os.path.join(LAB, "a_gap_results.json")))["per_aaf"]
    aafs = sorted(per_aaf)
    rng = random.Random(SPLIT_SEED)
    shuffled = aafs[:]
    rng.shuffle(shuffled)
    n_train = int(TRAIN_FRAC * len(shuffled))
    train_aafs, test_aafs = shuffled[:n_train], shuffled[n_train:]
    json.dump({"train": sorted(train_aafs), "test": sorted(test_aafs)},
              open(os.path.join(LAB, "c_split.json"), "w"), indent=1)

    hard_train = [a for a in train_aafs
                  if per_aaf[a]["n_cmp"] > per_aaf[a]["n_prf"]]
    picked = random.Random(1).sample(hard_train, N_HARD_TRAIN_AAFS)
    print(f"train={len(train_aafs)} test={len(test_aafs)} "
          f"hard_train={len(hard_train)} picked={len(picked)}")

    background = open(os.path.join(REPO, "background_knowledge.lp")).read()
    modes = open(os.path.join(REPO, "mode_declarations.las")).read()
    modes3 = modes.replace("#maxv(2).", "#maxv(3).")

    # C-i: pipeline encoding (empty exclusions), single hard AAF is enough
    demo_aaf = picked[0]
    lines = build_task([demo_aaf], per_aaf, pin_exact=False)
    with open(os.path.join(LAB, "tasks/c1_pipeline_hardneg.las"), "w") as f:
        f.write("\n".join(lines) + "\n" + background + "\n" + modes + "\n")
    print(f"C-i task: {demo_aaf}, {len(lines)} examples (pipeline encoding)")

    # C-ii: exact-pinning encoding, 20 hard train AAFs
    lines = build_task(picked, per_aaf, pin_exact=True)
    for tag, mode_text in [("v2", modes), ("v2_maxv3", modes3)]:
        with open(os.path.join(LAB, f"tasks/c2_pin_hardneg_{tag}.las"), "w") as f:
            f.write("\n".join(lines) + "\n" + background + "\n" + mode_text + "\n")
    print(f"C-ii tasks: {len(picked)} AAFs, {len(lines)} examples (exact pinning)")

    # C-ii-small fallback (8 AAFs) in case 20 is too slow
    lines_small = build_task(picked[:8], per_aaf, pin_exact=True)
    with open(os.path.join(LAB, "tasks/c2_pin_hardneg_small.las"), "w") as f:
        f.write("\n".join(lines_small) + "\n" + background + "\n" + modes + "\n")
    print(f"C-ii small: 8 AAFs, {len(lines_small)} examples")

    # manifest of train-AAF pool files for the pipeline-task baseline (C-iii)
    pool = os.path.join(LAB, "pools/labelled_PRF_full")
    train_stems = {a[:-3] for a in train_aafs}
    with open(os.path.join(LAB, "c_train_manifest.txt"), "w") as f:
        for fn in sorted(os.listdir(pool)):
            m = re.match(r"(aaf_\d+_\d+)_PRF_(POS|NEG)_\d+\.lp", fn)
            if m and m.group(1) in train_stems:
                f.write(fn + "\n")
    print("manifest written")


if __name__ == "__main__":
    main()
