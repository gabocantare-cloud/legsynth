"""Gait metrics for a planar foot path — with the definitions written down.

Wang (2026), arXiv:2606.22129, reports five gait numbers in Table 4 but never
publishes the formulas behind them. This module publishes ours. Every formula
below is stated in full so that anybody can get our numbers back, disagree with
a choice, and re-run with their own.

The one judgement call
----------------------
The foot of a Jansen leg is never *exactly* flat on the ground. Its bottom
stroke sags by a fraction of a millimetre. So "the foot is on the ground" needs
a threshold, and every downstream number — step length, duty factor, flatness,
ripple — moves with it.

We define the **ground line** as a band of height ``band * H`` above the lowest
point of the foot path, where ``H`` is the total height of the path:

    y_ground = min(y) + band * (max(y) - min(y))

and **stance** is the longest unbroken arc of the crank revolution spent at or
below that line. The default ``band = 0.01`` (1% of path height) is used
throughout the repo.

Why a *fraction* of path height rather than a fixed tolerance in millimetres:
it is scale-invariant. Build the same leg at twice the size and the duty
factor, flatness and ripple are unchanged, while step length and clearance
simply double. A fixed 0.5 mm tolerance has no such property — it would call a
model-sized leg twitchy and a full-sized one flat, for identical geometry.

The choice of 1% is still a choice. `tolerance_sweep` exists so that the
sensitivity is reported rather than hidden, and `band_matching` inverts the
question: what band would we need to reproduce a given published number?

See `docs/METRIC_DEFINITIONS.md` for the reproduction table and for where we
disagree with the paper.

Conventions
-----------
* A *path* is an array of shape (n, 2) of foot positions sampled at ``n`` crank
  angles spaced uniformly over one full revolution, endpoint excluded — exactly
  what `JansenLeg.foot_path` returns. Uniform spacing is what lets us read the
  duty factor straight off the sample count.
* Speeds are per radian of crank angle, not per second. Every metric that uses
  speed is a ratio, so the crank rate cancels and never has to be assumed.
* A path containing NaN (a design that will not assemble) yields NaN metrics
  rather than an exception.
"""
from __future__ import annotations

import numpy as np

#: Default stance band, as a fraction of total foot-path height.
DEFAULT_BAND = 0.01

#: Crank samples behind every published number in this repo.
#:
#: Stance is the *longest unbroken arc* of the turn inside the band, so its
#: measured extent is quantised by the sample spacing: duty factor and step
#: length both creep as the sample count changes (31.4% at 360 samples, 31.2%
#: at 1440, and 43.41 mm against 43.49 mm for step length at 3600). None of
#: that is error - each is the right answer to a slightly different question -
#: but quoting one quantity at two sample counts in two documents reads as
#: sloppiness. So every table in `docs/` and `README.md` is generated at this
#: one count, and every caption says so. The search itself still runs coarser
#: for speed (`optimize.N_EVAL`); anything published is re-scored here.
N_PUBLISHED = 1440

#: Wang (2026) Table 4, Jansen baseline row. Our reproduction targets.
PAPER_TABLE4 = dict(
    step_length=43.3,        # mm
    ground_clearance=25.7,   # mm
    stance_flatness=0.0281,  # dimensionless
    velocity_ripple=0.0956,  # dimensionless
    duty_factor=0.20,        # reported only as "approximately 20%"
)

METRIC_UNITS = dict(
    step_length="mm", ground_clearance="mm", stance_flatness="-",
    velocity_ripple="-", duty_factor="-",
)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _xy(path):
    """Split an (n, 2) path into x, y. Raises on the wrong shape."""
    P = np.asarray(path, float)
    if P.ndim != 2 or P.shape[1] != 2 or P.shape[0] < 3:
        raise ValueError("path must have shape (n, 2) with n >= 3")
    return P[:, 0], P[:, 1]


def is_closed(path):
    """True if the path is finite everywhere — the leg assembles all the way round."""
    return bool(np.all(np.isfinite(np.asarray(path, float))))


