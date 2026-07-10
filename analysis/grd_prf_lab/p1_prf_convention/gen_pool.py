"""PRF pool generator (route P1).

POS  = preferred labellings of each campaign AAF, enumerated with
       ASPARTIX/preferred.lp + --heuristic=Domain --enum=domRec (the domRec
       convention; plain clingo would give COMPLETE labellings -- the Exp2 bug),
       projected to in/1,out/1 (3-valued out; undec args unlabelled), p=1.0.

NEG  = perturbations of preferred labellings (flip_one / flip_2 / extend_in /
       drop_in / full_relabel / random), kept only if the TRUE core rejects them
       under BOTH conventions that matter:
         (a) ILASP training coverage: no answer set of
             [choice BG + core + AAF] includes the labelling atoms
             (guarantees the true core stays feasible in the learning task);
         (b) eval emptiness: [choice BG + core + completion + labelling-as-facts]
             is UNSAT (guarantees the instance is TN-able at eval).
       pool_adm: filtered against the TRUE ADMISSIBLE core.
       pool_cmp: filtered against the TRUE COMPLETE core (superset: includes
                 admissible-but-not-complete-consistent labellings).

NEVER uses --neg_mode complete_not_target: complete-not-preferred labellings are
models of the admissible core and would make the route-P1 target theory UNSAT.
"""
import os
import random
import sys

REPO = "/Users/fdasaro/Desktop/Zlatina/FabioExperimentsMacM4_claude"
LAB = os.path.join(REPO, "analysis/grd_prf_lab/p1_prf_convention")
sys.path.insert(0, REPO)

import clingo  # noqa: E402
from arglas.solver_runtime import solve_models  # noqa: E402

PREFERRED_LP = os.path.join(REPO, "ASPARTIX", "preferred.lp")
BG = os.path.join(REPO, "config/background_knowledge.lp")
ADM_CORE = os.path.join(LAB, "true_adm_core.lp")
CMP_CORE = os.path.join(LAB, "true_cmp_core.lp")
DOMREC = ["--heuristic=Domain", "--enum=domRec"]
AAF_DIR = os.path.join(REPO, "artifacts/final_synthetic_corrected_20260625/aafs")

BG_TEXT = open(BG).read()
ADM_TEXT = open(ADM_CORE).read()
CMP_TEXT = open(CMP_CORE).read()
COMPLETION = "in(X) :- arg(X), not out(X).\nout(X) :- arg(X), not in(X).\n"

NEG_CAP_PER_AAF = 6
SEED = 20260704


def sat(program):
    ctl = clingo.Control(["--warn=none", "1"])
    ctl.add("base", [], program)
    ctl.ground([("base", [])])
    return ctl.solve().satisfiable


def core_rejects(core_text, af_facts, labels):
    """True iff the core rejects labelling under BOTH conventions (see header)."""
    atoms = [f"{st}({a})" for a, st in sorted(labels.items())]
    af = "\n".join(af_facts)
    # (a) training-time coverage: exists answer set including the atoms?
    force = "".join(f":- not {atom}.\n" for atom in atoms)
    if sat(BG_TEXT + core_text + af + "\n" + force):
        return False
    # (b) eval-time: labelling as facts + completion rules.
    facts = "".join(f"{atom}.\n" for atom in atoms)
    if sat(BG_TEXT + core_text + COMPLETION + af + "\n" + facts):
        return False
    return True


def parse_aaf(path):
    facts = [ln.strip() for ln in open(path)
             if ln.strip().startswith(("arg(", "att("))]
    args = [f[4:-2] for f in facts if f.startswith("arg(")]
    return facts, args


def labelling_of(model_atoms):
    lab = {}
    for a in model_atoms:
        if a.startswith("in("):
            lab[a[3:-1]] = "in"
        elif a.startswith("out("):
            lab[a[4:-1]] = "out"
    return lab


