# Peer review request — for the reviewing session

You are reviewing **one session's work**, not the whole repo. A previous session
(the "fix session") worked [`FIX_PLAN.md`](FIX_PLAN.md) against
[`FINDINGS.md`](FINDINGS.md) and changed 20 files across 6 commits. **Your job is to
decide whether it did that honestly and well, and to say what should change.**

You have no context from any earlier session. Everything you need is in this
directory and in the repo. Read [`FINDINGS.md`](FINDINGS.md) first — it is the
evidence the fixes were supposed to satisfy — then [`FIX_PLAN.md`](FIX_PLAN.md),
whose final section records what the fix session says it did.

---

## The one rule that makes this review worth doing

**No document in this repo is evidence for itself.** The prose, the
`results/*.json` it quotes, and the commit messages explaining them were all
produced by AI sessions. An auditor who confirms `RESULTS.md` against
`results/robustness.json` has proved nothing about either, because the same
process wrote both.

That includes everything the fix session wrote — this file included. Recompute
from `legsynth/`. Where you cannot recompute (campaign-scale numbers cost tens of
minutes), say that the claim is inherited rather than verified, and treat the
distinction as load-bearing.

**Weakening or deleting an overstated claim is a good outcome, not a failure.**
The repo's owner is a mechanical engineering student submitting this with an
application; a repo that overclaims hurts him more than a smaller honest one.
That is his stated standard and it is written into `CLAUDE.md`. The last session
withdrew two published findings on exactly that basis. Do not look for a way to
restore strong wording, and do not soften a real objection into a suggestion.

## Ground rules

- **Do not push, and do not change git author configuration.** The repo is now on
  GitHub at `gabocantare-cloud/legsynth`, **private**, 14 commits, and the local
  `main` matches `origin/main` exactly. Gabriel does his own pushes.
- **Do not re-run the twenty optimization campaigns.** They cost 62 minutes and
  are in `results/audit/objective_replication.json`, which ships with the repo.
  Quote from it. Recomputing the *statistics* from it is cheap and is encouraged —
  see finding 1 below, which is exactly that.
- **Never tune a number to match the paper.** Disagreements with Wang (2026) are
  findings, not bugs.
- **Report before you rewrite.** For anything that changes a published claim,
  write the finding and let Gabriel decide. Unambiguous mechanical fixes (a stale
  runtime, a wrong multiplier) you may apply directly, but say that you did.

## Start here — five commands, about two minutes

```
python -m pytest -q                        # expect 91 passed
python -m ruff check .                     # expect clean, on ruff 0.16.6
python scripts/verify_docs.py --slow       # expect 40 passed, 0 failed
python scripts/verify_docs.py --coverage   # numbers no claim pins
git log --oneline -6                       # the work under review
```

`scripts/verify_docs.py` is the audit session's instrument: each published number
is pinned to the exact sentence that quotes it and recomputed from the package. A
claim marked `~` is *inherited* — it reads a JSON file rather than recomputing, so
it establishes that the document matches a recorded run, not that the run was
right. **Do not treat a green run as proof the documents are honest.** It checks
arithmetic, not whether a sentence is earned by its evidence.

---

## What the fix session changed

Six commits, `21fd97d` through `945a37d`:

| Commit | What |
|---|---|
| `21fd97d` | Ships the audit trail: `FINDINGS.md`, `FIX_PLAN.md`, `verify_docs.py`, six `.claude/skills/audit-*` inspectors, and `results/audit/` |
| `2cb6017` | **The substance.** Withdraws §7.2's finding and §7.3's design guideline across 8 documents; `robustness.py` changes; figure redrawn |
| `4517940` | Adds `scripts/feasibility.py` and rewrites §5 from its output |
| `bc1dd08` | Code hygiene: `constraints.check()` band, unified sample counts, dead code, symmetric edge mask, the 56°→48° docstring |
| `ab6bce5` | CI runs `verify_docs.py`; `ruff` pinned; Python floor raised to 3.10 |
| `945a37d` | `CITATION.cff` repository URL |

The two retractions, which are the heart of it:

- **§7.2** claimed the paper's mean-force wear shortcut "moves the optimum". That
  rested on one pair of campaigns showing +0.052 in best gait error. Re-run at ten
  seed triples, the paired difference averages **−0.0036** and the published
  +0.052 is the **maximum of the ten**. §7.2 is now a null.
- **§7.3** claimed the transmission-angle constraint is "expensive by 45°", pricing
  it against a seed-to-seed spread estimated from three campaigns. At ten triples
  that spread is **7× larger**, which puts 45° and 50° inside noise. The design
  guideline was deleted; §7.3 now claims only "free at 40°, impossible at 55°".

---

## Three defects the fix session found in its own work and did not fix

These are handed over rather than hidden. Confirm or reject each; the first two
are, in my judgement, real.

### 1. The 95% confidence interval uses the wrong multiplier — **z, not t**

