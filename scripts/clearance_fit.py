"""The last open discrepancy: can *any* nearby linkage give 25.7 mm of clearance?

Wang (2026) Table 4 reports 43.3 mm of step length and 25.7 mm of ground
clearance for Jansen's linkage. We reproduce the step length to 0.3%. The
clearance we cannot reproduce at all, and not because of a definitional
disagreement: ground clearance is bounded above by the total height of the foot
path, and Jansen's whole path is only 22.46 mm tall. 25.7 mm does not fit inside
it under *any* stance rule.

`METRIC_DEFINITIONS.md` therefore blames geometry - slightly different link
lengths from the holy numbers, or an unstated normalization - and then stops.
That is one hypothesis short of an answer, so this script tests it directly.

The question, made precise
--------------------------
Is there a set of link lengths, near Jansen's, that produces **both** 43.3 mm of
step length and 25.7 mm of ground clearance at once? And if so, how far from
Jansen does it have to be?

Answering it in two stages keeps the two possible outcomes separate, because
they are different findings:

  **Stage 1 - is it reachable at all?** Minimise the fit residual alone, over
  the paper's own +/-30% box, with no preference for staying near Jansen. If the
  residual cannot be driven to zero, no linkage in the box the paper allows
  itself produces those two numbers together, and the Table 4 row cannot be a
  link-length question either. That is a stronger statement than "we cannot
  reproduce it".

  **Stage 2 - if it is reachable, how far away is it?** Add a penalty on the
  largest relative link change and sweep its weight. That traces the trade-off
  between fitting the targets and staying near Jansen, and the answer to
  "different link lengths?" becomes a number: the smallest link change that
  still lands both targets.

Either way there is a third test the winner has to pass, and it is the one that
decides the hypothesis. A link set that matches step length and clearance but
destroys the velocity ripple is not the design the paper measured either, since
the paper's ripple *does* reproduce against ours. So the fitted design is
re-scored on all five Table 4 metrics.

Writes results/clearance_fit.json. Run:

    python scripts/clearance_fit.py
    python scripts/clearance_fit.py --quick   # smoke test, coarse search
"""
import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from legsynth import metrics as M                       # noqa: E402
from legsynth import optimize as O                      # noqa: E402
from legsynth.kinematics import HOLY, DESIGN_KEYS       # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

JANSEN = np.array([HOLY[k] for k in DESIGN_KEYS], float)

#: The two Table 4 numbers being fitted.
TARGET_STEP = M.PAPER_TABLE4["step_length"]
TARGET_CLEARANCE = M.PAPER_TABLE4["ground_clearance"]

#: Crank samples during the fit. The winner is re-scored at M.N_PUBLISHED.
N_FIT = 360

#: Penalty weights swept in stage 2. 0 is stage 1.
WEIGHTS = (0.0, 0.01, 0.03, 0.1, 0.3, 1.0)

#: A fit counts as landing both targets when each is within this fraction.
TOLERANCE = 0.005

BIG = 1e3


def deviation(x):
    """Largest relative link change from Jansen, as a fraction.

    The max, not the mean: "no link moved by more than X%" is the claim the
    paper makes about its own designs, so it is the one worth matching.
    """
    return float(np.max(np.abs(np.asarray(x, float) - JANSEN) / JANSEN))


def residual(x, n=N_FIT):
    """Relative miss on the two targets, as one number. BIG if it won't build."""
    leg = O.leg_from_vector(x)
    path = leg.foot_path(n)
    if not np.all(np.isfinite(path)):
        return BIG
    step = M.step_length(path)
    clear = M.ground_clearance(path)
    if not (np.isfinite(step) and np.isfinite(clear)):
        return BIG
    return float(np.hypot((step - TARGET_STEP) / TARGET_STEP,
                          (clear - TARGET_CLEARANCE) / TARGET_CLEARANCE))


def objective(x, weight):
    return residual(x) + weight * deviation(x)


def fit(weight, seed=0, maxiter=200, workers=-1):
    """Global search for the link set that best fits the targets at this weight.

    Differential evolution rather than a gradient method: step length and ground
    clearance are read off a sampled path, so the objective is mildly stepped
    and a derivative-based search walks straight into the steps. It is also
    global, which stage 1 needs - the claim being tested is that *no* design in
    the box fits, and a local method finding no fit would prove nothing.

    `workers=-1` spreads each generation over every core; the objective is a
    module-level function and the weight rides in `args`, so it pickles.
    """
    from scipy.optimize import differential_evolution
    lo, hi = O.bounds()
    t = time.perf_counter()
    res = differential_evolution(
        objective, list(zip(lo, hi)), args=(weight,), seed=seed,
        maxiter=maxiter, popsize=20, tol=1e-8, polish=True, init="sobol",
        workers=workers, updating="deferred")
    x = np.asarray(res.x, float)
    return dict(weight=weight, x=x.tolist(), residual=residual(x),
                deviation=deviation(x), runtime_s=time.perf_counter() - t)


def score(x, n=M.N_PUBLISHED):
    """All five Table 4 metrics for a fitted design, at the published sample count."""
    leg = O.leg_from_vector(x)
    path = leg.foot_path(n)
    out = dict(M.gait_metrics(path))
    out["path_height"] = M.path_height(path)
    out["assembles"] = bool(np.all(np.isfinite(path)))
    return out


