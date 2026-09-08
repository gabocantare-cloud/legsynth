"""Is this linkage sane to build? — the check the paper never makes.

The paper optimises for wear and gait and stops there. Nothing in it asks
whether the resulting geometry is a mechanism you would actually machine. This
module adds that layer. It is the contribution that is ours rather than a
reproduction, so the definitions are spelled out at length.

What a transmission angle is
----------------------------
When one bar pushes on the next, the push arrives at some angle. Only the part
of it that lies along the direction the driven part is free to move does any
work; the rest just squeezes the pin. The transmission angle is that angle,
measured so that **90 degrees is perfect** (the whole push turns into motion)
and **0 degrees is dead** (the push does nothing but crush the pin).

Picture pushing a door closed with a stick. Square to the door, it swings
easily. Nearly edge-on to the door, you shove hard, the door barely moves, and
all your effort goes into grinding the stick against the door. A linkage running
at a shallow transmission angle does the same thing to its own pins: enormous
bearing force, little motion, rapid wear, and it will bind or jam rather than
back-drive. Machine-design practice keeps the minimum above roughly 40 degrees.

That is why leaving it out of a paper about *wear* is a real gap. A design can
score well on the paper's wear objective while running at a shallow angle
somewhere in the cycle, and shallow angles are a wear mechanism.

Where the angle is defined, and where it is not
-----------------------------------------------
The textbook definition is the angle between a **coupler** (a binary link,
pinned at both ends, carrying force along its own length) and the **output
link** it drives, at the pin they share. That needs the driven body to have a
well-defined direction of motion, which it has when it pivots on ground: the
pin then moves perpendicular to the line joining it to that pivot.

Three interfaces in the Jansen leg qualify:

    LJ (J1-J2) drives T1, which pivots at G   -> angle to G-J2
    LK (J1-J4) drives LC, which pivots at G   -> angle to G-J4
    T1 drives LF (J3-J5), T1 pivots at G      -> angle to G-J3

Two candidate interfaces are deliberately excluded, and the reasons matter:

* **Anything involving the crank.** The coupler lines up with the crank twice per
  turn. In a crank-rocker that is not a defect, it is the normal dead point of
  the *rocker's* travel, where nothing needs to move. Counting it would report
  0 degrees for every healthy four-bar ever built.
* **The links attaching to the floating triangle T2.** T2 carries the foot and
  pivots on nothing, so it has no fixed line of motion and the textbook angle
  simply is not defined there. Rather than invent a number, `force_amplification`
  below covers those joints instead.

Both a geometric construction (angle between the two bars) and a kinematic one
(angle between the coupler and the pin's velocity) were implemented while
writing this, and they agree to within rounding on all three interfaces — which
is the check that the definition is the classical one.

Loaded versus unloaded: the refinement that matters
---------------------------------------------------
Measured over the whole revolution, Jansen's own linkage bottoms out at 8.6
degrees, which the 40-degree rule would call unbuildable. Look at when that
happens and the verdict inverts: it happens mid-swing, with the foot in the air
and 0.6 N in the pin. Meanwhile the largest pin force in the cycle, 25.8 N,
arrives at a perfectly healthy 48 degrees.

A shallow angle only costs you something when there is force behind it. So the
constraint this repo enforces is the **minimum transmission angle during
stance** — while the leg is actually carrying the machine — and by that measure
Jansen sits at 42.7 degrees and passes the rule of thumb with a little room.

This matters for the extension's honesty. Adding the naive whole-cycle
constraint would have rejected Theo Jansen's own linkage for a defect that costs
nothing, and any Pareto front drawn under it would have been an artefact.
`stance_only=True` is the default everywhere for that reason; pass False to see
the whole-cycle figure.

Force amplification: the measure that works everywhere
-------------------------------------------------------
The transmission angle is a *geometric* proxy for a *mechanical* worry: a joint
that needs a huge force to produce a small motion. That worry can be measured
directly and without exclusions, by taking the largest pin force anywhere in the
cycle and dividing it by the load being carried:

    amplification = max |pin force| / ground reaction

A well-behaved linkage sits near 1: the pins carry about what the ground pushes.
A linkage near a singular pose runs to tens or hundreds, which is a design that
will hammer its own bearings whatever its wear score says.

The two measures are related but not interchangeable, and on Jansen's own
linkage they disagree — see `docs/RESULTS.md`. Keeping both is the honest
choice: the transmission angle is what the linkage literature will expect, the
amplification is what the physics actually cares about.

Branch consistency
------------------
`kinematics.circ` picks one of the two intersections of a pair of circles. If
the two circles ever become tangent mid-cycle, the two solutions collide and the
mechanism can flip to the other assembly branch — the physical leg would have to
come apart and be rebuilt to follow the path our maths just drew. `branch_margin`
reports how close the closest such approach gets, normalised, so that an
optimizer can be told to stay away from it rather than being handed a design
that only works on paper.
"""
from __future__ import annotations

