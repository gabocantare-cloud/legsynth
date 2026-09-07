import numpy as np
import pytest

from legsynth.kinematics import JansenLeg
from legsynth import constraints as C, dynamics as D, metrics as M

JANSEN_BRANCH = (-1, -1, 1, -1, 1)


@pytest.fixture(scope="module")
def leg():
    return JansenLeg(branches=JANSEN_BRANCH)


# --------------------------------------------------------------------------
# the angle measure itself
# --------------------------------------------------------------------------

def test_fold_treats_nearly_collinear_both_ways_alike():
    """5 degrees apart and 175 degrees apart are equally close to collinear."""
    u = np.array([[1.0, 0.0]])
    for deg in (5.0, 175.0, 185.0, 355.0):
        r = np.radians(deg)
        w = np.array([[np.cos(r), np.sin(r)]])
        assert C._fold(u, w)[0] == pytest.approx(5.0, abs=1e-9)


def test_angles_stay_in_range(leg):
    ta = C.transmission_angles(leg, 720)
    for label, _, _, _, _ in C.TRANSMISSION_INTERFACES:
        assert np.all((ta[label] >= 0.0) & (ta[label] <= 90.0))


def test_geometric_and_velocity_definitions_agree(leg):
    """Cross-check that our angle is the classical transmission angle.

    For a coupler driving a body that pivots on ground, the pin moves square to
    the line joining it to that pivot. So the geometric angle (coupler to that
    line) and the kinematic one (90 degrees minus coupler-to-pin-velocity) are
    the same quantity derived two different ways. Agreement is the evidence
    that the definition in this module is the textbook one and not an invention.
    """
    n = 2880
    theta = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    pts = leg.solve(theta)
    dth = theta[1] - theta[0]
    geo = C.transmission_angles(leg, pts=pts)
    for label, ct, ch, pivot, pin in C.TRANSMISSION_INTERFACES:
        v = (np.roll(pts[pin], -1, axis=0) - np.roll(pts[pin], 1, axis=0)) / (2 * dth)
        kin = 90.0 - C._fold(pts[ch] - pts[ct], v)
        speed = np.hypot(v[:, 0], v[:, 1])
        fast = speed > 0.05 * speed.max()   # direction is noise where the pin stalls
        assert np.allclose(geo[label][fast], kin[fast], atol=0.5), label


# --------------------------------------------------------------------------
# the finding: loaded and unloaded tell different stories
# --------------------------------------------------------------------------

def test_jansen_baseline_angles(leg):
    """Pinned values. Jansen fails the 40-degree rule over the whole cycle and
    passes it while loaded — the result docs/RESULTS.md is built on."""
    ta = C.transmission_angles(leg, 2880)
    assert ta["min"] == pytest.approx(8.65, abs=0.1)
    assert ta["min_stance"] == pytest.approx(42.7, abs=0.2)
    assert ta["min"] < C.GOOD_TRANSMISSION_ANGLE < ta["min_stance"]


def test_the_shallow_angle_arrives_with_almost_no_load(leg):
    """Why the whole-cycle constraint would be wrong: at Jansen's worst angle
    the pin is carrying a fraction of what it carries at its worst force."""
    n = 1440
    theta = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    pts = leg.solve(theta)
    ta = C.transmission_angles(leg, pts=pts)
    per_sample = np.minimum.reduce([ta[k[0]] for k in C.TRANSMISSION_INTERFACES])
    sol = D.solve_statics(leg, theta=theta)
    worst_angle = int(np.argmin(per_sample))
    peak_force = np.nanmax(sol["forces"], axis=1)
    assert not sol["stance"][worst_angle], "worst angle should fall in swing"
    assert peak_force[worst_angle] < 0.1 * peak_force.max()


def test_stance_only_is_the_default(leg):
    assert C.min_transmission_angle(leg, 1440) == \
        pytest.approx(C.transmission_angles(leg, 1440)["min_stance"])
    assert C.min_transmission_angle(leg, 1440, stance_only=False) == \
        pytest.approx(C.transmission_angles(leg, 1440)["min"])


# --------------------------------------------------------------------------
# force amplification
# --------------------------------------------------------------------------

def test_amplification_is_a_ratio_not_a_force(leg):
    """Doubling the load doubles the pin forces, so the ratio must not move."""
    a = C.force_amplification(leg, n=360, grf=20.0, line_density=0.0)
    b = C.force_amplification(leg, n=360, grf=200.0, line_density=0.0)
    assert a == pytest.approx(b, rel=1e-9)


def test_jansen_is_not_force_amplifying(leg):
    """Jansen's pins carry about what the ground pushes: near 1, not tens."""
    amp = C.force_amplification(leg, n=720)
    assert 1.0 < amp < 2.0


# --------------------------------------------------------------------------
# branch consistency
# --------------------------------------------------------------------------

def test_jansen_stays_on_one_assembly_branch(leg):
    assert C.branch_margin(leg, 720) > C.MIN_BRANCH_MARGIN


def test_branch_margin_is_zero_for_a_design_that_cannot_close():
    bad = dict(JansenLeg().L)
    bad["h"] = 500.0
    assert C.branch_margin(JansenLeg(bad, branches=JANSEN_BRANCH), 360) == 0.0


def test_branch_margin_is_scale_invariant(leg):
    """Same linkage, bigger: the margin is normalised, so it must not change."""
    big = JansenLeg({k: 2.0 * v for k, v in leg.L.items()}, branches=JANSEN_BRANCH)
    assert C.branch_margin(big, 360) == pytest.approx(C.branch_margin(leg, 360), rel=1e-9)


# --------------------------------------------------------------------------
# the combined report
# --------------------------------------------------------------------------

def test_jansen_passes_every_check(leg):
    r = C.check(leg, n=720)
    assert r["assembles"] and r["ok"]
    assert r["passes_angle"] and r["passes_amplification"] and r["passes_branch"]


def test_check_fails_cleanly_on_an_unassemblable_design():
    bad = dict(JansenLeg().L)
    bad["h"] = 500.0
    r = C.check(JansenLeg(bad, branches=JANSEN_BRANCH), n=180)
    assert not r["assembles"] and not r["ok"]
    assert np.isnan(r["min_transmission_angle"])
