import numpy as np
import pytest

from legsynth.kinematics import HOLY, DESIGN_KEYS
from legsynth import optimize as O

JANSEN = np.array([HOLY[k] for k in DESIGN_KEYS], float)


@pytest.fixture(scope="module")
def baseline():
    return O.jansen_baseline(n=360)


# --------------------------------------------------------------------------
# the objective must be anchored on the baseline
# --------------------------------------------------------------------------

def test_jansen_scores_exactly_one_on_both_objectives(baseline):
    """Everything is a ratio to Jansen, so Jansen must sit at (1, 1).

    If this drifts, every percentage quoted in the README is measured from the
    wrong place.
    """
    f, g, _ = O.evaluate(JANSEN, baseline, n=360)
    assert f[0] == pytest.approx(1.0, rel=1e-9)
    assert f[1] == pytest.approx(1.0, rel=1e-9)


def test_jansen_satisfies_the_papers_own_constraints(baseline):
    """The floors are 0.85x Jansen, so Jansen clears each by exactly 0.15."""
    _, g, _ = O.evaluate(JANSEN, baseline, n=360)
    assert np.all(g <= 0)
    assert g[:3] == pytest.approx([-0.15, -0.15, -0.15], abs=1e-9)


def test_jansen_also_passes_our_added_constraint(baseline):
    """Jansen's loaded transmission angle is 42.7 deg, so the 40 deg rule holds.

    The whole-cycle version would fail here. That the constrained problem still
    admits Jansen is the evidence that our constraint is not just rejecting
    everything.
    """
    _, g, raw = O.evaluate(JANSEN, baseline, n=360, min_angle=40.0)
    assert len(g) == 5
    assert np.all(g <= 0)
    assert raw["min_transmission_angle"] > 40.0
    assert raw["min_transmission_angle_cycle"] < 40.0


def test_unassemblable_design_is_penalised_not_crashed(baseline):
    x = JANSEN.copy()
    x[DESIGN_KEYS.index("h")] = 500.0
    f, g, raw = O.evaluate(x, baseline, n=180)
    assert not raw["assembles"]
    assert np.all(f >= O.PENALTY) and np.all(g >= O.PENALTY)


# --------------------------------------------------------------------------
# search plumbing
# --------------------------------------------------------------------------

def test_bounds_are_thirty_percent_either_side():
    lo, hi = O.bounds()
    assert lo == pytest.approx(0.7 * JANSEN)
    assert hi == pytest.approx(1.3 * JANSEN)


def test_round_trip_between_vector_and_leg():
    leg = O.leg_from_vector(JANSEN)
    assert O.vector_from_leg(leg) == pytest.approx(JANSEN)
    for k in "alm":
        assert leg.L[k] == HOLY[k], "non-design lengths must not move"


def test_seeded_population_starts_at_jansen_and_stays_in_bounds():
    lo, hi = O.bounds()
    X = O.seeded_population(50, seed=3)
    assert X.shape == (50, len(DESIGN_KEYS))
    assert X[0] == pytest.approx(JANSEN), "first individual is the baseline"
    assert np.all(X >= lo - 1e-9) and np.all(X <= hi + 1e-9)


def test_seeded_population_beats_uniform_sampling(baseline):
    """The documented reason the search is seeded at all.

    Uniform sampling of the box finds essentially no feasible designs; seeding
    near Jansen finds some. If this ever stops being true the seeding can go.
    """
    lo, hi = O.bounds()
    rng = np.random.default_rng(0)
    uniform = rng.uniform(lo, hi, size=(120, len(lo)))
    seeded = O.seeded_population(120, seed=0)

    def n_feasible(X):
        return sum(bool(np.all(O.evaluate(x, baseline, n=180)[1] <= 0)) for x in X)

    assert n_feasible(uniform) == 0
    assert n_feasible(seeded) > 0


# --------------------------------------------------------------------------
# Pareto bookkeeping
# --------------------------------------------------------------------------

def test_nondominated_on_a_hand_worked_case():
    F = np.array([[1.0, 1.0],    # dominated by [0.5, 0.5]
                  [0.5, 0.5],    # on the front
                  [0.2, 0.9],    # on the front, better on axis 0
                  [0.9, 0.2],    # on the front, better on axis 1
                  [0.6, 0.6]])   # dominated
    assert list(O.nondominated(F)) == [False, True, True, True, False]


def test_nondominated_keeps_everything_when_nothing_dominates():
    F = np.array([[0.1, 0.9], [0.5, 0.5], [0.9, 0.1]])
    assert O.nondominated(F).all()


def test_merge_returns_a_sorted_joint_front():
    a = dict(X=np.array([[1.0] * 10, [2.0] * 10]), F=np.array([[0.9, 0.2], [1.0, 1.0]]))
    b = dict(X=np.array([[3.0] * 10]), F=np.array([[0.2, 0.9]]))
    X, F = O.merge([a, b])
    assert len(F) == 2, "the (1.0, 1.0) design is dominated and must be dropped"
    assert F[0, 0] < F[1, 0], "front is returned sorted by the first objective"


# --------------------------------------------------------------------------
# one very small end-to-end search
# --------------------------------------------------------------------------

