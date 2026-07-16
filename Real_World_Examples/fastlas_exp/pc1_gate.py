#!/usr/bin/env python3
"""P2 probe: run the synthetic grounded GATE through the EXACT harness machinery
(per_condition_experiment.run_vocab with gate_labels='grounded'), but with the
incremental state file redirected to a scratch path so we do NOT race the live
--smoke process, whose _flush() rewrites the whole shared OUT file.
No harness code is modified; OUT is a module-global read by _flush/_load."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import per_condition_experiment as P

SCRATCH = ("/private/tmp/claude-501/-Users-fdasaro-Desktop-Zlatina-FabioExperimentsMacM4-claude/"
           "b944494f-f629-4bf2-b8ab-90204d85f7ef/scratchpad")
os.makedirs(SCRATCH, exist_ok=True)
P.OUT = os.path.join(SCRATCH, "pc1_gate_state.json")
print(f"[pc1] gate state -> {P.OUT}", flush=True)

state = P._load()
P.run_vocab(state, "final", True, P.VERSIONS, gate_labels="grounded")
P.report(state, "final", "aux_GATE")
print("\n[pc1] GATE DONE", flush=True)
