# legsynth — project plan

**One-line pitch:** An open-source reproduction and extension of a June 2026 arXiv paper
that re-optimizes Theo Jansen's walking linkage for joint wear, not just gait quality.

## Why this project

**Anchor paper:** Jichao Wang, *"Durability-Aware Multi-Objective Optimization of the
Jansen Linkage: Trading Gait Quality Against Joint Wear"*, arXiv:2606.22129, 23 June 2026.

Four reasons it is the right target:

1. **It's two months old and the author released no code.** An open reproduction is a
   real contribution, not a tutorial rehash. Nobody can say you copied a repo.
2. **It's the mechanism TURTLE already builds.** Their GitHub has a `strandbeest` repo.
   You are handing them working code for a thing they own.
3. **The method is classical, not ML.** Kinematics → inverse dynamics → Archard wear law
   → NSGA-II. No GPU, no dataset, no training run that eats your week.
4. **It is mechanical engineering.** Wear, reaction forces, fatigue-adjacent reasoning,
   multi-objective design tradeoffs. This is MEEN 368 and MEEN 357 territory — you can
   defend every line of it in an interview, which is the entire point.

## What the paper does

- **Design variables:** ten link lengths `b`..`k`, each bounded to ±30% of Jansen's values.
- **Objective 1:** composite gait error (stance flatness + velocity ripple), normalized
  to the Jansen baseline.
- **Objective 2:** total normalized joint wear.
- **Constraints:** step length, ground clearance and duty factor each ≥ 0.85× Jansen;
  geometric assembly feasibility.
- **Wear model:** Archard, `V = k·F̄·s` with `s = Δφ·r_pin`, summed over ten revolute joints.
- **Optimizer:** NSGA-II, population 100, 80 generations, 3 runs merged.
- **Headline result:** Jansen's original numbers are Pareto-dominated. A representative
  redesign gets 28% better stance flatness, 58% lower velocity ripple, and 56% less wear,
  with link-length changes of ≤29%.
- **Reported baseline (Table 4):** step length 43.3 mm, ground clearance 25.7 mm,
  stance flatness 0.0281, velocity ripple 0.0956, duty factor ≈20%.

## Your extension (this is what makes it yours, not a copy)

The paper optimizes wear and gait. It does **not** check whether the resulting linkage is
mechanically sane to build:

1. **Transmission angle.** Add minimum-transmission-angle as a hard constraint. A linkage
   with a 12° transmission angle binds, backdrives badly, and hammers its pins — which is
   ironic in a paper about wear. This is the single best question you can raise about the
   paper, and it is a legitimate one.
2. **Branch and circuit defects.** Verify the optimized design stays on one assembly branch
   through a full revolution instead of silently jumping.
3. **Metric definitions — done.** The paper reports stance flatness and velocity ripple but
   never writes the formulas down. `legsynth/metrics.py` publishes ours, and
   `docs/METRIC_DEFINITIONS.md` shows the sensitivity plus the finding that his Table 4
   Jansen row cannot come from any single stance definition.
4. **CAD handoff.** Export the optimized geometry to DXF / a coordinate table so it drops
   straight into SolidWorks. Nobody in the ML-mechanism literature does this. You can,
   because you already do ASME drawings.

## Status — what already works

`legsynth/kinematics.py` is done and verified:

- Vectorized circle-circle dyad solver, NaN-on-infeasible so bad designs self-report.
- Full Jansen cascade `J1 → J2 → J3 → J4 → J5 → F` per the paper's Section 2.
- **Branch selection solved.** All 32 sign combinations were swept; `(-1,-1,1,-1,1)` is
  the one that reproduces the real Jansen foot path. This is the part that normally eats
  an entire weekend, and it is behind you.
- 5 passing tests, including a check that all 11 links stay rigid to 1e-9 at 200 poses.

`legsynth/metrics.py` — all five gait metrics, formulas published in
`docs/METRIC_DEFINITIONS.md`, 15 passing tests.

- Stance = the longest unbroken arc of the crank turn within `band × path height` of the
  lowest point of the foot path, `band = 0.01`. Using a *fraction* of path height rather
  than a fixed millimetre tolerance makes every metric scale-invariant, and there is a test
  that proves it.
- `tolerance_sweep` publishes the sensitivity; `band_matching` inverts it.

Measured baseline from this code at band = 1% (0.2246 mm): full path 67.9 mm wide ×
22.5 mm tall, step length 43.41 mm, ground clearance 22.23 mm, stance flatness 0.0011,
velocity ripple 0.0920, duty factor 31.2%, at 1440 crank samples.

