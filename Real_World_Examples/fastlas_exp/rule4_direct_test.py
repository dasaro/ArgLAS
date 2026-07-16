#!/usr/bin/env python3
"""DIRECT behavioural test of consensus rule 4 ("smoke/fire": violated :- reinstated(X),
has_many_attackers(X)) -- bypassing the learner entirely.

Data: the exact Exp2 pool the learners see (unified_compare.load_pooled): every participant's
final Part-A drawn graph (IndAF) with final Part-B labels, versions A-G, n=129 participants /
495 (participant, argument) response units.

Predicates: computed per (participant, argument) unit EXACTLY as the aux9 background defines
them (aux9_combined.AUX9_BG), with in/out taken from the participant's OWN committed labelling
(undec = neither, as in fl_discover._lab_ctx):
  reinstated(X)         : X is attacked and every attacker of X is itself attacked by some
                          in-labelled argument   [attacked(X), not att_not_killed_by_in(X)]
  has_many_attackers(X) : >= 2 distinct attackers of X in the participant's drawn graph

TWO operationalizations of "attackers all defeated" are reported:
  abi : the aux predicate verbatim (every attacker attacked_by_in) -- NOTE: on these stimuli
        this co-occurs with many attackers only if the participant labels mutually attacking
        arguments jointly in, so the many-attacker cell is near-empty (that emptiness is itself
        reported: the rule's antecedent is close to vacuous on the positive data);
  out : every attacker labelled out by the participant (defeat = the participant's own
        out-judgement) -- the behavioural reading of "attackers all defeated", with mass on
        both sides (float conditions = 2 attackers, simple chains = 1).

Hypothesis (one-sided, from rule 4): among REINSTATED units, P(X labelled in) is LOWER when X
has many attackers than when it has a single attacker.

Tests:
  1. pooled 2x2 Fisher exact (response level, the 2022 pooled convention), one- and two-sided;
  2. cell-level robustness: deduplicated to unique (graph, labelling, argument) units,
     mirroring the cell-level McNemar convention of unified_compare;
  3. participant-clustered robustness: exact sign test (binom_two_sided, the apples_to_apples
     McNemar machinery) over participants who contribute BOTH unit types, on the per-participant
     in-rate difference;
  4. graded acceptance rate by attacker count (1, 2, 3+) among reinstated units -- the
     rahwan2010 graded-reinstatement parallel.

A caveat computed alongside: reinstated is defined w.r.t. the participant's own labelling, so
the two predicates are not independent of the outcome by construction; the graph-side split
(attacker count) IS exogenous, which is why the primary contrast conditions on reinstated and
splits only on the structural predicate.

Run:  python3 rule4_direct_test.py        -> results/rule4_direct_test.json
"""
import json, math, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
sys.path.insert(0, HERE)
import unified_compare as U
import fl_discover as G
from apples_to_apples import binom_two_sided

OUT = os.path.join(HERE, "results", "rule4_direct_test.json")


# ---------------------------------------------------------------------------
# predicate computation (mirrors aux9_combined.AUX9_BG semantics, in Python)
# ---------------------------------------------------------------------------
def unit_predicates(rec):
    """Yield (arg, label, reinstated_abi, reinstated_out, n_attackers) per labelled argument."""
    attackers = defaultdict(set)
    for s, t in rec["attacks"]:
        attackers[t].add(s)
    in_set = {a for a, s in rec["labels"].items() if s == "in"}
    out_set = {a for a, s in rec["labels"].items() if s == "out"}
    attacked = {x for x in rec["args"] if attackers[x]}

    def attacked_by_in(y):
        return any(z in in_set for z in attackers[y])

    for x in rec["args"]:
        if x not in rec["labels"]:
            continue
        r_abi = x in attacked and all(attacked_by_in(y) for y in attackers[x])
        r_out = x in attacked and all(y in out_set for y in attackers[x])
        yield x, rec["labels"][x], r_abi, r_out, len(attackers[x])


