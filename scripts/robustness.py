"""Measure the four claims the write-up currently asserts without a number.

Each study here exists because a sentence already in `README.md` or
`docs/RESULTS.md` says something that had not been measured. Either the number
comes back and the sentence stands, or it does not and the sentence changes.

  seeds      "The gap between the two Pareto fronts is run-to-run variation,
             not a cost." Run the unconstrained campaign three times with
             different seed triples and measure how far the front moves on its
             own. If that spread covers the constrained-vs-unconstrained gap,
             the sentence is established; if it does not, the constraint really
             costs something and the write-up is wrong.

  objective  "The 51% mean-force bias partly cancels between designs, so the
             paper's ratio-based conclusions survive." Re-run with the second
             objective switched from the paper's cycle-mean-force wear to the
             integrated form. If the front barely moves, the shortcut changes
             the magnitude but not the answer. If it moves, that is a second
             finding about the shortcut.

  threshold  The transmission-angle constraint was non-binding at 40 deg. A
             null is a weak statement; a curve is a strong one. Sweep the
             threshold and find where it starts costing gait or wear. "Free up
             to X deg, costs Y% beyond it" is a design guideline.

  band       The whole repo rests on stance band = 1% of path height.
             `METRIC_DEFINITIONS.md` shows how the *baseline* metrics move with
             it; this asks whether the *optimization conclusions* do. Re-run at
             0.5% and 2%. If Jansen is dominated at all three, that is a
             robustness result.

How two fronts get compared
---------------------------
Comparing two sets of points needs one number, and the honest one here is
**hypervolume**: the area of the rectangle below-left of Jansen that the front
manages to cover. Jansen sits at exactly (1, 1) by construction, so the unit
square is the whole of what there is to win, and hypervolume is the fraction of
it won. 0 means nothing beats Jansen; 0.25 means a quarter of the available
improvement space is dominated. It rewards a front for being both *good* (close
to the origin) and *wide* (spread along the trade-off), which is what a Pareto
front is for, and unlike "best gait error" it cannot be moved by one lucky
design sitting at one corner.

Writes results/robustness.json. Run:

    python scripts/robustness.py                 # everything
    python scripts/robustness.py --study seeds   # one study
    python scripts/robustness.py --quick         # smoke test
"""
import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from legsynth import optimize as O                      # noqa: E402
from legsynth import metrics as M                       # noqa: E402
from legsynth import constraints as C                   # noqa: E402
from legsynth.kinematics import DESIGN_KEYS             # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Jansen is the reference point for hypervolume because both objectives are
#: ratios to Jansen, so it sits at exactly (1, 1) and the unit square is the
#: entire space of designs that beat it on both counts. The measure itself
#: lives in `optimize.py`, next to `nondominated`, because it is general Pareto
#: bookkeeping rather than anything specific to these four studies.
JANSEN_POINT = O.JANSEN_POINT
hypervolume = O.hypervolume

THRESHOLDS = (40.0, 45.0, 50.0, 55.0)
BANDS = (0.005, 0.01, 0.02)
SEED_TRIPLES = ((0, 1, 2), (3, 4, 5), (6, 7, 8))


def campaign(label, seeds, pop, gens, n_refine, min_angle=None,
             band=M.DEFAULT_BAND, wear_key="wear", workers=None):
    """One full campaign: several seeded runs, merged, re-scored, summarised.

    The baseline is recomputed for whatever `band` this campaign uses, so
    Jansen still lands at exactly (1, 1) and the fronts stay comparable across
    studies. That matters most in the band study: at a different band Jansen
    itself measures differently, and normalising by the 1% Jansen would smuggle
    the definitional change into the objective values.
    """
    t = time.perf_counter()
    base = O.jansen_baseline(n=O.N_EVAL, band=band)
    base_refine = O.jansen_baseline(n=n_refine, band=band)
    runs = [O.run(seed=s, min_angle=min_angle, pop=pop, gens=gens,
                  baseline=base, band=band, wear_key=wear_key, workers=workers)
            for s in seeds]
    X, _ = O.merge(runs)
    rows = O.refine(X, base_refine, n=n_refine, min_angle=min_angle,
                    band=band, wear_key=wear_key)
    rows = [r for r in rows if r["feasible"]]
    if rows:
        keep = O.nondominated(np.array([[r["gait_error"], r["wear_ratio"]]
                                        for r in rows]))
        rows = [r for r, k in zip(rows, keep) if k]
        rows.sort(key=lambda r: r["gait_error"])

    F = (np.array([[r["gait_error"], r["wear_ratio"]] for r in rows])
         if rows else np.zeros((0, 2)))
    out = dict(
        label=label, seeds=list(seeds), min_angle=min_angle, band=band,
        wear_key=wear_key, n_front=len(rows), hypervolume=hypervolume(F),
        best_gait=float(F[:, 0].min()) if len(F) else float("nan"),
        best_wear=float(F[:, 1].min()) if len(F) else float("nan"),
        n_dominating=int(np.sum((F < 1.0).all(axis=1))) if len(F) else 0,
        min_loaded_angle=[float(r["min_transmission_angle"]) for r in rows],
        front=[[float(a), float(b)] for a, b in F],
        runtime_s=time.perf_counter() - t,
    )
    print(f"  {label:<28} front {out['n_front']:>3}   "
          f"HV {out['hypervolume']:.4f}   best gait {out['best_gait']:.3f}   "
          f"best wear {out['best_wear']:.3f}   ({out['runtime_s']:.0f}s)")
    return out


