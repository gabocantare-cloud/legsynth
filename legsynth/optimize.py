"""Multi-objective search over the ten link lengths.

Reproduces the paper's optimization and then reruns it with the constraint the
paper leaves out, so the two Pareto fronts can be put on the same axes.

What is being traded
--------------------
Two things we want at once, which fight each other:

  **Gait error** — how badly the foot path walks, as one number. Stance flatness
  and velocity ripple, each divided by Jansen's value and averaged, so Jansen
  scores exactly 1.0 and anything below 1.0 walks more smoothly than Jansen.

  **Wear ratio** — total Archard wear per crank revolution, divided by Jansen's.
  Again Jansen is 1.0, and below 1.0 is less wear. Because it is a ratio the
  unknown wear coefficient cancels, which is what makes it trustworthy.

There is no single best answer, because pushing one down tends to push the other
up. What exists instead is a **Pareto front**: the set of designs you cannot
improve on one axis without giving up ground on the other. Everything behind the
front is simply worse at both and can be thrown away. Plotting the front is how
you show a trade-off honestly rather than picking a winner and hiding the cost.

The rules a design has to obey
------------------------------
From the paper: step length, ground clearance and duty factor each at least 85%
of Jansen's, and the linkage has to actually assemble through a full turn. A
design that walks beautifully with a 5 mm stride is not a walking machine, and
these keep the search from cheating that way.

Ours, added on top in the constrained run: minimum transmission angle **while
the foot is loaded** at or above 40 degrees, plus a branch-consistency margin so
the search cannot hand back a linkage that changes assembly branch mid-stride.
See `constraints.py` for why the loaded qualifier is doing real work.

Reading the numbers
-------------------
Both objectives are ratios to Jansen with Jansen at (1.0, 1.0), so a design at
(0.72, 0.44) walks 28% better and wears 56% less. That is the paper's headline
claim, in the paper's own units, which is exactly what makes it checkable.
"""
from __future__ import annotations

import numpy as np

from .kinematics import JansenLeg, HOLY, DESIGN_KEYS
from . import metrics as M, dynamics as D, wear as W, constraints as C

JANSEN_BRANCH = (-1, -1, 1, -1, 1)

#: Design variables may move this far either side of Jansen's values.
BOUND_FRACTION = 0.30

#: Constraint floors, as a fraction of the Jansen baseline (the paper's rule).
FLOOR = 0.85

#: Objective/constraint value handed back for a design that will not assemble.
PENALTY = 1e6

#: Crank samples per evaluation inside the search. Final designs get re-scored
#: at a finer sample; see `refine`.
N_EVAL = 360


def leg_from_vector(x, branches=JANSEN_BRANCH):
    """Build a JansenLeg from a vector of the ten design lengths b..k."""
    L = dict(HOLY)
    L.update({k: float(v) for k, v in zip(DESIGN_KEYS, x)})
    return JansenLeg(L, branches=branches)


def vector_from_leg(leg):
    return np.array([leg.L[k] for k in DESIGN_KEYS], float)


def bounds(fraction=BOUND_FRACTION):
    """Lower and upper bounds on the design vector, +/- `fraction` of Jansen."""
    base = np.array([HOLY[k] for k in DESIGN_KEYS], float)
    return base * (1.0 - fraction), base * (1.0 + fraction)


def describe(leg, n=N_EVAL, band=M.DEFAULT_BAND):
    """Every published number for one design, in one dict.

    Absolute values, not ratios — `evaluate` turns these into ratios against
    the baseline. Returns NaNs rather than raising for a design that does not
    assemble.
    """
    path = leg.foot_path(n)
    out = dict(M.gait_metrics(path, band=band))
    if not np.all(np.isfinite(path)):
        out.update(wear=float("nan"), wear_integrated=float("nan"),
                   min_transmission_angle=float("nan"),
                   min_transmission_angle_cycle=float("nan"),
                   force_amplification=float("nan"), branch_margin=0.0,
                   assembles=False)
        return out
    sol = D.solve_statics(leg, n=n)
    w = W.wear_per_cycle(sol)
    ta = C.transmission_angles(leg, n=n, band=band)
    forces = sol["forces"]
    out.update(
        wear=w["total"], wear_integrated=w["total_integrated"],
        min_transmission_angle=ta["min_stance"],
        min_transmission_angle_cycle=ta["min"],
        force_amplification=(float(np.max(forces) / D.GROUND_REACTION)
                             if np.isfinite(forces).all() else float("nan")),
        branch_margin=C.branch_margin(leg, n),
        assembles=True,
    )
    return out