def candidates_from(labelling, all_args, rng):
    """Perturbation candidates (dicts arg->in/out). No undec labels on purpose:
    undec atoms are underivable under the choice BG, making such negatives
    vacuously rejected by every hypothesis (zero learning signal)."""
    cands = []
    labelled = sorted(labelling)
    unlabelled = sorted(set(all_args) - set(labelled))
    # flip_one (all of them, deterministic)
    for a in labelled:
        c = dict(labelling)
        c[a] = "out" if c[a] == "in" else "in"
        cands.append(c)
    # flip_2 (random)
    if len(labelled) >= 2:
        for _ in range(4):
            c = dict(labelling)
            for a in rng.sample(labelled, 2):
                c[a] = "out" if c[a] == "in" else "in"
            cands.append(c)
    # extend_in: promote an unlabelled (undec) arg to in
    for a in unlabelled:
        c = dict(labelling)
        c[a] = "in"
        cands.append(c)
    # drop_in: demote one in to out (admissible-but-smaller probes; mostly
    # useful for the complete-core pool)
    for a in labelled:
        if labelling[a] == "in":
            c = dict(labelling)
            c[a] = "out"
            cands.append(c)
    # full_relabel (random in/out over the labelled args)
    for _ in range(2):
        c = {a: rng.choice(["in", "out"]) for a in labelled}
        cands.append(c)
    # random labellings over ALL args (generate_extensions-style)
    for _ in range(3):
        chosen = rng.sample(all_args, rng.randint(1, len(all_args)))
        c = {a: ("in" if a in chosen else "out") for a in all_args}
        cands.append(c)
    return cands


def main():
    pools = {
        "pool_adm": (ADM_TEXT, os.path.join(LAB, "pool_adm", "labelled_PRF_full")),
        "pool_cmp": (CMP_TEXT, os.path.join(LAB, "pool_cmp", "labelled_PRF_full")),
    }
    for _, d in pools.values():
        os.makedirs(d, exist_ok=True)

    files = sorted(f for f in os.listdir(AAF_DIR) if f.endswith(".lp"))
    stats = {"aafs": 0, "pos": 0, "empty_skipped": 0,
             "neg_adm": 0, "neg_cmp": 0, "cand_total": 0,
             "adm_rejected_admissible_but_not_preferred": 0}
    for fname in files:
        m = fname.replace(".lp", "").split("_")  # aaf_N_i
        size, idx = m[1], m[2]
        path = os.path.join(AAF_DIR, fname)
        af_facts, all_args = parse_aaf(path)
        rng = random.Random((SEED, size, idx).__repr__())

        models = solve_models([PREFERRED_LP, path], clingo_args=DOMREC,
                              show_predicates=["in/1", "out/1"])
        labellings = [labelling_of(m) for m in models]
        stats["aafs"] += 1

        pos_count = 0
        for lab in labellings:
            if not lab:
                stats["empty_skipped"] += 1
                continue
            pos_count += 1
            out = os.path.join(
                "{d}", f"aaf_{size}_{idx}_PRF_POS_{pos_count}.lp")
            atoms = [f"{st}({a})." for a, st in sorted(
                lab.items(), key=lambda kv: (kv[1], kv[0]))]
            content = "\n".join(af_facts + atoms) + "\n"
            for _, d in pools.values():
                with open(out.format(d=d), "w") as f:
                    f.write(content)
        stats["pos"] += pos_count

        # negatives
        seen = set()
        cands = []
        for lab in labellings:
            if lab:
                cands.extend(candidates_from(lab, all_args, rng))
        rng.shuffle(cands)
        counts = {"pool_adm": 0, "pool_cmp": 0}
        for cand in cands:
            sig = tuple(sorted(cand.items()))
            if sig in seen:
                continue
            seen.add(sig)
            stats["cand_total"] += 1
            adm_ok = core_rejects(ADM_TEXT, af_facts, cand)
            cmp_ok = adm_ok or core_rejects(CMP_TEXT, af_facts, cand)
            if cmp_ok and not adm_ok:
                stats["adm_rejected_admissible_but_not_preferred"] += 1
            for pool_name, ok in [("pool_adm", adm_ok), ("pool_cmp", cmp_ok)]:
                if not ok or counts[pool_name] >= NEG_CAP_PER_AAF:
                    continue
                counts[pool_name] += 1
                d = pools[pool_name][1]
                out = os.path.join(
                    d, f"aaf_{size}_{idx}_PRF_NEG_{counts[pool_name]}.lp")
                atoms = [f"{st}({a})." for a, st in sorted(
                    cand.items(), key=lambda kv: (kv[1], kv[0]))]
                with open(out, "w") as f:
                    f.write("\n".join(af_facts + atoms) + "\n")
            if min(counts.values()) >= NEG_CAP_PER_AAF:
                break
        stats["neg_adm"] += counts["pool_adm"]
        stats["neg_cmp"] += counts["pool_cmp"]

    print(stats)


if __name__ == "__main__":
    main()