def spread(values):
    """Max minus min: the plainest statement of how far a number wandered."""
    v = [x for x in values if np.isfinite(x)]
    return float(max(v) - min(v)) if len(v) > 1 else float("nan")


def cached(cache, key, *args, **kw):
    """Run a campaign unless an identical one has already been run."""
    if key not in cache:
        cache[key] = campaign(*args, **kw)
    return cache[key]


# --------------------------------------------------------------------------
# study 1 - is the gap between the two fronts bigger than the search's own noise?
# --------------------------------------------------------------------------

def study_seeds(cfg, cache):
    print("\n=== SEEDS: is the constrained-vs-unconstrained gap larger than "
          "run-to-run noise? ===")
    unc = [cached(cache, ("unc", trip, M.DEFAULT_BAND, "wear"),
                  f"unconstrained {trip}", trip, min_angle=None, **cfg)
           for trip in SEED_TRIPLES]
    trip = SEED_TRIPLES[0]
    con = cached(cache, ("con40", trip, M.DEFAULT_BAND, "wear"),
                 f"constrained 40 deg {trip}", trip,
                 min_angle=C.GOOD_TRANSMISSION_ANGLE, **cfg)

    noise_hv = spread([c["hypervolume"] for c in unc])
    noise_gait = spread([c["best_gait"] for c in unc])
    gap_hv = abs(unc[0]["hypervolume"] - con["hypervolume"])
    gap_gait = abs(unc[0]["best_gait"] - con["best_gait"])
    verdict = "noise" if noise_hv >= gap_hv else "cost"

    print(f"\n  seed-to-seed spread, hypervolume : {noise_hv:.4f}")
    print(f"  constrained-vs-unconstrained gap : {gap_hv:.4f}")
    print(f"  seed-to-seed spread, best gait   : {noise_gait:.4f}")
    print(f"  constrained-vs-unconstrained gap : {gap_gait:.4f}")
    print(f"  --> the gap is {'within' if verdict == 'noise' else 'LARGER than'}"
          f" the search's own run-to-run spread")
    if verdict == "cost":
        print("      the constraint costs something; the write-up must change")

    return dict(unconstrained=unc, constrained=con,
                seed_spread_hypervolume=noise_hv,
                seed_spread_best_gait=noise_gait,
                constraint_gap_hypervolume=gap_hv,
                constraint_gap_best_gait=gap_gait, verdict=verdict)


# --------------------------------------------------------------------------
# study 2 - does the mean-force shortcut change the answer or only the size?
# --------------------------------------------------------------------------

def study_objective(cfg, cache):
    print("\n=== OBJECTIVE: does the paper's mean-force wear shortcut move the "
          "front? ===")
    trip = SEED_TRIPLES[0]
    mean = cached(cache, ("unc", trip, M.DEFAULT_BAND, "wear"),
                  f"mean-force wear (paper) {trip}", trip, min_angle=None, **cfg)
    integ = cached(cache, ("unc", trip, M.DEFAULT_BAND, "wear_integrated"),
                   f"integrated wear {trip}", trip, min_angle=None,
                   wear_key="wear_integrated", **cfg)

    d_hv = integ["hypervolume"] - mean["hypervolume"]
    d_gait = integ["best_gait"] - mean["best_gait"]
    d_wear = integ["best_wear"] - mean["best_wear"]
    print(f"\n  hypervolume  {mean['hypervolume']:.4f} -> "
          f"{integ['hypervolume']:.4f} "
          f"({100 * d_hv / mean['hypervolume']:+.1f}%)")
    print(f"  best gait    {mean['best_gait']:.3f} -> {integ['best_gait']:.3f} "
          f"({100 * d_gait / mean['best_gait']:+.1f}%)")
    print(f"  best wear    {mean['best_wear']:.3f} -> {integ['best_wear']:.3f} "
          f"({100 * d_wear / mean['best_wear']:+.1f}%)")
    return dict(mean_force=mean, integrated=integ, d_hypervolume=d_hv,
                d_best_gait=d_gait, d_best_wear=d_wear)


# --------------------------------------------------------------------------
# study 3 - turn the null result into a curve
# --------------------------------------------------------------------------

