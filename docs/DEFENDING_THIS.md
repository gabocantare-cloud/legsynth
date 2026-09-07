# Defending this

Interview prep. Every finding in this repo, in the form you would actually have to produce it
across a table: the one-line version, the mechanism underneath it, and the reason it is not
an artefact of something you got wrong.

That last part is what separates a finding from a bug you have not caught yet. Anyone can
report a number that disagrees with a paper. The question you will be asked is *how do you
know it is the paper and not you*, and every section below has an answer to it that does not
depend on trusting the code.

Read `PAPER_GUIDE.md` Part 6 first — the nine self-check questions. This page is the answers
to the hard half of them.

---

## The one-paragraph version

We re-implemented a June 2026 paper that re-optimizes Theo Jansen's walking linkage to trade
gait quality against joint wear, and which released no code. The paper's central claim — that
Jansen's linkage is Pareto-dominated, that you can beat it on smoothness *and* wear at the
same time — reproduces cleanly. Three of its supporting numbers do not, and one of its
methodological shortcuts turns out to cost about fifteen times what it claims. We also added
the check the paper never makes: a linkage that binds on itself is a wear problem, and nobody
tested for it. That check came back negative, which we report as a negative.

---

## Finding 1 — The eleven bars are seven rigid bodies and ten joints

**One line.** The paper says the linkage has ten revolute joints and does not say why; the
eleven bars close two triangles, which makes them 7 moving bodies, and Grübler then gives
exactly 1 degree of freedom.

**Mechanism.** Bars `b, d, e` close the triangle `G–J2–J3`, and `g, h, i` close `J4–J5–F`. A
triangle of rigid bars pinned at its corners cannot deform — it is one rigid body, not three.
Counting eleven independent bars instead gives a statics system that is singular, because you
would be solving for internal forces in a structure with no internal freedom. Grübler's
count on the correct decomposition:

    3(8 − 1) − 2(10) = 21 − 20 = 1 DOF

which is what a leg driven by one crank had better be.

**Why it is not an artefact.** The statics solver writes force and moment balance for the 7
bodies — 21 equations, 21 unknowns (10 pin reaction pairs plus the crank torque) — and
nothing in that system knows anything about energy. So the check is **virtual work**: at
quasi-static equilibrium, the power the motor puts in must equal the power going into gravity
and the ground reaction. The residual is 4.1 × 10⁻⁵ of RMS torque, and it falls with the
*square* of the sample spacing. That second-order convergence is the fingerprint of
finite-difference error in the numerical derivative, not of a modelling mistake — a sign
error or a misplaced moment arm would give a residual that does not shrink at all. The
solver never enforces this; it is a genuinely independent check.

**If they push.** "Why not just model eleven bars and let the solver sort it out?" Because it
cannot. The triangles have no internal degree of freedom, so the force distribution inside
them is statically indeterminate — you would need material stiffness to resolve it, which a
rigid-body model does not have. Treating each triangle as one body is not a simplification,
it is the only well-posed choice.

---

## Finding 2 — The paper's mean-force wear shortcut costs 51%, not 3–4%

**One line.** The paper averages the pin force over the cycle *before* applying Archard's
law, argues that costs 3–4%, and it actually overestimates wear by 51.3%.

**Mechanism.** Archard says worn volume = k × force × sliding distance. Done properly you
integrate force against sliding, `∫F ds`. The paper computes `F̄ · s_total` instead. Those
agree only if force and sliding rate are uncorrelated — and on this linkage they are strongly
**anti**-correlated. The pins are loaded hardest during stance, which is exactly when they
are rotating slowest, because a Strandbeest leg is designed to move the foot slowly and
steadily along the ground and whip it quickly through the air. So multiplying the average
force by the total sliding charges the heavy stance load against the fast, *unloaded* swing
sliding as well.

**Why it is not an artefact.** This is the strongest single piece of evidence in the repo, so
it is worth stating precisely. The two calculations are compared joint by joint, and at joint
`O`, the crank pin, they agree to **0.0%**. That is the one joint where they *must* agree
analytically: the crank turns at a constant rate, so sliding is uniform in crank angle, so
averaging first is exact there. A bug in either calculation would almost certainly have
shown up at that joint too. Both are right — the shortcut is what is wrong. The result is
also converged: going from 360 to 5760 crank samples moves it by 0.1%.

**What it does and does not overturn.** It does not overturn the paper's conclusions, which
are stated as ratios between designs, and a bias that applies to every design largely cancels
in a ratio. We measured that rather than assuming it — see §7 of `RESULTS.md`. It does mean
the paper's *absolute* wear figures are high by about half.

