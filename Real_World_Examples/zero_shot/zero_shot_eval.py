#!/usr/bin/env python3
"""Zero-shot (out-of-corpus) evaluation of the FROZEN human semantics sigma_H.

sigma_H (sigma_h_frozen.lp, tag sigma-h-frozen-20260903) was learned from the Guillaume et
al. (2022) corpus only.  Here it is applied, unchanged, to the stimuli and published
aggregate responses of independent studies (external_afs.py, external_responses.py) and
compared with the catalogue semantics exactly as the Exp2 pipeline compares them
(discover_semantics.textbook_labellings + project):

  * status(kind, af, reading): the three-valued status of every argument.
      - catalogue semantics (grounded / complete / preferred / stable / cf2, ASPARTIX
        encodings), projected 'skeptical' = strongly accepted / strongly rejected / weakly
        undecided -- the statistic the external papers themselves use.  A semantics with
        NO extension on a framework (stable on AF3/AF6/AF11) makes no prediction there:
        status 'none', excluded from every score and counted.
      - sigma_H: the LEGAL labellings of the frozen verifier, projected 'skeptical' (the
        reading above) and 'credulous' (plurality; the in-corpus reading behind
        committed-only accuracy in the paper -- reported for honesty, see the JSON note).
        A framework with NO legal labelling (AF7) gets status 'none' for every argument:
        the theory is unsatisfiable there, which is reported as such, never as 'undecided'.
  * per-argument agreement with the published MAJORITY response (3 groups for Cramer &
    Guillaume 2019): acc3, Cohen's kappa, committed-only accuracy (arguments whose majority
    is accept/reject), commit precision (arguments the predictor commits on).
  * the verifier's native question: is the whole-framework majority labelling admitted?
  * a permissiveness control (admitted labellings / 3^n), and the number of extensions of
    each catalogue semantics.
  * the two frozen predictions of the paper (Sec. 8.1):
      P1  ACYCLIC single-attacker reinstatement chain -> full (committal) reinstatement
      P2  ACYCLIC reinstated argument with >= 2 attackers -> reinstatement BLOCKED
    Instances are grounded-reinstated arguments (attacked; every attacker OUT in the
    grounded labelling) with the argument and its attackers off every directed cycle.
    Reinstated arguments that sit on or behind a cycle (floating / cyclic reinstatement)
    are OUTSIDE P1/P2 (sigma_H's chain rules carry `not in_cycle`) and are listed apart.

Everything is evaluation-only: no learning run, no parameter, no fitting.
"""
import json, os, sys
from collections import Counter, OrderedDict
HERE = os.path.dirname(os.path.abspath(__file__)); RWE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(RWE, "scripts")); sys.path.insert(0, HERE)
import clingo
import discover_semantics as D
from external_afs import CG2019, CG2018, lower
from external_responses import CG2019_MAJORITY, CG2018_PCT, GROUPS

FROZEN = open(os.path.join(HERE, "sigma_h_frozen.lp")).read()
CATALOGUE = ("grounded", "complete", "preferred", "stable", "cf2")
READINGS = ("skeptical", "credulous")
RULE_LABELS = ("1", "2a", "2b", "3", "4")   # order of the five `violated` rules in the frozen program
RULES = [ln for ln in FROZEN.splitlines() if ln.startswith("violated :-")]
assert len(RULES) == 5
HUMAN = {"accept": "in", "reject": "out", "undecided": "undec", "tie": None}
CLASSES = ("in", "out", "undec")


def facts(af):
    return " ".join(f"arg({a})." for a in af["args"]) + " " + " ".join(f"att({x},{y})." for x, y in af["att"])


def sigma_h_program(rules_off=()):
    """The frozen program with the named rules switched off (labels of RULE_LABELS; used
    only for the ablations -- '4' is the smoke/fire candidate)."""
    out, k = [], 0
    for ln in FROZEN.splitlines():
        if ln.startswith("violated :-"):
            lab = RULE_LABELS[k]; k += 1
            if lab in rules_off:
                out.append("% (off) " + ln); continue
        out.append(ln)
    return "\n".join(out)


