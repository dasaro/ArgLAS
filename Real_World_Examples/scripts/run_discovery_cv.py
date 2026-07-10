#!/usr/bin/env python3
"""Run the corrected discovery CV one condition at a time (5 folds, extended ILASP
timeout), writing incremental progress so it can be monitored with a live bar.

  run:    python3 run_discovery_cv.py run   --versions A,B,C,G --folds 5 --phase first \
                                            --ilasp-timeout 1800 --out /tmp/cvrun
  watch:  python3 run_discovery_cv.py watch --out /tmp/cvrun --interval 5

Each condition is independent: results are flushed after every fold and every condition,
so a kill loses at most the in-flight fold and the rest are already on disk.
"""
import argparse
import json
import os
import sys
import time

import discover_semantics as D

PHASES = {"first": "att_first__lab_first", "final": "att_final__lab_final", "group": "att_group__lab_group"}


def _write(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f)
    os.replace(tmp, path)


def cmd_run(a):
    versions = [x.strip() for x in a.versions.split(",") if x.strip()]
    D.PHASE = PHASES[a.phase]
    D.GRAPH = a.graph
    os.makedirs(a.out, exist_ok=True)
    prog_path = os.path.join(a.out, "progress.json")
    res_path = os.path.join(a.out, "results.json")
    folds = a.folds
    st = {"versions": versions, "folds": folds, "phase": a.phase, "graph": a.graph,
          "reading": a.reading, "ilasp_timeout": a.ilasp_timeout,
          "total": len(versions) * folds, "done": 0, "current": None, "results": {},
          "start": time.time(), "status": "running"}
    _write(prog_path, st)
    base = 0
    for v in versions:
        def on_prog(fdone, ftot, v=v, base=base):
            st["current"] = f"{v}: fold {fdone}/{ftot}"
            st["done"] = base + fdone
            _write(prog_path, st)
        t0 = time.time()
        try:
            r = D.cv(v, folds, ilasp_timeout=a.ilasp_timeout, on_progress=on_prog)
        except Exception as e:
            r = {"v": v, "error": repr(e)}
        r["wall_seconds"] = round(time.time() - t0, 1)
        st["results"][v] = r
        base += folds
        st["done"] = base
        _write(prog_path, st)
        _write(res_path, st["results"])
        lm = r.get("learned", {}).get(a.reading, {})
        print(f"[done] {v} in {r['wall_seconds']}s · learned({a.reading}) macroF1={lm.get('macroF1','?')}", flush=True)
    st["status"] = "done"
    st["current"] = None
    _write(prog_path, st)
    print("ALL CONDITIONS DONE")


def _bar(frac, w=32):
    n = int(round(max(0.0, min(1.0, frac)) * w))
    return "█" * n + "░" * (w - n)


def _dur(s):
    s = int(max(0, s))
    h, m = s // 3600, (s % 3600) // 60
    return f"{h}h{m:02d}m" if h else f"{m}m{s % 60:02d}s"


def cmd_watch(a):
    prog_path = os.path.join(a.out, "progress.json")
    while True:
        try:
            st = json.load(open(prog_path))
        except Exception:
            print("waiting for progress.json …")
            time.sleep(a.interval)
            continue
        done, total = st["done"], st["total"]
        el = time.time() - st["start"]
        rate = done / el if el > 0 and done else 0
        eta = _dur((total - done) / rate) if rate > 0 and done < total else ("done" if done >= total else "—")
        if a.interval:
            sys.stdout.write("\033[2J\033[H")
        print(f"Discovery CV · graph={st.get('graph','own')} phase={st['phase']} reading={st.get('reading','credulous')}"
              f" · ilasp_timeout={st['ilasp_timeout']}s · {st['folds']} folds")
        print(f"[{_bar(done / total if total else 0)}] {done}/{total} folds ({(done / total * 100) if total else 0:.0f}%) "
              f"· {st.get('current') or '—'} · elapsed {_dur(el)} · ETA ~{eta}")
        for v in st["versions"]:
            r = st["results"].get(v)
            if not r:
                running = (st.get("current") or "").startswith(v + ":")
                print(f"  {v}: {'running ' + (st['current'].split(': ', 1)[1] if running else '') if running else 'pending'}")
            elif "error" in r:
                print(f"  {v}: ERROR {r['error'][:70]}")
            else:
                rd = st.get("reading", "credulous")
                lm = r.get("learned", {}).get(rd, {})
                best = max(((k, r[k][rd]["macroF1"]) for k in D.TEXTBOOK), key=lambda x: x[1])
                to = r.get("ilasp_timeouts", 0)
                tag = f"  ⚠ {to} ILASP timeout(s)" if to else ""
                print(f"  {v}: learned macroF1={lm.get('macroF1', float('nan')):.3f} commit={lm.get('commit_rate', float('nan')):.2f}"
                      f"  |  best textbook {best[0]}={best[1]:.3f}{tag}")
        if st.get("status") == "done":
            print("\n✓ ALL DONE")
            return
        if not a.interval:
            return
        try:
            time.sleep(a.interval)
        except KeyboardInterrupt:
            return


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--versions", default="A,B,C,D,E,F,G")
    r.add_argument("--folds", type=int, default=5)
    r.add_argument("--phase", default="first", choices=tuple(PHASES))
    r.add_argument("--graph", default="own", choices=("own", "gold"))
    r.add_argument("--reading", default="credulous", choices=D.READINGS)
    r.add_argument("--ilasp-timeout", type=int, default=1800)
    r.add_argument("--out", default="/tmp/cvrun")
    r.set_defaults(fn=cmd_run)
    w = sub.add_parser("watch")
    w.add_argument("--out", default="/tmp/cvrun")
    w.add_argument("--interval", type=float, default=5)
    w.set_defaults(fn=cmd_watch)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
