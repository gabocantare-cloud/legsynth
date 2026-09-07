"""legsynth — durability-aware synthesis of the Jansen walking linkage.

An open reproduction and extension of Wang (2026), *"Durability-Aware
Multi-Objective Optimization of the Jansen Linkage: Trading Gait Quality Against
Joint Wear"* (arXiv:2606.22129), for which the author released no code.

The pipeline runs in one direction, each stage feeding the next:

    kinematics   where every joint is, at every crank angle
        |        `JansenLeg.solve` / `.foot_path`
        v
    metrics      how well that foot path walks - five numbers
        |        `gait_metrics`
        v
    dynamics     what force each of the ten pins carries, from statics
        |        `solve_statics`, checked independently by virtual work
        v
    wear         Archard: worn volume = k x force x sliding distance
        |        `wear_per_cycle`
        v
    constraints  is this a linkage you would actually machine?
        |        `check`, `min_transmission_angle` - the extension
        v
    optimize     NSGA-II over the ten link lengths, gait against wear
        |        `run`, `refine`
        v
    cad          DXF and a coordinate table, ready for SolidWorks
                 `export_all`

Two conventions run through all of it. **Millimetres and newtons**, everywhere,
with angles in radians inside the code and degrees only at the point of
printing. And **a design that cannot be assembled returns NaN rather than
raising**, so a search can score a million candidates without a try/except in
the loop.

Quick start
-----------
    >>> from legsynth import JansenLeg, JANSEN_BRANCH, gait_metrics, N_PUBLISHED
    >>> leg = JansenLeg(branches=JANSEN_BRANCH)
    >>> m = gait_metrics(leg.foot_path(N_PUBLISHED))
    >>> round(m["step_length"], 2)
    43.41
    >>> round(100 * m["duty_factor"], 1)
    31.2

Pass `branches` every time. `JansenLeg()` alone defaults to the all-`+1`
assembly mode, which closes but traces a different curve; `JANSEN_BRANCH` is
the one of the 32 sign combinations that reproduces the real Jansen foot path.

Where the numbers live: `docs/RESULTS.md` for every published figure and the
argument behind it, `docs/METRIC_DEFINITIONS.md` for the formulas the paper
never writes down, and `README.md` for the short version.
"""
from __future__ import annotations

__version__ = "0.1.0"

from .kinematics import JansenLeg, HOLY, DESIGN_KEYS, circ
from .metrics import (
    gait_metrics, step_length, ground_clearance, duty_factor,
    stance_flatness, velocity_ripple, stance_mask, path_height,
    tolerance_sweep, band_matching, DEFAULT_BAND, N_PUBLISHED, PAPER_TABLE4,
)
from .dynamics import solve_statics, power_residual, peak_forces, GROUND_REACTION
from .wear import wear_per_cycle, breakdown_table, total_wear, wear_ratio
from .constraints import (
    check, transmission_angles, min_transmission_angle, force_amplification,
    branch_margin, GOOD_TRANSMISSION_ANGLE,
)

#: The branch of the dyad cascade that reproduces the real Jansen foot path.
#: All 32 sign combinations were swept to find it; see `docs/RESULTS.md`.
JANSEN_BRANCH = (-1, -1, 1, -1, 1)

__all__ = [
    "__version__", "JANSEN_BRANCH",
    # kinematics
    "JansenLeg", "HOLY", "DESIGN_KEYS", "circ",
    # metrics
    "gait_metrics", "step_length", "ground_clearance", "duty_factor",
    "stance_flatness", "velocity_ripple", "stance_mask", "path_height",
    "tolerance_sweep", "band_matching", "DEFAULT_BAND", "N_PUBLISHED",
    "PAPER_TABLE4",
    # dynamics
    "solve_statics", "power_residual", "peak_forces", "GROUND_REACTION",
    # wear
    "wear_per_cycle", "breakdown_table", "total_wear", "wear_ratio",
    # constraints
    "check", "transmission_angles", "min_transmission_angle",
    "force_amplification", "branch_margin", "GOOD_TRANSMISSION_ANGLE",
]