def jansen_baseline(n=N_EVAL, band=M.DEFAULT_BAND):
    """The reference design every objective and constraint is measured against."""
    return describe(JansenLeg(branches=JANSEN_BRANCH), n=n, band=band)


#: Which wear number the second objective minimises. "wear" is Archard applied
#: to the cycle-mean pin force, which is the paper's own shortcut and therefore
#: the right default for a reproduction. "wear_integrated" integrates force
#: against sliding instead, which `wear.py` shows is 51% smaller on Jansen.
#: Swapping it asks whether the paper's shortcut changes the *answer* as well as
#: the magnitude - see `scripts/robustness.py`.
WEAR_KEYS = ("wear", "wear_integrated")


def evaluate(x, baseline, n=N_EVAL, min_angle=None,
             min_margin=C.MIN_BRANCH_MARGIN, band=M.DEFAULT_BAND,
             wear_key="wear"):
    """Objectives and constraints for one design vector.

    Returns (objectives, constraints, raw) where objectives are
    [gait error, wear ratio] to be minimised, constraints follow the convention
    g <= 0 is satisfied, and raw is the `describe` dict.

    `min_angle` of None runs the paper's problem exactly; a number adds our
    loaded-transmission-angle constraint on top.
    """
    leg = leg_from_vector(x)
    raw = describe(leg, n=n, band=band)
    n_con = 4 if min_angle is None else 5

    def dead():
        return (np.full(2, PENALTY), np.full(n_con, PENALTY), raw)

    if not raw["assembles"]:
        return dead()
    needed = ("stance_flatness", "velocity_ripple", wear_key, "step_length",
              "ground_clearance", "duty_factor")
    if not all(np.isfinite(raw[k]) for k in needed):
        return dead()

    gait = 0.5 * (raw["stance_flatness"] / baseline["stance_flatness"]
                  + raw["velocity_ripple"] / baseline["velocity_ripple"])
    wear_ratio = raw[wear_key] / baseline[wear_key]

    g = [FLOOR - raw["step_length"] / baseline["step_length"],
         FLOOR - raw["ground_clearance"] / baseline["ground_clearance"],
         FLOOR - raw["duty_factor"] / baseline["duty_factor"],
         min_margin - raw["branch_margin"]]
    if min_angle is not None:
        mu = raw["min_transmission_angle"]
        g.append(min_angle - mu if np.isfinite(mu) else PENALTY)
    return np.array([gait, wear_ratio]), np.array(g, float), raw


def nondominated(F):
    """Boolean mask of the Pareto-optimal rows of an (n, 2) objective array.

    A row is kept when no other row is at least as good on both objectives and
    strictly better on one — the formal statement of "you cannot improve this
    design without giving something up".
    """
    F = np.asarray(F, float)
    keep = np.ones(len(F), bool)
    for i, f in enumerate(F):
        if not keep[i]:
            continue
        dominated = np.all(F <= f, axis=1) & np.any(F < f, axis=1)
        if dominated.any():
            keep[i] = False
    return keep


#: Reference point for `hypervolume`. Both objectives are ratios to Jansen, so
#: Jansen sits at exactly (1, 1) and the unit square below-left of it is the
#: entire space of designs that beat it on both counts.
JANSEN_POINT = (1.0, 1.0)


def hypervolume(F, ref=JANSEN_POINT):
    """Area of the box below-left of `ref` that a point set dominates.

    Comparing two Pareto fronts needs one number, and this is the honest one.
    It rewards a front for being both *good* - close to the origin - and *wide*
    - spread along the trade-off - which is what a front is for. "Best gait
    error" can be moved by a single lucky design at one corner; hypervolume
    cannot.

    With `ref` at Jansen, the answer reads directly as a fraction: 0 means
    nothing on the front beats Jansen, 0.25 means the front dominates a quarter
    of the improvement space that was available.

    Standard 2-D sweep: sort by the first objective, walk left to right, and add
    each strip that reaches below every strip before it. A point that fails to
    beat `ref` on both objectives contributes nothing, which is the behaviour we
    want - it has won no ground.
    """
    P = sorted((p for p in np.atleast_2d(np.asarray(F, float))
                if p[0] < ref[0] and p[1] < ref[1]), key=lambda p: p[0])
    hv, floor = 0.0, float(ref[1])
    for x, y in P:
        if y < floor:
            hv += (ref[0] - x) * (floor - y)
            floor = y
    return float(hv)


