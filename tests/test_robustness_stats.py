"""The two statistics `scripts/robustness.py` prints a verdict from.

Neither is a physical property, which is exactly why they need pinning: they
are the arithmetic that turns `robustness.N_CAMPAIGNS` campaigns into two
sentences in `docs/RESULTS.md` section 7, and both have already been wrong once.

  * The seeds verdict was decided on the *range* of the unconstrained
    hypervolumes. The range of n samples grows with n, so that verdict got
    stronger the more campaigns you ran - a decision rule that rewards
    sampling. It has to be the standard deviation.
  * The objective study's 95% interval was `mean +/- 1.96 * stderr` on ten
    paired differences. With the sd estimated from the same n numbers the
    multiplier is Student's t, and the normal one reports an interval about 13%
    too narrow - in the direction that flatters the null this section argues.

A third test pins `N_CAMPAIGNS`, the count the documents quote, to the number of
campaigns the studies actually request. It was a literal 26 while `SEED_TRIPLES`
held ten, and going to twenty made it a literal 46 in four documents at once -
exactly the staleness the repo's own ground rule warns about.

Every test here stubs `campaign`, so nothing runs an optimization.
"""
import os
import sys

import numpy as np
import pytest
from scipy import stats

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))
import robustness as R                                   # noqa: E402

CFG = dict(pop=4, gens=1, n_refine=60, workers=None)


def fake_campaigns(monkeypatch, hv, gait):
    """Stub `campaign` with canned per-(seeds, wear_key) front summaries."""
    def stub(label, seeds, pop, gens, n_refine, min_angle=None,
             band=R.M.DEFAULT_BAND, wear_key="wear", workers=None):
        key = (tuple(seeds), wear_key, min_angle)
        return dict(label=label, seeds=list(seeds), hypervolume=hv(key),
                    best_gait=gait(key), best_wear=1.0, n_front=1,
                    n_dominating=1, runtime_s=0.0)
    monkeypatch.setattr(R, "campaign", stub)


def test_the_seeds_verdict_is_decided_on_the_sd_not_the_range(monkeypatch):
    """`seed_verdict` must be handed `spread()["sd"]`.

    The range is still recorded and printed beside it, so a test that only read
    the JSON could not tell which one the verdict came from. Intercept the call.
    """
    # Generated from SEED_TRIPLES rather than written out, so raising the
    # triple count does not silently turn this test into a KeyError. The values
    # only have to be spread unevenly enough that sd and range disagree.
    spread_pattern = (0.060, 0.064, 0.068, 0.052, 0.066,
                      0.051, 0.067, 0.058, 0.061, 0.059)
    values = {t: spread_pattern[i % len(spread_pattern)] + 0.0001 * i
              for i, t in enumerate(R.SEED_TRIPLES)}
    fake_campaigns(monkeypatch,
                   hv=lambda k: values[k[0]] - (0.002 if k[2] else 0.0),
                   gait=lambda k: 0.70)

    seen = []
    real = R.seed_verdict
    monkeypatch.setattr(R, "seed_verdict",
                        lambda noise, gap: (seen.append(noise), real(noise, gap))[1])

    out = R.study_seeds(CFG, {})
    hv = [values[t] for t in R.SEED_TRIPLES]
    sd, rng = float(np.std(hv, ddof=1)), float(max(hv) - min(hv))

    assert seen == [pytest.approx(sd)], (
        "the seeds verdict was decided on the range again; the range of n "
        "samples grows with n, so that rule changes answer with sample size")
    assert out["sd_over_gap"] == pytest.approx(sd / 0.002)
    assert out["range_over_gap"] == pytest.approx(rng / 0.002)
    assert out["verdict_statistic"] == "sd"


def test_the_objective_interval_uses_student_t(monkeypatch):
    """Paired differences with the sd estimated from the same n: t, not 1.96."""
    offsets = {t: 0.01 * (i % 3 - 1) for i, t in enumerate(R.SEED_TRIPLES)}
    fake_campaigns(
        monkeypatch, hv=lambda k: 0.06,
        gait=lambda k: 0.70 + (offsets[tuple(k[0])] if k[1] == "wear_integrated"
                               else 0.0))

    out = R.study_objective(CFG, {})
    d = np.array([p["delta"] for p in out["pairs"]], float)
    n = len(d)
    stderr = d.std(ddof=1) / np.sqrt(n)
    t = stats.t.ppf(0.975, n - 1)

    assert out["ci95_dist"] == "t"
    assert out["ci95_df"] == n - 1
    assert out["ci95_multiplier"] == pytest.approx(t)
    assert out["ci95"][0] == pytest.approx(d.mean() - t * stderr)
    assert out["ci95"][1] == pytest.approx(d.mean() + t * stderr)
    assert out["p_value"] == pytest.approx(stats.ttest_1samp(d, 0.0).pvalue)
    # and the normal multiplier really is the narrower, more flattering one
    assert t > 1.96


def test_the_campaign_count_matches_what_the_studies_actually_request(
        monkeypatch):
    """`N_CAMPAIGNS` is what the documents quote; this is what a run costs.

    The four studies share campaigns through `cached`, so the cost of a full run
    is the number of distinct cache keys, not the number of `campaign()` calls.
    `N_CAMPAIGNS` states that as arithmetic over `SEED_TRIPLES`, `THRESHOLDS`
    and `BANDS`; this checks the arithmetic against the studies themselves, so
    the count in `README.md` cannot go stale the way the literal 26 did.
    """
    fake_campaigns(monkeypatch, hv=lambda k: 0.06, gait=lambda k: 0.70)

    cache = {}
    for name in R.STUDIES:
        R.STUDIES[name](CFG, cache)

    assert len(cache) == R.N_CAMPAIGNS, (
        f"a full run requests {len(cache)} distinct campaigns but "
        f"N_CAMPAIGNS says {R.N_CAMPAIGNS}; the documents quote N_CAMPAIGNS")
