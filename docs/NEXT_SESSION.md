# Handoff — what to do next

Written at the end of the session that built `dynamics.py`, `wear.py`, `constraints.py`,
`optimize.py` and `cad.py`. State on arrival: **76 tests passing, all seven build steps done,
every documented number verified against `results/pareto.json`.**

Work top-down. P0 is the difference between a submitted project and an unsubmitted one; P1 is
correctness of what is already written; P2 is the set of claims that are currently *asserted
but not measured*; P3 makes the project better if there is time.

**Read `## Ground rules` at the bottom before changing anything.** Several decisions in this
repo look wrong until you know why they were made, and a well-meaning "fix" would undo the
most defensible findings in it.

---

## P0 — Blocking. The TURTLE deadline is 7 September 2026.

1. **This is not a git repository yet.** `git rev-parse` fails; nothing is committed and there
   is no remote. Everything below is worthless until this is done.
   ```
   git init && git add -A && git commit -m "Reproduction and extension of Wang (2026)"
   ```
   Then create the GitHub repo and push. Check `.gitignore` catches `__pycache__`, `.venv`,
   `*.egg-info`, and confirm `results/*.json` **is** committed (the negation rule is deliberate
   — a reviewer should see the Pareto front without a 20-minute run).

2. **Decide whether `results/cad/*.dxf` gets committed.** Current `.gitignore` (`results/*`
   plus `!results/*.json`) excludes them. They are deliverables and they are small. Either add
   `!results/cad/` or say in the README that `run_optimization.py` produces them.

3. **Clone-and-run test, from scratch, in a fresh virtualenv.** The four README commands must
   work on a machine that is not this one:
   ```
   pip install -e . && pytest && python scripts/mechanics_report.py && python scripts/make_figures.py
   ```
   `pymoo` was added to `pyproject.toml` this session and has never been installed from a clean
   state here. If it drags in a heavy or broken dependency on another Python version, better to
   find out now than in CI.

4. **Read the README once, cold, as a stranger with 60 seconds.** It grew long. The GIF, the
   two-sentence pitch and the comparison table must be above the fold; everything else can slide
   down. `PLAN.md` has the intended 60-second structure — check it still holds.

---

## P1 — Real inconsistencies, all verified. Roughly an hour.

5. **The same quantity is quoted at two different sample counts.** Not wrong, but it looks
   sloppy and a sharp reviewer will spot it:

   | Quantity | `README.md` / `RESULTS.md` | `METRIC_DEFINITIONS.md` | Cause |
   |---|---|---|---|
   | Step length | 43.41 mm | 43.49 mm | n=1440 vs n=3600 |
   | Duty factor | 31.2% | — (31.4% in RESULTS §6 table) | n=1440 vs n=360 |

   Fix: pick **n = 1440** as the published sample count everywhere, regenerate, and state the
   sample count in each table caption. `gait_report.py` currently uses 3600 and
   `optimize.jansen_baseline` uses `N_EVAL = 360`; the §6 Jansen row comes from the latter.
   Do not just edit the text — change the scripts and re-run, so the numbers stay generated.

6. **`docs/RESULTS.md` §6 has em-dash placeholders** in the representative-designs table (best
   gait and best wear rows, step/duty/angle columns). Fill them from `results/pareto.json`.

7. **`PLAN.md` says "Three findings worth defending"** and then lists five (the wear-magnitude
   disagreement and the non-binding-constraint null were appended later). Fix the count.

8. **`legsynth/__init__.py` is empty (0 bytes).** Add the package docstring, `__version__`, and
   convenience re-exports (`JansenLeg`, `gait_metrics`, `solve_statics`, `wear_per_cycle`,
   `check`). Small, but it is the first file anyone opens.

9. **`figures/jansen_check.png` is orphaned** — no document references it, and it predates this
   session. Either reference it or delete it.

10. **Cross-check the test-count claim.** README, `CLAUDE.md` and `PLAN.md` all hardcode
    "76 tests". If you add tests, update all three (or better, stop quoting the number).

11. **`docs/PAPER_GUIDE.md` Part 3, Stop 1** still calls the paper's five Table 4 numbers
    "your reproduction targets. Everything you build gets checked against them." We now know
    that row is internally inconsistent. Add one sentence pointing forward to
    `METRIC_DEFINITIONS.md` so the guide does not contradict the findings.

---

## P2 — Claims currently asserted without measurement. **This is the highest-value work.**

Each of these is a sentence already written in the docs that is not yet backed by a number.
Either measure it or soften the wording. In order of how exposed the claim is:

12. **"The gap between the two Pareto fronts is run-to-run variation, not a cost."**
    `RESULTS.md` §6 and the README both say this, and it is the load-bearing sentence of the
    negative result. It has *not* been measured. Fix it properly:
    - Run the **unconstrained** campaign with three *different* seeds (say 3, 4, 5) and compare
      front-to-front spread against the constrained-vs-unconstrained gap.
    - If the seed-to-seed spread is comparable to or larger than the 0.642 → 0.658 gap, the
      claim is established. Report both numbers.
    - If it is *smaller*, the constraint does cost something and the write-up must change.
    Either outcome is publishable; leaving it unmeasured is the only bad option.
    Budget ~10 min of compute (three runs, one campaign).