def report(row):
    s = score(row["x"])
    step_err = 100.0 * (s["step_length"] - TARGET_STEP) / TARGET_STEP
    clear_err = 100.0 * (s["ground_clearance"] - TARGET_CLEARANCE) / TARGET_CLEARANCE
    hit = (abs(step_err) < 100 * TOLERANCE and abs(clear_err) < 100 * TOLERANCE)
    print(f"  weight {row['weight']:<5} residual {row['residual']:.4f}  "
          f"max link change {100 * row['deviation']:5.1f}%   "
          f"step {s['step_length']:6.2f} ({step_err:+5.1f}%)  "
          f"clearance {s['ground_clearance']:6.2f} ({clear_err:+6.1f}%)  "
          f"{'HIT' if hit else 'miss'}")
    row["scored"] = s
    row["step_error_pct"] = step_err
    row["clearance_error_pct"] = clear_err
    row["hits_both_targets"] = hit
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true",
                    help="coarse search; smoke test only, not a published answer")
    args = ap.parse_args()
    # A coarse global search that fails to find a fit proves nothing, so the
    # quick mode writes somewhere else and its verdict is not quotable.
    maxiter = 20 if args.quick else 200
    seeds = (0,) if args.quick else (0, 1, 2)
    weights = WEIGHTS[1:2] if args.quick else WEIGHTS[1:]

    t0 = time.perf_counter()
    print("Fitting the two Table 4 numbers our baseline does not reproduce:")
    print(f"  step length      {TARGET_STEP} mm   (ours: 43.41 mm, reproduces)")
    print(f"  ground clearance {TARGET_CLEARANCE} mm   (ours: 22.23 mm, does not)")
    print(f"  search box: Jansen +/-{100 * O.BOUND_FRACTION:.0f}%, "
          f"the paper's own bounds\n")

    print("STAGE 1 - is it reachable at all, ignoring closeness to Jansen?")
    rows = [report(fit(0.0, seed=s, maxiter=maxiter)) for s in seeds]
    best = min(rows, key=lambda r: r["residual"])
    reachable = best["hits_both_targets"]
    print(f"  --> best residual over three restarts: {best['residual']:.4f} "
          f"({'targets are reachable' if reachable else 'TARGETS ARE NOT REACHABLE'})")

    sweep = []
    if reachable:
        print("\nSTAGE 2 - how close to Jansen can a design get and still fit?")
        sweep = [report(fit(w, seed=0, maxiter=maxiter)) for w in weights]
        hits = [r for r in sweep + rows if r["hits_both_targets"]]
        closest = min(hits, key=lambda r: r["deviation"]) if hits else None
    else:
        closest = None

    print("\nWHAT IT MEANS")
    if not reachable:
        print(f"  No linkage in the paper's own +/-30% box produces "
              f"{TARGET_STEP} mm of step")
        print(f"  and {TARGET_CLEARANCE} mm of clearance together. Best miss "
              f"{100 * best['residual']:.1f}%.")
        print("  So the Table 4 clearance is not a link-length question either.")
        print("  It is most likely a different quantity than the one we define, or")
        print("  a normalization the paper does not state.")
    else:
        s = closest["scored"]
        print(f"  A linkage {100 * closest['deviation']:.1f}% from Jansen fits both "
              f"targets.")
        print("  But it must also survive the metrics that already agree. "
              "At that design:")
        print(f"    velocity ripple {s['velocity_ripple']:.4f} against the "
              f"paper's {M.PAPER_TABLE4['velocity_ripple']}")
        print(f"    duty factor     {100 * s['duty_factor']:.1f}% against the "
              f"paper's ~20%")
        rip = abs(s["velocity_ripple"] - M.PAPER_TABLE4["velocity_ripple"])
        rip /= M.PAPER_TABLE4["velocity_ripple"]
        print(f"  Ripple {'still agrees' if rip < 0.10 else 'no longer agrees'} "
              f"({100 * rip:.0f}% off), so the different-link-lengths hypothesis")
        print(f"  {'survives' if rip < 0.10 else 'does not survive'} its own "
              f"cross-check.")

    out = dict(
        targets=dict(step_length=TARGET_STEP, ground_clearance=TARGET_CLEARANCE),
        jansen=dict(zip(DESIGN_KEYS, JANSEN.tolist())),
        jansen_scored=score(JANSEN), design_keys=list(DESIGN_KEYS),
        settings=dict(n_fit=N_FIT, n_report=M.N_PUBLISHED,
                      weights=[0.0] + list(weights), maxiter=maxiter,
                      seeds=list(seeds), quick=args.quick,
                      tolerance=TOLERANCE, bound_fraction=O.BOUND_FRACTION),
        stage1=rows, stage2=sweep, reachable=reachable, closest=closest,
        runtime_s=time.perf_counter() - t0,
    )
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    name = "clearance_fit_quick.json" if args.quick else "clearance_fit.json"
    dest = os.path.join(ROOT, "results", name)
    with open(dest, "w") as fh:
        json.dump(out, fh, indent=2, default=float)
    print(f"\nwrote {os.path.relpath(dest, ROOT)} "
          f"({out['runtime_s']:.0f}s)")


if __name__ == "__main__":
    main()