def longest_run(mask):
    """Longest unbroken run of True in a *circular* boolean array.

    The crank revolution wraps, so a stance phase straddling theta = 0 is one
    run, not two. Returns a boolean array selecting only that run.
    """
    m = np.asarray(mask, bool)
    n = m.size
    if not m.any():
        return np.zeros(n, bool)
    if m.all():
        return m.copy()
    # Rotate so index 0 starts a run; then no run wraps the end of the array.
    start = int(np.flatnonzero(m & ~np.roll(m, 1))[0])
    rot = np.roll(m, -start).astype(np.int8)
    edges = np.flatnonzero(np.diff(np.concatenate([[0], rot, [0]])))
    starts, ends = edges[0::2], edges[1::2]
    k = int(np.argmax(ends - starts))
    out = np.zeros(n, bool)
    out[starts[k]:ends[k]] = True
    return np.roll(out, start)


def path_height(path):
    """Total vertical extent of the foot path, max(y) - min(y), in mm."""
    _, y = _xy(path)
    return float(np.ptp(y))


def ground_line(path, band=DEFAULT_BAND, tol=None):
    """Height of the ground line, in path units.

    ``band`` is a fraction of the path height; pass ``tol`` instead to set the
    band directly in millimetres. ``tol`` wins if both are given.
    """
    _, y = _xy(path)
    if tol is not None:
        if tol < 0:
            raise ValueError("tol must be >= 0")
        return float(np.min(y) + tol)
    if not 0 <= band < 1:
        raise ValueError("band must be in [0, 1)")
    return float(np.min(y) + band * np.ptp(y))


def stance_mask(path, band=DEFAULT_BAND, tol=None):
    """Boolean mask of the samples counted as stance.

    Stance := the longest unbroken arc of the revolution with y <= y_ground.
    """
    _, y = _xy(path)
    if not np.all(np.isfinite(y)):
        return np.zeros(y.size, bool)
    return longest_run(y <= ground_line(path, band, tol) + 1e-12)


def foot_speed(path):
    """Foot speed at every sample, per radian of crank angle.

    Central difference on a periodic sample: |dr/dtheta|, dtheta = 2*pi/n.
    """
    x, y = _xy(path)
    dtheta = 2.0 * np.pi / x.size
    dx = (np.roll(x, -1) - np.roll(x, 1)) / (2.0 * dtheta)
    dy = (np.roll(y, -1) - np.roll(y, 1)) / (2.0 * dtheta)
    return np.hypot(dx, dy)


# --------------------------------------------------------------------------
# the five metrics
# --------------------------------------------------------------------------

def step_length(path, band=DEFAULT_BAND, tol=None):
    """Horizontal distance the foot sweeps while on the ground, in mm.

        step = max(x_stance) - min(x_stance)

    Physically: how far the body is pushed forward in one crank revolution,
    assuming the foot does not slip.
    """
    x, _ = _xy(path)
    m = stance_mask(path, band, tol)
    if not m.any():
        return float("nan")
    return float(np.ptp(x[m]))


def ground_clearance(path, band=DEFAULT_BAND, tol=None):
    """Peak height of the foot above the ground line during the return, in mm.

        clearance = max(y) - y_ground

    Physically: the tallest obstacle the leg can step over without stubbing.
    It is bounded above by the path height, so it barely moves with the band —
    the one metric the stance definition cannot explain away.
    """
    _, y = _xy(path)
    if not np.all(np.isfinite(y)):
        return float("nan")
    return float(np.max(y) - ground_line(path, band, tol))


def duty_factor(path, band=DEFAULT_BAND, tol=None):
    """Fraction of one crank revolution spent in stance (0-1).

        duty = (crank angle swept during stance) / (2*pi)

    Because the path is sampled uniformly in crank angle, this is the fraction
    of samples in the stance mask.

    Physically: at duty factor d, a machine needs at least 1/d legs, phase
    shifted, to always have a foot on the ground.
    """
    m = stance_mask(path, band, tol)
    if not m.any():
        return float("nan")
    return float(m.sum()) / float(m.size)


