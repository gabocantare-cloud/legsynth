"""Regenerate every published number and figure, in order. One command.

The five scripts below are the whole repo. They have to run in this order
because each one leaves a file the next one reads:

  1. gait_report.py       the Jansen baseline and the stance-band sensitivity
                          -> results/gait_metrics.json, figures/gait_sensitivity.png
  2. mechanics_report.py  pin forces, wear breakdown, transmission angles
                          -> results/mechanics.json
  3. run_optimization.py  both Pareto fronts, and the CAD export of the
                          balanced design
                          -> results/pareto.json, results/cad/*
  4. feasibility.py       how much of the paper's design box assembles and how
                          much of it is feasible, at three seeds - the numbers
                          behind docs/RESULTS.md section 5
                          -> results/feasibility.json
  5. make_figures.py      every figure in the README, several of which read
                          results/pareto.json - and, with --with-studies, the
                          threshold figure reads results/robustness.json - so
                          this always runs last, after the studies
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

That caveat about the figures is gone. `make_figures.py` used to draw the
seed-to-seed band on the threshold figure from the shipped
`results/audit/objective_replication.json` rather than from this run, because
the audit file measured the spread over ten triples where the seeds study on
disk had measured three - so the band and the curve behind a single figure could
come from different campaigns. The seeds study now runs at twenty triples, which
makes the live file both the matching source and the better one, and the
preference has been removed. With `--with-studies`, every part of the threshold
figure comes from this reproduction.

Run:

    python scripts/reproduce.py                  # the five stages
    python scripts/reproduce.py --quick          # smoke test
    python scripts/reproduce.py --with-studies   # everything, incl. the studies

On wall-clock times. They were quoted here for a while from a study program
that had since grown, and the two recorded timings in the repo disagreed with
each other, so they were deleted rather than guessed at. One has now been
measured on the current program: `robustness.py` alone is 46 campaigns and took
**2 h 32 m on 12 workers** (one run, one machine, September 2026). The count
comes from `robustness.N_CAMPAIGNS`, which is arithmetic over the study
parameters rather than a literal, and the script prints it at startup; the
timing is a measurement of one run on one machine, so read it as an order of
magnitude and not a promise. Each stage prints its own elapsed time and the
total is printed at the end.

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
    ("feasibility.py", ["--quick"]),
]

STUDIES = [
    ("robustness.py", ["--quick"]),
    ("clearance_fit.py", ["--quick"]),
]

#: Always last. The threshold figure reads results/robustness.json, so drawing
#: the figures before the studies ran would publish a figure of the *previous*
#: study's output while claiming it came from this reproduction.
FIGURES = [
    ("make_figures.py", []),
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
                    help="also run robustness.py (it prints its campaign "
                         "count) and clearance_fit.py, before the figures")
    args = ap.parse_args()

    stages = (list(STAGES) + (list(STUDIES) if args.with_studies else [])
              + list(FIGURES))

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
