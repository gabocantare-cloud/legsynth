# Handoff — what to do next

Written after the build session, then updated by the audit session, then by the fix
session that worked `docs/audit/FIX_PLAN.md`, and again by the session that extended the
§7 studies from ten seed triples to twenty.

**State on arrival: `pytest` passing, `ruff` clean, `scripts/verify_docs.py --slow` green,
nothing from the audit or the peer review left unfixed, nothing pushed.** The prioritised list below
is short, because the previous one is done.

**Read `## Ground rules` at the bottom before changing anything.** Several decisions in this
repo look wrong until you know why they were made, and two of the bugs found last session
were introduced by exactly that kind of well-meaning fix.

---

## Read this first: the audit is done and its fixes are in

**The push is now the top of the list.** The three-session chain is finished:

1. ~~**build the inspector and audit**~~ — **done.** `.claude/skills/audit-*` (six
   inspectors), `scripts/verify_docs.py` (published numbers pinned to the sentences that
   quote them), and `docs/audit/FINDINGS.md`. The audit also ran 20 optimization campaigns
   to settle a contested claim; they are in `results/audit/` and they ship with the repo.
2. ~~**fix**~~ — **done.** Every finding in [`FINDINGS.md`](audit/FINDINGS.md) was worked
   through [`FIX_PLAN.md`](audit/FIX_PLAN.md); nothing was left unfixed. `verify_docs.py
   --slow` is green, `pytest` passes, `ruff` is clean.
3. **publish** — done; the repo is private at `gabocantare-cloud/legsynth`.

A fourth step was added after the push: **peer review.** A reviewing session is
asked to audit the fix session's work rather than the repo as a whole — see
[`docs/audit/PEER_REVIEW_REQUEST.md`](audit/PEER_REVIEW_REQUEST.md), which carries
three defects the fix session found in its own work and did not fix, the largest
being a 95% CI computed with a normal multiplier on ten samples. The review came
back as [`PEER_REVIEW.md`](audit/PEER_REVIEW.md) with seven findings (PR1-PR7);
all seven are now applied. PR1 replaced the normal multiplier with Student's *t*,
PR3 moved the seeds verdict from the range onto the standard deviation, and PR4
made `reproduce.py` draw the figures after the studies rather than before.

**What the audit changed, in one paragraph, because you will otherwise defend the old
version.** §7.2's headline — that the paper's mean-force wear shortcut moves the optimum —
did not survive: measured at ten seed triples instead of one, the paired difference in best
gait error was −0.0036, four of ten positive, and the published +0.052 turned out to be the
maximum of the ten. That is a null, in both directions: it is not evidence that the bias
cancels either. The same twenty campaigns showed §7.1's seed-to-seed spread was understated
7× (0.0170, not 0.0024), which also took down §7.3's "expensive by 45°" design guideline — at
the measured spread, 45° and 50° are inside noise, so §7.3 now claims only "free at 40°,
impossible at 55°". §7.1's own verdict survived and got much better supported. §5's "0 of
600" became "0 or 1 of 600 across three draws", with `scripts/feasibility.py` behind it.
What is untouched: Jansen is Pareto-dominated on every front measured, and the mean-force
shortcut still overstates the absolute wear figures by 51%.