import numpy as np

from . import dynamics as D
from . import metrics as M

#: The three interfaces where the classical transmission angle is defined:
#: (label, coupler tail, coupler head, driven-body pivot, driven pin).
TRANSMISSION_INTERFACES = (
    ("LJ-T1@J2", "J1", "J2", "G", "J2"),
    ("LK-LC@J4", "J1", "J4", "G", "J4"),
    ("T1-LF@J3", "J3", "J5", "G", "J3"),
)

#: Machine-design rule of thumb for the minimum acceptable value, degrees.
GOOD_TRANSMISSION_ANGLE = 40.0

#: Pin force above this multiple of the applied load means a near-singular design.
MAX_AMPLIFICATION = 25.0

#: Branch margin below this fraction of a link length is treated as unsafe.
MIN_BRANCH_MARGIN = 0.02


def _fold(u, w):
    """Angle between two direction arrays, folded into [0, 90] degrees.

    Folded because a bar at 175 degrees to its neighbour is as close to
    collinear, and as badly off, as one at 5 degrees.
    """
    cross = u[..., 0] * w[..., 1] - u[..., 1] * w[..., 0]
    dot = u[..., 0] * w[..., 0] + u[..., 1] * w[..., 1]
    a = np.abs(np.arctan2(cross, dot)) % np.pi
    return np.degrees(np.minimum(a, np.pi - a))


def transmission_angles(leg, n=M.N_PUBLISHED, pts=None, band=M.DEFAULT_BAND):
    """Transmission angle at each defined interface, over one revolution.

    Returns a dict of label -> array of degrees in [0, 90], plus
        "min"         minimum over every interface and every crank angle
        "min_stance"  the same, restricted to samples with the foot down
        "stance"      the stance mask used
    NaN anywhere the design does not assemble.
    """
    if pts is None:
        theta = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
        pts = leg.solve(theta)
    out = {}
    for label, ct, ch, pivot, pin in TRANSMISSION_INTERFACES:
        out[label] = _fold(pts[ch] - pts[ct], pts[pin] - pts[pivot])
    per_sample = np.minimum.reduce([out[k[0]] for k in TRANSMISSION_INTERFACES])

    path = pts["F"]
    stance = (M.stance_mask(path, band) if np.all(np.isfinite(path))
              else np.zeros(path.shape[0], bool))
    out["stance"] = stance
    out["min"] = (float(np.nanmin(per_sample)) if np.isfinite(per_sample).any()
                  else float("nan"))
    out["min_stance"] = (float(np.nanmin(per_sample[stance])) if stance.any()
                         else float("nan"))
    return out


def min_transmission_angle(leg, n=M.N_PUBLISHED, stance_only=True,
                           band=M.DEFAULT_BAND):
    """Worst transmission angle in degrees. NaN if the design does not assemble.

    By default this is the worst angle *while the foot is on the ground*, which
    is the only time a shallow angle costs anything — see the module docstring.
    Pass ``stance_only=False`` for the whole-cycle figure.
    """
    ta = transmission_angles(leg, n, band=band)
    return ta["min_stance"] if stance_only else ta["min"]


