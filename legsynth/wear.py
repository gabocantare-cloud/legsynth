"""Archard wear at the ten pins.

Archard's law: the volume of material rubbed out of a sliding contact is

    V = k * F * s

with F the normal load, s the distance slid, and k a wear coefficient carrying
the material pair and the lubrication. At a revolute joint the two bodies do not
slide past each other in a straight line, they rotate against each other, so the
distance slid at the pin surface over one crank revolution is

    s = r_pin * sum |d(phi_A - phi_B)|

— the pin radius times the *total* relative rotation, accumulated as absolute
increments so that rocking back and forth counts twice rather than cancelling.
A joint that swings 30 degrees each way per cycle slides just as far as one that
sweeps 60 degrees one way.

Following the paper we use the cycle-mean force rather than integrating the
instantaneous force against the instantaneous sliding, so

    V_joint = k * mean(|F|) * r_pin * total_relative_rotation

The paper argues this costs 3-4%. We can do better than argue: `wear_per_cycle`
also returns the properly integrated value, and on the Jansen baseline the two
differ by the amount reported in `docs/RESULTS.md`.

Why the ratio is the number to trust
------------------------------------
k is the weakest number in the whole model. Textbook values for a steel pin in a
polymer bushing span two orders of magnitude, and the real value depends on
surface finish, grit and whether anyone greased it. So an absolute wear volume
in cubic millimetres per cycle is honest only to within that factor.

But k multiplies every joint of every design identically. Divide one design's
total wear by another's and k cancels, exactly, along with the pin radius if the
pins are the same size. What survives is a statement about geometry: *this
linkage puts less rubbing-under-load into its pins than that one*, which is the
comparison the optimizer actually needs, and it holds no matter what the pins
are made of. This is why the paper's headline claim ("56% less wear") is much
more defensible than any absolute lifetime it could have quoted, and why
`wear_ratio` is the function used everywhere downstream.
"""
from __future__ import annotations

import numpy as np

from . import dynamics as D

K_WEAR = 1e-13     # m^3 / (N*m), representative steel-on-polymer value
R_PIN = 4e-3       # m, pin radius


def relative_rotations(sol):
    """Total relative rotation at each joint over the cycle, in radians.

    Uses the body orientations at the solved poses, unwrapped so that a joint
    passing through +/-pi is not credited with a spurious full turn. Returns an
    array of length 10, in `dynamics.JOINT_NAMES` order.
    """
    ang = D.body_angles(sol["pts"])
    n = sol["theta"].size
    zero = np.zeros(n)
    out = np.empty(len(D.JOINTS))
    for i, (_, _, ba, bb) in enumerate(D.JOINTS):
        a = zero if ba == "ground" else ang[ba]
        b = zero if bb == "ground" else ang[bb]
        rel = np.unwrap(b - a)
        # Close the loop: the last sample slides back round to the first.
        steps = np.diff(np.concatenate([rel, rel[:1]]))
        steps = (steps + np.pi) % (2 * np.pi) - np.pi
        out[i] = float(np.sum(np.abs(steps)))
    return out


def wear_per_cycle(sol, k=K_WEAR, r_pin=R_PIN):
    """Worn volume at each joint per crank revolution, in cubic metres.

    Returns a dict with
        per_joint   (10,)  V = k * mean|F| * r_pin * total relative rotation
        integrated  (10,)  the same with force integrated against sliding
                           rather than averaged first — what the paper's
                           mean-force simplification is being checked against
        total       float  sum of per_joint
        sliding     (10,)  distance slid at each pin per cycle, m
        rotation    (10,)  total relative rotation at each joint, rad
        mean_force  (10,)  cycle-mean force magnitude at each joint, N

    NaN forces (an unassemblable or singular design) propagate to NaN totals.
    """
    rot = relative_rotations(sol)
    sliding = r_pin * rot
    f = sol["forces"]
    # One NaN anywhere in the force history means the design failed to
    # assemble at some crank angle, and a mean over the samples that did solve
    # would be a wear number for a leg that does not exist. So it is all or
    # nothing, per design rather than per sample.
    mean_force = (np.mean(f, axis=0) if np.isfinite(f).all()
                  else np.full(f.shape[1], np.nan))
    per_joint = k * mean_force * sliding

    # Integrated form: sum |F| * r_pin * |d phi| step by step round the cycle.
    ang = D.body_angles(sol["pts"])
    n = sol["theta"].size
    zero = np.zeros(n)
    integrated = np.empty(f.shape[1])
    for i, (_, _, ba, bb) in enumerate(D.JOINTS):
        a = zero if ba == "ground" else ang[ba]
        b = zero if bb == "ground" else ang[bb]
        rel = np.unwrap(b - a)
        steps = np.diff(np.concatenate([rel, rel[:1]]))
        steps = (steps + np.pi) % (2 * np.pi) - np.pi
        fmid = 0.5 * (f[:, i] + np.roll(f[:, i], -1))
        integrated[i] = k * r_pin * float(np.sum(fmid * np.abs(steps)))

    return dict(per_joint=per_joint, integrated=integrated,
                total=float(np.sum(per_joint)),
                total_integrated=float(np.sum(integrated)),
                sliding=sliding, rotation=rot, mean_force=mean_force)


def total_wear(leg, n=360, **kw):
    """Total worn volume per cycle for one leg, in cubic metres. NaN if infeasible."""
    sol = D.solve_statics(leg, n=n, **kw)
    if not np.isfinite(sol["forces"]).all():
        return float("nan")
    return wear_per_cycle(sol)["total"]


def wear_ratio(leg, baseline_total, n=360, **kw):
    """This leg's wear per cycle divided by a baseline's.

    Dimensionless, and independent of the wear coefficient and pin radius as
    long as both designs use the same ones — which is the whole reason this,
    and not an absolute volume, is the objective the optimizer minimises.
    Values below 1 wear less than the baseline.
    """
    t = total_wear(leg, n=n, **kw)
    if not np.isfinite(t) or not np.isfinite(baseline_total) or baseline_total <= 0:
        return float("nan")
    return t / baseline_total


def breakdown_table(sol, k=K_WEAR, r_pin=R_PIN):
    """Per-joint wear breakdown as a list of dicts, worst joint first."""
    w = wear_per_cycle(sol, k, r_pin)
    rows = []
    for i, name in enumerate(D.JOINT_NAMES):
        rows.append(dict(
            joint=name,
            mean_force_N=float(w["mean_force"][i]),
            peak_force_N=float(np.nanmax(sol["forces"][:, i])),
            rotation_deg=float(np.degrees(w["rotation"][i])),
            sliding_mm=float(w["sliding"][i] * 1e3),
            wear_mm3=float(w["per_joint"][i] * 1e9),
            share=float(w["per_joint"][i] / w["total"]) if w["total"] else float("nan"),
        ))
    rows.sort(key=lambda r: -r["wear_mm3"])
    return rows