**What doubling the sample to twenty triples then changed, which is what §7 now says.** The
seeds and objective studies run at twenty triples, (0, 1, 2) through (57, 58, 59), and
`results/robustness.json` is that run — 46 campaigns, 2 h 32 m on 12 workers. §7.2's null
held and tightened: the paired difference is now **+0.0004**, 95% CI **[−0.011, +0.012]**
(Student's *t*, nineteen degrees of freedom; *p* = 0.95), nine of twenty positive. The
interval narrowed 30%, the sqrt(2) that doubling the sample predicts. Two things are worth
carrying forward. The point estimate **changed sign** between ten triples and twenty, which
is what a quantity with no signal does, and the +0.052 that the section was originally built
on is no longer even the largest difference — (45, 46, 47) gives +0.0581. §7.1's verdict
survived the redraw and strengthened slightly: the gap is 0.0020 against a seed-to-seed sd
of 0.0055, a factor of **2.8** where ten triples gave 2.6. The seed-to-seed *range* grew from
0.0170 to 0.0229 while the sd barely moved — the repo's own warning about ranges, now
demonstrated in its own data rather than argued from theory. §7.3's yardstick moved with it:
seed alone moves the hypervolume by 33.5% of baseline, not 24.9%, so the middle of the
threshold sweep is further inside noise than before, not less.

**And the first ten triples were re-run, not reused.** All twenty of the campaigns the audit
had already run came back **bit-identical** — 689 numbers, maximum deviation exactly 0.0 —
across the fix session's changes to constraint defaults and band threading. That is evidence
the search is deterministic across those changes, and it is why the new twenty-triple numbers
can be compared against the old ten-triple ones as a genuine increase in sample rather than
as two different experiments.

The reason for the separation is worth knowing, because it is the whole point: this session's
documentation and its `results/*.json` were produced by the *same* AI session, so an auditor
that confirms the prose against the JSON has proved nothing. Every document in this repo —
including this one and `CLAUDE.md` — is the **subject** of that audit, not evidence for it.
`audit-claims` is authorised to challenge the conclusions themselves, not just the arithmetic,
and to recommend that an overstated finding be weakened or deleted.

---

## P0 — the push, and only you can do it

1. **Push to GitHub.** The repository exists locally with seven commits and nothing
   uncommitted.
   It has never been pushed, and creating a public repo under your account is not something an
   agent should do on your behalf.
   ```
   gh repo create legsynth --public --source=. --remote=origin --push
   ```
   or create it in the browser and `git remote add origin … && git push -u origin main`.

2. **Two things to correct once the URL exists.**
   - `CITATION.cff` has `repository-code: "https://github.com/gabocantare/legsynth"`, which is
     a **guess**. Fix it to the real URL.
   - Commit authorship is `Gabriel Cantare <gabocantare@gmail.com>`, set from the email in the
     session config. If you want a different name on the commits, change it *before* pushing:
     `git config user.name "..."` then `git rebase -i --root` is painful — easier to fix now
     than later.

3. **Watch the first CI run.** `.github/workflows/tests.yml` has a `lint` job, `pytest` on
   3.10 and 3.12, and a step running `scripts/verify_docs.py` so the documents cannot drift
   from the code between commits. It has never run. `ruff` is pinned to 0.16.6, the version
   the tree is clean on, so the lint job should not fail on a cosmetic new default rule.

---

## P1 — Worth an hour, not more

4. **`JansenLeg()` with no arguments is a trap.** The default is `branches=(1,1,1,1,1)`, which
   assembles but traces a different curve; the leg everyone means is
   `branches=(-1,-1,1,-1,1)`, exported as `legsynth.JANSEN_BRANCH`. Every caller in the repo
   passes it explicitly and the package docstring warns about it, so nothing is wrong today —
   but it is the first thing a reader will get wrong. Changing the default would *install* the
   answer the branch sweep already found rather than override it, and no caller depends on the
   current default (the six that omit `branches` only read `.L`, which is branch-independent).
   It was left alone last session purely because it sits inside a "do not change without
   re-running the sweep" area three days before a deadline. Make the call deliberately.

5. **`figures/threshold_sweep.png` is referenced only from `RESULTS.md` §7.3.** Consider
   putting it in the README too — the "free at 40°, impossible at 55°" curve is the single
   most interesting plot in the repo and it is currently buried three clicks deep.

6. **`docs/STEPS.md` was not touched last session** and still describes the build order as if
   the seven steps were the whole project. One paragraph pointing at `robustness.py` and
   `clearance_fit.py` would stop it reading as stale.

---

## P2 — Real work, if there is time

7. ~~**The seed-spread estimate in §7.1 is three campaigns.**~~ **Done by the audit, then
   doubled.** It is now measured at twenty seed triples (hypervolume spread 0.0229, sd 0.0055;
   best gait 0.0939, sd 0.0252), from the 46 campaigns in `results/robustness.json`. §7.1's
   verdict survived both widenings: the gap is 0.0020 against an sd of 0.0055, a factor of
   2.8.

8. **Find the knee in §7.3 properly, and this is now the biggest open question in §7.** The
   threshold sweep is one campaign per threshold, and at the measured seed spread (33.5% of
   the hypervolume baseline) everything between 40° and 50° is inside noise. Only "free at
   40°" and "impossible at 55°" are resolved. Repeating the sweep at **ten seed triples per
   threshold** is 40 campaigns, about two and a quarter hours at the rate the twenty-triple
   run measured (200 s per campaign on 12 workers); that would locate the knee instead of
   stating that this data cannot, and sampling 41–44° on top of that would put it to a
   degree. Note the spread grew when the sample doubled, so this is a slightly harder target
   than it looked.

9. **The ground-clearance investigation has an answer now — decide what to do with it.**
   `scripts/clearance_fit.py` and `results/clearance_fit.json` hold it, written up in
   `RESULTS.md`. If the conclusion is that the paper's Table 4 clearance implies a linkage
   materially different from the holy numbers, that is a claim about *which mechanism the
   paper actually measured*, and it deserves more care than a P3 slot got. Re-read it cold
   before quoting it in an interview.

10. **The objective set loses ground clearance and nothing stops it.** Every design on our
    front drops from Jansen's 22.2 mm to about 19 mm, held up only by the 0.85× constraint.
    `RESULTS.md` §6 says so and calls it a fair criticism of the paper's objective set. Adding
    clearance as a third objective would be a genuine extension rather than a reproduction —
    and it is the obvious next paper, not the obvious next commit. Scope it before starting.

---

## P3 — Nice to have

11. **Zenodo DOI.** `CITATION.cff` is in place; connecting the repo to Zenodo and cutting a
    v0.1.0 release gets a citable DOI for free.

12. **`solve_statics` is the remaining hot spot.** The optimizer is parallel across designs
    now (`optimize.run(workers=…)`, ~2× wall-clock on 12 cores) but each design still solves
    its 21×21 system per crank angle in a Python loop. Batching that over designs the way it
    is already batched over crank angle is the next factor. Only worth it if you plan several
    more campaigns.

13. **`results/*_quick.json` and `results/cad/*quick*` are gitignored but still on disk.**
    Harmless; delete them if the directory bothers you.

---

## What changed last session, so you do not redo it

- **Git.** Repo initialised, four commits, `.gitignore` keeps `results/*.json` and
  `results/cad/*` and excludes every `--quick` output.
- **One sample count.** `metrics.N_PUBLISHED = 1440` is behind every published table.
  `tests/test_published_numbers.py` holds the documents to it.
- **A real bug under that.** `refine()` scored designs at 1440 and divided by a Jansen
  measured at 360. Fixed; the campaign was re-run. Best gait error 0.642 → **0.658**, best
  wear 0.754 → **0.758**. The design vectors did not change.
- **A second real bug.** `describe()` never passed `band` to `solve_statics`, so the
  stance-band study measured gait under one definition and wear under another. Fixed and
  re-run; nothing published was affected.
- **Parallel search.** Full campaign 1152 s → 567 s, bit-identical to serial, with a test.
- **§7 of `RESULTS.md`** — the four studies. One of them (7.2) came back *against* the
  write-up and the write-up changed.
- **New:** `docs/DEFENDING_THIS.md`, `scripts/robustness.py`, `scripts/clearance_fit.py`,
  `scripts/reproduce.py`, `CITATION.cff`, `ruff` in CI, threshold-sweep figure.

---

## Ground rules — do not undo these

Every one of these looks like a bug until you know the reason. All are load-bearing.

- **Never tune a number to match the paper.** Disagreements are findings and get documented.
  This is the explicit standard in `CLAUDE.md` and it is why the repo is worth anything.
- **Branch selection is `(-1,-1,1,-1,1)`.** All 32 combinations were swept. Do not change it
  without re-running the sweep. (Item 4 above is about the *default argument*, not this.)
- **Stance band is 1% of *path height*, not a fixed millimetre tolerance.** The fraction is
  what makes every metric scale-invariant; there is a test for it.
- **The band must reach `solve_statics`, not just the metrics.** It decides which samples
  carry the ground reaction and therefore sets every pin force and all the wear. This was
  wrong once and produced plausible numbers rather than a crash. `test_the_stance_band_
  reaches_the_statics_as_well_as_the_metrics` guards it.
- **`refine` takes its own baseline, measured at its own sample count.** Both objectives are
  ratios; numerator and denominator have to be measured the same way. Passing the coarse
  search baseline shifts every published ratio by about a percent — small enough to look like
  a result.
- **`stance_only=True` is the default for transmission angle, everywhere.** The whole-cycle
  minimum (8.6°) would reject Theo Jansen's own linkage for a defect that happens with 0.6 N
  in the pin. Reverting this default silently invalidates the extension.
- **The leg is 7 rigid bodies and 10 revolute joints, not 11 bars.** Two bar-triples close
  triangles. Re-modelling it as 11 independent bars makes the statics singular.
- **The virtual-work residual is the test that matters in `dynamics.py`.** It is an independent
  check the solver does not enforce. If you touch that module and the residual rises above
  ~1e-4 at n=1440, something is wrong regardless of what the other tests say.
- **The search is seeded from Jansen on purpose.** At most 1 of 600 uniform designs satisfies
  the paper's own constraints, across three draws (`scripts/feasibility.py`). Do not "fix" this
  by switching to uniform sampling, and quote the range rather than one draw's "0 of 600".
- **`--quick` writes to `*_quick.json`.** It used to overwrite the real results; do not merge
  those paths back together. `robustness.py` also *merges* into `robustness.json` rather than
  overwriting, so `--study band` cannot destroy the other three studies.
- **The negative result stays a negative result.** The added constraint was non-binding at 40°,
  and §7.1 now measures that the residual gap is search noise. Do not let it get quietly
  upgraded into a claimed benefit — the honest null, plus the threshold curve in §7.3 and the
  loaded/unloaded distinction in §4, is a stronger story than an overstated win.
- **Do not re-assert either direction on "the wear bias cancels in the ratio".** The
  objective-swap comparison was measured at twenty seed triples and came back null: paired
  difference +0.0004 in best gait error, 95% CI [−0.011, +0.012], *p* = 0.95. Do not re-assert
  movement of the optimum without new evidence — and do not upgrade the null into "it cancels"
  either, as the interval still admits ±0.012. The point estimate changed sign between ten
  triples and twenty; do not read a direction into it. Jansen stays dominated under either wear definition, so
  the paper's central claim survives, and the 51% overstatement of the absolute wear figures
  is a separate measurement that stands.
- **Do not hardcode any count a command prints.** The test count went stale in three
  documents at once; the claim count in this file went stale the same way, one commit after
  the fix plan asked for more claims. Test counts, claim counts, campaign counts in prose —
  say "`pytest` passes" and "`verify_docs.py --slow` is green" and let the command print the
  number. The README quotes the test count beside the `pytest` line; nowhere else should.
