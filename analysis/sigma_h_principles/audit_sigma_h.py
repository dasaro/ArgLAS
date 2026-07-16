#!/usr/bin/env python3
"""Principle-profile audit of the learned human semantics sigma_H (AIJ paper, Section 8).

sigma_H is the Figure "consensus human acceptance policy": a labelling VERIFIER --
a 3-valued labelling (via the fl_discover generator _GEN) is *legal* iff none of the
five consensus `violated` rules fires.  Rule set (read from
Real_World_Examples/fastlas_exp/results/consensus.json, i.e. exactly what the paper
prints): final_base consensus_rules[0..3] + the final_aux smoke/fire rule
(reinstated & has_many_attackers).

This script enumerates ALL labelled digraphs with n <= NMAX arguments (self-attacks
included; the same exhaustive surface as analysis/zlatina_theorems/check_equivalence.py,
~66k AFs at NMAX=4) and, per AF, computes

  * legal(F)    -- sigma_H's legal labellings (clingo: _GEN + features + rules + ":- violated.")
  * complete(F) -- the complete labellings (standard Caminada labelling encoding)

and audits the Baroni-Caminada-Giacomin principle catalogue:

  (i)   totality          : legal(F) is non-empty for every F
  (ii)  conflict-freeness : the in-set of every legal labelling is conflict-free
  (iii) admissibility     : the in-set of every legal labelling is admissible
  (iv)  reinstatement     : in every legal labelling, every argument defended by the
                            in-set (all its attackers attacked by the in-set;
                            vacuously, every unattacked argument) is itself in
  (v)   relation to complete: is every complete labelling legal?  is every legal
                            labelling complete (overall / on acyclic AFs)?  on acyclic
                            AFs, is the unique complete(=grounded) labelling legal?
  (vi)  directionality    : for every unattacked set U, the accepted sets of F
                            restricted to U coincide with the accepted sets of F|U
                            ({in(L) & U : L in legal(F)} = {in(L') : L' in legal(F|U)}).
                            (Failure implies sigma_H is not SCC-recursive either,
                            since SCC-recursive semantics satisfy directionality.)

For each violated principle the lexicographically minimal counterexample (first in the
n-ascending, edge-mask-ascending enumeration order) is recorded.  Output JSON goes to
Real_World_Examples/fastlas_exp/results/sigma_h_principle_audit.json.

Reused verbatim (imported, not copied): _GEN, _FEATS, _FEATS_ENR from
Real_World_Examples/fastlas_exp/fl_discover.py and AUX9_BG from
Real_World_Examples/fastlas_exp/aux9_combined.py.
"""
import itertools, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
FLX = os.path.join(REPO, "Real_World_Examples", "fastlas_exp")
sys.path.insert(0, FLX)

import clingo
import fl_discover as G            # _GEN, _FEATS, _FEATS_ENR (verbatim reuse)
from aux9_combined import AUX9_BG  # aux feature background (verbatim reuse)

RESULTS = os.path.join(FLX, "results")
CONSENSUS = os.path.join(RESULTS, "consensus.json")
OUT = os.path.join(RESULTS, "sigma_h_principle_audit.json")

NMAX = int(sys.argv[1]) if len(sys.argv) > 1 else 4


# ---------------------------------------------------------------- rule set
def load_rules():
    c = json.load(open(CONSENSUS))
    base = [r["rule"] for r in c["final_base"]["consensus_rules"]]        # 4 rules
    aux = [r["rule"] for r in c["final_aux"]["consensus_rules"]
           if "reinstated" in r["rule"] and "has_many_attackers" in r["rule"]
           and r["rule"].count(",") == 2]                                  # smoke/fire rule
    assert len(base) == 4, base
    assert len(aux) == 1, aux
    return base + aux


# ---------------------------------------------------------------- programs
def sigma_h_program(rules):
    feats = G._FEATS + "\n" + G._FEATS_ENR + "\n" + AUX9_BG
    return "\n".join([G._GEN, feats] + rules + [":- violated.",
                                                "#show in/1.", "#show out/1."])

