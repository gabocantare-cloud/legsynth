# Build order

One step at a time. Don't start a step until the one before it runs.
Each step says what you're adding, what to ask Claude Code for, and what you should be able
to explain when it's done.

---

## Step 1 — Get it running ✅ (setup)

**Add:** nothing. Just make it work.

**Ask Claude Code:**
> Set up this project. Create a virtual environment, install it with `pip install -e .`,
> run `pytest`, then run `python scripts/show_leg.py`. Tell me what each test checks.

**Done when:** the suite passes and `figures/jansen_leg.gif` shows the leg walking.

**You can explain:** The leg is eleven rigid bars driven by one crank. Each joint is found by
intersecting two circles, in a chain. A test proves no bar ever changes length, so the
simulation is physically honest.

---

## Step 2 — Read the paper 📖

**Add:** nothing. This is reading.

**Do:** work through `docs/PAPER_GUIDE.md`. 90 minutes. Write the five Table 4 baseline
numbers down by hand.

**Done when:** you can answer the seven questions at the end of the guide out loud.

**You can explain:** the whole project, to anyone.

---

## Step 3 — Score the walk (`metrics.py`)

**Add:** code that turns "this leg walks nicely" into five numbers.

**Ask Claude Code:**
> Create `legsynth/metrics.py`. Given a foot path array, compute step length, ground
> clearance, duty factor, stance flatness and velocity ripple. The paper never publishes its
> formulas, so define each one explicitly and document your definition in the docstring.
> Add tests. Then print our values for the Jansen baseline next to the paper's Table 4.

**The judgment call that's yours:** where does "stance" begin and end? The foot is never
exactly flat — you have to pick a tolerance. Try several and see how much the answer moves.
That sensitivity is a result worth publishing.

**Done — see `docs/METRIC_DEFINITIONS.md`.** Stance is the longest unbroken arc of the crank
turn spent within 1% of the foot path's height above its lowest point. A fraction of path
height rather than a fixed millimetre tolerance, so the metrics are scale-invariant: the same
leg built twice as big gets the same duty factor and flatness, and twice the step length.

The sensitivity study answered the step-length question, and the answer was better than
expected. At our threshold we reproduce the paper's step length to 0.4% and its velocity
ripple to 4%. But asking what threshold each of his five numbers would require gives five
different thresholds spanning a factor of 90 — so his Table 4 row is internally inconsistent,
and his 25.7 mm ground clearance exceeds our entire 22.46 mm path height, which no threshold
can explain. Reported as a disagreement, not tuned away.

**You can explain:** what each metric measures physically, why the threshold has to be a
fraction rather than a fixed number, and why the paper's row cannot be reproduced by any
single definition.

---

## Step 4 — Find the joint forces (`dynamics.py`)

**Add:** code that computes how hard each of the ten pins is being pushed, through a full
crank revolution.

**Ask Claude Code:**
> Create `legsynth/dynamics.py`. Implement the paper's quasi-static inverse dynamics: gravity
> on all links at 0.05 kg/m, a 20 N vertical ground reaction during stance, crank at 1 rev/s.
> Solve for the ten pin reaction forces. Explain the constraint-Jacobian approach to me before
> you write it. Add a test that checks global force balance.

**Done — `legsynth/dynamics.py`.** Force and moment balance for all 7 moving bodies (21
equations) solved for the 10 pin reactions and the crank torque (21 unknowns). Peak pin force
25.8 N against a 20 N ground push; peak crank torque 0.026 N·m.

The check that it is right is **virtual work**: motor power must equal the power going into
gravity and the ground reaction, and nothing in the solver enforces that. Residual 4×10⁻⁵,
falling as the square of the sample spacing — finite-difference error, not a modelling error.

One thing fell out of the free-body diagrams worth knowing: the eleven bars are really **7
rigid bodies and exactly 10 revolute joints**, because `b,d,e` close one triangle and `g,h,i`
close another. That is where the paper's "ten joints" comes from, and Grübler confirms it:
3(8−1) − 2(10) = 1 DOF.

**You can explain:** the bars can't stretch or separate; those constraints require specific
pin forces; solving for them is what inverse dynamics does.

---

## Step 5 — Turn force into wear (`wear.py`)

**Add:** Archard's law applied at each of the ten joints.

**Ask Claude Code:**
> Create `legsynth/wear.py`. Implement Archard wear V = k·F̄·s per joint, with
> s = Δφ·r_pin, k = 1e-13 m³/N·m, r_pin = 4 mm. Report per-joint and total wear per cycle,
> and also as a ratio to the Jansen baseline. Explain why the ratio is the number we trust.

**Done — `legsynth/wear.py`.** Per-joint breakdown in `docs/RESULTS.md`. The three pins that
turn a full revolution take 49% of the wear, not because they are loaded hardest but because
they slide furthest.

**And it turned up a disagreement.** The paper computes wear from the cycle-average force and
argues that costs 3–4%. Measured here it costs **51%** — force and sliding rate are
anti-correlated, so averaging first counts the heavy stance load against sliding that happens
unloaded. The evidence that both calculations are right: at the crank pin they agree to 0.0%,
which is the one joint where they must agree analytically.

