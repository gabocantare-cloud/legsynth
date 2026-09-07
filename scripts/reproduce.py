"""Regenerate every published number and figure, in order. One command.

The four scripts below are the whole repo. They have to run in this order
because each one leaves a file the next one reads:

  1. gait_report.py       the Jansen baseline and the stance-band sensitivity
                          -> results/gait_metrics.json, figures/gait_sensitivity.png
  2. mechanics_report.py  pin forces, wear breakdown, transmission angles
                          -> results/mechanics.json
  3. run_optimization.py  both Pareto fronts, and the CAD export of the
                          balanced design
                          -> results/pareto.json, results/cad/*
  4. make_figures.py      every figure in the README, several of which read
                          results/pareto.json, so this must come last
                          -> figures/*.png, figures/optimized_leg.gif

Two more scripts are deliberately *not* in the default list, because between
them they cost a dozen more optimization campaigns:

  robustness.py     the seed / objective / threshold / stance-band studies
                    behind docs/RESULTS.md section 7
                    -> results/robustness.json
  clearance_fit.py  the last open discrepancy: whether any nearby link set
                    gives both of the Table 4 numbers we cannot reproduce
                    -> results/clearance_fit.json

Pass --with-studies to include them.

Run:

    python scripts/reproduce.py                  # the four, ~10 min
    python scripts/reproduce.py --quick          # smoke test, ~2 min
    python scripts/reproduce.py --with-studies   # everything, ~1 h

Exit status is non-zero if any stage fails, so CI can use this directly.
"""
import argparse
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.join(ROOT, "scripts")

#: (script, extra args when --quick). A script with no --quick mode is cheap
#: enough to run in full either way.
STAGES = [
    ("gait_report.py", []),
    ("mechanics_report.py", []),
    ("run_optimization.py", ["--quick"]),
    ("make_figures.py", []),
]

STUDIES = [
    ("robustness.py", ["--quick"]),
    ("clearance_fit.py", []),
]


def stage(script, args, quick):
    argv = [sys.executable, os.path.join(HERE, script)] + (args if quick else [])
    label = " ".join([script] + (args if quick else []))
    print(f"\n{'=' * 70}\n=== {label}\n{'=' * 70}", flush=True)
    t = time.perf_counter()
    r = subprocess.run(argv, cwd=ROOT)
    dt = time.perf_counter() - t
    print(f"--- {label}: {'ok' if r.returncode == 0 else 'FAILED'} ({dt:.0f}s)",
          flush=True)
    return r.returncode, dt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true",
                    help="pass --quick to the expensive stages; smoke test only")
    ap.add_argument("--with-studies", action="store_true",
                    help="also run robustness.py and clearance_fit.py (adds ~45 min)")
    args = ap.parse_args()

    stages = list(STAGES) + (STUDIES if args.with_studies else [])

    t0, failed = time.perf_counter(), []
    for script, extra in stages:
        code, _ = stage(script, extra, args.quick)
        if code != 0:
            failed.append(script)
            # Later stages read what earlier ones write, so carrying on after a
            # failure would produce figures from stale results. Stop instead.
            break

    total = time.perf_counter() - t0
    print(f"\n{'=' * 70}")
    if failed:
        print(f"FAILED at {failed[0]} after {total:.0f}s")
        return 1
    if args.quick:
        print(f"smoke test passed in {total:.0f}s - the *_quick.json outputs are "
              f"not the published numbers")
    else:
        print(f"reproduced everything in {total:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
