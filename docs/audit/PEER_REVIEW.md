# Peer review — fix-session scope (`21fd97d..945a37d`)

## Summary

The two substantive retractions are honestly made. Section 7.2 no longer says
the wear shortcut moves the optimum, retains the direction-neutral null caveat,
and the interview document preserves it. Section 7.3 deletes the 45° design
guideline. Those wording checks are **verified** from the current documents;
the campaign outcomes supporting them remain **inherited** from
`results/audit/objective_replication.json` and were not re-run.

| ID | Severity | Where | Finding |
|---|---|---|---|
| [PR1](#pr1) | S1 | §7.2 and `robustness.py` | The stated 95% CI uses a normal multiplier for ten paired observations. |
| [PR2](#pr2) | S2 | runtime documentation | The advertised study runtimes do not follow from the current 26-campaign program; the available timing sources also conflict. |
| [PR3](#pr3) | S2 | `robustness.py` | The new standard deviation is recorded but the seed verdict still compares the sample-size-dependent range. |
| [PR4](#pr4) | S2 | `reproduce.py`, `make_figures.py` | The threshold figure depends on audit-only data and is generated before `--with-studies` refreshes its production inputs. |
| [PR5](#pr5) | S3 | feasibility script and §5 | “2% jitter” is ambiguous: the implemented distribution is independent Gaussian jitter with σ = 2%, not bounded ±2%. |
| [PR6](#pr6) | S3 | `test_optimize.py` | The band-threading assertion relies on 10–20% bands, so it does not test the real study regime. |
| [PR7](#pr7) | S3 | `NEXT_SESSION.md` | The handoff hardcodes the verifier’s 40-claim count despite the repository’s rule against this drift pattern. |

## Confirmed corrections that need no new finding

- **Verified:** `constraints.check()` now accepts and passes `band`; its changed
  sample-count defaults do not alter an internal caller’s published result. All
  non-definition call sites in `legsynth/`, `scripts/`, and `tests/` either pass
  `n` explicitly or pass precomputed points, whose length determines the sample
  count. The changed defaults do make an unspecified `check()` call slower, but
  no optimizer call uses it.
- **Verified:** `verify_docs.py` marks R1–R7 as inherited and its 5e-5
  tolerances are tight enough for the quoted four-decimal results. A green
  verifier therefore establishes text/artifact agreement, not campaign validity.
- **Verified:** `pytest -q` passed 91 tests (outside the sandbox, which blocks
  pytest temporary files and Windows multiprocessing pipes); `ruff check .` and
  `verify_docs.py --slow` were clean. These are regression checks, not evidence
  for the campaign claims.

## Findings

### PR1 — the 95% confidence interval is too narrow {#pr1}

**Severity:** S1

**Where.** `scripts/robustness.py:274-279`; `docs/RESULTS.md:450`; also
`README.md:107`, `CLAUDE.md:131`, `docs/DEFENDING_THIS.md:96`, and
`docs/NEXT_SESSION.md:38,209`.

**Verified.** The code computes `mean ± 1.96 × stderr` at `n=10`. Independently
recomputing the statistics from the ten stored paired deltas gives mean
−0.00357166, sample sd 0.02306851, stderr 0.00729490, and Student’s
`t(0.975, 9) = 2.26215716`. The correct 95% t interval is
**[−0.02007388, +0.01293056]**, rather than the published normal interval
[−0.01786967, +0.01072635]. The two-sided paired t-test is `p = 0.63612178`.

**Inherited.** The ten deltas themselves came from
`results/audit/objective_replication.json`; their campaign outputs were not
re-run. This finding verifies the statistical transformation, not the campaigns.

**Fix.** Use `scipy.stats.t.ppf(0.975, n - 1)` in `study_objective`; update all
copies to **95% CI [−0.020, +0.013]** and, preferably, add `p = 0.64`. Register
the interval endpoints (or multiplier and `n`) as inherited verifier claims so
they cannot silently return to a z interval. The null conclusion remains intact.

### PR2 — runtime promises are unsupported by the current study program {#pr2}

**Severity:** S2

**Where.** `scripts/reproduce.py:37,83`; `README.md:29,234`; and
`docs/RESULTS.md:17`.

**Verified.** With an empty cache, a full `robustness.py` invocation makes **26
unique campaigns**, not the old small study: 10 unconstrained plus constrained
40° in `study_seeds` (11), 10 integrated-wear campaigns in `study_objective`
(21 total), 45°/50°/55° in `study_threshold` (24), and 0.5%/2% in
`study_band` (26). This follows directly from the cache keys at
`scripts/robustness.py:193-199,257-263,311-317,345-346`.

**Inherited.** No full campaign was run for this review. The available timing
records are themselves inconsistent: the handoff calls the 20-campaign audit
62 minutes, while its shipped JSON records `runtime_s = 3002.04` (50.03 minutes).
Neither record measures the current 26-campaign program. Consequently I cannot
verify a replacement wall-clock number.

**Fix.** Do not retain `~50 min`, `adds ~45 min`, or `~1 h`. On the next planned
full regeneration, time `robustness.py` and `reproduce.py --with-studies` on a
stated worker count, then update all five locations from that measurement. Until
then say “tens of minutes” rather than a false precision. The deterministic
campaign count should be documented beside the timing.

### PR3 — the range remains the decision statistic despite the new SD {#pr3}

**Severity:** S2

**Where.** `scripts/robustness.py:136-147,201-206`.

**Verified.** `spread()` correctly returns both a range and a sample standard
deviation, and its own docstring says to compare against the SD when sample
sizes differ. But `study_seeds()` assigns `noise_hv = noise["range"]` and sends
that range to `seed_verdict()`; the verdict and `margin` are therefore still
based on max-minus-min. This does not overturn the present §7.1 conclusion:
using the inherited SD 0.0052 still exceeds its 0.0020 gap. It does mean the
code did not complete the planned correction to the decision rule.

**Inherited.** The 0.0052 and 0.0020 numerical comparison is read from the
stored audit/robustness outputs, not regenerated.

**Fix.** Make the verdict’s comparator explicit and statistically consistent:
pass `noise["sd"]` to `seed_verdict()`, record `sd_over_gap` (and optionally
retain `range_over_gap` as descriptive context), and update the printed labels
and prose. Add a unit test proving that the verdict receives the SD rather than
the range.

### PR4 — the production reproduction path has an audit-data dependency and wrong order {#pr4}

**Severity:** S2

**Where.** `scripts/reproduce.py:52-63,86`; `scripts/make_figures.py:221-242`.

**Verified.** `reproduce.py --with-studies` runs `make_figures.py` in `STAGES`
before it appends `robustness.py` and `clearance_fit.py`. Separately,
`seed_spread_hypervolume()` preferentially reads
`results/audit/objective_replication.json`, which a normal reproduction does not
produce. Thus the threshold figure is not generated from the current
`robustness.py` output, even after `--with-studies`; it is generated from an
audit artifact whenever that artifact is present. This is a provenance boundary,
not merely a stale caption.

**Inherited.** The ten-triple band is valid only to the extent that the shipped
audit campaigns are valid; they were not re-run. The ordering/dependency defect
is established from code alone.

**Fix.** The clean solution is to run the full ten-triple seed study into
`results/robustness.json`, remove the audit preference, and run
`make_figures.py` after the studies; this needs one planned full study run, not
a rerun during this review. If compute is deferred, make the audit dependency an
explicit input/flag and state it in the reproduce command and figure caption;
do not present that path as a fully self-contained normal reproduction.

### PR5 — “2% jitter” does not identify the implemented distribution {#pr5}

**Severity:** S3

**Where.** `scripts/feasibility.py:58-72`; `docs/RESULTS.md:202-204` and its
downstream summaries.

**Verified.** Each of the ten lengths is drawn independently as
`base × (1 + Normal(0, 0.02))`, then clipped to the search box. Thus 2% is a
Gaussian standard deviation, with nonzero probability of perturbations exceeding
±2%; it is not a uniform or bounded ±2% perturbation. The present prose can
reasonably be read either way.

**Inherited.** The reported 2.8–5.8% feasibility range is read from the saved
experiment and was not re-run here.

**Fix.** Say “independent Gaussian relative jitter, σ = 2% per length (clipped
to the ±30% box)” wherever the experiment is summarized. If the intended claim
was bounded ±2%, change the sampler and regenerate the numbers instead.

### PR6 — the band-threading test validates only an extreme, non-study regime {#pr6}

**Severity:** S3

**Where.** `tests/test_optimize.py:244-260`.

**Verified.** At the study bands 0.5%, 1%, and 2%, `check(...)["min_transmission_angle"]`
is 42.72066° in each case. The new assertion therefore extends the test to 10%
and 20%, where it becomes 37.10502° and 28.64525°. That does show a passed band
can change a result, but it validates a physically irrelevant 20% stance window
rather than parameter forwarding in the actual robustness study range.

**Inherited.** None; this is a direct code calculation.

**Fix.** Replace the numeric-response surrogate with a forwarding test: wrap or
monkeypatch `constraints.transmission_angles`, call `check(..., band=0.01)`, and
assert it received `band=0.01`. Keep a separate physical-response test only if a
design whose shallow angle lies near a 0.5–2% stance boundary is deliberately
constructed.

### PR7 — the handoff repeats the count-staleness pattern {#pr7}

**Severity:** S3

**Where.** `docs/NEXT_SESSION.md:6-7,25-26`.

**Verified.** The file says the verifier is “green at 40 claims” twice. The
registry currently contains 40 `Claim(...)` entries, but adding a claim is the
normal maintenance action encouraged by the fix plan. This recreates the same
hardcoded-command-output problem that `CLAUDE.md` explicitly warns against.

**Inherited.** None; this is direct source inspection.

**Fix.** Change both occurrences to “`scripts/verify_docs.py --slow` is green”
and generalize the local rule from test counts to any count printed by a command.

## Disposition

No evidence found that the §7.2 or §7.3 retractions went too far. Their central
campaign evidence remains inherited, not independently verified; settling that
would require the prohibited 20-campaign rerun. The remaining work is to repair
the statistical presentation and the reproduction/provenance path without
strengthening the withdrawn claims.