def study_threshold(cfg, cache):
    print("\n=== THRESHOLD: where does the transmission-angle constraint start "
          "costing something? ===")
    trip = SEED_TRIPLES[0]
    free = cached(cache, ("unc", trip, M.DEFAULT_BAND, "wear"),
                  f"unconstrained {trip}", trip, min_angle=None, **cfg)

    rows = []
    for mu in THRESHOLDS:
        c = cached(cache, (f"con{mu:.0f}", trip, M.DEFAULT_BAND, "wear"),
                   f"min loaded angle >= {mu:.0f} deg", trip, min_angle=mu, **cfg)
        rows.append(dict(
            threshold=mu, hypervolume=c["hypervolume"], best_gait=c["best_gait"],
            best_wear=c["best_wear"], n_front=c["n_front"],
            hv_cost_pct=(100.0 * (1.0 - c["hypervolume"] / free["hypervolume"])
                         if free["hypervolume"] else float("nan"))))

    print(f"\n  {'threshold':>10}{'front':>7}{'HV':>10}{'best gait':>11}"
          f"{'best wear':>11}{'HV lost':>10}")
    print(f"  {'none':>10}{free['n_front']:>7}{free['hypervolume']:>10.4f}"
          f"{free['best_gait']:>11.3f}{free['best_wear']:>11.3f}{0.0:>9.1f}%")
    for r in rows:
        print(f"  {r['threshold']:>9.0f}d{r['n_front']:>7}"
              f"{r['hypervolume']:>10.4f}{r['best_gait']:>11.3f}"
              f"{r['best_wear']:>11.3f}{r['hv_cost_pct']:>9.1f}%")
    return dict(unconstrained=free, sweep=rows)


# --------------------------------------------------------------------------
# study 4 - do the conclusions survive the definition underneath them?
# --------------------------------------------------------------------------

def study_band(cfg, cache):
    print("\n=== BAND: do the optimization conclusions depend on the 1% stance "
          "band? ===")
    trip = SEED_TRIPLES[0]
    rows = []
    for band in BANDS:
        c = cached(cache, ("unc", trip, band, "wear"),
                   f"band {band:.1%}", trip, min_angle=None, band=band, **cfg)
        rows.append(dict(band=band, hypervolume=c["hypervolume"],
                         best_gait=c["best_gait"], best_wear=c["best_wear"],
                         n_front=c["n_front"], n_dominating=c["n_dominating"]))

    everywhere = all(r["n_dominating"] > 0 for r in rows)
    print(f"\n  {'band':>7}{'front':>7}{'dominating':>12}{'HV':>10}"
          f"{'best gait':>11}{'best wear':>11}")
    for r in rows:
        print(f"  {r['band']:>6.1%}{r['n_front']:>7}{r['n_dominating']:>12}"
              f"{r['hypervolume']:>10.4f}{r['best_gait']:>11.3f}"
              f"{r['best_wear']:>11.3f}")
    print("  --> Jansen is " + ("dominated at every band" if everywhere
                                else "NOT dominated at every band"))
    return dict(sweep=rows, jansen_dominated_at_every_band=everywhere)


STUDIES = dict(seeds=study_seeds, objective=study_objective,
               threshold=study_threshold, band=study_band)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", choices=tuple(STUDIES) + ("all",), default="all")
    ap.add_argument("--quick", action="store_true",
                    help="tiny population and few generations; smoke test only")
    ap.add_argument("--workers", type=int, default=None,
                    help="processes evaluating a generation at once")
    args = ap.parse_args()

    pop, gens, n_refine = (24, 8, 360) if args.quick else (100, 80, M.N_PUBLISHED)
    cfg = dict(pop=pop, gens=gens, n_refine=n_refine, workers=args.workers)
    print(f"NSGA-II: population {pop}, {gens} generations, "
          f"re-scored at n={n_refine}")

    # Several studies want the same campaign. Compute each one once.
    cache, out, t0 = {}, {}, time.perf_counter()
    names = tuple(STUDIES) if args.study == "all" else (args.study,)
    for name in names:
        out[name] = STUDIES[name](cfg, cache)

    out["settings"] = dict(
        pop=pop, gens=gens, n_eval=O.N_EVAL, n_refine=n_refine,
        seed_triples=[list(t) for t in SEED_TRIPLES],
        thresholds=list(THRESHOLDS), bands=list(BANDS),
        design_keys=list(DESIGN_KEYS), reference_point=list(JANSEN_POINT))
    out["runtime_s"] = time.perf_counter() - t0

    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    name = "robustness_quick.json" if args.quick else "robustness.json"
    dest = os.path.join(ROOT, "results", name)
    with open(dest, "w") as fh:
        json.dump(out, fh, indent=2, default=float)
    print(f"\nwrote {os.path.relpath(dest, ROOT)} "
          f"({out['runtime_s']:.0f}s total)")


if __name__ == "__main__":
    main()