#: Fraction of the starting population drawn near the baseline rather than
#: uniformly across the box. See `seeded_population` for why this is necessary.
SEEDED_FRACTION = 0.8


def seeded_population(pop, seed=0, fraction=SEEDED_FRACTION):
    """Starting designs: mostly jittered Jansen, the rest spread across the box.

    A uniform random start does not work on this problem. Of 600 designs drawn
    uniformly from the +/-30% box, 17% assemble at all and **none** satisfy the
    paper's own constraints — step length and duty factor fail in essentially
    every one. The reason is worth stating, because it is a property of the
    mechanism and not of the optimizer: our stance band sits within 1% of the
    path height, so a design that loses Jansen's unusually flat bottom stroke
    also loses most of the arc that counts as stance, and its measured step
    length collapses. The feasible set is a thin shell around Jansen.

    So the population is seeded: one individual at Jansen exactly, most of the
    rest scattered around it at a range of jitter levels, and a remainder drawn
    uniformly to keep some diversity and let the search leave the shell if it
    can. This is a documented deviation - the paper does not say how it
    initialised - and it biases *where the search starts*, not what counts as
    good, which is still decided by the objectives and constraints alone.
    """
    rng = np.random.default_rng(seed)
    lo, hi = bounds()
    base = np.array([HOLY[k] for k in DESIGN_KEYS], float)
    n_seed = max(1, int(round(fraction * pop)))
    jitter = rng.uniform(0.01, 0.12, size=(n_seed - 1, 1))
    near = base * (1.0 + rng.normal(0.0, 1.0, size=(n_seed - 1, len(base))) * jitter)
    wide = rng.uniform(lo, hi, size=(pop - n_seed, len(base)))
    X = np.vstack([base[None, :], near, wide])
    return np.clip(X, lo, hi)


#: Evaluating one design costs about 20 ms and the population is evaluated one
#: generation at a time, so the search is trivially parallel across designs: no
#: individual in a generation depends on any other. `run` spreads a generation
#: over a process pool. The result is bit-identical to the serial version -
#: `pool.map` preserves order and each evaluation is deterministic - so this is
#: a wall-clock change only, not a numerical one. There is a test for that.
_W = {}


def _worker_init(baseline, n, min_angle, band, wear_key):
    """Runs once per worker process. Ships the baseline over instead of per call."""
    _W.update(baseline=baseline, n=n, min_angle=min_angle, band=band,
              wear_key=wear_key)


def _worker_eval(x):
    f, g, _ = evaluate(np.asarray(x, float), _W["baseline"], n=_W["n"],
                       min_angle=_W["min_angle"], band=_W["band"],
                       wear_key=_W["wear_key"])
    return f, g


def _n_workers(workers, pop):
    """How many processes to use. None means auto, 1 means stay in-process."""
    import os
    if workers is None:
        workers = max(1, min(os.cpu_count() or 1, pop))
    return max(1, int(workers))