13. **"The 51% mean-force bias partly cancels between designs, so the paper's ratio-based
    conclusions survive."** Also asserted, also untested. Test it directly: re-run the
    unconstrained campaign with the objective switched to `wear.total_integrated` and compare
    the fronts. If the front barely moves, the claim holds and you can state by how much. If it
    moves, that is a *second* substantive finding about the paper's shortcut and belongs in the
    README. `optimize.evaluate` already computes `wear_integrated` in `describe`, so this is a
    one-line objective swap plus a run.

14. **Turn the null result into a curve.** The constraint is non-binding at 40°. Sweep the
    threshold — 40°, 45°, 50°, 55° — and find where it *starts* costing gait or wear. "The
    constraint is free up to 48° and costs X% beyond it" is a far stronger statement than "it
    was free", and it converts a null into a design guideline. This is the single best
    improvement available to the extension.

15. **Pareto front sensitivity to the stance band.** The whole repo rests on band = 1% of path
    height. `METRIC_DEFINITIONS.md` shows how the *baseline* metrics move with it, but not
    whether the *optimization conclusions* do. Re-run one campaign at band = 0.5% and 2%. If
    Jansen is dominated at all three, that is a robustness result worth one paragraph. This is
    the natural completion of the definitional work that started this whole project.

---

## P3 — Genuine improvements, if there is time.

16. **The ground-clearance gap is the last open discrepancy.** The paper reports 25.7 mm;
    our entire foot path is 22.46 mm tall, so no stance rule can produce it. Test the "different
    link lengths" hypothesis directly: solve for the link set closest to the holy numbers that
    yields *both* 43.3 mm step and 25.7 mm clearance. If a solution exists within a few percent
    of Jansen, that is the explanation and it closes the last loose end. If none exists, that is
    a stronger statement than the current "we cannot reproduce it". `optimize.py` already has
    all the machinery — it is a two-objective fit, not new code.

17. **Speed up the optimizer.** ~20 ms per design, single-threaded, ~20 min per full campaign.
    Two easy wins: vectorize `solve_statics` over a *population* of designs (the 21×21 solve is
    already batched over crank angle — batching over designs is the same trick one axis out),
    or just add `multiprocessing` in the pymoo problem. Worth doing only because P2 needs
    several more campaigns.

18. **Add `ruff` (or flake8) to CI.** There are unused imports in the test files
    (`test_constraints.py` imports `M`, `make_figures.py` imports `HOLF`/`DESIGN_KEYS`
    unnecessarily). Cheap, and a linted repo reads as more professional.

19. **Add `CITATION.cff`** so GitHub renders a citation box, and consider a Zenodo DOI. Free
    credibility for an application.

20. **One reproduce-everything entry point** — `make all` or `scripts/reproduce.py` that runs
    the four scripts in order. The README promises four commands; one would be better.

21. **Consider a short `docs/DEFENDING_THIS.md`** — the five findings, each with the one-line
    version, the mechanism behind it, and the evidence that it is not an artefact. The
    `PAPER_GUIDE.md` self-check questions 7–9 are the seed. This is interview prep, and it is
    the thing most likely to actually get used.

---

## Ground rules — do not undo these

Every one of these looks like a bug until you know the reason. All are load-bearing.

- **Never tune a number to match the paper.** Disagreements are findings and get documented.
  This is the explicit standard in `CLAUDE.md` and it is why the repo is worth anything.
- **Branch selection is `(-1,-1,1,-1,1)`.** All 32 combinations were swept. Do not change it
  without re-running the sweep.
- **Stance band is 1% of *path height*, not a fixed millimetre tolerance.** The fraction is
  what makes every metric scale-invariant; there is a test for it.
- **`stance_only=True` is the default for transmission angle, everywhere.** The whole-cycle
  minimum (8.6°) would reject Theo Jansen's own linkage for a defect that happens with 0.6 N in
  the pin. Reverting this default silently invalidates the extension.
- **The leg is 7 rigid bodies and 10 revolute joints, not 11 bars.** Two bar-triples close
  triangles. Re-modelling it as 11 independent bars makes the statics singular.
- **The virtual-work residual is the test that matters in `dynamics.py`.** It is an independent
  check the solver does not enforce. If you touch that module and the residual rises above
  ~1e-4 at n=1440, something is wrong regardless of what the other tests say.
- **The search is seeded from Jansen on purpose.** 0 of 600 uniform designs satisfy the paper's
  own constraints. Do not "fix" this by switching to uniform sampling.
- **`--quick` writes to `pareto_quick.json`.** It used to overwrite the real results; do not
  merge those paths back together.
- **The negative result stays a negative result.** The added constraint was non-binding. Do not
  let it get quietly upgraded into a claimed benefit — the honest null plus the loaded/unloaded
  distinction is a stronger story than an overstated win, and a reviewer who spots an oversold
  claim will discount everything else.
