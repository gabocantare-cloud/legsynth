# Handoff — what to do next

Written at the end of the session that worked through the previous handoff: git history,
the sample-count unification, the parallel optimizer, the four robustness studies, and the
clearance fit.

**State on arrival: 91 tests passing, `ruff` clean, four commits on `main`, every documented
number regenerated from code that ran in this repo.** The prioritised list below is short,
because the previous one is done.

**Read `## Ground rules` at the bottom before changing anything.** Several decisions in this
repo look wrong until you know why they were made, and two of the bugs found last session
were introduced by exactly that kind of well-meaning fix.

---

## P0 — Blocking, and only you can do it

1. **Push to GitHub.** The repository exists locally with four commits and nothing uncommitted.
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

3. **Watch the first CI run.** `.github/workflows/tests.yml` now has a `lint` job as well as
   `pytest` on 3.10 and 3.12. It has never run. The tree is `ruff`-clean locally on 0.16.6;
   if CI installs a newer ruff with new default rules, the lint job may fail on something
   cosmetic. Pin the version in the workflow if that happens.

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
   putting it in the README too — the "free at 40°, expensive by 45°" curve is the single most
   interesting plot in the repo and it is currently buried three clicks deep.

6. **`docs/STEPS.md` was not touched last session** and still describes the build order as if
   the seven steps were the whole project. One paragraph pointing at `robustness.py` and
   `clearance_fit.py` would stop it reading as stale.

---

## P2 — Real work, if there is time

7. **The seed-spread estimate in §7.1 is three campaigns.** That is enough to say the
   constrained-vs-unconstrained gap is *of the same order* as the noise, which is what the
   text claims, and not enough to put an interval on it. The hypervolume margin is narrow —
   0.0020 against a 0.0024 spread. Six seed triples instead of three would either firm it up
   or expose it, and it is one line in `robustness.py` (`SEED_TRIPLES`) plus about 15 minutes
   of compute per extra triple. This is the weakest quantitative claim left in the repo.

8. **Find the knee in §7.3 properly.** The threshold sweep jumps 40 → 45 → 50 → 55, and the
   interesting behaviour is all between 40 and 45: free at one end, 11% at the other. Sampling
   41, 42, 43, 44 would locate the knee to a degree and let the write-up say "free up to 43°"
   instead of "free at 40°, expensive by 45°". Four more campaigns, about an hour.

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
- **The search is seeded from Jansen on purpose.** 0 of 600 uniform designs satisfy the paper's
  own constraints. Do not "fix" this by switching to uniform sampling.
- **`--quick` writes to `*_quick.json`.** It used to overwrite the real results; do not merge
  those paths back together. `robustness.py` also *merges* into `robustness.json` rather than
  overwriting, so `--study band` cannot destroy the other three studies.
- **The negative result stays a negative result.** The added constraint was non-binding at 40°,
  and §7.1 now measures that the residual gap is search noise. Do not let it get quietly
  upgraded into a claimed benefit — the honest null, plus the threshold curve in §7.3 and the
  loaded/unloaded distinction in §4, is a stronger story than an overstated win.
- **Do not restore "the wear bias cancels in the ratio".** §7.2 measured it. Jansen stays
  dominated under either wear definition, so the paper's central claim survives — but the
  optimum moves by 1.8× the seed-to-seed spread. The defence only half works, and the docs
  now say so in four places.
- **Do not hardcode the test count in prose.** It went stale in three documents at once. The
  README quotes it beside the `pytest` line; nowhere else should.