**The step-length discrepancy is resolved and documented.** Instead of asking what our
number is, we asked what stance band would be needed to reproduce each of the paper's
numbers: 0.35% for his duty factor, 0.98% for his step length, 1.27% for his ripple, 31%
for his flatness. A spread of 90×, so no single stance definition reproduces his Table 4
Jansen row — it is internally inconsistent, not merely unpublished. At our band we
reproduce his step length to 0.4% and his velocity ripple to 4%; his duty factor and
flatness stand as documented disagreements. Do not tune the band to close them.

**Still open — and it is not a definition problem:** the paper's 25.7 mm ground clearance
is larger than our entire foot path is tall (22.46 mm), so no stance rule can produce it.
That points to slightly different link lengths or an unstated normalization. Worth one
hour, not five.

`legsynth/dynamics.py`, `wear.py`, `constraints.py`, `optimize.py`, `cad.py` — all complete,
Numbers and arguments in `docs/RESULTS.md`. Four findings worth defending
in an interview, plus one honest negative:

1. **The eleven bars are 7 rigid bodies and 10 revolute joints.** Two of the bar triples close
   triangles. That derives the paper's joint count instead of taking it on faith, and Grübler
   confirms 1 DOF. The statics is checked by virtual work, which the solver never enforces.
2. **The paper's mean-force wear shortcut costs 51%, not the 3–4% it claims.** Force and
   sliding rate are anti-correlated. Validated by the two forms agreeing to 0.0% at the crank
   pin, the one joint where they must agree analytically.
3. **Jansen's minimum transmission angle is 8.6° over the cycle but 42.7° while loaded.** The
   shallow angle falls mid-swing with 0.6 N in the pin. So the obvious version of our own
   extension would have rejected Jansen's linkage for a defect that costs nothing — the
   contribution is the *loaded* qualifier, not the constraint.
4. **We do not reproduce the paper's 56% wear reduction.** Its gait claims land close (20% and
   52% against 28% and 58%); the best wear ratio anywhere on our front is 0.754, i.e. 25%.

And one honest negative: **the added constraint turns out to be non-binding.** No design on the
paper's own front violates the 40° rule. Say so plainly in interviews — checking and reporting
a null is the point, and the loaded/unloaded distinction is the finding that stands.

## Day-by-day, ~24 hours to Sept 7

| Day | Hours | Work |
|---|---|---|
| Sat 30 | 4 | Read the paper properly. Understand the cascade code you now have. Write `metrics.py`: stance flatness, velocity ripple, step length, clearance, duty factor — your own explicit definitions. |
| Sun 31 | 4 | `dynamics.py`: quasi-static inverse dynamics for pin reaction forces. `wear.py`: Archard per joint. Reproduce the Jansen baseline row of Table 4. |
| Mon 1 | 3 | `constraints.py`: assembly feasibility, min transmission angle, branch consistency. |
| Tue 2 | 4 | `optimize.py`: NSGA-II via `pymoo`. Get a Pareto front out, even a rough one. |
| Wed 3 | 3 | Run the real optimization. Compare your front against the paper's claims. Write down where you agree and where you don't. |
| Thu 4 | 3 | Figures: Pareto front, baseline-vs-optimized foot paths, per-joint wear bars, animated GIF of the optimized leg. DXF export. |
| Fri 5 | 3 | README, docstrings, GitHub Actions running pytest, LICENSE (MIT). |
| Sat 6 | 2 | Buffer. Reread the README as a stranger. Submit the application. |

Ship a smaller repo on time over a bigger one on Sept 8. If you fall behind, cut the
optimizer to a simple weighted-sum scan and keep the wear model — the wear model is the
interesting part.

## README structure that a reviewer reads in 60 seconds

1. The animated GIF of the leg walking, first thing, above the fold.
2. Two sentences: what this reproduces, and what it adds.
3. The comparison table: paper's numbers | your numbers | difference.
4. `pip install -e . && pytest && python scripts/run_optimization.py` — reproducible in
   three commands.
5. A short "where this disagrees with the paper" section. Do not hide it. It is the part
   that shows you can actually read a paper critically.
6. Citation of the paper, and the license.

## On the security worry

For this repo, essentially nothing to worry about. It is a public repo with no server,
no user input, no secrets. The complete list:

- Don't commit API keys or `.env` files. Add a `.gitignore` before your first commit.
- Pin GitHub Actions to a version, and don't use `pull_request_target`.
- Don't `pickle.load()` files from strangers — use `.npz` or JSON for saved results.

That's it. You were right that you were overthinking this part.

## One thing worth saying plainly

Use this scaffold, but make sure you understand every line of what ships. TURTLE reviewers
may ask you to walk through the wear model or explain why the branch sign matters. The
repo is only worth something to you if you can answer.
