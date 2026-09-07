"""Run the paper's optimization, then run it again with our added constraint.

Two campaigns, three NSGA-II runs each (the paper merges three), fronts merged
and re-scored at a finer crank sample:

  paper        step length, clearance, duty factor >= 0.85x Jansen
  constrained  the same, plus minimum loaded transmission angle >= 40 degrees

Writes results/pareto.json, exports the balanced design to results/cad/, and
prints the comparison. Takes about twenty minutes; pass --quick for a coarse
version that takes under a minute and writes to results/pareto_quick.json
instead, so a smoke test cannot overwrite a real campaign.

Run:  python scripts/run_optimization.py [--quick]
"""
import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from legsynth import optimize as O                      # noqa: E402
from legsynth.kinematics import DESIGN_KEYS             # noqa: E402
from legsynth import constraints as C                   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEEDS = (0, 1, 2)


def campaign(name, min_angle, baseline, pop, gens, seeds, n_refine):
    print(f"\n=== {name} ===")
    runs = []
    for s in seeds:
        t = time.perf_counter()
        r = O.run(seed=s, min_angle=min_angle, pop=pop, gens=gens,
                  baseline=baseline)
        runs.append(r)
        print(f"  seed {s}: {len(r['F']):3d} feasible designs "
              f"({time.perf_counter() - t:.0f}s)")
    X, F = O.merge(runs)
    print(f"  merged front: {len(F)} designs")
    rows = O.refine(X, baseline, n=n_refine, min_angle=min_angle)
    rows = [r for r in rows if r["feasible"]]
    if rows:
        keep = O.nondominated(np.array([[r["gait_error"], r["wear_ratio"]]
                                        for r in rows]))
        rows = [r for r, k in zip(rows, keep) if k]
        rows.sort(key=lambda r: r["gait_error"])
    print(f"  after re-scoring at n={n_refine}: {len(rows)} on the front")
    return rows


def summarise(name, rows):
    if not rows:
        print(f"{name}: no feasible designs")
        return
    g = np.array([r["gait_error"] for r in rows])
    w = np.array([r["wear_ratio"] for r in rows])
    dominating = [r for r in rows if r["gait_error"] < 1.0 and r["wear_ratio"] < 1.0]
    print(f"\n{name}: {len(rows)} designs on the front")
    print(f"  gait error  {g.min():.3f} .. {g.max():.3f}   (Jansen = 1.000)")
    print(f"  wear ratio  {w.min():.3f} .. {w.max():.3f}   (Jansen = 1.000)")
    print(f"  designs beating Jansen on both objectives: {len(dominating)}")
    if dominating:
        best = min(dominating, key=lambda r: r["gait_error"] + r["wear_ratio"])
        print(f"  balanced pick: gait {best['gait_error']:.3f} "
              f"({100 * (1 - best['gait_error']):.0f}% better), "
              f"wear {best['wear_ratio']:.3f} "
              f"({100 * (1 - best['wear_ratio']):.0f}% less), "
              f"min loaded transmission angle "
              f"{best['min_transmission_angle']:.1f} deg")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true",
                    help="small population, few generations, one seed")
    args = ap.parse_args()

    pop, gens, seeds, n_refine = (40, 20, (0,), 720) if args.quick \
        else (100, 80, SEEDS, 1440)

    baseline = O.jansen_baseline()
    print(f"Jansen baseline: step {baseline['step_length']:.2f} mm, "
          f"clearance {baseline['ground_clearance']:.2f} mm, "
          f"duty {100 * baseline['duty_factor']:.1f}%")
    print(f"  wear {baseline['wear'] * 1e9:.3e} mm3/cycle, "
          f"min loaded transmission angle "
          f"{baseline['min_transmission_angle']:.1f} deg")
    print(f"NSGA-II: population {pop}, {gens} generations, seeds {list(seeds)}")

    t0 = time.perf_counter()
    paper = campaign("paper constraints", None, baseline, pop, gens, seeds, n_refine)
    ours = campaign(f"plus loaded transmission angle >= "
                    f"{C.GOOD_TRANSMISSION_ANGLE:.0f} deg",
                    C.GOOD_TRANSMISSION_ANGLE, baseline, pop, gens, seeds, n_refine)

    summarise("Paper's problem", paper)
    summarise("With our constraint", ours)

    if paper and ours:
        gp = min(r["gait_error"] for r in paper)
        go = min(r["gait_error"] for r in ours)
        wp = min(r["wear_ratio"] for r in paper)
        wo = min(r["wear_ratio"] for r in ours)
        print("\nWhat the manufacturability constraint costs:")
        print(f"  best gait error   {gp:.3f} -> {go:.3f} "
              f"({100 * (go / gp - 1):+.1f}%)")
        print(f"  best wear ratio   {wp:.3f} -> {wo:.3f} "
              f"({100 * (wo / wp - 1):+.1f}%)")
        bad = [r for r in paper
               if r["min_transmission_angle"] < C.GOOD_TRANSMISSION_ANGLE]
        print(f"  {len(bad)} of {len(paper)} designs on the paper's front "
              f"would fail the 40-degree rule")

    out = dict(
        settings=dict(pop=pop, gens=gens, seeds=list(seeds), n_eval=O.N_EVAL,
                      n_refine=n_refine, bound_fraction=O.BOUND_FRACTION,
                      floor=O.FLOOR, min_angle=C.GOOD_TRANSMISSION_ANGLE),
        design_keys=list(DESIGN_KEYS),
        baseline={k: (float(v) if not isinstance(v, bool) else v)
                  for k, v in baseline.items()},
        paper_front=paper, constrained_front=ours,
        runtime_s=time.perf_counter() - t0,
    )
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    # --quick writes somewhere else on purpose: a smoke test must not be able to
    # overwrite the campaign the published numbers are quoted from.
    name = "pareto_quick.json" if args.quick else "pareto.json"
    dest = os.path.join(ROOT, "results", name)
    with open(dest, "w") as fh:
        json.dump(out, fh, indent=2, default=float)
    print(f"\nwrote {os.path.relpath(dest, ROOT)} "
          f"({time.perf_counter() - t0:.0f}s total)")

    # Hand the chosen design off to CAD. "Balanced" is the design that improves
    # both objectives most evenly; it is a defensible pick, not the only one,
    # which is why the whole front is saved above rather than just this design.
    if paper:
        from legsynth import cad
        best = min(paper, key=lambda r: r["gait_error"] + r["wear_ratio"])
        files = cad.export_all(O.leg_from_vector(best["x"]),
                               os.path.join(ROOT, "results", "cad"),
                               stem="optimized_quick" if args.quick else "optimized")
        print(f"exported the balanced design (gait {best['gait_error']:.3f}, "
              f"wear {best['wear_ratio']:.3f}) to CAD:")
        for kind, path in files.items():
            print(f"  {kind:<12} {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
