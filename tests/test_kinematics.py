import numpy as np
import pytest
from legsynth.kinematics import JansenLeg, HOLY, circ

JANSEN_BRANCH = (-1, -1, 1, -1, 1)


def test_circ_known_intersection():
    p = circ([0.0, 0.0], 1.0, [1.0, 0.0], 1.0, 1)
    assert np.allclose(p, [0.5, np.sqrt(3) / 2])


def test_circ_returns_nan_when_circles_do_not_meet():
    p = circ([0.0, 0.0], 1.0, [10.0, 0.0], 1.0, 1)
    assert np.all(np.isnan(p))


def test_jansen_assembles_through_full_revolution():
    assert JansenLeg(branches=JANSEN_BRANCH).assembles()


def test_link_lengths_are_respected_at_every_pose():
    leg = JansenLeg(branches=JANSEN_BRANCH)
    j = leg.solve(np.linspace(0, 2 * np.pi, 200, endpoint=False))
    L = leg.L
    bars = [("O", "J1", "m"), ("J1", "J2", "j"), ("G", "J2", "b"),
            ("J2", "J3", "e"), ("G", "J3", "d"), ("J1", "J4", "k"),
            ("G", "J4", "c"), ("J3", "J5", "f"), ("J4", "J5", "g"),
            ("J4", "F", "i"), ("J5", "F", "h")]
    for u, v, key in bars:
        d = np.linalg.norm(j[u] - j[v], axis=-1)
        assert np.allclose(d, L[key], atol=1e-9), f"link {key} not rigid"


def test_foot_path_reproduces_jansen_signature():
    """Flat stance stroke, single closed loop, well below the frame."""
    P = JansenLeg(branches=JANSEN_BRANCH).foot_path(3600)
    x, y = P[:, 0], P[:, 1]
    assert y.max() < -60, "foot should hang below the frame pivots"
    stance = y <= y.min() + 0.5
    assert stance.sum() / len(y) > 0.30, "expected a long flat stance phase"
    assert np.ptp(x[stance]) > 45, "stance stroke too short"