COMPLETE = """1 { in(X); out(X); undec(X) } 1 :- arg(X).
att_in(X) :- att(Y,X), in(Y).
att_not_out(X) :- att(Y,X), not out(Y).
:- in(X), att_not_out(X).
:- out(X), not att_in(X).
:- undec(X), att_in(X).
:- undec(X), not att_not_out(X).
#show in/1.
#show out/1.
"""


def labellings(prog, n, edges):
    """All models as tuples over args 0..n-1 with entries 'i'/'o'/'u'."""
    facts = "".join(f"arg(a{i})." for i in range(n)) + \
            "".join(f"att(a{i},a{j})." for i, j in edges)
    ctl = clingo.Control(["0", "--warn=none"])
    ctl.add("base", [], prog + "\n" + facts)
    ctl.ground([("base", [])])
    labs = set()
    with ctl.solve(yield_=True) as h:
        for m in h:
            ins, ous = set(), set()
            for a in m.symbols(shown=True):
                (ins if a.name == "in" else ous).add(int(str(a.arguments[0])[1:]))
            labs.add(tuple("i" if k in ins else "o" if k in ous else "u"
                           for k in range(n)))
    return labs


# ---------------------------------------------------------------- AF surface
def all_afs(n):
    pairs = [(i, j) for i in range(n) for j in range(n)]  # self-attacks included
    for mask in range(2 ** len(pairs)):
        yield [pairs[k] for k in range(len(pairs)) if mask >> k & 1]


def is_acyclic(n, edges):
    adj = {i: [] for i in range(n)}
    for s, t in edges:
        adj[s].append(t)
    state = [0] * n  # 0 unseen, 1 on stack, 2 done

    def dfs(v):
        state[v] = 1
        for w in adj[v]:
            if state[w] == 1 or (state[w] == 0 and dfs(w)):
                return True
        state[v] = 2
        return False
    return not any(state[v] == 0 and dfs(v) for v in range(n))


# ---------------------------------------------------------------- principles
def in_set(lab):
    return frozenset(k for k, v in enumerate(lab) if v == "i")


def conflict_free(S, edges):
    return not any(s in S and t in S for s, t in edges)


def admissible(S, n, edges):
    if not conflict_free(S, edges):
        return False
    attacked_by_S = {t for s, t in edges if s in S}
    # every attacker y of a member of S must itself be attacked by S
    return all(y in attacked_by_S for y, x in edges if x in S)


def reinstatement_ok(lab, n, edges):
    """every argument defended by the in-set (all attackers attacked by in-set,
    vacuously if unattacked) must itself be in."""
    S = in_set(lab)
    attacked_by_S = {t for s, t in edges if s in S}
    for x in range(n):
        attackers = [s for s, t in edges if t == x]
        if all(y in attacked_by_S for y in attackers) and x not in S:
            return False
    return True


def witness(n, edges, lab=None, extra=None):
    w = {"n": n, "attacks": sorted(edges)}
    if lab is not None:
        w["labelling"] = {f"a{k}": {"i": "in", "o": "out", "u": "undec"}[v]
                          for k, v in enumerate(lab)}
    if extra:
        w.update(extra)
    return w


