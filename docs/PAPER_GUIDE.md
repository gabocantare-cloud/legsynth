# How to read the anchor paper — plain version

**Paper:** Jichao Wang, *"Durability-Aware Multi-Objective Optimization of the Jansen
Linkage: Trading Gait Quality Against Joint Wear."* arXiv:2606.22129, 23 June 2026.
**Read it at:** https://arxiv.org/abs/2606.22129

**Budget 90 minutes.** Read Part 1 below first — it defines every word you'll hit. Then read
the paper in the order given in Part 3. Don't read the paper front to back.

---

## The habit that matters more than this document

Any sentence in the paper that stops you, paste it into Claude Code exactly as written and
say:

> Explain this sentence like I'm a mechanical engineering junior who hasn't taken this class.
> Use an analogy. Don't use any new technical words without defining them.

Do that every single time. Do not push past a sentence you don't get. This habit *is* the
skill you said you want to learn — it's not a crutch, it's the actual method.

---

# PART 1 — Every word you'll hit, in plain English

Read this once. Come back to it whenever a word stops you.

### About the mechanism

**Linkage** — a set of rigid bars pinned together. A pair of scissors is a linkage. Your car's
windshield wiper is a linkage.

**Link / bar** — one rigid piece. Can't stretch, can't bend.

**Joint / pin** — where two bars are pinned together so they can rotate. A metal pin sitting
in a hole.

**Revolute joint** — a joint that only rotates, doesn't slide. That's all ten of ours.

**Crank** — the one bar that a motor spins in a full circle. It's the input. Everything else
moves because the crank moves.

**Degree of freedom (1-DOF)** — how many separate inputs you need to know where every part is.
Ours is 1: tell me the crank angle and I can tell you where every single bar is. That's why
one motor drives the whole leg.

**Foot path / coupler curve** — the loop the foot traces as the crank goes around once. This
is the thing the whole paper is about.

**Stance** — the part of the loop where the foot is on the ground pushing the body forward.

**Swing** — the part where the foot is in the air coming back for the next step.

**Duty factor** — what percentage of one crank turn is stance. 20% means the foot is on the
ground for a fifth of each turn.

### About the geometry

**Circle-circle intersection** — the trick the code uses to find where every joint is. If you
know a joint is 50 mm from joint A and 41.5 mm from joint B, then it must sit where a
50 mm circle around A crosses a 41.5 mm circle around B. Draw two overlapping circles: they
cross in **two** places.

**Branch** — which of those two crossing points you pick. Same bar lengths, two different
ways to fold the linkage together — like a folding chair that can collapse two directions.
Five joints × two choices = 32 combinations, and only one is the real Jansen leg. That's why
the code carries `(-1,-1,1,-1,1)`.

**Transmission angle** — *this one is yours, learn it properly.* It's the angle at which one
bar pushes on the next.

> Analogy: pushing a door open. Push perpendicular to the door (90°) and it swings easily.
> Push nearly along the door's edge (near 0°) and you're just crushing the hinge — almost none
> of your force turns into motion.

Near 90° = good, force becomes motion. Near 0° or 180° = bad, force gets dumped into the pin.
Machine design practice says keep the minimum above about 40°. **The paper never checks this.**

### About the forces

**Statics / dynamics** — you know these. Dynamics adds the forces from things accelerating.

**Quasi-static** — a shortcut. It means: work out the positions and speeds from the geometry
first, then solve the forces at each frozen instant as if it were a statics problem. Cheaper
than a full dynamic simulation, accurate when things aren't moving violently. Our leg turns
once per second, so it's fine.

**Finite differences** — how you get speed and acceleration from positions. If you know where
the foot is at each moment, subtract consecutive positions to get speed, then subtract
consecutive speeds to get acceleration. That's it. It's just subtraction and division.

**Constraint** — a rule the mechanism physically can't break. "This bar is exactly 41.5 mm
long." "These two bars stay pinned together." Ten joints' worth of rules.

**Inverse dynamics** — normally you know forces and solve for motion. Here it's backwards: you
already know the motion (from the geometry), and you solve for the forces that must have
caused it. Hence "inverse."

**Constraint Jacobian** — a bookkeeping table. It records, for each rule, how sensitive that
rule is to each part moving. Nothing conceptually deep — it's the organized list of "if this
bar rotates a little, how much does that violate this rule?"

**Lagrange multipliers** — sounds terrifying, is simple here: **they are the pin forces.** When
you solve the math, the numbers that pop out to enforce "these bars stay connected" are
literally the forces in the pins. That's the whole idea. You already met these in Calc III as
the λ in constrained optimization — same object, different use.

**Reaction force** — the force a joint pushes back with. What we're solving for.

### About the wear

**Tribology** — the study of rubbing, friction and wear. That's the whole word.

**Archard's law** — the standard wear equation, and it's almost insultingly simple:

> **Volume worn away = k × (average force) × (sliding distance)**

