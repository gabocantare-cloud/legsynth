# legsynth — project context for Claude Code

## Who you're working with

Gabriel ("Jhon") is a **third-year mechanical engineering student at Texas A&M**. He is not
a programmer and is not trying to become one. His goal is to direct AI to build working
engineering software and to understand it well enough to defend it in an interview.

He is submitting this repo with an application to **TURTLE** (Texas A&M University Robotics
Team and Leadership Experience) with a deadline of **September 7, 2026**.

## How to work with him — this is the important part

**Explain before you write.** Before creating or changing a file, say in two or three plain
sentences what it will do and why. Then write it.

**Explain after you run.** When a script produces numbers or a plot, tell him what the
numbers mean physically — not "the objective decreased to 0.41" but "the foot path got
flatter, which means the body bounces less as it walks."

**No undefined jargon.** If you use a term like Jacobian, Pareto front, duty factor, or
transmission angle, define it in one plain sentence the first time it appears in a session.

**Mechanical intuition first, code second.** He understands statics, dynamics, stress and
machine design. Anchor every explanation to that, not to programming concepts.

**When he says "dumb it down" — the standard to hit.** Rewrite so that a smart person who has
never taken the relevant class can read it start to finish with zero unexplained words. Every
technical term gets a one-sentence plain definition the first time it appears, and abstract
ideas get a physical analogy. If a sentence needs a second read, it failed. He will tell you
when it's still too dense — believe him and go simpler, don't defend the draft.

**The doubt rule.** If he pastes in a confusing sentence from the paper, never just paraphrase
it in the same register. Break it into its parts, define each one, then give an analogy.

**Push back on him.** If he asks for something that would be wrong or misleading in the
final repo, say so. A repo that overclaims will hurt his application more than a small
honest one.

**Never invent results.** Every number that reaches the README must come from code that
actually ran in this repo. If something doesn't reproduce the paper, that is a finding to
document, not a bug to paper over.

## What this project is

An open-source **reproduction and extension** of:

> Jichao Wang, *"Durability-Aware Multi-Objective Optimization of the Jansen Linkage:
> Trading Gait Quality Against Joint Wear."* arXiv:2606.22129, 23 June 2026.

The paper re-optimizes Theo Jansen's eleven-bar walking linkage to reduce joint wear while
preserving gait quality. **The author released no code.** This repo is the open
implementation, plus one extension the paper omits.

See `docs/PAPER_GUIDE.md` for the plain-language walkthrough of the paper and
`docs/STEPS.md` for the build order.

## The extension that makes this his work, not a copy

The paper optimizes for wear but never constrains the **transmission angle** — the angle at
which one link pushes on the next. When it gets too shallow the joint binds, backdrives
badly and hammers its own pins, which is self-defeating in a paper about wear. This repo
adds minimum transmission angle as a hard constraint and reports how the Pareto front moves
when you enforce it.

Secondary contributions: explicit published definitions of the gait metrics (the paper never
writes the formulas down), branch/circuit defect checking, and DXF export for SolidWorks.

## Current state

`legsynth/kinematics.py` is complete and verified:

- Vectorized circle–circle dyad solver; returns NaN when a design cannot assemble.
- Full Jansen cascade `J1 → J2 → J3 → J4 → J5 → F` per the paper's Kinematic Model section.
- **Branch selection is solved.** All 32 sign combinations were swept; `(-1,-1,1,-1,1)` is
  the one that reproduces the real Jansen foot path. Do not change this without re-running
  the sweep.
- Tested, including a rigidity check on all eleven links across 200 poses.

`legsynth/metrics.py` is complete and verified:

- All five gait metrics with the formulas published in `docs/METRIC_DEFINITIONS.md`.
- **Stance is defined as** the longest unbroken arc of the crank turn spent within
  `band × path height` of the lowest point of the foot path, `band = 0.01`. The band is a
  *fraction* of path height, not a fixed tolerance in mm, so every metric is scale-invariant
  — there is a test for that. Do not change the default without re-running `gait_report.py`
  and rewriting the docs table.
- `tolerance_sweep` publishes the sensitivity; `band_matching` inverts it.

Measured baseline from this code, at band = 1% (0.2246 mm): foot path 67.9 mm wide ×
22.5 mm tall; step length 43.41 mm; ground clearance 22.23 mm; stance flatness 0.0011;
velocity ripple 0.0920; duty factor 31.2%, all at `metrics.N_PUBLISHED` = 1440 crank
samples. Regenerate with `python scripts/gait_report.py`.

**The step-length discrepancy is resolved and documented.** Inverting the question — what
band would reproduce each of the paper's Table 4 numbers? — gives 0.35% for his duty factor,
0.98% for his step length, 1.27% for his ripple and 31% for his flatness: a spread of 90×.
No single stance definition reproduces his Jansen row. At our band we reproduce his step
length to 0.4% and his ripple to 4%; his duty factor (+56%) and flatness stand as documented
disagreements, and his 25.7 mm ground clearance exceeds our entire 22.46 mm path height so it
cannot be a definition issue at all. Full argument in `docs/METRIC_DEFINITIONS.md`, pinned by
`test_no_single_band_reproduces_the_papers_table`. **Do not tune the band to close these gaps.**

