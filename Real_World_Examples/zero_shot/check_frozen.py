#!/usr/bin/env python3
"""Verify that sigma_h_frozen.lp still equals the audited sigma_H (rules + backgrounds)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); RWE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(RWE, "fastlas_exp"))
import fl_discover as G
from aux9_combined import AUX9_BG
frozen = open(os.path.join(HERE, "sigma_h_frozen.lp")).read()
audited = json.load(open(os.path.join(RWE, "fastlas_exp/results/sigma_h_principle_audit.json")))["rules"]
for block in (G._GEN, G._FEATS, G._FEATS_ENR, AUX9_BG, *audited, ":- violated."):
    assert block in frozen, f"missing from frozen program: {block[:60]}"
rules = [l for l in frozen.splitlines() if l.startswith("violated :-")]
assert rules == audited, (rules, audited)
print("sigma_h_frozen.lp == audited sigma_H (5 rules, verbatim backgrounds): OK")
