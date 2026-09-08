---
name: audit-claims
description: Challenge the interpretations in legsynth's docs, not just the arithmetic — whether the evidence actually supports the conclusion drawn from it, whether a comparison is between comparable things, and whether a claim's confidence matches its sample size. Use when auditing docs/RESULTS.md, README.md, CLAUDE.md or docs/DEFENDING_THIS.md, or whenever a sentence asserts what a number means.
---

# Auditing the claims

This is the inspector authorised to argue. The other four ask whether the numbers are
right; this one asks whether the sentences built on them are earned.

**Weakening or deleting an overstated claim is a good outcome.** A repo that overclaims
hurts its author more than a smaller honest one, and that is the author's own stated
standard. Do not soften a real objection into a suggestion.

## The four questions to put to every load-bearing sentence

**1. Is the yardstick strong enough for the difference it is measuring?**
A noise estimate built from three campaigns can establish *order of magnitude*. It
cannot support a ratio quoted to two significant figures, and it cannot adjudicate a
difference of its own size. Every time a document says "X is N times the seed-to-seed
spread" or "smaller than the spread", find out how many runs the spread came from and
whether the document elsewhere admits that number is soft. **An internal inconsistency —
a caveat stated in one section and then ignored in the next — is the highest-value thing
this skill finds, because both halves were written by the same session and neither
noticed the other.**

**2. Is the comparison between comparable quantities?**
Two campaigns that each normalise against their own baseline both land at (1, 1)
honestly, and their values are then not comparable with each other. A number's meaning
travels with its denominator. Check every table whose rows come from different
campaigns, and every sentence that puts a number from one study next to a number from
another.

**3. Is the statistic the one the document itself endorses?**
If a preamble argues that some measure is untrustworthy — "best gait error can be moved
by one lucky design at one corner" — then a later section resting its conclusion on that
same measure is contradicting its own methodology. Read the methodology paragraph and
the conclusion paragraph together, not separately.

**4. Would the sentence survive one more run?**
For each verdict, ask what would have to come back differently to flip it, and how
likely that is given the spread already measured. A verdict with a 0.0004 margin
computed from three samples is a coin flip presented as a finding. Where the margin is
thin, the fix is either more seeds or softer wording — and recommending the softer
wording is a legitimate answer, not a cop-out.

## The claims that are load-bearing here

Ranked by how much of the repo falls over if they are wrong:

1. **Jansen is Pareto-dominated.** The central reproduction. Survives in every study run
   so far, at every band, under either wear definition. Strongest claim in the repo.
2. **The constraint is non-binding at 40 degrees / the residual gap is noise.** The
   negative result. Measured at ten seed triples: a hypervolume margin of 0.0020 against
   a spread of 0.0170, a factor of 8.5. Best supported claim in section 7. (It rested on
   0.0020 against a three-campaign spread of 0.0024 until that spread was re-measured.)
3. **The mean-force shortcut changes the absolute wear figures by 51% and, at ten seed
   triples, does not detectably move the optimum.** The stronger version - that it moves
   the optimum - was published off one paired campaign, withdrawn when the pair turned
   out to be the maximum of ten differences averaging -0.0036. Watch this one in both
   directions: the null is not evidence that the bias cancels either.
4. **The magnitude disagreements with Wang (2026) are real, not definitional.** Rests on
   the band sweep and the clearance investigation.
5. **The loaded/unloaded transmission-angle distinction is what makes the extension
   work.** Rests on the 8.6 vs 42.7 degree measurement, which is cheap to recheck.

## Rules

- A claim about the *paper* needs the paper's own numbers quoted as the paper's, and our
  disagreement documented as a disagreement. Never tune to close a gap.
- A negative result stays a negative result. Watch for it being quietly upgraded into a
  benefit between one document and the next — `README.md` and `docs/DEFENDING_THIS.md`
  are where that happens, because they compress.
- The compressed documents inherit the caveats of the source. If `RESULTS.md` carries a
  caveat and `DEFENDING_THIS.md` drops it, that is a finding against the second document
  even though every number in it is right.
- Propose the specific experiment that would settle a disputed claim, with its cost, in
  preference to expressing vague doubt.