Push harder → more wear. Slide farther → more wear. `k` is a material constant.

**Wear coefficient (k)** — that constant. Ours is 1e-13, a typical steel-on-steel number.
Nobody knows it precisely. **This matters — see the trick below.**

### About the optimization

**Objective** — a number you're trying to make small. We have two: how badly it walks, and how
much it wears.

**Multi-objective** — two goals that fight each other. You can't have both perfectly.

**Pareto front** — the set of designs where you *can't* improve one goal without hurting the
other.

> Analogy: buying a car with money and speed as your two goals. A $30k car doing 150 mph is
> on the front. A $30k car doing 90 mph is *not* — because the faster one exists at the same
> price, so nobody would ever pick it. The front is the honest menu of real trade-offs.

**Pareto-dominated** — a design that's beaten on *every* goal at once, so there's no reason to
ever choose it. **The paper's headline claim is that Jansen's famous numbers are dominated:
there exist legs that walk better AND wear less, simultaneously.**

**Genetic algorithm / NSGA-II** — how the computer searches. It makes 100 random legs, keeps
the good ones, "breeds" them by mixing their bar lengths, adds small random changes, repeats
80 times. Crude, but it works well when you can't do calculus on the problem.

**Design variables** — what the computer is allowed to change. Here: ten bar lengths, each
allowed to move ±30% from Jansen's value.

### About the paper itself

**arXiv** — a free website where researchers post papers, often before any review.

**Preprint** — a paper posted before peer review. **This one is a preprint by a single
independent researcher.** Not a reason to distrust it — a reason your reproduction has value,
because nobody has checked it.

**Reproduction** — rebuilding someone's result from their written description to see if it
holds. Respected work. It's what you're doing.

---

# PART 2 — The whole paper in one paragraph

A Strandbeest leg is eleven rigid bars driven by one crank. The foot traces a flat-bottomed
loop — flat while pushing the body along the ground, arcing high while swinging back. Theo
Jansen tuned those eleven bar lengths by hand until the walk looked right, and they're famous
enough that people call them "the holy numbers." This paper asks something Jansen never did:
**those lengths make it walk well, but do they make it wear out fast?** Every pin is metal
rubbing in a hole, and wear depends on how hard the pin is pushed and how far it slides. The
paper builds a model of both the walk quality and the wear, has a computer search for better
bar lengths, and finds that Jansen's numbers are beaten on both at the same time.

---

# PART 3 — Read the paper in this order

## Stop 1: Abstract, then jump to Table 4 (10 min)

Table 4 is the whole paper. Jansen's baseline is one row; optimized designs are below it.
**Write these five numbers down on paper by hand:**

| Metric | Jansen | What it means |
|---|---|---|
| Step length | 43.3 mm | How far the body moves per step |
| Ground clearance | 25.7 mm | How high the foot lifts on the return |
| Stance flatness | 0.0281 | How flat the ground stroke is. Lower is better — a wobbly stance makes the body bob up and down |
| Velocity ripple | 0.0956 | How much the foot's speed varies while on the ground. Lower is better — uneven speed makes the body surge and drag |
| Duty factor | ≈20% | Fraction of each crank turn spent on the ground |

These five are your reproduction targets. Everything you build gets checked against them.

## Stop 2: Kinematic Model section (20 min)

This is the part your code **already does**. Read it with `legsynth/kinematics.py` open
beside it and match them up.

Two fixed pivots. The crank tip swings in a circle. Every other joint is found by
intersecting two circles, in a chain, ending at the foot. That's the entire section.

**The one thing to really get:** two circles cross in two places, and picking wrong gives a leg
assembled backwards. That's the branch problem, and it's already solved for you.

## Stop 3: Dynamic Model section (20 min) — slow down here

This finds the force in each of the ten pins. Here's the logic in four sentences:

1. The geometry tells you where everything is, and how fast it's moving, at every instant.
2. The bars have rules they can't break — fixed lengths, joints staying connected.
3. If you know how everything is moving *and* you know the rules, there's exactly one set of
   pin forces that could be making it happen.
4. Solving for that set is inverse dynamics. The answer comes out as Lagrange multipliers,
   which *are* the pin forces.

**Assumptions to write down — you will be asked about these:**

- Flat, 2D. Seven moving bars, ten pins.
- Quasi-static (see glossary).
- **No friction in the joints at all.**
- Gravity on every bar, thin uniform bars at 0.05 kg/m.
- A fixed **20 N** push up from the ground during stance (he also tried 5–100 N).
- Crank spinning at **1 turn per second** (also tried 0.5–4).

## Stop 4: Wear Model section (15 min) — shortest, easiest

Archard's law: worn volume = k × average force × sliding distance. Sliding distance per cycle
is how far the pin twists in its hole (Δφ) times the pin radius (4 mm).

**The clever bit — understand this, it's the paper's best move.** The constant `k` is a guess.
The pin radius is a guess. But the paper only ever reports wear as a **ratio** — new design
divided by Jansen. In a ratio, both guesses appear on top and bottom and **cancel out**. So
"56% less wear" doesn't depend on getting the tribology right at all.