def sigma_h_labellings(af, rules_off=()):
    """Legal labellings of the frozen sigma_H (optionally with named rules switched off)."""
    ctl = clingo.Control(["0", "--warn=none"])
    ctl.add("base", [], sigma_h_program(rules_off) + "\n" + facts(af))
    ctl.ground([("base", [])])
    labs = []
    def on_model(m):
        ins = {str(s.arguments[0]) for s in m.symbols(shown=True) if s.name == "in"}
        outs = {str(s.arguments[0]) for s in m.symbols(shown=True) if s.name == "out"}
        labs.append({a: ("in" if a in ins else "out" if a in outs else "undec") for a in af["args"]})
    ctl.solve(on_model=on_model)
    return labs


_STATIC = [ln for ln in FROZEN.splitlines()
           if not ln.startswith(("0 { in(X) }", "0 { out(X) }", ":- in(X), out(X).", ":- violated.", "#show", "violated :-"))]


def firing_rules(af, labelling, rules_off=()):
    """Which sigma_H rules (by label) fire on a GIVEN labelling -- the verifier's native question."""
    given = " ".join(f"in({a})." if v == "in" else f"out({a})." for a, v in labelling.items() if v != "undec")
    fired = []
    for lab, rule in zip(RULE_LABELS, RULES):       # always the full, ordered rule list
        if lab in rules_off:
            continue
        ctl = clingo.Control(["--warn=none"])
        ctl.add("base", [], "\n".join(_STATIC) + "\n" + rule + "\n#show violated/0.\n" + facts(af) + " " + given)
        ctl.ground([("base", [])])
        hit = []
        ctl.solve(on_model=lambda m: hit.append(any(s.name == "violated" for s in m.symbols(shown=True))))
        if hit and hit[0]:
            fired.append(lab)
    return fired


def labellings(kind, af, rules_off=()):
    return sigma_h_labellings(af, rules_off) if kind == "sigma_h" else D.textbook_labellings(kind, af["args"], af["att"])


def status(kind, af, reading="skeptical", rules_off=(), labs=None):
    """Three-valued status per argument; 'none' everywhere when the predictor has no
    labelling on this framework (unsatisfiable sigma_H, or no extension)."""
    if labs is None:
        labs = labellings(kind, af, rules_off)
    if not labs:
        return {a: "none" for a in af["args"]}, 0
    return D.project(labs, af["args"], reading), len(labs)


def kappa(pairs):
    """Cohen's kappa over (gold, pred) pairs, 3 classes."""
    n = len(pairs)
    if not n:
        return float("nan")
    po = sum(g == p for g, p in pairs) / n
    cg, cp = Counter(g for g, _ in pairs), Counter(p for _, p in pairs)
    pe = sum(cg[c] * cp[c] for c in CLASSES) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def in_cycle_set(af):
    reach = {a: set() for a in af["args"]}
    for x, y in af["att"]:
        reach[x].add(y)
    changed = True
    while changed:
        changed = False
        for a in af["args"]:
            new = set(reach[a])
            for b in list(reach[a]):
                new |= reach[b]
            if new != reach[a]:
                reach[a] = new; changed = True
    return {a for a in af["args"] if a in reach[a]}


def score_rows(gold, preds):
    """gold/preds: {argnum: label}; arguments with pred 'none' are excluded and counted."""
    res = {}
    for p, pr in preds.items():
        sc = [n for n in gold if gold[n] is not None and pr[n] != "none"]
        none = [n for n in gold if gold[n] is not None and pr[n] == "none"]
        committed = [n for n in sc if gold[n] in ("in", "out")]
        pc = [n for n in sc if pr[n] in ("in", "out")]
        res[p] = {"acc3": sum(pr[n] == gold[n] for n in sc) / len(sc) if sc else float("nan"),
                  "kappa": kappa([(gold[n], pr[n]) for n in sc]),
                  "n": len(sc), "n_no_prediction": len(none),
                  "acc_committed": sum(pr[n] == gold[n] for n in committed) / len(committed) if committed else float("nan"),
                  "n_committed": len(committed),
                  "commit_precision": sum(pr[n] == gold[n] for n in pc) / len(pc) if pc else float("nan"),
                  "n_predictor_committed": len(pc)}
    return res


