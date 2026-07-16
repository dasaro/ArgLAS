#!/usr/bin/env python3
"""Decisive OPL-vs-NOPL probe: can FastLAS RECOVER a known semantics on the study graphs, and
which mode (--opl faster / --nopl more expressive) works? Builds a clean synthetic task (each
graph labelled by the textbook semantics), runs both modes, reports timing + learned rules.

  python3 run_probe.py --version D --kind grounded --variant det [--enrich] [--maxv 2] [--timeout 120]
"""
import argparse, os, subprocess, tempfile, time
import fl_build as F


def run_fastlas(task_text, mode, timeout=120, extra=None):
    with tempfile.NamedTemporaryFile("w", suffix=".las", delete=False) as f:
        f.write(task_text); path = f.name
    cmd = ["FastLAS", f"--{mode}", "--timeout", str(timeout)] + (extra or []) + [path]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 60)
        out, err, rc = p.stdout, p.stderr, p.returncode
    except subprocess.TimeoutExpired:
        out, err, rc = "", "__WALL_TIMEOUT__", -1
    dt = time.time() - t0
    os.unlink(path)
    return {"mode": mode, "seconds": round(dt, 1), "rc": rc, "stdout": out.strip(), "stderr": err.strip()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="D")
    ap.add_argument("--kind", default="grounded", choices=("grounded", "stable", "complete", "preferred", "cf2"))
    ap.add_argument("--variant", default="det", choices=("det", "choice"))
    ap.add_argument("--enrich", action="store_true")
    ap.add_argument("--maxv", type=int, default=2)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--modes", default="opl,nopl")
    ap.add_argument("--constraints", action="store_true", help="add #modeh(false) constraint learning.")
    ap.add_argument("--negs", action="store_true", help="add the Hamming-1 hard shell as #neg.")
    a = ap.parse_args()

    cells = F.grounded_cells(a.version, a.kind, limit=a.limit)
    negs = F.shell_negs(cells) if a.negs else None
    task = F.build_task(cells, variant=a.variant, enrich=a.enrich, maxv=a.maxv,
                        negs=negs, constraints=a.constraints)
    outdir = os.path.dirname(os.path.abspath(__file__))
    tag = f"{a.version}_{a.kind}_{a.variant}{'_enr' if a.enrich else ''}{'_c' if a.constraints else ''}{'_neg' if a.negs else ''}_v{a.maxv}"
    with open(os.path.join(outdir, f"task_{tag}.las"), "w") as f:
        f.write(task)
    print(f"=== {tag} : {len(cells)} pos cells + {len(negs or [])} neg (clean {a.kind}) ===")
    print(f"    task written to task_{tag}.las  ({task.count(chr(10))} lines)\n")
    for mode in a.modes.split(","):
        r = run_fastlas(task, mode, timeout=a.timeout)
        head = f"[--{mode}] {r['seconds']}s rc={r['rc']}"
        if r["stderr"] == "__WALL_TIMEOUT__":
            print(f"{head}  WALL-TIMEOUT"); continue
        body = r["stdout"] or "(empty)"
        print(head)
        for ln in body.splitlines():
            print(f"    {ln}")
        if r["stderr"] and "UNSAT" not in body:
            errtail = r["stderr"].splitlines()[-3:]
            print(f"    stderr: {' / '.join(errtail)}")
        print()


if __name__ == "__main__":
    main()
