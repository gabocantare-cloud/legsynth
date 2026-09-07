import numpy as np
import pytest

from legsynth.kinematics import JansenLeg
from legsynth import metrics as M

JANSEN_BRANCH = (-1, -1, 1, -1, 1)


@pytest.fixture(scope="module")
def path():
    """The Jansen foot path at the one sample count every published table uses.

    Not an arbitrary number. Stance is the longest unbroken arc inside the band,
    so its measured extent is quantised by the sample spacing and step length
    reads 43.41 mm here against 43.49 mm at 3600. Testing at the published count
    is what keeps the tests and the documents talking about the same thing.
    """
    return JansenLeg(branches=JANSEN_BRANCH).foot_path(M.N_PUBLISHED)


# --------------------------------------------------------------------------
# the stance rule itself
# --------------------------------------------------------------------------

def test_longest_run_wraps_around_the_crank_revolution():
    """Stance straddling theta = 0 is one phase, not two."""
    m = np.array([1, 1, 0, 0, 1, 0, 0, 1], bool)  # run of 3 across the wrap
    got = M.longest_run(m)
    assert np.array_equal(got, np.array([1, 1, 0, 0, 0, 0, 0, 1], bool))


def test_longest_run_handles_all_and_nothing():
    assert M.longest_run(np.ones(5, bool)).all()
    assert not M.longest_run(np.zeros(5, bool)).any()


def test_stance_is_a_single_contiguous_arc(path):
    m = M.stance_mask(path)
    assert m.any()
    starts = np.diff(np.concatenate([m[-1:], m]).astype(int)) == 1
    assert starts.sum() == 1, "stance mask must be one unbroken arc"


def test_stance_is_the_bottom_of_the_path(path):
    """Every stance sample sits below every swing sample's peak, near the floor."""
    y = path[:, 1]
    m = M.stance_mask(path)
    assert y[m].max() <= M.ground_line(path) + 1e-9
    assert y[~m].max() > y[m].max()


# --------------------------------------------------------------------------
# physical properties the numbers must obey
# --------------------------------------------------------------------------

def test_metrics_are_physically_bounded(path):
    g = M.gait_metrics(path)
    assert 0.0 < g["duty_factor"] < 1.0
    assert 0.0 < g["step_length"] <= np.ptp(path[:, 0]) + 1e-9
    assert 0.0 < g["ground_clearance"] <= M.path_height(path) + 1e-9
    assert g["stance_flatness"] >= 0.0
    assert g["velocity_ripple"] >= 0.0


def test_step_and_duty_grow_with_the_band(path):
    """A looser definition of 'on the ground' can only include more of the path."""
    bands = [0.005, 0.01, 0.02, 0.05, 0.10]
    steps = [M.step_length(path, b) for b in bands]
    duties = [M.duty_factor(path, b) for b in bands]
    assert np.all(np.diff(steps) >= -1e-9)
    assert np.all(np.diff(duties) >= -1e-9)


def test_clearance_shrinks_with_the_band(path):
    """Raising the ground line lowers the obstacle the foot can clear."""
    assert M.ground_clearance(path, 0.02) < M.ground_clearance(path, 0.005)


def test_metrics_are_scale_invariant_where_they_should_be(path):
    """Build the same leg twice as big: lengths double, ratios do not.

    This is the whole reason the band is a fraction of path height rather than
    a fixed number of millimetres.
    """
    big = M.gait_metrics(2.0 * path)
    small = M.gait_metrics(path)
    assert big["step_length"] == pytest.approx(2 * small["step_length"], rel=1e-12)
    assert big["ground_clearance"] == pytest.approx(
        2 * small["ground_clearance"], rel=1e-12)
    assert big["duty_factor"] == pytest.approx(small["duty_factor"], rel=1e-12)
    assert big["stance_flatness"] == pytest.approx(small["stance_flatness"], rel=1e-12)
    assert big["velocity_ripple"] == pytest.approx(small["velocity_ripple"], rel=1e-12)