**The pretty corollary.** The three pins that turn a full revolution take 49% of the total
wear between them, and it is not because they carry the most load — `O` carries 4.03 N mean
against `G_bd`'s 25.8 N peak. It is because they slide the furthest. Wear is force **times**
distance, and on this mechanism distance does most of the sorting. If you were choosing where
to put a bronze bushing, that is where.

---

## Finding 3 — "Loaded" is the word that makes the extension work

**One line.** Jansen's minimum transmission angle is 8.6° over the whole cycle but 42.7°
during stance, so the obvious form of our own extension would have rejected Theo Jansen's own
linkage for a defect that costs nothing.

**Mechanism.** The transmission angle is the angle at which one bar pushes the next: 90° means
the whole push turns into motion, near 0° means it all goes into squeezing the pin. Practice
keeps it above about 40°, and a paper about wear that never checks it has a real gap, because
a shallow angle *is* a wear mechanism.

So we added the constraint — and Jansen fails it, at 8.6°. That should stop you, not please
you. Look at *when* the 8.6° happens: crank angle 191°, mid-swing, foot in the air, with
**0.6 N** in the pin. The largest pin force of the cycle, 25.8 N, arrives at crank 335°, where
the worst interface sits at a healthy 48°. A shallow transmission angle only costs you
something when there is force behind it.

