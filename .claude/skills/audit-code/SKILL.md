---
name: audit-code
description: Read legsynth's physics and search modules for defects the test suite does not catch — a parameter threaded through one path and silently defaulted on another, a metric that is algebraically degenerate, a statistic computed on too small a sample, a comparison between two things normalised differently. Use when auditing legsynth/*.py or scripts/*.py.
---

# Auditing the code

The suite passes and `ruff` is clean. That is the starting condition, not a result. Look
for the class of defect that produces **plausible numbers rather than a crash**, because
that is the only class that survives a green suite and reaches a document.

## The five patterns that have actually bitten this repo

**1. A parameter that reaches one code path and is defaulted on another.**
`optimize.describe` once passed `band` to the gait metrics and the transmission angles
but not to `dynamics.solve_statics`, which uses it to decide which samples carry the
ground reaction. Every design was then scored with its gait under one stance definition
and its wear under another, and the result was a plausible front. Trace every threaded
parameter — `band`, `n`, `wear_key`, `min_angle` — from caller to every leaf that
consumes it, and look hardest at leaves that take it as a keyword with a default.

**2. A ratio whose numerator and denominator were measured differently.** Sample count,
stance band, wear definition. Both objectives here are ratios to Jansen, so this is the
repo's structural weak point.

**3. A metric that is not independent of another.** Reduce each formula in `metrics.py`
algebraically before believing it measures something new. If a metric collapses to a
constant multiple of another quantity, every claim resting on it is really a claim about
that other quantity, and the docs have to say so.

**4. A statistic estimated from too few samples and then used as a precision
instrument.** `scripts/robustness.py:spread()` is max-minus-min over three campaigns.
That is a legitimate order-of-magnitude statement and an illegitimate denominator. Find
every place a spread, a threshold or a verdict is computed, and check the sample count
behind it against the size of the difference it is being asked to resolve.

**5. A default argument that is a trap.** `JansenLeg()` with no `branches` assembles and
traces the wrong curve. Every caller passes `JANSEN_BRANCH` today, so nothing is wrong —
but a defect prevented only by every caller remembering is a defect waiting.

## Also check

- **Dead or unreachable branches.** `wear.wear_per_cycle` computes `mean_force` twice
  and the first computation cannot survive the second. Harmless, but it means nobody
  re-read that block after editing it.
- **NaN handling.** The convention is that an unassemblable design returns NaN rather
  than raising. Check that NaN actually propagates to the *total* rather than being
  swallowed by an `nanmean` or `nansum` somewhere in the middle.
- **Asymmetric masks.** `dynamics.power_residual` drops samples around touchdown with
  `edge |= roll(edge,-1) | roll(edge,1) | roll(edge,2)` — one sample on one side, two on
  the other. Decide whether that is deliberate.
- **Sample counts that differ between a function's default and its caller.**
  `constraints.transmission_angles` defaults to `n=720`, `constraints.check` calls it at
  `n=360`, `min_transmission_angle` defaults to 720. Same name, different answers.
- **Keyword arguments dropped at a call site.** `constraints.check` calls
  `transmission_angles(leg, n)` without `band`. Ask which callers vary the band.

## How to establish a finding

Do not report a defect from reading alone. Write the two-line script that exhibits it,
run it, and put the output in the finding. If it cannot be exhibited, it is a
code-quality note rather than a defect, and the finding must say which it is.

The independent check that matters in `dynamics.py` is `power_residual`: virtual work is
not enforced by the solver, so agreement is real evidence rather than a tautology. If
you touch that module, the residual at `n=1440` is the number to watch.