That's genuinely good engineering reasoning, and it's a great thing to point out in an
interview.

## Stop 5: Optimization section (15 min)

Two goals that fight: walk quality vs durability. So the answer isn't one design, it's a
Pareto front — the menu of honest trade-offs.

- **What the computer can change:** ten bar lengths, ±30% each.
- **Rules it must respect:** step length, clearance and duty factor each at least 85% of
  Jansen's, and the leg has to physically assemble.
- **How it searches:** genetic algorithm, 100 designs, 80 generations, three runs merged.

**Headline:** Jansen's design is Pareto-dominated. One example gets 28% flatter stance, 58%
less velocity ripple, and 56% less wear, with no bar changing more than 29%.

## Stop 6: Conclusion / limitations (10 min) — read twice

The author lists his own weaknesses. Know them cold:

- Pins are modeled as **perfect and gap-free.** So the wear numbers are *rankings*, not real
  predictions of how long a leg lasts.
- The wear math uses an **average** force instead of the instantaneous one (he argues this
  costs 3–4%).
- **Nothing was built or tested.** No experiment.
- Ground contact is a made-up fixed load, not real contact physics.

---

# PART 4 — The two gaps you're going to fill

**Gap 1: he never writes down the formulas for stance flatness and velocity ripple.** He
reports the numbers but not the equations, so literally nobody can reproduce his exact values.
Your repo publishes explicit definitions (`docs/METRIC_DEFINITIONS.md`) and shows how much
each number moves when you change the one threshold they all hang on.

**This is now filled, and it turned into a finding.** With our definitions we get 43.49 mm
step length against his 43.3 mm, and 0.0918 velocity ripple against his 0.0956 — both
reproduced. But turn the question around and ask what threshold would be needed to reproduce
*each* of his five numbers, and you get five different thresholds spanning a factor of 90.
His Table 4 Jansen row cannot have come from one consistent definition. His 25.7 mm ground
clearance is taller than our whole foot path, which no threshold can fix. So we report
agreement where we have it and disagreement where we do not, and we do not tune anything to
close the gap. That is the reproducibility result, and it is worth more than a match.

**Gap 2: transmission angle is never mentioned.** Go reread that glossary entry. A paper that
optimizes for *wear*, while allowing designs where bars push on each other at terrible angles,
may be creating legs whose pins get hammered by exactly the thing it's trying to prevent.

**This is also filled, and it got more interesting than expected.** Measured over the whole
crank revolution, Jansen's own linkage bottoms out at 8.6 degrees — which the 40-degree rule
of thumb would call unbuildable. But look at *when*: mid-swing, foot in the air, 0.6 N in the
pin. While the leg is actually carrying the machine it never drops below 42.7 degrees.

So the naive version of your own contribution would have rejected Theo Jansen's linkage for a
defect that costs nothing. The repo enforces the minimum transmission angle **during stance**
instead. If you remember one thing for the interview, remember that the qualifier is the
contribution — anyone can bolt on a constraint, the work is in knowing where it applies.

**Your contribution in one sentence:** *I reproduced this result, and I show what happens to
the trade-off curve when you add the manufacturability constraint the paper leaves out.*

---

# PART 5 — Do you need the other papers?

**No.** Skim two for 15 minutes total, only so you can place your work in the field:

- **LINKS (arXiv:2208.14567)** — a free dataset of 100 million linkages. Shows the field has
  gone data-driven.
- **arXiv:2606.17409** (June 2026) — uses an AI model to generate linkages matching a target
  curve. Also released no code.

The sentence you want to own: *"Most recent mechanism-synthesis work is data-driven and only
optimizes the shape of the curve. This durability paper is unusual because it optimizes a
physical failure mode instead — and my extension adds the manufacturability constraint that
neither one enforces."*

**Do not do a full literature review.** You have eight days.

---

# PART 6 — Self-check

Answer these out loud, no notes. If one is fuzzy, go back — don't move on.

1. What does a Strandbeest leg do, and why does the flat bottom of the foot path matter?
2. How does the code find where each joint is, and what's the "branch" problem?
3. What is Archard's law, in one sentence?
4. Why doesn't the paper's wear conclusion depend on knowing the wear coefficient?
5. What is a Pareto front? What does "Jansen is Pareto-dominated" mean?
6. Name two limitations the author admits to.
7. What is transmission angle, why is ignoring it a problem in a paper about wear, and why
   does it have to be measured *while the foot is loaded*?
8. The paper says averaging the force costs 3-4%. What does it actually cost, and how do you
   know your own two calculations aren't the thing that's wrong?
9. Why is the feasible design space a thin shell around Jansen, and what does that tell you
   about how the step-length constraint interacts with the stance definition?

If you can do all nine, you understand this project better than most people who will read
your repo — including, on at least three specific points, the person who wrote the paper.
