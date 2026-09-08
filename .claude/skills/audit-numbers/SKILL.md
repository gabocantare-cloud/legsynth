---
name: audit-numbers
description: Verify that every number published in legsynth's README, CLAUDE.md and docs/ still comes out of code that runs in this repo. Use when auditing published figures, checking a table against results/*.json, after changing any metric or solver, or before publishing. Runs scripts/verify_docs.py and adds the judgement the script cannot make.
---

# Auditing the published numbers

## The mechanical half

    python scripts/verify_docs.py             # every fast claim
    python scripts/verify_docs.py --slow      # include the campaign-scale claims
    python scripts/verify_docs.py --coverage  # numbers in docs that no claim covers

`verify_docs.py` holds a registry of claims. Each claim pins a quoted phrase in a
document to a value recomputed from `legsynth`, so it fails in two independent ways: the
document changed and the phrase no longer appears, or the phrase is still there and the
value no longer agrees. Both are reported.

A green run is necessary and nowhere near sufficient. The registry covers only what
somebody thought to register.

## The half the script cannot do

**Run `--coverage` and read the misses.** It lists numeric literals in the docs that no
claim touches. Most are fine — a paper's number quoted as the paper's, a rounded figure
in a sentence. Some are a published result nobody pinned. Those are the ones to chase.

**Check the sample count on everything.** `metrics.N_PUBLISHED = 1440` is meant to be
the single count behind every published table, and the failure mode is a number quoted
from a run at a different count. `duty_factor` and `step_length` both creep with the
count, because stance is measured as a whole number of samples. A table caption that
does not say its count is a finding.

**Check that a ratio's numerator and denominator were measured the same way.** This has
already gone wrong here once: designs scored at 1440 divided by a Jansen measured at 360
shifted every published ratio by about a percent. `optimize.refine` now takes its own
baseline. When you meet a new ratio, find out where its denominator came from.

**Check what a number is a ratio *of*.** Two campaigns each normalise against their own
Jansen, so both sit at (1, 1) legitimately — and their second-objective values are then
not comparable with each other, even though both get printed to three decimals in the
same table. RESULTS section 7.2 is the live example.

**Look for numbers that are algebraically forced.** A metric that is a fixed multiple of
another metric is not independent evidence, and quoting it as if it were is a finding
even when the arithmetic is right. Reduce each formula in `metrics.py` by hand before
treating its value as a measurement.

## Evidence rules

- `results/*.json` is a record of a run, not proof the run was right. Recompute anything
  that costs less than a minute.
- A number appearing in two documents should be generated once. If both were typed by
  hand, say so — that is how three documents went stale at once before.
- Do not cite `CLAUDE.md`, `docs/NEXT_SESSION.md` or `docs/DEFENDING_THIS.md` as the
  source of a number. They are downstream prose, and they are in scope for this audit.

## Where the numbers live

| Claim | Source of truth |
|---|---|
| Jansen baseline gait metrics | `scripts/gait_report.py`, `results/gait_metrics.json` |
| pin forces, torque, virtual-work residual | `scripts/mechanics_report.py`, `results/mechanics.json` |
| wear breakdown, mean-vs-integrated bias | `results/mechanics.json` |
| Pareto fronts, the 24% / 34% headline | `scripts/run_optimization.py`, `results/pareto.json` |
| the four robustness studies | `scripts/robustness.py`, `results/robustness.json` |
| the ground-clearance investigation | `scripts/clearance_fit.py`, `results/clearance_fit.json` |
