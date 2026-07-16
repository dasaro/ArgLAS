#!/usr/bin/env python3
"""P3 probe 4: demonstrate report()'s None handling: within/global/transfer None -> nan (ok),
cf2 committed_only None -> TypeError crash (vals[3] has no None fallback)."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts")); sys.path.insert(0, HERE)
import per_condition_experiment as pce

def fake_cond(cf2_none):
    row = lambda v: {"credulous": {"acc3": 0.5, "committed_only": v, "n_committed": 0 if v is None else 10}}
    return {"done": True, "n_cells": 5,
            "table": {"within": row(None), "global": row(0.5), "transfer": row(0.5),
                      "cf2": row(None if cf2_none else 0.7)},
            "tests": {"H1_within_vs_global": {"credulous": {"n1_only": 0, "n2_only": 0, "p": 1.0}},
                      "H2_within_vs_transfer": {"credulous": {"n1_only": 0, "n2_only": 0, "p": 1.0}}},
            "paired": {a: [1, 0] for a in ("within", "global", "transfer", "cf2")}}

for cf2_none in (False, True):
    state = {"final_aux": {"conditions": {"D": fake_cond(cf2_none)}}}
    print(f"\n--- cf2 committed_only {'None' if cf2_none else '0.7'} ---")
    try:
        pce.report(state, "final", "aux")
        print("report() OK")
    except Exception as e:
        print(f"report() CRASH: {type(e).__name__}: {e}")