@pytest.mark.slow
def test_a_short_search_returns_feasible_improving_designs(baseline):
    """End-to-end smoke test of the search machinery.

    A 24 x 8 search is far too small to settle whether Jansen is dominated -
    that claim comes from the full 100 x 80 x 3 campaign in docs/RESULTS.md.
    All this asserts is that the loop runs, respects the constraints, and moves
    in the right direction on at least one objective.
    """
    r = O.run(seed=0, pop=24, gens=8, baseline=baseline)
    assert len(r["F"]) > 0, "search should find at least one feasible design"
    assert np.all(r["G"] <= 1e-9), "returned designs must satisfy the constraints"
    assert np.any(r["F"] < 1.0), "expected improvement on at least one objective"


# --------------------------------------------------------------------------
# hypervolume — how two fronts get compared
# --------------------------------------------------------------------------

def test_hypervolume_on_a_hand_worked_case():
    """Two points, worked out by hand as a union of rectangles.

    With Jansen at (1, 1), each design covers the rectangle between itself and
    (1, 1). The design at (0.5, 0.5) covers 0.5 x 0.5 = 0.25. The design at
    (0.2, 0.8) covers 0.8 x 0.2 = 0.16. They overlap on x in [0.5, 1] and y in
    [0.8, 1], which is 0.5 x 0.2 = 0.10, and hypervolume is the *union*:

        0.25 + 0.16 - 0.10 = 0.31

    Subtracting the overlap is the whole content of the sweep - two designs
    that improve on the same region of the trade-off are not worth twice one.
    """
    assert O.hypervolume([[0.5, 0.5]]) == pytest.approx(0.25)
    assert O.hypervolume([[0.5, 0.5], [0.2, 0.8]]) == pytest.approx(0.31)


def test_hypervolume_ignores_designs_that_do_not_beat_jansen():
    """A design worse than Jansen on either axis has won no ground."""
    assert O.hypervolume([[1.5, 0.5]]) == 0.0
    assert O.hypervolume([[0.5, 1.5]]) == 0.0
    assert O.hypervolume(np.zeros((0, 2))) == 0.0
    assert O.hypervolume([[0.5, 0.5], [1.5, 0.1]]) == pytest.approx(0.25)


def test_hypervolume_rewards_a_wider_front():
    """Two fronts with the same best-on-each-axis, one spread and one not.

    This is the property that makes hypervolume the right summary: "best gait
    error" cannot tell these apart, and they are not the same front.
    """
    narrow = [[0.4, 0.9], [0.9, 0.4]]
    wide = [[0.4, 0.9], [0.6, 0.6], [0.9, 0.4]]
    assert O.hypervolume(wide) > O.hypervolume(narrow)


# --------------------------------------------------------------------------
# an empty campaign is an answer, not a crash
# --------------------------------------------------------------------------

def test_merge_survives_every_run_coming_back_empty():
    """Tighten the transmission-angle constraint far enough and nothing is
    feasible. That is the measurement, so it must not raise."""
    empty = dict(X=np.zeros((0, len(DESIGN_KEYS))), F=np.zeros((0, 2)))
    X, F = O.merge([empty, empty])
    assert X.shape == (0, len(DESIGN_KEYS)) and F.shape == (0, 2)
    assert O.refine(X, O.jansen_baseline(n=180)) == []
    assert O.hypervolume(F) == 0.0


# --------------------------------------------------------------------------
# the two knobs the robustness studies turn
# --------------------------------------------------------------------------

def test_the_stance_band_reaches_the_objective(baseline):
    """`band` has to travel all the way from `evaluate` down into the metrics.

    A wider band counts more of the crank turn as stance, so duty factor rises.
    If this ever stops being true the band argument has been dropped somewhere
    in the chain and the band study is silently measuring nothing.
    """
    x = JANSEN.copy()
    narrow = O.describe(O.leg_from_vector(x), n=360, band=0.005)
    wide = O.describe(O.leg_from_vector(x), n=360, band=0.02)
    assert wide["duty_factor"] > narrow["duty_factor"]
    assert wide["step_length"] > narrow["step_length"]


def test_jansen_is_still_the_anchor_under_the_integrated_wear_objective():
    """Swapping which wear number the objective minimises must not move Jansen.

    Both objectives are ratios to Jansen, so Jansen sits at (1, 1) whichever
    wear form is used. The 51% gap between the two forms lives in the absolute
    numbers, not in the normalised ones - which is exactly the thing the
    objective study is testing on the rest of the front.
    """
    base = O.jansen_baseline(n=360)
    for key in O.WEAR_KEYS:
        f, _, _ = O.evaluate(JANSEN, base, n=360, wear_key=key)
        assert f[1] == pytest.approx(1.0, rel=1e-9), key
    assert base["wear"] > 1.4 * base["wear_integrated"], \
        "the mean-force form should still be the larger of the two"


# --------------------------------------------------------------------------
# running a generation across processes must not change the answer
# --------------------------------------------------------------------------

@pytest.mark.slow
def test_parallel_evaluation_matches_serial_exactly(baseline):
    """The speed-up must be a wall-clock change only.

    Each design is evaluated independently and `pool.map` preserves order, so
    spreading a generation over processes cannot change a single number. If
    this ever fails, the parallel path has picked up state that the serial path
    does not have, and every result computed with `--workers` is suspect.
    """
    kw = dict(seed=0, pop=16, gens=4, baseline=baseline)
    serial = O.run(workers=1, **kw)
    parallel = O.run(workers=2, **kw)
    assert np.array_equal(serial["F"], parallel["F"])
    assert np.array_equal(serial["X"], parallel["X"])