def evaluate_cg2019(rules_off=(), verbose=True):
    """Per-argument agreement with the majority responses of Cramer & Guillaume (2019)."""
    preds, nlegal = {}, {}
    for name, af0 in CG2019.items():
        af = lower(af0)
        for sem in CATALOGUE:
            st, _ = status(sem, af)
            preds.setdefault(sem, {}).update({af["num"][a]: st[a] for a in af["args"]})
        labs = sigma_h_labellings(af, rules_off); nlegal[name] = len(labs)
        for rd in READINGS:
            st, _ = status("sigma_h", af, rd, labs=labs)
            preds.setdefault(f"sigma_h/{rd}", {}).update({af["num"][a]: st[a] for a in af["args"]})
    res = OrderedDict()
    for group in GROUPS:
        gold = {n: HUMAN[CG2019_MAJORITY[n][group]] for n in CG2019_MAJORITY}
        for p, r in score_rows(gold, preds).items():
            res[(group, p)] = r
    if verbose:
        print(f"\n== Cramer & Guillaume 2019: 12 AFs / 60 arguments; majority response per group  (rules off: {rules_off or 'none'})")
        print("   sigma_H legal labellings per AF:", nlegal)
        for group in GROUPS:
            print(f"   [{group}]  predictor           acc3   kappa  n   no-pred  acc_committed(n)  commit-precision(n)")
            for p in list(CATALOGUE) + [f"sigma_h/{rd}" for rd in READINGS]:
                r = res[(group, p)]
                print(f"      {p:20} {r['acc3']:.3f}  {r['kappa']:+.3f}  {r['n']:2d}   {r['n_no_prediction']:2d}      "
                      f"{r['acc_committed']:.3f} ({r['n_committed']:2d})        {r['commit_precision']:.3f} ({r['n_predictor_committed']:2d})")
    return res, preds, nlegal


def is_labelling_of(kind, af, lab):
    return lab in D.textbook_labellings(kind, af["args"], af["att"])


def admission_cg2019(rules_off=(), verbose=True):
    """Labelling-level test: is the whole-framework MAJORITY labelling admitted by sigma_H
    (no rule fires), and is it a grounded / complete / preferred / cf2 labelling?"""
    if verbose:
        print(f"\n== Labelling-level admission of the majority labelling, Cramer & Guillaume 2019 (rules off: {rules_off or 'none'})")
    rows = []
    for name, af0 in CG2019.items():
        af = lower(af0)
        for g in GROUPS:
            lab = {a: HUMAN[CG2019_MAJORITY[af["num"][a]][g]] for a in af["args"]}
            if any(v is None for v in lab.values()):
                rows.append({"af": name, "group": g, "labelling": "tie", "legal": None, "fires": None,
                             "grounded": None, "complete": None, "preferred": None, "cf2": None}); continue
            fired = firing_rules(af, lab, rules_off)
            flags = {k: is_labelling_of(k, af, lab) for k in ("grounded", "complete", "preferred", "cf2")}
            rows.append({"af": name, "group": g, "labelling": lab, "legal": not fired, "fires": fired, **flags})
            if verbose:
                ltxt = " ".join(f"{a.upper()}:{v[:2]}" for a, v in lab.items())
                print(f"   {name:5} {g:12} {ltxt:40} {'LEGAL' if not fired else 'illegal':8} {','.join(fired) or '-':6} "
                      + "  ".join(f"{k}={'yes' if v else 'no '}" for k, v in flags.items()))
    if verbose:
        for g in GROUPS:
            r = [x for x in rows if x["group"] == g and x["labelling"] != "tie"]
            print(f"   [{g}] admitted by sigma_H: {sum(x['legal'] for x in r)}/{len(r)};  grounded: {sum(x['grounded'] for x in r)};  "
                  f"complete: {sum(x['complete'] for x in r)};  preferred: {sum(x['preferred'] for x in r)};  cf2: {sum(x['cf2'] for x in r)}")
    return rows


def permissiveness():
    out = {}
    for name, af0 in CG2019.items():
        af = lower(af0)
        out[name] = {"n": len(af["args"]), "sigma_H": len(sigma_h_labellings(af)),
                     **{k: len(D.textbook_labellings(k, af["args"], af["att"])) for k in CATALOGUE}}
    return out