`docs/RESULTS.md` §7.2 and four other documents quote **95% CI [−0.018, +0.011]**
for the paired difference. That interval is `mean ± 1.96 × stderr` — a *normal*
multiplier applied to **n = 10**. With ten paired observations the correct
multiplier is Student's t at 9 degrees of freedom, **2.2622**:

```
n=10  mean=-0.003572  sd=0.023069  se=0.007295
published (z=1.96) : [-0.01787, +0.01073]
correct  (t=2.2622): [-0.02007, +0.01293]
two-sided paired t-test: p = 0.636
```

So the published interval is about **15% too narrow**. The conclusion does not
change — it straddles zero either way, comfortably — but the repo's whole argument
in §7 is that small samples were quoted with more precision than they support, and
this is the same error one level down. It originates in the audit session's
`results/audit/objective_replication.json` (`ci95`), was propagated by the fix
session into `RESULTS.md`, `README.md`, `CLAUDE.md`, `DEFENDING_THIS.md` and
`NEXT_SESSION.md`, and is reproduced in `scripts/robustness.py:study_objective`,
which also hardcodes `1.96`.

**Recommended fix:** use `scipy.stats.t.ppf(0.975, n-1)` in `study_objective`,
restate the interval as **[−0.020, +0.013]** in all five documents, and consider
quoting the p-value (0.64) as well, since "we could not detect an effect" is
better supported by a p-value than by an interval a reader has to interpret.
Check whether a `verify_docs.py` claim should pin the interval; today only
`delta_mean`, `n_positive` and `delta_max` are pinned, so the CI could drift
silently.

### 2. Advertised runtimes are now roughly half of what the code will actually do

The fix session raised `robustness.SEED_TRIPLES` from 3 triples to 10, and changed
`study_objective` to run *every* triple rather than only the first. It did not
update the runtimes quoted around the script:

| Where | Says | Reality after the change |
|---|---|---|
| `README.md:234` | `robustness.py` … ~50 min | ~27 campaigns; on the audit's own measured rate (20 campaigns / 62 min on 12 cores) that is **~85 min** |
| `README.md:29` | `--with-studies` (~1 h) | closer to 1 h 40 m |
| `scripts/reproduce.py:37` | `--with-studies … ~1 h` | same |
| `scripts/reproduce.py:83` | `adds ~45 min` | same |
| `docs/RESULTS.md:17` | `robustness.py … (~50 min)` | same |

This is precisely the documentation-drift class that `verify_docs.py` exists to
catch, and it slipped through because runtimes are prose, not pinned numbers.
**Estimate it properly** (the campaign count is deterministic — count the `cached`
calls across the four studies) rather than copying my arithmetic, then correct all
five sites.

### 3. A hardcoded count in prose, which is the repo's own documented anti-pattern

`CLAUDE.md` carries an explicit rule: *"Do not hardcode the test count in prose. It
used to appear in three documents and went stale in all of them."* The fix session
then wrote "**green at 40 claims**" into `docs/NEXT_SESSION.md` in two places. The
claim count changes every time anyone registers a claim — which the fix plan
actively encourages — so it will go stale the same way. Either drop the number or
state it as "green", and consider whether the rule in `CLAUDE.md` should be
generalised from "the test count" to "any count a command prints".

---

## Where else the work is most likely to be wrong

Ranked by how much rests on it. For each, the specific question to answer.

1. **Did §7.2 actually withdraw its claim, or only soften the wording?** This is
   the highest-value question in the review. Read the rewritten §7.2 and §7.3 cold
   and put the four questions in `.claude/skills/audit-claims/SKILL.md` to them.
   In particular: the section now says the effect is "not detectable", and
   separately warns that this is *not* evidence the bias cancels. Is that
   even-handed, or does the surrounding prose lean toward one direction anyway?
   Check `DEFENDING_THIS.md` especially — it is the interview-facing document and
   it compresses, and compression is where caveats get dropped.

2. **`scripts/make_figures.py` now reads `results/audit/`.** `fig_threshold` draws
   the seed-spread band behind the threshold curve. That band used to come from
   the three-triple spread in `robustness.json` and was seven times too narrow,
   which made the middle of the sweep look resolved when it is not. The fix
   session added `seed_spread_hypervolume()`, which prefers
   `results/audit/objective_replication.json` and falls back to `robustness.json`.
   **Is that a legitimate source, or a layering violation?** A figure generator now
   depends on audit evidence that a normal `reproduce.py` run does not produce. The
   alternative — re-run `robustness.py --study seeds` at ten triples (~1 h) so
   `robustness.json` carries the honest number itself — costs compute but removes
   the special case. Judge which is right.

3. **`results/robustness.json` is now internally inconsistent with the code.** It
   holds a seeds study run at three triples and an objective study run at one pair.
   The code that produced it would now produce ten and ten. `RESULTS.md` §7.1 prints
   the old three-campaign table *and* the new ten-triple spread row, with a note
   explaining the difference. **Is that note enough, or is the section confusing?**
   Read it as a reviewer who has never seen this repo.

