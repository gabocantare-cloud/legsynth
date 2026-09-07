import numpy as np
import pytest

from legsynth.kinematics import JansenLeg
from legsynth import dynamics as D, wear as W

JANSEN_BRANCH = (-1, -1, 1, -1, 1)


@pytest.fixture(scope="module")
def leg():
    return JansenLeg(branches=JANSEN_BRANCH)


@pytest.fixture(scope="module")
def sol(leg):
    return D.solve_statics(leg, n=1440)


def test_crank_pin_turns_exactly_once_per_revolution(sol):
    """The crank rotates a full turn against ground: 2*pi, no more, no less."""
    rot = W.relative_rotations(sol)
    assert rot[D.JOINT_NAMES.index("O")] == pytest.approx(2 * np.pi, rel=1e-9)


def test_oscillating_joints_rotate_less_than_the_crank(sol):
    """Rockers swing back and forth; none should out-slide the driven pin."""
    rot = W.relative_rotations(sol)
    for name in ("J2", "J3", "J4_c", "J5", "G_bd", "G_c"):
        assert 0.0 < rot[D.JOINT_NAMES.index(name)] < 2 * np.pi


def test_wear_is_never_negative(sol):
    w = W.wear_per_cycle(sol)
    assert np.all(w["per_joint"] >= 0.0)
    assert np.all(w["integrated"] >= 0.0)
    assert w["total"] > 0.0


def test_mean_force_and_integrated_forms_agree_at_the_crank_pin(sol):
    """The one joint where they must agree analytically, and do.

    The crank turns at a constant rate, so sliding is uniform in crank angle
    and averaging the force first is exact there. Any disagreement would mean
    one of the two calculations is wrong.
    """
    w = W.wear_per_cycle(sol)
    i = D.JOINT_NAMES.index("O")
    assert w["per_joint"][i] == pytest.approx(w["integrated"][i], rel=1e-6)


def test_averaging_the_force_inflates_total_wear(sol):
    """Documented disagreement: the paper says this costs 3-4%; we measure ~51%.

    Force and sliding rate are anti-correlated - the pins are loaded hardest
    while turning slowest - so averaging first overstates the total. Pinned as
    a test so the claim in docs/RESULTS.md cannot drift.
    """
    w = W.wear_per_cycle(sol)
    error = w["total"] / w["total_integrated"] - 1.0
    assert error > 0.25, "mean-force form should overestimate substantially"
    assert error == pytest.approx(0.513, abs=0.03)


def test_wear_scales_the_way_archards_law_says(sol):
    """V = k * F * s: linear in the wear coefficient and in the pin radius."""
    base = W.wear_per_cycle(sol)["total"]
    assert W.wear_per_cycle(sol, k=2 * W.K_WEAR)["total"] == pytest.approx(2 * base)
    assert W.wear_per_cycle(sol, r_pin=3 * W.R_PIN)["total"] == pytest.approx(3 * base)


def test_the_ratio_forgets_the_material_constants(leg):
    """Why we report ratios: k and r_pin cancel exactly between two designs.

    This is the claim that makes the wear conclusion survive not knowing what
    the bushings are made of.
    """
    other = dict(leg.L)
    other["f"] = other["f"] * 1.08
    other_leg = JansenLeg(other, branches=JANSEN_BRANCH)

    def ratio(k, r):
        a = W.wear_per_cycle(D.solve_statics(other_leg, n=360), k=k, r_pin=r)["total"]
        b = W.wear_per_cycle(D.solve_statics(leg, n=360), k=k, r_pin=r)["total"]
        return a / b

    assert ratio(1e-13, 4e-3) == pytest.approx(ratio(7e-11, 1.5e-3), rel=1e-9)


def test_wear_ratio_against_itself_is_one(leg):
    base = W.total_wear(leg, n=360)
    assert W.wear_ratio(leg, base, n=360) == pytest.approx(1.0, rel=1e-12)


def test_breakdown_shares_sum_to_one(sol):
    rows = W.breakdown_table(sol)
    assert len(rows) == 10
    assert sum(r["share"] for r in rows) == pytest.approx(1.0)
    assert rows[0]["wear_mm3"] >= rows[-1]["wear_mm3"]


def test_infeasible_design_has_undefined_wear():
    bad = dict(JansenLeg().L)
    bad["h"] = 500.0
    assert np.isnan(W.total_wear(JansenLeg(bad, branches=JANSEN_BRANCH), n=180))
    assert np.isnan(W.wear_ratio(JansenLeg(bad, branches=JANSEN_BRANCH), 1.0, n=180))