def test_metrics_converge_with_sampling():
    """The numbers must be properties of the linkage, not of the sample count."""
    leg = JansenLeg(branches=JANSEN_BRANCH)
    coarse = M.gait_metrics(leg.foot_path(720))
    fine = M.gait_metrics(leg.foot_path(7200))
    for k in ("step_length", "ground_clearance", "duty_factor"):
        assert fine[k] == pytest.approx(coarse[k], rel=0.02)
    for k in ("stance_flatness", "velocity_ripple"):
        assert fine[k] == pytest.approx(coarse[k], rel=0.05)


def test_circle_path_has_the_expected_geometry():
    """A foot that traces a circle: known answers, worked out by hand.

    With a 1% band on a unit circle the ground line sits at y = -1 + 0.02,
    which the circle crosses at x = +/- sqrt(1 - 0.98**2) = 0.199. So the step
    length is twice that, the clearance is 2 - 0.02, and the foot speed is
    constant so the ripple is zero. Step length and duty factor land a hair
    under the exact values because the crossing falls between samples.
    """
    t = np.linspace(0, 2 * np.pi, 20000, endpoint=False)
    circle = np.stack([np.cos(t), np.sin(t)], axis=-1)
    g = M.gait_metrics(circle)
    half = np.sqrt(1 - 0.98 ** 2)
    assert g["step_length"] == pytest.approx(2 * half, rel=5e-3)
    assert g["ground_clearance"] == pytest.approx(1.98, rel=1e-6)
    assert g["velocity_ripple"] == pytest.approx(0.0, abs=1e-9)
    assert g["duty_factor"] == pytest.approx(np.arcsin(half) / np.pi, rel=1e-3)


# --------------------------------------------------------------------------
# infeasible designs and bad input
# --------------------------------------------------------------------------

def test_unassemblable_design_gives_nan_not_a_crash():
    bad = dict(JansenLeg().L)
    bad["h"] = 500.0  # a foot link far too long to close the loop
    g = M.gait_metrics(JansenLeg(bad, branches=JANSEN_BRANCH).foot_path(360))
    assert all(np.isnan(v) for v in g.values())


def test_bad_band_and_shape_are_rejected(path):
    with pytest.raises(ValueError):
        M.ground_line(path, band=1.5)
    with pytest.raises(ValueError):
        M.ground_line(path, tol=-1.0)
    with pytest.raises(ValueError):
        M.step_length(np.zeros((4, 3)))


# --------------------------------------------------------------------------
# the published disagreement with the paper
# --------------------------------------------------------------------------

def test_no_single_band_reproduces_the_papers_table(path):
    """The core finding of docs/METRIC_DEFINITIONS.md, pinned as a test.

    Each of the paper's Jansen numbers implies a different stance band, and the
    implied bands differ by more than an order of magnitude. If this test ever
    fails, the claim in the docs has stopped being true and must be rewritten.
    """
    needed = {k: M.band_matching(path, k, v) for k, v in M.PAPER_TABLE4.items()}
    assert np.isnan(needed["ground_clearance"]), \
        "paper clearance should be unreachable at any band"
    finite = [b for b in needed.values() if np.isfinite(b)]
    assert len(finite) == 4
    assert max(finite) / min(finite) > 10.0


def test_step_length_and_ripple_agree_with_the_paper_at_our_band(path):
    """The two metrics we do reproduce, held to the tolerance we claim."""
    g = M.gait_metrics(path)
    assert g["step_length"] == pytest.approx(M.PAPER_TABLE4["step_length"], rel=0.01)
    assert g["velocity_ripple"] == pytest.approx(
        M.PAPER_TABLE4["velocity_ripple"], rel=0.05)


def test_duty_factor_disagrees_with_the_paper(path):
    """Documented disagreement. Do not 'fix' this by tuning the band."""
    assert M.duty_factor(path) > 1.4 * M.PAPER_TABLE4["duty_factor"]