# ---------------------------------------------------------------- main
def main():
    rules = load_rules()
    prog_h = sigma_h_program(rules)
    print("sigma_H rule set:")
    for r in rules:
        print("  ", r)

    legal_cache = {}   # (n, frozenset(edges)) -> set of labelling tuples

    def legal_of(n, edges):
        key = (n, frozenset(edges))
        if key not in legal_cache:
            legal_cache[key] = labellings(prog_h, n, edges)
        return legal_cache[key]

    stats = {
        "nmax": NMAX,
        "rules": rules,
        "afs_total": 0, "afs_acyclic": 0,
        "legal_labellings_total": 0, "complete_labellings_total": 0,
        "totality": {"violated_afs": 0, "witness": None},
        "conflict_freeness": {"violated_afs": 0, "violating_labellings": 0, "witness": None},
        "admissibility": {"violated_afs": 0, "violating_labellings": 0, "witness": None},
        "reinstatement": {"violated_afs": 0, "violating_labellings": 0, "witness": None,
                          "clean_witness": None},  # clean = in-set admissible
        "complete_subset_legal": {"violated_afs": 0, "witness": None},
        "legal_subset_complete": {"violated_afs": 0, "witness": None},
        "acyclic_grounded_legal": {"checked_afs": 0, "violated_afs": 0, "witness": None},
        "acyclic_legal_equals_complete": {"equal_afs": 0, "legal_strictly_larger_afs": 0,
                                          "legal_missing_complete_afs": 0,
                                          "strictly_larger_witness": None},
        "directionality": {"checked_pairs": 0, "violated_afs": 0, "violated_pairs": 0,
                           "witness": None},
    }
    t0 = time.time()
    for n in range(1, NMAX + 1):
        for edges in all_afs(n):
            stats["afs_total"] += 1
            legal = legal_of(n, edges)
            comp = labellings(COMPLETE, n, edges)
            stats["legal_labellings_total"] += len(legal)
            stats["complete_labellings_total"] += len(comp)
            acyc = is_acyclic(n, edges)
            if acyc:
                stats["afs_acyclic"] += 1
                assert len(comp) == 1, (n, edges, comp)

            # (i) totality
            if not legal:
                stats["totality"]["violated_afs"] += 1
                if stats["totality"]["witness"] is None:
                    stats["totality"]["witness"] = witness(n, edges)

            # (ii)-(iv) per legal labelling
            cf_bad = adm_bad = rei_bad = 0
            for lab in sorted(legal):
                S = in_set(lab)
                if not conflict_free(S, edges):
                    cf_bad += 1
                    if stats["conflict_freeness"]["witness"] is None:
                        stats["conflict_freeness"]["witness"] = witness(n, edges, lab)
                if not admissible(S, n, edges):
                    adm_bad += 1
                    if stats["admissibility"]["witness"] is None:
                        stats["admissibility"]["witness"] = witness(n, edges, lab)
                if not reinstatement_ok(lab, n, edges):
                    rei_bad += 1
                    if stats["reinstatement"]["witness"] is None:
                        stats["reinstatement"]["witness"] = witness(n, edges, lab)
                    if stats["reinstatement"]["clean_witness"] is None \
                            and admissible(S, n, edges):
                        stats["reinstatement"]["clean_witness"] = witness(n, edges, lab)
            for key, bad in (("conflict_freeness", cf_bad), ("admissibility", adm_bad),
                             ("reinstatement", rei_bad)):
                if bad:
                    stats[key]["violated_afs"] += 1
                    stats[key]["violating_labellings"] += bad

            # (v) relation to complete
            if not comp <= legal:
                stats["complete_subset_legal"]["violated_afs"] += 1
                if stats["complete_subset_legal"]["witness"] is None:
                    lab = sorted(comp - legal)[0]
                    stats["complete_subset_legal"]["witness"] = witness(n, edges, lab)
            if not legal <= comp:
                stats["legal_subset_complete"]["violated_afs"] += 1
                if stats["legal_subset_complete"]["witness"] is None:
                    lab = sorted(legal - comp)[0]
                    stats["legal_subset_complete"]["witness"] = witness(n, edges, lab)
            if acyc:
                stats["acyclic_grounded_legal"]["checked_afs"] += 1
                if not comp <= legal:
                    stats["acyclic_grounded_legal"]["violated_afs"] += 1
                    if stats["acyclic_grounded_legal"]["witness"] is None:
                        stats["acyclic_grounded_legal"]["witness"] = witness(
                            n, edges, sorted(comp)[0])
                if legal == comp:
                    stats["acyclic_legal_equals_complete"]["equal_afs"] += 1
                elif comp <= legal:
                    stats["acyclic_legal_equals_complete"]["legal_strictly_larger_afs"] += 1
                    if stats["acyclic_legal_equals_complete"]["strictly_larger_witness"] is None:
                        stats["acyclic_legal_equals_complete"]["strictly_larger_witness"] = \
                            witness(n, edges, sorted(legal - comp)[0])
                else:
                    stats["acyclic_legal_equals_complete"]["legal_missing_complete_afs"] += 1

            # (vi) directionality over accepted sets
            af_dir_bad = False
            for size in range(1, n):
                for U in itertools.combinations(range(n), size):
                    Uset = set(U)
                    if any(s not in Uset and t in Uset for s, t in edges):
                        continue  # not an unattacked set
                    stats["directionality"]["checked_pairs"] += 1
                    remap = {v: k for k, v in enumerate(U)}
                    redges = [(remap[s], remap[t]) for s, t in edges
                              if s in Uset and t in Uset]
                    sub_legal = legal_of(size, redges)
                    proj = {frozenset(remap[x] for x in in_set(lab) if x in Uset)
                            for lab in legal}
                    sub = {in_set(lab) for lab in sub_legal}
                    if proj != sub:
                        stats["directionality"]["violated_pairs"] += 1
                        af_dir_bad = True
                        if stats["directionality"]["witness"] is None:
                            stats["directionality"]["witness"] = witness(
                                n, edges, extra={
                                    "unattacked_set": [f"a{u}" for u in U],
                                    "accepted_sets_projected": sorted(
                                        sorted(f"a{x}" for x in s) for s in proj),
                                    "accepted_sets_restricted_af": sorted(
                                        sorted(f"a{x}" for x in s) for s in sub)})
            if af_dir_bad:
                stats["directionality"]["violated_afs"] += 1
        print(f"[n<={n}] cumulative: {stats['afs_total']} AFs, "
              f"{time.time()-t0:.0f}s", flush=True)

    # ---------------- attribution ablations ----------------
    # A: drop rule 4 (smoke/fire) -> is the totality failure exactly rule 4's doing?
    # B: strict rule 1 (no attacked_by_in exception) -> is the CF failure exactly
    #    the exception's doing?
    prog_no4 = sigma_h_program(rules[:4])
    strict1 = ["violated :- not defended(V0), in(V0), arg(V0)."] + rules[1:]
    prog_strict1 = sigma_h_program(strict1)
    abl = {"drop_rule4": {"totality_violated_afs": 0, "cf_violated_afs": 0},
           "strict_rule1": {"cf_violated_afs": 0, "totality_violated_afs": 0}}
    ta = time.time()
    for n in range(1, NMAX + 1):
        for edges in all_afs(n):
            l4 = labellings(prog_no4, n, edges)
            if not l4:
                abl["drop_rule4"]["totality_violated_afs"] += 1
            if any(not conflict_free(in_set(lab), edges) for lab in l4):
                abl["drop_rule4"]["cf_violated_afs"] += 1
            l1 = labellings(prog_strict1, n, edges)
            if not l1:
                abl["strict_rule1"]["totality_violated_afs"] += 1
            if any(not conflict_free(in_set(lab), edges) for lab in l1):
                abl["strict_rule1"]["cf_violated_afs"] += 1
    abl["secs"] = round(time.time() - ta, 1)
    stats["ablations"] = abl

    # ---------------- the seven experimental stimulus graphs ----------------
    GOLD = {"float_ABC": (4, [("b", "a"), ("c", "b"), ("c", "d"), ("d", "b"), ("d", "c")],
                          ["a", "b", "c", "d"]),
            "simple_DEF": (3, [("b", "a"), ("c", "b")], ["a", "b", "c"]),
            "cycle_G": (5, [("b", "a"), ("c", "b"), ("c", "d"), ("d", "b"), ("d", "e"),
                            ("e", "b"), ("e", "c")], ["a", "b", "c", "d", "e"])}
    gold = {}
    for name, (n, atts, names) in GOLD.items():
        idx = {a: i for i, a in enumerate(names)}
        edges = [(idx[s], idx[t]) for s, t in atts]
        legal = labellings(prog_h, n, edges)
        comp = labellings(COMPLETE, n, edges)
        gold[name] = {"n_legal": len(legal), "n_complete": len(comp),
                      "total": bool(legal), "complete_subset_legal": comp <= legal,
                      "cf_violating_legal": sum(1 for lab in legal
                                                if not conflict_free(in_set(lab), edges))}
    stats["gold_stimulus_graphs"] = gold

    stats["secs"] = round(time.time() - t0, 1)
    for p in ("totality", "conflict_freeness", "admissibility", "reinstatement",
              "complete_subset_legal", "legal_subset_complete", "directionality"):
        stats[p]["holds"] = stats[p]["violated_afs"] == 0
    json.dump(stats, open(OUT, "w"), indent=1)
    print(json.dumps({k: (v if not isinstance(v, dict) else
                          {kk: vv for kk, vv in v.items() if kk != "witness"})
                      for k, v in stats.items() if k != "rules"}, indent=1))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
