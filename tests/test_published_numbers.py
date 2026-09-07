"""Pin the numbers that appear in README.md and docs/RESULTS.md.

Every other test file checks a property you can reason about physically. This
one checks something duller and just as necessary: that the specific figures
quoted in the documents are still what the code produces, at the sample count
the documents say they were produced at.

Two failure modes it exists to catch.

**Drift.** Someone changes a default, the baseline shifts by 3%, the tests still
pass because they all assert inequalities, and the README quietly becomes wrong.

**Mixed sample counts.** The published tables used to quote step length at two
different crank sample counts in two different documents (43.41 mm and 43.49 mm)
because two scripts disagreed about how finely to sample. Neither was wrong;
the pair was just indefensible. `metrics.N_PUBLISHED` is now the single answer
and this file is what holds the documents to it.

If one of these fails, do not adjust the number here until you know why it
moved. If the physics changed, the documents change too.
"""
import numpy as np
import pytest

from legsynth import metrics as M, optimize as O
from legsynth.kinematics import JansenLeg

JANSEN_BRANCH = (-1, -1, 1, -1, 1)

#: The Jansen baseline row, exactly as printed in README.md and RESULTS.md §1.
#: Tolerances are the last quoted digit, not a generous band.
PUBLISHED_BASELINE = dict(
    step_length=(43.41, 0.005),        # mm
    ground_clearance=(22.23, 0.005),   # mm
    stance_flatness=(0.0011, 0.00005),
    velocity_ripple=(0.0920, 0.00005),
    duty_factor=(0.312, 0.0005),
)

#: Foot path envelope, quoted in both documents.
PUBLISHED_PATH = dict(width=(67.91, 0.005), height=(22.46, 0.005))


@pytest.fixture(scope="module")
def path():
    return JansenLeg(branches=JANSEN_BRANCH).foot_path(M.N_PUBLISHED)


def test_the_published_sample_count_is_what_the_documents_say():
    """1440. Changing it means regenerating every table, not editing this line."""
    assert M.N_PUBLISHED == 1440


def test_the_baseline_row_still_reproduces(path):
    got = M.gait_metrics(path)
    for key, (want, tol) in PUBLISHED_BASELINE.items():
        assert got[key] == pytest.approx(want, abs=tol), (
            f"{key} moved: README says {want}, code now gives {got[key]!r}")


def test_the_foot_path_envelope_still_reproduces(path):
    assert np.ptp(path[:, 0]) == pytest.approx(PUBLISHED_PATH["width"][0],
                                               abs=PUBLISHED_PATH["width"][1])
    assert M.path_height(path) == pytest.approx(PUBLISHED_PATH["height"][0],
                                                abs=PUBLISHED_PATH["height"][1])


def test_the_papers_clearance_exceeds_our_entire_path_height(path):
    """The one disagreement that cannot be a definition problem.

    25.7 mm of ground clearance does not fit inside a 22.46 mm tall foot path at
    any stance threshold whatsoever. This is the sentence in the README that a
    reviewer is most likely to check, so it gets a test.
    """
    assert M.PAPER_TABLE4["ground_clearance"] > M.path_height(path)


def test_step_length_is_quoted_at_one_sample_count_only():
    """The inconsistency this file was written to prevent, stated as a test.

    Step length reads 43.41 mm at 1440 samples and 43.49 mm at 3600. Both are
    correct measurements of the same linkage; quoting one in the README and the
    other in METRIC_DEFINITIONS.md is what was wrong. The gap is real and this
    pins its size, so that if anything ever makes the metric sample-independent
    the docs can be simplified on purpose rather than by accident.
    """
    leg = JansenLeg(branches=JANSEN_BRANCH)
    at_published = M.step_length(leg.foot_path(M.N_PUBLISHED))
    at_3600 = M.step_length(leg.foot_path(3600))
    assert at_published != pytest.approx(at_3600, abs=1e-3)
    assert abs(at_published - at_3600) < 0.2, \
        "the two are within a fifth of a millimetre; if that grows, investigate"


# --------------------------------------------------------------------------
# the objective is anchored where the documents say it is
# --------------------------------------------------------------------------

def test_jansen_sits_at_exactly_one_one_at_the_published_sample_count():
    """Every percentage in the README is measured from this point.

    `refine` divides designs scored at N_PUBLISHED by a baseline that must also
    be measured at N_PUBLISHED. Feeding it the coarse search baseline instead
    shifts every published ratio by about a percent - small enough to look like
    a result, which is exactly what makes it dangerous.
    """
    base = O.jansen_baseline(n=M.N_PUBLISHED)
    x = O.vector_from_leg(JansenLeg(branches=JANSEN_BRANCH))
    f, _, _ = O.evaluate(x, base, n=M.N_PUBLISHED)
    assert f[0] == pytest.approx(1.0, rel=1e-12)
    assert f[1] == pytest.approx(1.0, rel=1e-12)


def test_a_mismatched_baseline_visibly_moves_the_ratio():
    """The trap, measured. This is why `refine` takes its own baseline.

    Scoring Jansen at the published sample count but normalising by the coarse
    search baseline should give something clearly different from 1.0. If this
    ever stops being true the two sample counts have converged and the two
    baselines could be merged - but until then, they cannot.
    """
    coarse = O.jansen_baseline(n=O.N_EVAL)
    x = O.vector_from_leg(JansenLeg())
    f, _, _ = O.evaluate(x, coarse, n=M.N_PUBLISHED)
    assert abs(f[0] - 1.0) > 1e-3, \
        "mismatched baselines must not silently look like a correct anchor"