def stance_flatness(path, band=DEFAULT_BAND, tol=None):
    """Dimensionless roughness of the ground stroke. Lower is better.

        flatness = std(y_stance) / step_length

    The numerator is the RMS wobble of the foot about its own mean height while
    on the ground; dividing by step length makes it scale-invariant.

    Physically: multiply by step length and you get, in millimetres, how much
    the body bobs up and down over one step.
    """
    _, y = _xy(path)
    m = stance_mask(path, band, tol)
    s = step_length(path, band, tol)
    if not m.any() or not np.isfinite(s) or s == 0.0:
        return float("nan")
    return float(np.std(y[m]) / s)


def velocity_ripple(path, band=DEFAULT_BAND, tol=None):
    """Dimensionless unevenness of foot speed during stance. Lower is better.

        ripple = std(|v|_stance) / mean(|v|_stance)

    i.e. the coefficient of variation of foot speed over the ground stroke.
    Speeds are per radian of crank, so a constant crank rate cancels out.

    Physically: the planted foot is the body's only connection to the ground,
    so a foot that speeds up and slows down while planted makes the whole
    machine surge and drag even at constant crank speed.
    """
    m = stance_mask(path, band, tol)
    if not m.any():
        return float("nan")
    v = foot_speed(path)[m]
    mu = float(np.mean(v))
    if mu == 0.0:
        return float("nan")
    return float(np.std(v) / mu)


METRIC_FUNCS = dict(
    step_length=step_length, ground_clearance=ground_clearance,
    stance_flatness=stance_flatness, velocity_ripple=velocity_ripple,
    duty_factor=duty_factor,
)


def gait_metrics(path, band=DEFAULT_BAND, tol=None):
    """All five metrics for one foot path, as a dict.

    Returns NaN for every metric if the path is not fully assemblable.
    """
    if not is_closed(path):
        return {k: float("nan") for k in METRIC_FUNCS}
    return {k: f(path, band, tol) for k, f in METRIC_FUNCS.items()}


# --------------------------------------------------------------------------
# sensitivity: how much does the band choice actually matter?
# --------------------------------------------------------------------------

DEFAULT_BANDS = (0.002, 0.005, 0.01, 0.02, 0.03, 0.05, 0.08, 0.12, 0.20)


def tolerance_sweep(path, bands=DEFAULT_BANDS):
    """Recompute every metric across a range of stance bands.

    Returns a list of dicts, one per band, each carrying the band as a fraction
    ('band'), the same band in mm ('tol_mm'), and the five metrics. This is the
    published sensitivity result: it lets a reader see how much of any
    disagreement is a definition and how much is geometry.
    """
    H = path_height(path)
    rows = []
    for b in bands:
        row = dict(band=float(b), tol_mm=float(b * H))
        row.update(gait_metrics(path, band=b))
        rows.append(row)
    return rows


def band_matching(path, metric, target, lo=1e-6, hi=0.9, iters=200):
    """Band (as a fraction of path height) at which `metric` equals `target`.

    Inverts the sensitivity question: instead of asking what our number is at
    our band, ask what band we would need in order to reproduce somebody else's
    published number. Bisection; returns NaN if the target is not bracketed on
    [lo, hi].

    Caveat: only `step_length`, `ground_clearance` and `duty_factor` are
    monotonic in the band. `stance_flatness` and `velocity_ripple` are not
    strictly monotonic near zero band, so a returned root is *a* band that
    reproduces the target, not necessarily the only one.
    """
    f = METRIC_FUNCS[metric]

    def g(b):
        return f(path, band=b)

    glo, ghi = g(lo), g(hi)
    if not (np.isfinite(glo) and np.isfinite(ghi)):
        return float("nan")
    if (glo - target) * (ghi - target) > 0:
        return float("nan")
    rising = ghi > glo
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if (g(mid) < target) == rising:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)