**Still open:** the ground-clearance gap. It is geometry, not definition — most likely
slightly different link lengths from the holy numbers, or an unstated normalization.

`legsynth/dynamics.py` — quasi-static inverse dynamics, verified:

- The eleven bars are **7 rigid bodies and exactly 10 revolute joints** (`b,d,e` close one
  triangle, `g,h,i` close another). That derivation is where the paper's "ten joints" comes
  from; Grübler confirms 1 DOF. Do not re-model this as eleven independent bars.
- 21 equations, 21 unknowns, solved per crank angle; NaN on singular or unassemblable poses.
- Checked by **virtual work**, which the solver does not enforce: residual 4e-5, second order
  in the sample spacing. If you change this module, that residual is the test that matters.

`legsynth/wear.py` — Archard per joint, and one substantive disagreement: the paper's
cycle-mean-force shortcut costs **51%**, not the 3–4% it claims. Force and sliding rate are
anti-correlated. Both calculations are validated by agreeing to 0.0% at the crank pin, the one
joint where they must agree analytically.

**Do not restore the claim that the bias cancels in the ratio.** It was asserted here for a
while and §7.2 of `docs/RESULTS.md` measured it: optimising against the integrated form moves
the best achievable gait error from 0.658 to 0.710, which is 1.8x the seed-to-seed spread.
The central claim survives (Jansen is dominated under either wear definition); the "it all
cancels" defence does not.

`legsynth/constraints.py` — the extension. **The key result is the loaded/unloaded
distinction:** Jansen's minimum transmission angle is 8.6° over the whole cycle but 42.7°
during stance, because the shallow angle falls mid-swing with 0.6 N in the pin. The naive
whole-cycle constraint would reject Jansen's own linkage for a defect that costs nothing, so
`stance_only=True` is the default everywhere. Do not "fix" this by reverting to the
whole-cycle minimum.

`legsynth/optimize.py` — NSGA-II via pymoo. The search is **seeded from the baseline** because
0 of 600 uniformly sampled designs satisfy the paper's own constraints: stance is a band near
the lowest point, so a design that loses Jansen's flat bottom loses its measured step length
too, making the feasible set a thin shell around Jansen.

`legsynth/cad.py` — DXF R12 assembly, cuttable link profiles, coordinate CSV.

**Optimization results (100 pop x 80 gen x 3 seeds x 2 campaigns, ~10 min on 12 cores):**
the paper's central claim reproduces — all 20 designs on the front dominate Jansen on both
objectives. Its magnitudes do not: we get 17% flatter stance and 51% lower ripple against its
28% and 58%, but only **24% less wear against its claimed 56%**, and no design on our front
moves a link more than 8.5% where its move 29%.

Both objectives are ratios to Jansen, so **the baseline has to be measured at the same crank
sample count as the designs it normalises**. It was not, for a while: designs were scored at
1440 samples and divided by a Jansen measured at 360, which shifted every published ratio by
about a percent — small enough to look like a result. `refine` now takes its own baseline and
`tests/test_published_numbers.py` pins it. `metrics.N_PUBLISHED` = 1440 is the single sample
count behind every table in the repo; do not quote a number generated at any other.

**Our added constraint turned out to be non-binding** — no design on the paper's unconstrained
front violates the 40 deg rule (range 41.9-52.0 deg, median 48.3) and the two fronts nearly
coincide. This is written up as a negative result and must stay written up that way. The part
of the extension that actually changes an answer is the loaded/unloaded distinction, not the
constraint.

That the remaining gap is *noise rather than a cost* is measured, not asserted:
`scripts/robustness.py` re-runs the unconstrained campaign under different random seeds and
compares the spread against the gap, sweeps the constraint threshold to find where it starts
costing something, swaps the objective to the integrated wear form, and re-runs at stance
bands of 0.5% and 2%. Results in `docs/RESULTS.md` §7. `docs/DEFENDING_THIS.md` is the
interview-facing version of all of it.

Full numbers and the argument behind each in `docs/RESULTS.md`.

**Do not hardcode the test count in prose.** It used to appear in three documents and
went stale in all of them the first time a test was added. `README.md` quotes it once,
beside the `pytest` line where a reader can check it in one command; nowhere else
should.

## Starting a new session

Read `docs/NEXT_SESSION.md` first. It carries the prioritised to-do list, the claims that are
currently asserted but not yet measured, and a "do not undo these" list of decisions that look
like bugs until you know why they were made.

## Conventions

- Python 3.9+, numpy / scipy / matplotlib, `pymoo` for optimization (all now in use).
- Everything vectorized over crank angle where possible.
- Every new physics module gets a test that checks a property you can reason about
  physically (rigid links stay rigid, forces balance, wear is non-negative).
- Results saved as `.npz` or JSON. Never pickle.
- No secrets in the repo. `.gitignore` is already in place.