**Why it is not an artefact.** Two independent constructions of the angle were implemented
while writing this — the geometric one (angle between the coupler and the output link) and the
kinematic one (angle between the coupler and the pin's velocity) — and they agree to within
rounding at all three interfaces. That is the check that the definition being used is the
classical one and not something invented to make the numbers work.

The interfaces that are *excluded* matter as much as the ones included. Anything involving the
crank is excluded because a coupler lines up with the crank twice per turn, which is the normal
dead point of the rocker's travel, not a defect — counting it would report 0° for every healthy
four-bar ever built. The links attaching to the floating triangle T2 are excluded because T2
pivots on nothing, so it has no fixed line of motion and the textbook angle is simply not
defined there. Rather than invent a number, force amplification covers those joints instead.

**This is the part that is actually ours.** Not the constraint — the qualifier. Enforcing the
whole-cycle minimum would have produced a Pareto front that was an artefact of a badly posed
constraint, and it would have looked completely reasonable in a plot.

**Read the other way, it is a compliment to Jansen.** He spends his shallow angles exactly
where they are free and stays above the rule of thumb everywhere they are paid for. Whether
he did that deliberately or the physical selection he was doing found it for him is a nice
question to raise and not one this repo can answer.

---

## Finding 4 — The paper's Table 4 baseline cannot come from any single definition of stance

**One line.** The paper reports five gait numbers for Jansen and never publishes the formulas;
asking which stance threshold each number would require gives five incompatible answers
spanning a factor of 90.

**Mechanism.** Every one of the five metrics depends on where you draw the line between
"the foot is on the ground" and "the foot is in the air". We define stance as the longest
unbroken arc of the crank turn spent within 1% of the foot path's height above its lowest
point — a *fraction* of path height, not a fixed tolerance in millimetres, so every metric is
scale-invariant (double every link length and nothing changes; there is a test for it).

Rather than argue about whose definition is right, invert the question. What band would our
code need to reproduce each of *his* numbers?

| His number | Band we would need |
|---|---|
| Duty factor ≈20% | 0.35% of path height |
| Step length 43.3 mm | 0.98% |
| Velocity ripple 0.0956 | 1.27% |
| Stance flatness 0.0281 | 31.2% |
| Ground clearance 25.7 mm | unreachable at any band |

**Why it is not an artefact.** The inversion is the whole argument, and it does not require
you to trust our definition at all. If a single consistent definition sat behind his table,
these five bands would agree. They span 90×. Step length and velocity ripple agree tightly at
about 1%, which is a genuine reproduction and is why 1% was adopted; the other three do not.

And the ground clearance is not a threshold question at all: 25.7 mm is taller than our
entire foot path is tall (22.46 mm). No stance rule can produce it, so it points at different
link lengths or an unstated normalization. That one is still open, and saying so is better
than inventing an explanation.

**If they push.** "Couldn't you just tune your band to match him?" Yes, to any *one* of his
numbers, and that is precisely the point — you cannot match more than one at a time, and
tuning to match would have destroyed the finding. There is a test,
`test_no_single_band_reproduces_the_papers_table`, that fails if anyone ever tries.

---

## Finding 5 — We do not reproduce the 56% wear reduction

**One line.** The paper's gait claims land close (we get 17% and 51% against its 28% and 58%);
its wear claim does not — the lowest wear ratio anywhere on our front is 0.758, a 24%
reduction rather than 56%.

**Mechanism.** Two things point the same way. First, our optima sit much closer to Jansen than
the paper's do: no design on our front moves a link by more than 8.5%, where the paper reports
changes up to 29%. Second, of 600 designs drawn uniformly from the paper's own ±30% box, 17%
assemble at all and **none** satisfy the paper's own constraints.

That second number explains the first. Stance is a band near the lowest point of the foot
path, so a design that loses Jansen's unusually flat bottom stroke also loses most of the arc
that counts as stance — and its measured step length collapses with it. Under an explicit
definition, the paper's step-length constraint is far stricter than it looks: it is partly a
flatness constraint in disguise. The feasible set is a thin shell around Jansen, and a search
that respects the constraints cannot wander 29% away from it.

**Why it is not an artefact.** The honest position is that this is a *disagreement*, not a
refutation, and the difference matters. A search that reported 29% link changes was either
exploring a region our constraints exclude, or measuring step length in a way that tolerates
a much less flat foot path. We cannot tell which without his code, and we say so. What we can
say is that under an explicitly published definition of the constraints, those designs are
not reachable.

**The honest weakness to volunteer.** Every design on our front trades away ground clearance,
from Jansen's 22.2 mm down to roughly 19 mm, and stops only because the 0.85× constraint
stops it. Nothing in either objective rewards lifting the foot higher. That is a fair
criticism of the paper's objective set — and it is a criticism of ours too, because we
reproduced it deliberately rather than quietly improving it.

---

## The negative result — and why it is still worth having

**One line.** Our added constraint turned out to be non-binding: not one design on the paper's
unconstrained front violates the 40° rule, the range being 41.9°–52.0° with a median of 48.3°.

Say this plainly. Do not let it get upgraded into a claimed benefit — an oversold claim is the
fastest way to make a reviewer discount everything else on the page.

**Why it is not nothing.**

*You could not have known without checking.* "The optimizer's preferred designs happen to be
well-conditioned" is a fact about this problem, not a general fact about linkage optimization.
The check costs one extra geometric evaluation per design, and the campaign that includes it
is the evidence that the paper's omission did not damage its conclusions **here**.

*There is a reason, and the reason is interesting.* Wear and transmission angle are partly
aligned objectives on this mechanism. A shallow-angle design puts large forces through its
pins, and large pin forces are exactly what the wear objective is already punishing. The
search was never going to want shallow-angle designs. That is a satisfying explanation for the
null rather than a coincidence, and it is the sort of thing that makes a null publishable.

*The claim that it is noise is measured, not asserted.* See `RESULTS.md` §7 — the
unconstrained campaign is re-run with different random seeds so the search's own run-to-run
spread can be compared against the gap the constraint opens. Saying "that difference is just
noise" without measuring the noise is exactly the move this repo exists to avoid.

*A null becomes a guideline when you sweep it.* "The constraint is free" is weak. "The
constraint is free up to X degrees and costs Y% of the achievable improvement beyond it" is a
design rule someone could use. `RESULTS.md` §7 has the curve.

---

## Questions you should expect, with short answers

**"How do you know your kinematics is right?"** All eleven links are checked to stay rigid to
1e-9 across 200 poses, and the branch selection was not guessed — all 32 sign combinations
were swept, and `(-1,-1,1,-1,1)` is the one that reproduces the real Jansen foot path. The
dyad solver returns NaN rather than raising when a design cannot assemble, which is what lets
the optimizer score a bad design without a try/except in the inner loop.

**"Why NSGA-II and not a weighted sum?"** A weighted sum returns one design per choice of
weights and silently hides the shape of the trade-off — and it cannot find any design in a
non-convex region of the front no matter what weights you choose. The whole point of the
result is the shape.

**"Why is the search seeded from Jansen? Isn't that biasing the answer?"** It biases where the
search *starts*, not what counts as good, which is still decided by the objectives and
constraints alone. It is necessary because 0 of 600 uniformly sampled designs are feasible —
see Finding 5. It is a documented deviation; the paper does not say how it initialised.

**"What would you do with another week?"** Close the ground-clearance gap: solve directly for
the link set nearest the holy numbers that gives both 43.3 mm step length and 25.7 mm
clearance. If a solution exists within a few percent of Jansen, that explains the paper's
number. If none exists, that is a stronger statement than "we cannot reproduce it".

**"What is the weakest part of this repo?"** The wear model is Archard with a single unknown
coefficient and a quasi-static force solve — no lubrication regime, no surface finish, no
fatigue. It gives *ratios* between designs, which is all the conclusions need and all the
paper claims, but it is not a life prediction and should never be quoted as one.