# ---------------------------------------------------------------------------
# exact tests (no scipy dependency)
# ---------------------------------------------------------------------------
def _log_comb(n, k):
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def fisher_exact(a, b, c, d):
    """2x2 table [[a,b],[c,d]] (rows: many/single, cols: in/not-in).
    Returns (odds_ratio, p_two_sided, p_one_sided_less) where 'less' = row1 (many) has a
    LOWER in-proportion than row2 (single), i.e. small 'a' is extreme."""
    r1, r2, c1 = a + b, c + d, a + c
    n = a + b + c + d
    lo, hi = max(0, c1 - r2), min(r1, c1)
    denom = _log_comb(n, c1)
    pmf = {k: math.exp(_log_comb(r1, k) + _log_comb(r2, c1 - k) - denom) for k in range(lo, hi + 1)}
    p_obs = pmf[a]
    p_two = min(1.0, sum(p for p in pmf.values() if p <= p_obs * (1 + 1e-9)))
    p_less = min(1.0, sum(p for k, p in pmf.items() if k <= a))
    odds = (a * d) / (b * c) if b * c else float("inf") if a * d else float("nan")
    return odds, p_two, p_less


def rate(k, n):
    return round(k / n, 4) if n else None


# ---------------------------------------------------------------------------
def collect():
    recs = U.load_pooled("final")
    units = []
    for r in recs:
        cellk = (tuple(sorted(r["attacks"])), tuple(sorted(r["labels"].items())))
        for a, lab, r_abi, r_out, natt in unit_predicates(r):
            units.append({"pid": f"{r['version']}/{r['pid']}", "cell": (cellk, a),
                          "arg": a, "label": lab, "reinstated_abi": r_abi,
                          "reinstated_out": r_out, "n_att": natt})
    return recs, units


def table_and_tests(units, tag, key):
    """2x2 on reinstated units: many(>=2) vs single(1) attackers x in vs not-in."""
    ru = [u for u in units if u[key]]
    a = sum(1 for u in ru if u["n_att"] >= 2 and u["label"] == "in")
    b = sum(1 for u in ru if u["n_att"] >= 2 and u["label"] != "in")
    c = sum(1 for u in ru if u["n_att"] == 1 and u["label"] == "in")
    d = sum(1 for u in ru if u["n_att"] == 1 and u["label"] != "in")
    odds, p2, p1 = fisher_exact(a, b, c, d)
    by_count = {}
    for grp, sel in (("1", lambda n: n == 1), ("2", lambda n: n == 2), ("3+", lambda n: n >= 3)):
        g = [u for u in ru if sel(u["n_att"])]
        k = sum(1 for u in g if u["label"] == "in")
        by_count[grp] = {"n": len(g), "n_in": k, "rate_in": rate(k, len(g))}
    res = {"n_reinstated_units": len(ru),
           "table_many_single_x_in_notin": {"many_in": a, "many_notin": b,
                                            "single_in": c, "single_notin": d},
           "rate_in_many": rate(a, a + b), "rate_in_single": rate(c, c + d),
           "fisher_odds_ratio": round(odds, 4) if math.isfinite(odds) else None,
           "fisher_p_two_sided": round(p2, 6), "fisher_p_one_sided_many_lower": round(p1, 6),
           "acceptance_by_attacker_count": by_count}
    print(f"[{tag}] reinstated units={len(ru)}  many: {a}/{a+b} in ({res['rate_in_many']})  "
          f"single: {c}/{c+d} in ({res['rate_in_single']})  "
          f"Fisher p2={p2:.4g} p1(less)={p1:.4g} OR={odds:.3f}", flush=True)
    print(f"[{tag}] graded: " + "  ".join(f"{g}att {v['n_in']}/{v['n']}={v['rate_in']}"
                                          for g, v in by_count.items()), flush=True)
    return res


