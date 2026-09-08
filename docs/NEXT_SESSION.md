# Handoff — what to do next

Written after the build session, then updated by the audit session and again by the fix
session that worked `docs/audit/FIX_PLAN.md`.

**State on arrival: 91 tests passing, `ruff` clean, `scripts/verify_docs.py --slow` green at
40 claims, nothing from the audit left unfixed, nothing pushed.** The prioritised list below
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
   --slow` is green at 40 claims, `pytest` at 91, `ruff` clean.
3. **publish** — the P0 below.

**What the audit changed, in one paragraph, because you will otherwise defend the old
version.** §7.2's headline — that the paper's mean-force wear shortcut moves the optimum —
did not survive: measured at ten seed triples instead of one, the paired difference in best
gait error is **−0.0036**, 95% CI **[−0.018, +0.011]**, four of ten positive, and the
published +0.052 turned out to be the *maximum* of the ten. That is a null, in both
directions: it is not evidence that the bias cancels either. The same twenty campaigns
showed §7.1's seed-to-seed spread was understated 7× (0.0170, not 0.0024), which also took
down §7.3's "expensive by 45°" design guideline — at the measured spread, 45° and 50° are
inside noise, so §7.3 now claims only "free at 40°, impossible at 55°". §7.1's own verdict
survived and is much better supported than before (a factor of 8.5, not 1.2). §5's "0 of
600" became "0 or 1 of 600 across three draws", with `scripts/feasibility.py` behind it.
What is untouched: Jansen is Pareto-dominated on every front measured, and the mean-force
shortcut still overstates the absolute wear figures by 51%.

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

7. ~~**The seed-spread estimate in §7.1 is three campaigns.**~~ **Done by the audit.** It is
   now measured at ten seed triples (hypervolume spread 0.0170, best gait 0.0810), from the
   twenty campaigns in `results/audit/objective_replication.json`. §7.1's verdict survived and
   got stronger: the gap is 0.0020 against 0.0170, a factor of 8.5.

8. **Find the knee in §7.3 properly, and this is now the biggest open question in §7.** The
   threshold sweep is one campaign per threshold, and at the measured seed spread (24.9% of
   the hypervolume baseline) everything between 40° and 50° is inside noise. Only "free at
   40°" and "impossible at 55°" are resolved. Repeating the sweep at **ten seed triples per
   threshold** — about 2 hours — would locate the knee instead of stating that this data
   cannot; sampling 41–44° on top of that would put it to a degree.

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
  objective-swap comparison was measured at ten seed triples and came back null: paired
  difference −0.0036 in best gait error, 95% CI [−0.018, +0.011]. Do not re-assert movement of
  the optimum without new evidence — and do not upgrade the null into "it cancels" either, as
  the interval still admits ±0.018. Jansen stays dominated under either wear definition, so
  the paper's central claim survives, and the 51% overstatement of the absolute wear figures
  is a separate measurement that stands.
- **Do not hardcode the test count in prose.** It went stale in three documents at once. The
  README quotes it beside the `pytest` line; nowhere else should.