def force_amplification(leg, n=M.N_PUBLISHED, grf=D.GROUND_REACTION, **kw):
    """Largest pin force in the cycle, as a multiple of the ground reaction.

    1.0 means the pins carry exactly what the foot carries. Large values mean
    the linkage is buying its motion with force, which is what wears pins out.
    NaN if the design does not assemble or goes singular.
    """
    sol = D.solve_statics(leg, n=n, grf=grf, **kw)
    f = sol["forces"]
    if not np.isfinite(f).all():
        return float("nan")
    return float(np.max(f) / grf)


def branch_margin(leg, n=M.N_PUBLISHED):
    """How close the leg comes to flipping assembly branch, normalised.

    Each joint in the cascade is the meeting point of two circles. Reproducing
    `kinematics.circ`, the half-chord `h` between the two intersections goes to
    zero exactly when the circles touch and the two assembly branches merge.
    This returns the smallest `h`, over all five dyads and the whole revolution,
    divided by the mean link length, so it is dimensionless and comparable
    across designs. Zero means the leg changes branch mid-stride; larger is
    safer.
    """
    theta = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    p = leg.solve(theta)
    L = leg.L
    dyads = (("J1", "j", "G", "b"), ("J2", "e", "G", "d"), ("J1", "k", "G", "c"),
             ("J3", "f", "J4", "g"), ("J4", "i", "J5", "h"))
    scale = float(np.mean([L[k] for k in "bcdefghijkm"]))
    worst = np.inf
    for a, ra, b, rb in dyads:
        d = p[b] - p[a]
        dist = np.hypot(d[..., 0], d[..., 1])
        with np.errstate(divide="ignore", invalid="ignore"):
            A = (L[ra] ** 2 - L[rb] ** 2 + dist ** 2) / (2 * dist)
            h2 = L[ra] ** 2 - A ** 2
        if not np.isfinite(h2).all() or np.nanmin(h2) < 0:
            return 0.0
        worst = min(worst, float(np.sqrt(np.nanmin(h2))))
    return worst / scale


def check(leg, n=M.N_PUBLISHED, min_angle=GOOD_TRANSMISSION_ANGLE,
          max_amp=MAX_AMPLIFICATION, min_margin=MIN_BRANCH_MARGIN,
          band=M.DEFAULT_BAND):
    """Full manufacturability report for one design.

    Returns a dict with the measures, a pass/fail against each threshold, and
    `ok`, True only if the leg assembles and passes all three. The reported
    transmission angle is the loaded (stance) one; the whole-cycle value is
    carried alongside as `min_transmission_angle_cycle` for reference but is
    not what the design is judged on.

    `band` decides which samples count as stance and therefore which angles the
    loaded minimum is taken over, so it has to reach `transmission_angles` -
    this function used to drop it and silently report the default band's answer
    whatever the caller asked for. That is the same defect shape that already
    cost this repo one study: a parameter threaded through one path and
    defaulted on another gives plausible numbers rather than a crash.

    `n` defaults to `M.N_PUBLISHED`, the one sample count behind every published
    number in the repo. The four measures below are sensitive to it - stance is
    an arc, so how finely the turn is sampled changes where its edges fall - and
    having each entry point default to a different count was a good way to get
    two different answers to the same question.
    """
    if not leg.assembles(n):
        return dict(assembles=False, min_transmission_angle=float("nan"),
                    min_transmission_angle_cycle=float("nan"),
                    force_amplification=float("nan"), branch_margin=0.0,
                    passes_angle=False, passes_amplification=False,
                    passes_branch=False, ok=False)
    ta = transmission_angles(leg, n, band=band)
    mu, mu_cycle = ta["min_stance"], ta["min"]
    amp = force_amplification(leg, n)
    margin = branch_margin(leg, n)
    passes = (bool(np.isfinite(mu) and mu >= min_angle),
              bool(np.isfinite(amp) and amp <= max_amp),
              bool(margin >= min_margin))
    return dict(assembles=True, min_transmission_angle=mu,
                min_transmission_angle_cycle=mu_cycle,
                force_amplification=amp, branch_margin=margin,
                passes_angle=passes[0], passes_amplification=passes[1],
                passes_branch=passes[2], ok=all(passes))