4. **`feasibility.py`'s "2% jitter" is a Gaussian standard deviation.** It draws
   `base * (1 + normal(0, 0.02))` per length. §5 says "jittering Jansen's own
   lengths by 2%", which a reader could equally take as uniform ±2%. The script
   reproduces the audit's numbers exactly (2.8 / 5.8 / 4.0%), which shows both
   sessions read it the same way — not that the reading is right. **Decide whether
   the documented sentence matches what the code does**, and if the wording is
   ambiguous, make the sentence say which.

5. **The band-threading test was weakened to make it pass.** In
   `tests/test_optimize.py`, `test_the_stance_band_reaches_the_statics_as_well_as_
   the_metrics` gained coverage of `constraints.check(band=...)`. The first version
   compared bands 0.5% / 1% / 2% and **failed** — Jansen's worst loaded angle sits
   inside the stance window at every band that narrow, so `check()` returns the
   identical angle. The test now compares 1% / 10% / 20%. A 20% stance band is not
   physically meaningful. **Is that a legitimate test of parameter threading, or a
   contrivance that would pass even if `band` were doing something wrong?** Propose
   something better if you can — for instance a design whose shallow angle falls
   near the stance boundary.

6. **Sample-count defaults changed in `legsynth/constraints.py`.**
   `transmission_angles`, `min_transmission_angle`, `force_amplification`,
   `branch_margin` and `check` all defaulted to 720 / 720 / 360 / 720 / 360 and now
   default to `M.N_PUBLISHED` (1440). The justification was that every caller in
   the repo passes `n` explicitly, so nothing published moves. **Verify that claim
   independently** — grep every call site including tests — and consider the cost:
   `check()` is now four times slower, and its docstring used to say it was "cheap
   enough to call in an optimizer loop" (that sentence was removed).

7. **`spread()` changed its return type** from a float to a dict of
   `range` / `sd` / `n`. Confirm no consumer was missed, including anything reading
   `results/robustness.json` keys.

8. **Claims `R1`–`R7` in `verify_docs.py` read `results/audit/`** rather than
   recomputing from `legsynth`. They are labelled `inherited`, which is honest, but
   check the labelling is accurate and the tolerances are tight enough to catch a
   real drift rather than merely a typo.

---

## What was checked by earlier sessions and should not be redone

Listed so you spend your effort on what is unsettled. All of these were recomputed
from the package during the audit and survived:

- The Jansen baseline table, all six metrics at `N_PUBLISHED = 1440`.
- The mean-force shortcut's **51.3%** overestimate, and the crank-pin cross-check
  that validates both wear calculations by agreeing to 0.0% where they must agree
  analytically. This is the repo's strongest quantitative disagreement with the
  paper and it holds.
- The extension's numbers: 8.6° whole cycle, 42.7° during stance, 0.6 N in the pin
  at the shallow angle.
- The virtual-work residual, 4.1e-5 at n=1440, second order in the spacing. The fix
  session made the edge mask symmetric and re-checked it: unchanged at 4.149e-5.
- The band-matching table, and the argument that no single stance definition
  reproduces the paper's Table 4 row.
- **Jansen is Pareto-dominated** — the central reproduction, at every band and under
  either wear definition. Nothing has been found against it.
- §7.1's negative result, which the ten-triple spread *strengthened*: the gap is
  0.0020 against 0.0170, a factor of 8.5.

## Deliberately left undone

- **The §7.3 threshold sweep at ten seed triples per threshold**, ~2 h. It would
  locate the knee instead of the write-up stating that this data cannot. Recorded
  as P2 in `docs/NEXT_SESSION.md`. An upgrade, not a correction — the softened
  §7.3 wording is fully supported without it.
- **Re-running `robustness.py` at the new ten triples**, ~1 h 40 m, which would make
  `results/robustness.json` self-consistent with the code. See question 2 and 3.

## How to report

Write `docs/audit/PEER_REVIEW.md` in the style of `FINDINGS.md`: an ID, a severity,
the file and line, the evidence, and a concrete fix for each finding, with a summary
table at the top. Severity should order the work, not decide whether it happens.

Three things that would make the report most useful:

1. **Say plainly if the two retractions went too far.** Deleting a supported claim
   is as much an error as keeping an unsupported one. If §7.3's 45° cost is in fact
   defensible on evidence the fix session overlooked, that is a finding.
2. **Separate what you verified from what you inherited**, every time.
3. **Propose the specific experiment that would settle anything you cannot**, with
   its cost in minutes, rather than expressing doubt in the abstract.

If you find nothing beyond the three self-reported defects above, say so plainly —
"the corrections are sound and here is what I checked" is a useful review. Do not
manufacture findings to look thorough.