def run(seed=0, min_angle=None, pop=100, gens=80, n=N_EVAL, baseline=None,
        verbose=False, workers=1, band=M.DEFAULT_BAND, wear_key="wear"):
    """One NSGA-II run. Returns a dict of design vectors, objectives, constraints.

    NSGA-II is a genetic algorithm for more than one objective: it keeps a
    population of designs, breeds the good ones, and sorts them by how many
    other designs beat them outright, which pushes the whole population toward
    the Pareto front instead of toward a single winner. Infeasible designs are
    ranked behind feasible ones by total constraint violation, which is how the
    search finds its way back into the feasible shell described in
    `seeded_population`.

    `workers` sets how many processes evaluate a generation at once: 1 stays
    in-process (the default, and what the tests use), None uses every core.
    Callers that pass anything other than 1 must be under an
    `if __name__ == "__main__"` guard, because Windows starts subprocesses by
    re-importing the calling module.
    """
    from pymoo.core.problem import Problem
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.operators.crossover.sbx import SBX
    from pymoo.operators.mutation.pm import PM
    from pymoo.optimize import minimize

    base = (jansen_baseline(n=n, band=band) if baseline is None else baseline)
    lo, hi = bounds()
    n_con = 4 if min_angle is None else 5
    nw = _n_workers(workers, pop)

    class LegProblem(Problem):
        def __init__(self):
            super().__init__(n_var=len(DESIGN_KEYS), n_obj=2, n_ieq_constr=n_con,
                             xl=lo, xu=hi)

        def _evaluate(self, X, out, *args, **kwargs):
            X = np.atleast_2d(X)
            if pool is None:
                _worker_init(base, n, min_angle, band, wear_key)
                rows = [_worker_eval(x) for x in X]
            else:
                rows = pool.map(_worker_eval, list(X))
            out["F"] = np.array([r[0] for r in rows], float)
            out["G"] = np.array([r[1] for r in rows], float)

    pool = None
    try:
        if nw > 1:
            import multiprocessing as mp
            pool = mp.Pool(nw, initializer=_worker_init,
                           initargs=(base, n, min_angle, band, wear_key))
        res = minimize(
            LegProblem(),
            NSGA2(pop_size=pop, sampling=seeded_population(pop, seed=seed),
                  crossover=SBX(prob=0.9, eta=15), mutation=PM(eta=20),
                  eliminate_duplicates=True),
            ("n_gen", gens), seed=seed, verbose=verbose, save_history=False)
    finally:
        if pool is not None:
            pool.terminate()
            pool.join()

    if res.X is None:
        return dict(X=np.zeros((0, len(DESIGN_KEYS))), F=np.zeros((0, 2)),
                    G=np.zeros((0, n_con)), seed=seed, min_angle=min_angle,
                    band=band, wear_key=wear_key)
    X = np.atleast_2d(res.X)
    F = np.atleast_2d(res.F)
    G = np.atleast_2d(res.G) if res.G is not None else np.zeros((len(X), n_con))
    return dict(X=X, F=F, G=G, seed=seed, min_angle=min_angle, band=band,
                wear_key=wear_key)


def merge(runs):
    """Merge several runs and keep only the designs on the joint Pareto front.

    The paper merges three runs; genetic algorithms are stochastic, so one run
    can miss a corner of the front that another finds.

    Every run coming back empty is a legitimate answer, not an error: tighten
    the transmission-angle constraint far enough and there is nothing feasible
    left to find, which is precisely the measurement `scripts/robustness.py`
    goes looking for. So this returns correctly-shaped empty arrays rather than
    letting `vstack` raise on an empty list.
    """
    kept = [r for r in runs if len(r["X"])]
    if not kept:
        n_var = len(runs[0]["X"][0]) if runs and len(runs[0]["X"]) \
            else len(DESIGN_KEYS)
        return np.zeros((0, n_var)), np.zeros((0, 2))
    X = np.vstack([r["X"] for r in kept])
    F = np.vstack([r["F"] for r in kept])
    if not len(F):
        return X, F
    keep = nondominated(F)
    X, F = X[keep], F[keep]
    order = np.argsort(F[:, 0])
    return X[order], F[order]


def refine(X, baseline, n=M.N_PUBLISHED, min_angle=None,
           band=M.DEFAULT_BAND, wear_key="wear"):
    """Re-score final designs at a finer crank sample.

    The search runs at a coarse sample for speed. Anything that gets published
    is recomputed here, so no headline number rests on the optimizer's
    shortcut.

    **`baseline` must be `jansen_baseline(n=n)`, at this same sample count.**
    Both objectives are ratios, and the numerator and the denominator have to be
    measured the same way or the ratio picks up the difference between two
    sample counts as if it were a difference between two designs. Stance
    flatness moves 3.7% between n=360 and n=1440, which is the same order as the
    gap between neighbouring designs on the front - large enough to matter, small
    enough to look like a result. `run_optimization.py` passes the coarse
    baseline to `run` and this one to `refine`, deliberately.
    """
    rows = []
    for x in np.atleast_2d(X):
        f, g, raw = evaluate(x, baseline, n=n, min_angle=min_angle,
                             band=band, wear_key=wear_key)
        rows.append(dict(x=np.asarray(x, float).tolist(), gait_error=float(f[0]),
                         wear_ratio=float(f[1]), feasible=bool(np.all(g <= 1e-9)),
                         **{k: (float(v) if isinstance(v, (int, float, np.floating))
                                else bool(v)) for k, v in raw.items()}))
    return rows