def frozen_predictions(rules_off=(), verbose=True):
    """P1 / P2 instances (acyclic, grounded-reinstated) and the floating/cyclic reinstated
    arguments that fall outside them, with the majority responses."""
    rows = []
    for src, afs in (("CG2019", CG2019), ("CG2018", CG2018)):
        for name, af0 in afs.items():
            af = lower(af0)
            attackers = {a: [x for x, y in af["att"] if y == a] for a in af["args"]}
            cyc = in_cycle_set(af)
            gr, _ = status("grounded", af)
            labs = sigma_h_labellings(af, rules_off)
            for a in af["args"]:
                if not attackers[a]:
                    continue
                g_reinst = all(gr[x] == "out" for x in attackers[a])
                every_attacker_attacked = all(any(y == x for _, y in af["att"]) for x in attackers[a])
                acyclic = a not in cyc and all(x not in cyc for x in attackers[a])
                if g_reinst and acyclic:
                    kind = "P1 single-attacker chain" if len(attackers[a]) == 1 else "P2 multi-attacker"
                elif a not in cyc and every_attacker_attacked:
                    # reinstatement that runs through a cycle (floating / behind a cycle): the chain
                    # rules of sigma_H carry `not in_cycle` on the attackers' side only indirectly, and
                    # the paper's P1/P2 were stated for acyclic chains -- listed apart, not scored as P1/P2
                    kind = "floating/behind-cycle reinstatement (outside P1/P2)"
                else:
                    continue
                sh = {rd: status("sigma_h", af, rd, labs=labs)[0][a] for rd in READINGS}
                if src == "CG2019":
                    num = af["num"][a]; human = {g: CG2019_MAJORITY[num][g] for g in GROUPS}
                else:
                    human = {"pct": CG2018_PCT[name][a.upper()]}
                rows.append({"src": src, "af": name, "arg": a.upper(), "kind": kind, "n_attackers": len(attackers[a]),
                             "in_cycle": a in cyc, "grounded_reinstated": g_reinst, "sigma_h": sh,
                             "n_legal": len(labs), "theory_inconsistent": len(labs) == 0,
                             "catalogue": {s: status(s, af)[0][a] for s in ("grounded", "preferred", "cf2")}, "human": human})
    if verbose:
        print(f"\n== Frozen predictions (Sec. 8.1), rules off: {rules_off or 'none'}")
        for r in rows:
            sh = "NO LEGAL LABELLING" if r["theory_inconsistent"] else f"sk={r['sigma_h']['skeptical']} cr={r['sigma_h']['credulous']}"
            print(f"   {r['src']} {r['af']:9} {r['arg']}  {r['kind']:44} attackers={r['n_attackers']} cyc={int(r['in_cycle'])}  "
                  f"sigma_H: {sh:26} legal={r['n_legal']:3d}  catalogue={r['catalogue']}  human={r['human']}")
    return rows


def cg2018(verbose=True):
    if verbose:
        print("\n== Cramer & Guillaume 2018 (COMMA): percentages read off Fig. 4 (+-3), majority; labelling-level admission")
    out = {}
    for name, af0 in CG2018.items():
        af = lower(af0)
        labs = sigma_h_labellings(af)
        maj = {}
        for a in af["args"]:
            pct = CG2018_PCT[name][a.upper()]
            top = sorted(pct.values(), reverse=True)
            maj[a] = max(pct, key=pct.get)
            # the majority must be robust to the +-3 reading error, or be stated in the paper's text
            # (Cramer & Guillaume 2018, Sec. 6: 3-cycle -- "the majority of participants accepted A
            # and rejected B while considering every other argument as undecided")
            assert top[0] - top[1] > 6 or (name == "cycle3" and a in ("c", "d", "e") and maj[a] == "undecided"), (name, a, pct)
            out[f"{name}/{a.upper()}"] = {"pct": pct, "majority": maj[a],
                                          "sigma_h": {rd: status("sigma_h", af, rd, labs=labs)[0][a] for rd in READINGS},
                                          "catalogue": {s: status(s, af)[0][a] for s in ("grounded", "preferred", "cf2")}}
        lab = {a: HUMAN[maj[a]] for a in af["args"]}
        fired = firing_rules(af, lab)
        flags = {k: is_labelling_of(k, af, lab) for k in ("grounded", "complete", "preferred", "cf2")}
        out[f"{name}/majority_labelling"] = {"labelling": lab, "legal": not fired, "fires": fired, **flags}
        if verbose:
            print(f"   {name:9} " + " | ".join(f"{a.upper()}:{maj[a][:3].upper()} sH={out[f'{name}/{a.upper()}']['sigma_h']['skeptical'][:2]} "
                                              f"gr={out[f'{name}/{a.upper()}']['catalogue']['grounded'][:2]} cf2={out[f'{name}/{a.upper()}']['catalogue']['cf2'][:2]}" for a in af["args"]))
            print(f"             majority labelling: sigma_H={'LEGAL' if not fired else 'illegal ' + ','.join(fired)}  "
                  + "  ".join(f"{k}={'yes' if v else 'no'}" for k, v in flags.items()))
    return out