**You can explain:** why reporting wear as a ratio makes the conclusion independent of the
uncertain material constants.

---

## Step 6 — Add your constraint, then search (`constraints.py`, `optimize.py`)

**Add:** the transmission-angle check — the contribution that's yours — and then the search.

**Ask Claude Code (first):**
> Create `legsynth/constraints.py`. Compute the transmission angle at each joint through a
> full revolution and report the minimum. Also check the mechanism stays on one assembly
> branch. Explain what a transmission angle is geometrically before writing it. Then report
> the minimum transmission angle of Jansen's original design.

**Ask Claude Code (then):**
> Create `legsynth/optimize.py` using pymoo's NSGA-II. Design variables: link lengths b..k at
> ±30%. Objectives: composite gait error, and total wear ratio. Constraints: step length,
> clearance and duty factor each ≥ 0.85× Jansen, plus assembly feasibility. Run it twice —
> once as the paper specifies, and once with minimum transmission angle ≥ 40° added — and
> plot both Pareto fronts on the same axes.

**Done — `legsynth/constraints.py` and `legsynth/optimize.py`.** Run with
`python scripts/run_optimization.py`; fronts plotted by `scripts/make_figures.py`.

**The finding that makes this yours.** Jansen's minimum transmission angle is 8.6° over the
whole cycle — which would condemn it — but 42.7° while the foot is actually loaded. The shallow
angle happens mid-swing with 0.6 N in the pin. So the naive constraint would have rejected Theo
Jansen's own linkage for a defect that costs nothing, and the constraint this repo enforces is
the **loaded** minimum transmission angle. That distinction is the contribution, not the
constraint itself.

**You can explain:** what a Pareto front is, and what your added constraint did to it. **This
is the slide you'd present.**

---

## Step 7 — Ship it

**Add:** README, figures, CAD export, CI.

**Ask Claude Code:**
> Write the README: the GIF at the top, two sentences on what this reproduces and what it
> adds, the comparison table, three commands to reproduce everything, and an honest section
> on where our results disagree with the paper. Add a GitHub Actions workflow running pytest.
> Add MIT LICENSE. Add a DXF export of the optimized geometry for SolidWorks.

**Done.** README with the comparison tables and the disagreements, MIT LICENSE, GitHub
Actions running pytest on 3.10 and 3.12, and DXF export (`legsynth/cad.py`) that writes an
assembly drawing, individual cuttable link profiles with pin holes, and a coordinate table.

**Done when:** a stranger can clone it, run three commands, and get your figures.

**You can explain:** all of it. That was the point.

---

## Step 8 — Measure the sentences you asserted (`robustness.py`, `clearance_fit.py`)

**Add:** the two studies that turn the write-up's remaining assertions into measurements.
Roughly a third of the repo's evidence is here, and it is the third a reviewer will push on,
because it is where the write-up was wrong before.

**Ask Claude Code (first):**
> Create `scripts/robustness.py`. Four studies against the claims in the write-up that have
> no number behind them: re-run the unconstrained campaign at several seed triples and
> measure how far the front moves on its own; swap the second objective from the paper's
> mean-force wear to the integrated form and compare the *paired* difference across every
> triple; sweep the transmission-angle threshold to find where the constraint starts costing
> something; and re-run at stance bands of 0.5% and 2%. Merge into `results/robustness.json`
> rather than overwriting it.

**Ask Claude Code (then):**
> Create `scripts/clearance_fit.py`. The paper reports 25.7 mm of ground clearance and our
> Jansen gives 22.23 mm from a foot path only 22.46 mm tall. Ask whether any set of link
> lengths gives both the paper's clearance *and* its step length, first near Jansen and then
> across the whole ±30% box, and report what each candidate costs on the numbers we do
> reproduce.

**Done — `scripts/robustness.py` and `scripts/clearance_fit.py`.** Written up in §7 and §8 of
[`RESULTS.md`](RESULTS.md). Neither runs by default: `python scripts/reproduce.py
--with-studies` includes them. `robustness.py` is the expensive one: 46 campaigns, measured
at 2 h 32 m on 12 workers.

**The lesson, which is the reason this step exists.** Two of the four robustness studies came
back confirming the sentence they were testing. One came back *against* it — and then, when it
was re-run at ten seed triples instead of one, came back against the correction as well. A
single campaign compared against a spread estimated from three campaigns is not a measurement;
the range of a small sample understates the spread by construction, and every comparison made
against it leans toward "the difference is real". Run the thing enough times to see its own
noise before you quote a difference.

The studies were later doubled again, to twenty seed triples, and that is worth knowing for
the same reason. The seed-to-seed *range* grew from 0.0170 to 0.0229 purely from drawing more
samples, while the standard deviation over those campaigns barely moved (0.0052 to 0.0055).
The warning above stopped being a theoretical argument and became something measured in this
repo's own data.

**You can explain:** which of your claims are measured, which are asserted, and what the
search's own run-to-run noise is. That is the difference between a result and a story.
