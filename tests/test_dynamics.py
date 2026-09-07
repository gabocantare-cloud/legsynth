import numpy as np
import pytest

from legsynth.kinematics import JansenLeg
from legsynth import dynamics as D

JANSEN_BRANCH = (-1, -1, 1, -1, 1)
GROUND_JOINTS = ("O", "G_bd", "G_c")


@pytest.fixture(scope="module")
def leg():
    return JansenLeg(branches=JANSEN_BRANCH)


@pytest.fixture(scope="module")
def sol(leg):
    return D.solve_statics(leg, n=720)


def _external_totals(leg, sol, grf=D.GROUND_REACTION):
    """Total external force and moment on the whole leg, ground pins excluded."""
    pts = {k: v * D.MM for k, v in sol["pts"].items()}
    n = sol["theta"].size
    F = np.zeros((n, 2))
    Mz = np.zeros(n)
    for bars in D.BODY_BARS.values():
        for key, u, v in bars:
            w = D.LINE_DENSITY * (leg.L[key] * D.MM) * D.G_ACCEL
            mid = 0.5 * (pts[u] + pts[v])
            F[:, 1] -= w
            Mz -= mid[:, 0] * w
    up = np.where(sol["stance"], grf, 0.0)
    F[:, 1] += up
    Mz += pts["F"][:, 0] * up
    return F, Mz


# --------------------------------------------------------------------------
# the leg as a whole must be in equilibrium
# --------------------------------------------------------------------------

def test_global_force_balance(leg, sol):
    """Gravity + ground push + the three ground-pin reactions must cancel."""
    idx = [D.JOINT_NAMES.index(j) for j in GROUND_JOINTS]
    pins = sol["reactions"][:, idx, :].sum(axis=1)
    ext, _ = _external_totals(leg, sol)
    assert np.allclose(pins + ext, 0.0, atol=1e-9)


def test_global_moment_balance(leg, sol):
    """Moments about the origin, including the crank torque, must cancel too."""
    pts = {k: v * D.MM for k, v in sol["pts"].items()}
    Mz = np.zeros(sol["theta"].size)
    for j in GROUND_JOINTS:
        i = D.JOINT_NAMES.index(j)
        p = pts[dict((n_, pin) for n_, pin, _, _ in D.JOINTS)[j]]
        R = sol["reactions"][:, i, :]
        Mz += p[:, 0] * R[:, 1] - p[:, 1] * R[:, 0]
    _, ext_M = _external_totals(leg, sol)
    assert np.allclose(Mz + ext_M + sol["torque"], 0.0, atol=1e-9)


def test_virtual_work_agrees_with_the_solve(leg, sol):
    """Independent check: motor power must equal the power going into loads.

    Nothing in solve_statics enforces this, so it catches sign and moment-arm
    errors that per-body balance alone cannot.
    """
    assert D.power_residual(leg, sol) < 1e-3


def test_virtual_work_residual_is_only_discretisation(leg):
    """Refining the crank sample must shrink the residual, ~ second order."""
    coarse = D.power_residual(leg, D.solve_statics(leg, n=360))
    fine = D.power_residual(leg, D.solve_statics(leg, n=1440))
    assert fine < coarse / 8.0


# --------------------------------------------------------------------------
# the forces must respond to load the way statics says they should
# --------------------------------------------------------------------------

def test_no_load_means_no_force(leg):
    """Weightless bars and no ground contact: nothing to react, nothing to drive."""
    sol = D.solve_statics(leg, n=180, grf=0.0, line_density=0.0)
    assert np.allclose(sol["forces"], 0.0, atol=1e-12)
    assert np.allclose(sol["torque"], 0.0, atol=1e-12)


def test_forces_scale_linearly_with_the_ground_reaction(leg):
    """Statics is linear in the applied load once the geometry is fixed."""
    a = D.solve_statics(leg, n=180, grf=20.0, line_density=0.0)
    b = D.solve_statics(leg, n=180, grf=60.0, line_density=0.0)
    assert np.allclose(b["forces"], 3.0 * a["forces"], rtol=1e-9, atol=1e-12)
    assert np.allclose(b["torque"], 3.0 * a["torque"], rtol=1e-9, atol=1e-12)


def test_swing_phase_carries_only_the_legs_own_weight(leg, sol):
    """Off the ground the pins should be far more lightly loaded than on it."""
    f = np.nanmax(sol["forces"], axis=1)
    assert np.nanmean(f[sol["stance"]]) > 3.0 * np.nanmean(f[~sol["stance"]])


def test_the_mechanism_is_never_singular_on_the_baseline(sol):
    """Jansen's own design stays well away from a locked-up pose."""
    assert sol["feasible"]
    assert np.nanmax(sol["cond"]) < 1e5


# --------------------------------------------------------------------------
# model bookkeeping
# --------------------------------------------------------------------------

def test_ten_joints_and_eleven_bars():
    """The body decomposition must account for every bar exactly once."""
    assert len(D.JOINTS) == 10
    bars = [b[0] for bars in D.BODY_BARS.values() for b in bars]
    assert sorted(bars) == sorted("abcdefghijklm".replace("a", "").replace("l", ""))
    assert len(bars) == len(set(bars)) == 11


def test_grubler_gives_one_degree_of_freedom():
    """8 links (7 moving + ground), 10 revolute joints -> DOF 1."""
    n_links = len(D.BODIES) + 1
    assert 3 * (n_links - 1) - 2 * len(D.JOINTS) == 1


def test_every_body_is_held_by_at_least_two_joints():
    """A body on one pin would spin freely and make the system singular."""
    for body in D.BODIES:
        held = [j for j in D.JOINTS if body in (j[2], j[3])]
        assert len(held) >= 2, f"{body} is under-constrained"


def test_unassemblable_design_gives_nan_not_a_crash():
    bad = dict(JansenLeg().L)
    bad["h"] = 500.0
    sol = D.solve_statics(JansenLeg(bad, branches=JANSEN_BRANCH), n=180)
    assert not sol["feasible"]
    assert np.isnan(sol["forces"]).all()