def participant_sign_test(units, pred):
    """Per participant: in-rate among reinstated-many vs reinstated-single units; exact sign
    test over participants contributing both types (ties dropped)."""
    per = defaultdict(lambda: {"m": [0, 0], "s": [0, 0]})  # [n_in, n]
    for u in units:
        if not u[pred]:
            continue
        bucket = "m" if u["n_att"] >= 2 else "s"
        per[u["pid"]][bucket][1] += 1
        per[u["pid"]][bucket][0] += int(u["label"] == "in")
    both = {p: v for p, v in per.items() if v["m"][1] and v["s"][1]}
    lower = higher = ties = 0
    for v in both.values():
        rm, rs = v["m"][0] / v["m"][1], v["s"][0] / v["s"][1]
        if rm < rs:
            lower += 1
        elif rm > rs:
            higher += 1
        else:
            ties += 1
    n = lower + higher
    p_two = binom_two_sided(min(lower, higher), n, 0.5) if n else float("nan")
    # one-sided (many lower): P(X >= lower) under Binom(n, .5)
    p_one = sum(math.exp(_log_comb(n, k) - n * math.log(2)) for k in range(lower, n + 1)) if n else float("nan")
    res = {"n_participants_with_both": len(both), "many_lower": lower,
           "many_higher": higher, "ties": ties,
           "sign_p_two_sided": round(p_two, 6) if p_two == p_two else None,
           "sign_p_one_sided_many_lower": round(p_one, 6) if p_one == p_one else None}
    print(f"[clustered] {len(both)} participants w/ both unit types: many-lower={lower} "
          f"many-higher={higher} ties={ties}  sign p2={p_two:.4g} p1={p_one:.4g}", flush=True)
    return res


def rule4_fires(args, attacks, lab):
    """Does `violated :- reinstated(X), has_many_attackers(X)` fire on this labelling?
    (aux abi definition, verbatim)."""
    attackers = defaultdict(set)
    for s, t in attacks:
        attackers[t].add(s)
    in_set = {a for a, s in lab.items() if s == "in"}
    for x in args:
        if len(attackers[x]) >= 2 and all(
                any(z in in_set for z in attackers[y]) for y in attackers[x]):
            return True
    return False


def shell_diagnostic(recs):
    """Where does the learner's evidence for rule 4 live? Firing rate on the human labellings
    (positives) vs the full Hamming-1 negative shell of the same pool."""
    pos_fire = sum(1 for r in recs if rule4_fires(r["args"], r["attacks"], r["commit"]))
    shell = G.shell_of(recs)
    neg_fire = sum(1 for ar, at, ng in shell if rule4_fires(ar, at, ng))
    res = {"n_positives": len(recs), "positives_fired": pos_fire,
           "pos_rate": rate(pos_fire, len(recs)),
           "n_h1_shell_negatives": len(shell), "negatives_fired": neg_fire,
           "neg_rate": rate(neg_fire, len(shell))}
    print(f"[shell] rule 4 fires on {pos_fire}/{len(recs)} human labellings "
          f"vs {neg_fire}/{len(shell)} H1-shell negatives", flush=True)
    return res


def main():
    recs, units = collect()
    print(f"pool: {len(recs)} participants, {len(units)} labelled (participant,arg) units",
          flush=True)
    out = {"pool": {"n_participants": len(recs), "n_units": len(units),
                    "n_reinstated_abi": sum(1 for u in units if u["reinstated_abi"]),
                    "n_reinstated_out": sum(1 for u in units if u["reinstated_out"]),
                    "n_many_attackers": sum(1 for u in units if u["n_att"] >= 2)}}
    # cell-level dedup: first occurrence of each unique ((graph, labelling), arg) unit
    seen, cell_units = set(), []
    for u in units:
        if u["cell"] in seen:
            continue
        seen.add(u["cell"])
        cell_units.append(u)
    for key, name in (("reinstated_abi", "abi_aux_predicate_verbatim"),
                      ("reinstated_out", "out_attackers_all_labelled_out")):
        print(f"\n--- operationalization: {name} ---", flush=True)
        out[name] = {
            "response_level": table_and_tests(units, f"{key} response-level", key),
            "cell_level": table_and_tests(cell_units, f"{key} cell-level", key),
            "participant_clustered": participant_sign_test(units, key)}
    print("\n--- where the learner's rule-4 evidence lives ---", flush=True)
    out["shell_diagnostic"] = shell_diagnostic(recs)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=1)
    os.replace(tmp, OUT)
    print(f"-> {OUT}\nDONE", flush=True)


if __name__ == "__main__":
    main()