def self_test():
    """Guards for the defects found in review: rule labelling under ablation, 'none' status."""
    af = lower(CG2019["AF1"])
    lab = {a: HUMAN[CG2019_MAJORITY[af["num"][a]]["all"]] for a in af["args"]}
    assert firing_rules(af, lab) == ["2b"], firing_rules(af, lab)
    assert firing_rules(af, lab, rules_off=("2a",)) == ["2b"]
    assert firing_rules(af, lab, rules_off=("1",)) == ["2b"]
    assert status("sigma_h", lower(CG2019["AF7"]))[0] == {a: "none" for a in lower(CG2019["AF7"])["args"]}
    assert status("stable", lower(CG2019["AF3"]))[0]["l"] == "none"


def main():
    self_test()
    out = {"note": "sigma_h/credulous is the plurality projection over all legal labellings (the in-corpus "
                   "reading behind committed-only accuracy in the paper); on these frameworks sigma_H admits "
                   "10-550 labellings, so the plurality commits almost everywhere -- reported for honesty, not "
                   "as a meaningful point predictor. Status 'none' = the predictor has no labelling/extension "
                   "on that framework (excluded from every score, counted in n_no_prediction)."}
    res, preds, nlegal = evaluate_cg2019()
    out["cg2019"] = {f"{g}|{p}": v for (g, p), v in res.items()}
    out["cg2019_predictions"] = {p: {str(k): v for k, v in pr.items()} for p, pr in preds.items()}
    out["cg2019_sigma_h_legal_count"] = nlegal
    res3, _, nlegal3 = evaluate_cg2019(rules_off=("4",))
    out["cg2019_rules1to3"] = {f"{g}|{p}": v for (g, p), v in res3.items()}
    out["cg2019_rules1to3_legal_count"] = nlegal3
    out["cg2019_admission"] = admission_cg2019()
    out["cg2019_admission_rules1to3"] = admission_cg2019(rules_off=("4",))
    out["cg2019_permissiveness"] = permissiveness()
    print("\n   permissiveness (admitted labellings / 3^n; 0 = no extension / no legal labelling):")
    for name, v in out["cg2019_permissiveness"].items():
        tot = 3 ** v["n"]
        print(f"      {name:5} n={v['n']} 3^n={tot:5d}  " + "  ".join(f"{k}={v[k]} ({100*v[k]/tot:.1f}%)" for k in ("sigma_H",) + CATALOGUE))
    out["cg2019_all_undec_baseline"] = {}
    for g in GROUPS:
        gold = [HUMAN[CG2019_MAJORITY[n][g]] for n in CG2019_MAJORITY]; gold = [x for x in gold if x is not None]
        out["cg2019_all_undec_baseline"][g] = sum(x == "undec" for x in gold) / len(gold)
        print(f"   all-undecided baseline [{g}]: acc3 = {sum(x == 'undec' for x in gold)}/{len(gold)} = {out['cg2019_all_undec_baseline'][g]:.3f}")
    out["frozen_predictions"] = frozen_predictions()
    out["frozen_predictions_rules1to3"] = frozen_predictions(rules_off=("4",))
    out["cg2018"] = cg2018()
    json.dump(out, open(os.path.join(HERE, "zero_shot_results.json"), "w"), indent=1)
    print("\nwrote", os.path.join(HERE, "zero_shot_results.json"))


if __name__ == "__main__":
    main()
