"""Measure the four claims the write-up currently asserts without a number.

Each study here exists because a sentence already in `README.md` or
`docs/RESULTS.md` says something that had not been measured. Either the number
comes back and the sentence stands, or it does not and the sentence changes.

  seeds      "The gap between the two Pareto fronts is run-to-run variation,
             not a cost." Run the unconstrained campaign at twenty different
             seed triples and measure how far the front moves on its own. If that
             spread covers the constrained-vs-unconstrained gap, the sentence is
             established; if it does not, the constraint really costs something
             and the write-up is wrong.

  objective  "The 51% mean-force bias partly cancels between designs, so the
             paper's ratio-based conclusions survive." Re-run with the second
             objective switched from the paper's cycle-mean-force wear to the
             integrated form, at every seed triple, and read the mean of the
             paired differences. One pair is not enough: the first pair run
             here moved by +0.052 and turned out to be the largest of ten
             differences averaging -0.004.

  threshold  The transmission-angle constraint was non-binding at 40 deg. A
             null is a weak statement; a curve is a stronger one. Sweep the
             threshold and see where it starts costing gait or wear. One
             campaign per threshold only resolves the ends of that curve - at
             the measured seed spread, 45 and 50 deg are inside noise - so read
             it as "free at 40, impossible at 55" rather than as a price list.

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
from scipy import stats

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
#: Seed triples for the seeds and objective studies. Twenty, not ten and not
#: three. Three came first, and the *range* they gave understated the true
#: seed-to-seed spread by 7x on hypervolume, because the range of n samples
#: grows with n (see `spread()`); ten fixed that and the verdict moved onto the
#: standard deviation, which does not have that property. Twenty is here for a
#: different reason: it is the only change that buys statistical *power*. The
#: objective study's null rests on the paired differences, whose confidence
#: interval narrows as 1/sqrt(n), so doubling the triples narrows it by about
#: sqrt(2); re-running the same ten would have narrowed nothing. The first ten
#: are unchanged so this run can be compared campaign-by-campaign against
#: results/audit/objective_replication.json, which is the historical record of
#: what the ten-triple claim rested on. Twenty triples is 46 unique campaigns
#: and a few hours on 12 cores (see `N_CAMPAIGNS`); the seeds and objective
#: studies share their unconstrained campaigns through the cache.
SEED_TRIPLES = tuple((3 * i, 3 * i + 1, 3 * i + 2) for i in range(20))

#: How many distinct campaigns a full run costs, which is not the number of
#: `campaign()` calls the four studies make - they share work through `cached`.
#: Written as the arithmetic rather than as a literal because this number has
#: already gone stale once in four documents (it was 26 at ten triples), and a
#: count that a document quotes has to come from the thing that determines it:
#:
#:   2 x len(SEED_TRIPLES)  the unconstrained and integrated-wear campaigns,
#:                          shared between the seeds and objective studies
#:   + len(THRESHOLDS)      the constrained sweep, at SEED_TRIPLES[0]; its
#:                          40 deg row is also the seeds study's constrained one
#:   + len(BANDS) - 1       the band study, less the 1% campaign that is the
#:                          unconstrained one already counted above
#:
#: `test_the_campaign_count_matches_what_the_studies_actually_request` stubs
#: `campaign` and counts cache keys, so this cannot drift from the truth.
N_CAMPAIGNS = 2 * len(SEED_TRIPLES) + len(THRESHOLDS) + len(BANDS) - 1


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
    """How far a number wandered: the range, the standard deviation, and n.

    The range is the plainest statement of it and it is the one the write-up
    quotes, but on its own it is a trap. The range of n samples *grows with n* -
    about 1.7 standard deviations at n=3, about 3.1 at n=10 - so this function
    returns a systematically smaller spread the fewer campaigns you ran, and
    every comparison made against it is biased toward "the difference is real".
    That is exactly the error this repo made when the spread was estimated from
    three campaigns and then used as a yardstick in three sections. The standard
    deviation does not have that property, so it is returned alongside and
    recorded in the JSON; compare against it whenever the sample sizes differ.
    """
    v = [x for x in values if np.isfinite(x)]
    if len(v) < 2:
        return dict(range=float("nan"), sd=float("nan"), n=len(v))
    return dict(range=float(max(v) - min(v)), sd=float(np.std(v, ddof=1)),
                n=len(v))


#: How close the seed spread and the constraint gap have to be before the seeds
#: study refuses to call it either way. See `seed_verdict`.
INCONCLUSIVE_BAND = 0.25


def seed_verdict(noise, gap):
    """Three-valued verdict for the seeds study, plus the margin behind it.

    This used to be `"noise" if noise >= gap else "cost"`, decided on a margin of
    0.0004 off a three-campaign range - a coin flip printed as a fact, and
    recorded in the JSON, where a later session reads the verdict rather than the
    prose around it. When the two quantities are within `INCONCLUSIVE_BAND` of
    each other, this many campaigns cannot decide, so say that instead. Returns
    (verdict, spread / gap).

    `noise` must be the **standard deviation** from `spread()`, not its range.
    The range grows with the number of campaigns, so a verdict decided on it is
    a verdict that changes when you run more of the same experiment - see
    `spread()`. The range is still printed and recorded as description; it is
    not what decides this.
    """
    if not (np.isfinite(noise) and np.isfinite(gap)) or gap == 0.0:
        return "inconclusive", float("nan")
    margin = noise / gap
    if abs(margin - 1.0) <= INCONCLUSIVE_BAND:
        return "inconclusive", margin
    return ("noise" if margin > 1.0 else "cost"), margin


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

    noise = spread([c["hypervolume"] for c in unc])
    noise_g = spread([c["best_gait"] for c in unc])
    noise_hv, noise_gait = noise["range"], noise_g["range"]
    gap_hv = abs(unc[0]["hypervolume"] - con["hypervolume"])
    gap_gait = abs(unc[0]["best_gait"] - con["best_gait"])

    # The sd decides the verdict; the range is kept beside it as description.
    verdict, sd_over_gap = seed_verdict(noise["sd"], gap_hv)
    range_over_gap = noise_hv / gap_hv if gap_hv else float("nan")

    print(f"\n  seed-to-seed spread, hypervolume : sd {noise['sd']:.4f}"
          f"  (range {noise_hv:.4f}, n={noise['n']})")
    print(f"  constrained-vs-unconstrained gap : {gap_hv:.4f}")
    print(f"  seed-to-seed spread, best gait   : sd {noise_g['sd']:.4f}"
          f"  (range {noise_gait:.4f}, n={noise_g['n']})")
    print(f"  constrained-vs-unconstrained gap : {gap_gait:.4f}")
    print(f"  --> verdict: {verdict}   (sd / gap = {sd_over_gap:.2f}; "
          f"range / gap = {range_over_gap:.2f}, descriptive only)")
    if verdict == "cost":
        print("      the constraint costs something; the write-up must change")
    elif verdict == "inconclusive":
        print(f"      spread and gap agree to within "
              f"{100 * INCONCLUSIVE_BAND:.0f}%; this many campaigns cannot "
              f"decide it, and more seed triples are the only fix")

    return dict(unconstrained=unc, constrained=con,
                seed_spread_hypervolume=noise_hv,
                seed_spread_best_gait=noise_gait,
                seed_spread_hypervolume_sd=noise["sd"],
                seed_spread_best_gait_sd=noise_g["sd"],
                n_triples=noise["n"],
                constraint_gap_hypervolume=gap_hv,
                constraint_gap_best_gait=gap_gait,
                sd_over_gap=sd_over_gap, range_over_gap=range_over_gap,
                margin=sd_over_gap, verdict=verdict,
                verdict_statistic="sd")


# --------------------------------------------------------------------------
# study 2 - does the mean-force shortcut change the answer or only the size?
# --------------------------------------------------------------------------

def study_objective(cfg, cache):
    """Does switching the wear definition move the front, or only its size?

    Every triple in `SEED_TRIPLES`, not one. This study was run at a single pair
    of campaigns first and reported a +0.052 move in best gait error as a
    finding. Repeated at ten pairs, that pair turned out to be the *maximum* of
    ten differences averaging -0.0036, and the finding was withdrawn. The
    comparison is paired by construction - same seeds, same band, same sample
    count, only `wear_key` changes - which is what makes the mean of the paired
    differences the statistic to read, rather than either campaign alone.

    Best gait error is the only axis the two campaigns share. Their wear axes
    are not comparable (each normalises against a Jansen measured its own way,
    so each sits at (1, 1) while reducing a different quantity), and
    hypervolume mixes both axes and inherits that. The hypervolumes are still
    recorded, but they are not the answer to this question.
    """
    print("\n=== OBJECTIVE: does the paper's mean-force wear shortcut move the "
          "front? ===")
    pairs = []
    for trip in SEED_TRIPLES:
        mean = cached(cache, ("unc", trip, M.DEFAULT_BAND, "wear"),
                      f"mean-force wear (paper) {trip}", trip, min_angle=None,
                      **cfg)
        integ = cached(cache, ("unc", trip, M.DEFAULT_BAND, "wear_integrated"),
                       f"integrated wear {trip}", trip, min_angle=None,
                       wear_key="wear_integrated", **cfg)
        pairs.append(dict(seeds=list(trip),
                          best_gait_mean=mean["best_gait"],
                          best_gait_integrated=integ["best_gait"],
                          delta=integ["best_gait"] - mean["best_gait"],
                          hv_mean=mean["hypervolume"],
                          hv_integrated=integ["hypervolume"]))

    d = np.array([p["delta"] for p in pairs], float)
    d = d[np.isfinite(d)]
    n = len(d)
    mean_d = float(d.mean()) if n else float("nan")
    sd = float(d.std(ddof=1)) if n > 1 else float("nan")
    stderr = sd / np.sqrt(n) if n > 1 else float("nan")

    # Student's t, not 1.96. Ten campaigns is not a large sample and the
    # population sd is not known - it is estimated from the same ten numbers -
    # so the normal multiplier reports an interval about 13% narrower than the
    # data support. That direction matters here: this interval is the evidence
    # for a *null*, and a null argued from an interval that is too narrow is
    # the one mistake this section cannot afford to make.
    tmult = float(stats.t.ppf(0.975, n - 1)) if n > 1 else float("nan")
    ci = [mean_d - tmult * stderr, mean_d + tmult * stderr] if n > 1 else [
        float("nan"), float("nan")]
    tstat, pval = (stats.ttest_1samp(d, 0.0) if n > 1
                   else (float("nan"), float("nan")))
    n_pos = int((d > 0).sum())

    print(f"\n  paired difference in best gait error, {n} seed triples")
    for p in pairs:
        print(f"    {str(tuple(p['seeds'])):<14} "
              f"{p['best_gait_mean']:.4f} -> {p['best_gait_integrated']:.4f}"
              f"   {p['delta']:+.4f}")
    print(f"  mean {mean_d:+.4f}   sd {sd:.4f}   "
          f"95% CI [{ci[0]:+.4f}, {ci[1]:+.4f}] (t_{{{n - 1}}}={tmult:.3f})   "
          f"p {float(pval):.2f}   {n_pos} of {n} positive")
    straddles = n > 1 and ci[0] < 0.0 < ci[1]
    tail = ("no detectable effect on the reachable gait quality" if straddles
            else "the wear definition moves the reachable gait quality")
    print(f"  --> the interval "
          f"{'straddles' if straddles else 'excludes'} zero: {tail}")

    return dict(pairs=pairs, n_pairs=n, delta_mean=mean_d, delta_sd=sd,
                delta_min=float(d.min()) if n else float("nan"),
                delta_max=float(d.max()) if n else float("nan"),
                delta_stderr=float(stderr), ci95=[float(c) for c in ci],
                ci95_multiplier=tmult, ci95_dist="t", ci95_df=n - 1,
                t_stat=float(tstat), p_value=float(pval),
                n_positive=n_pos, straddles_zero=bool(straddles),
                mean_force=cache[("unc", SEED_TRIPLES[0], M.DEFAULT_BAND,
                                  "wear")],
                integrated=cache[("unc", SEED_TRIPLES[0], M.DEFAULT_BAND,
                                  "wear_integrated")])


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
    if args.study == "all":
        print(f"{N_CAMPAIGNS} distinct campaigns, "
              f"{len(SEED_TRIPLES)} seed triples")

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

    # Merge rather than overwrite. `--study band` re-runs one study, and a plain
    # write would silently drop the three that cost 40 minutes to produce. Only
    # the studies actually run this time are replaced; `--study all` replaces
    # every one of them anyway.
    if os.path.exists(dest):
        try:
            with open(dest) as fh:
                merged = json.load(fh)
        except (ValueError, OSError):
            merged = {}
        merged.update(out)
        out = merged

    with open(dest, "w") as fh:
        json.dump(out, fh, indent=2, default=float)
    print(f"\nwrote {os.path.relpath(dest, ROOT)} "
          f"({out['runtime_s']:.0f}s total)")


if __name__ == "__main__":
    main()
