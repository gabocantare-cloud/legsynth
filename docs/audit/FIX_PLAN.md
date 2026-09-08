# Handoff to the fix session — work the audit findings

You are session 3 of a three-session chain: session 1 built the repo, session 2 audited it
and wrote [`FINDINGS.md`](FINDINGS.md), and **you fix everything in it**. You have no
context from either. Everything you need is in this directory.

**Read [`FINDINGS.md`](FINDINGS.md) in full before touching a file.** This plan is the work
order and the exact edit locations; `FINDINGS.md` is the evidence and the reasoning. Where
they appear to disagree, `FINDINGS.md` is authoritative — it has the measurements.

**State on arrival:** 91 tests passing, `ruff` clean, 8 commits on `main`, `.gitignore`
modified and four paths untracked (`.claude/`, `docs/audit/`, `results/audit/`,
`scripts/verify_docs.py`). Nothing has ever been pushed.

---

## Ground rules

- **Do not push to GitHub. Do not change git author configuration. Ask before either.**
  Gabriel does the push himself, after this session.
- **The corrections make the repo's claims weaker, and that is the intended outcome.**
  §7.2 goes from a finding to a null; §7.3 loses its design guideline. Do not look for a
  way to preserve the stronger wording. A repo that overclaims hurts him more than a
  smaller honest one — that is his standard and it is written into `CLAUDE.md`.
- **Never tune a number to match the paper.** Disagreements with Wang (2026) are findings.
- **Do not re-derive the audit.** `FINDINGS.md` lists what was checked and survived; do not
  re-verify the baseline table, the 51.3% shortcut, the virtual-work residual or the
  band-matching table.
- **`results/audit/objective_replication.json` holds the 20 campaigns behind the §7
  corrections.** Quote from it. Do not re-run them; they cost 62 minutes.
- **Everything in `FINDINGS.md` is meant to be fixed.** Severity orders the work, it does
  not decide whether the work happens.

## Skills available

`.claude/skills/` has six inspectors from the audit. `audit-numbers` and `audit-claims` are
the useful ones here — invoke them when you are unsure whether a rewrite is honest, and run
`audit-all` at the end as a regression pass.

---

## Stage A — the §7 corrections (S1, do first, ~1 h, no compute)

This is the substance. Five documents assert claims the audit measured and refuted. All of
Stage A is prose; every number you need is in `FINDINGS.md` [E1](FINDINGS.md#e1) and
[C4](FINDINGS.md#c4).

### A1. Rewrite `docs/RESULTS.md` §7.2 — findings [E1](FINDINGS.md#e1), [C2](FINDINGS.md#c2)

| Line | What is there now |
|---|---|
| 365 | Heading: "The paper's mean-force shortcut **changes the answer**, not only the magnitude" |
| 380 | "**The front moves, and it moves by more than the noise.**" |
| 391-393 | "0.658 to 0.710 … that change of 0.052 is **1.8 times the 0.0297 seed-to-seed spread**" |
| 402-405 | "**'The bias partly cancels' does not survive.**" |

The measured replacement, at ten seed triples: mean paired difference **−0.0036**, sd
0.0231, **95% CI [−0.018, +0.011]**, four of ten positive, and the published +0.052 is the
**maximum of the ten**. Use the suggested verdict paragraph in
[E1's "Fix for §7.2"](FINDINGS.md#e1) — it is written to drop in.

Retitle the section. "Changes the answer, not only the magnitude" is the claim being
withdrawn. Something like *"The paper's mean-force shortcut inflates the magnitude — and, at
ten seed triples, does not move the optimum."*

Add the ten-triple table from [E1](FINDINGS.md#e1) so the null is shown rather than
asserted, and per [C2](FINDINGS.md#c2) say plainly why: hypervolume is unusable across the
two wear definitions, best gait error is the only comparable axis, and at one pair it was
too noisy to carry a conclusion. That turns §7's internal contradiction into a worked
example of its own preamble's warning, which is a better section than the one there now.

**Careful about direction.** Ten null triples remove the evidence that *refuted* "the bias
partly cancels". They are not proof that it does cancel. Write "no detectable effect at ten
seed triples", never "the bias cancels".

### A2. Rewrite `docs/RESULTS.md` §7.3 — finding [C4](FINDINGS.md#c4)

| Line | What is there now |
|---|---|
| 412 | Heading: "The constraint is free at 40° **and expensive by 45°**" |
| 427-429 | "2.9% … smaller than the 3.5% the seed alone moves it … 11.1% … more than three times that spread, so it is [a cost]" |
| 443-445 | The one-line design guideline |

The seed-alone hypervolume movement is **24.9%**, not 3.5%. At that yardstick, 45° (11.1%)
and 50° (13.0%) are both **inside noise**. Delete the design guideline at 443; it quantifies
a cost this data cannot resolve. Use the replacement paragraph in
[C4's "Fix"](FINDINGS.md#c4).

**Keep the figure and keep 55°.** 100% hypervolume lost, best gait 2.343, nine feasible
designs and none beating Jansen — that is far outside noise and needs no defending. Keep the
observation that Jansen's own 42.7° sits inside the free region. Re-caption
`figures/threshold_sweep.png` to the surviving claim. Retitle the section to something like
*"The constraint is free at 40° and impossible at 55°"*.

### A3. Fix `docs/RESULTS.md` §7.1's spread table and the §7 preamble — [C1](FINDINGS.md#c1)

Lines **347-350**: replace the three-triple spreads with the ten-triple ones.

| | published (3 triples) | correct (10 triples) |
|---|---|---|
| Hypervolume | 0.0024 | **0.0170** (sd 0.0052) |
| Best gait error | 0.0297 | **0.0810** (sd 0.0255) |

**§7.1's verdict does not change — it gets stronger.** The constrained-40° front still sits
inside the unconstrained range on both axes (hypervolume 0.0664 in 0.0514–0.0684; best gait
0.676 in 0.658–0.739), and the gap is now 0.0020 against 0.0170, a factor of 8.5 rather than
1.2. Rewrite the caveat at line 359 accordingly: the spread is now measured at ten
campaigns, and the negative result is the best-supported claim in §7. Say so.

### A4. Add the caveat to `docs/RESULTS.md` §7.4 — [C1](FINDINGS.md#c1)

Lines **473-475**, the 43.0 / 34.2 / 27.5 improvement table. Consecutive band rows are 0.088
and 0.067 apart in best gait error, against a measured seed spread of **0.081**. One campaign
per row. Keep the qualitative result — Jansen dominated at every band, 7/7, 20/20, 15/15, far
outside noise — and keep the physical mechanism §7.4 gives for the direction. Mark the
magnitude trend indicative rather than measured.

### A5. Propagate to the four downstream documents

Every one of these compresses §7.2 or §7.3 and inherits the retracted claim:

| File | Line | What to fix |
|---|---|---|
| `docs/RESULTS.md` | 126-131 | §3's back-reference: "when it was finally measured it turned out to be wrong … The shortcut misplaces the *optimum*" |
| `README.md` | 104-105 | "moves the Pareto front by more than the search's own run-to-run noise … it moves where the optimum is" |
| `README.md` | 181-183 | "Sweeping the threshold turns the null into a design guideline … §7 says where" |
| `CLAUDE.md` | 130 | "0.658 to 0.710, which is 1.8x the seed-to-seed spread" |
| `docs/DEFENDING_THIS.md` | 94-101 | Finding 2's "1.8 times", "it moves the optimum", and the interview answer "mostly, but not enough" |
| `docs/DEFENDING_THIS.md` | 348 | "turn 'free at 40°, expensive by 45°' into an exact number" |
| `docs/NEXT_SESSION.md` | 192 | The ground rule "the optimum moves by 1.8× the seed-to-seed spread" |
| `docs/NEXT_SESSION.md` | 81, 102 | Two references to the "free at 40°, expensive by 45°" curve |

Rewrite the `NEXT_SESSION.md` ground rule (192) to: *the objective-swap comparison was
measured at ten seed triples and came back null; do not re-assert movement of the optimum
without new evidence.* Do not delete the rule — it still guards against re-asserting either
direction.

`docs/DEFENDING_THIS.md` is the interview-facing document, so its Finding 2 needs the most
care. The honest interview answer to "doesn't it all cancel in the ratio?" is now: *we
measured it at ten seed triples and found no detectable effect on the reachable gait
quality; what does survive is that the absolute wear figures are high by 51%.*

---

## Stage B — the one-liners (S1/S2, ~15 min, no compute)

- **[N1](FINDINGS.md#n1)** — `legsynth/constraints.py:63`: `56 degrees` → `48 degrees`. This
  is the only failing claim in `verify_docs.py`; fixing it turns the run green.
- **[P1](FINDINGS.md#p1)** — `README.md:24`: `# 90 tests` → `# 91 tests`, or better, drop
  the count entirely and write `# the suite`, since the reader is running the command that
  prints it.
- **[R2](FINDINGS.md#r2)** — `README.md:33`: "Every number below is generated by that
  command" is false. Name the command that is actually true, or extend the default stages.
  Do this **after** Stage C, which is what makes the stronger version true.
- **[P3](FINDINGS.md#p3)** — `docs/DEFENDING_THIS.md:102`: "4.03 N mean against `G_bd`'s
  25.8 N peak" → "against `G_bd`'s 5.89 N mean". The point survives, the comparison becomes
  like-for-like.
- **[P4](FINDINGS.md#p4)** — reconcile the campaign runtime across `docs/RESULTS.md` §6
  ("20 minutes on one laptop core"), `README.md` and `CLAUDE.md` ("~10 min, all cores").

---

## Stage C — the feasibility script (S1, ~30 min writing + ~15 min compute)

Findings [R1](FINDINGS.md#r1) and [N2](FINDINGS.md#n2) are one job. `docs/RESULTS.md` §5
(line 178) publishes numbers that **no script in this repo produces**, and they are
single-draw values presented as facts.

Write `scripts/feasibility.py`:

- Draw *n* designs uniformly from `optimize.bounds()` at several seeds; report the assembly
  rate and the feasibility rate per seed and as a range.
- Do the same for the 2% jitter variant around `HOLY`.
- Write `results/feasibility.json`.
- Add it to `STAGES` in `scripts/reproduce.py` — it is minutes, not tens of minutes.

Measured during the audit, so you know what to expect:

| | seed 0 | seed 1 | seed 2 | published |
|---|---|---|---|---|
| uniform, assemble | 103/600 (17.2%) | 122/600 (20.3%) | 88/600 (14.7%) | "17%" |
| uniform, feasible | **0** | **1** | **0** | "**0**" |
| 2% jitter, feasible | 2.8% | 5.8% | 4.0% | "4%" |

Then rewrite §5 from the script's output: "14.7–20.3% assemble at all; 0 or 1 in 600
satisfies the paper's constraints" and "2.8–5.8% under a 2% jitter". **Keep the
conclusion** — the feasible set is a thin shell around Jansen, and the seeded population is
justified — it is only the wording that was over-precise. Update the five other copies
(`README.md:188`, `CLAUDE.md:142`, `docs/NEXT_SESSION.md:181`,
`docs/DEFENDING_THIS.md:200` and `:333`, `legsynth/optimize.py:233`).

---

## Stage D — code hygiene (S2/S3, ~45 min, no compute)

- **[C3](FINDINGS.md#c3)** — `scripts/robustness.py:study_seeds`: make `verdict`
  three-valued (`noise` / `cost` / `inconclusive` when the two are within ~25%), and record
  the margin in the JSON. Raise `SEED_TRIPLES` to the ten triples the audit ran.
- **[C1](FINDINGS.md#c1), the code half** — `scripts/robustness.py:spread()` returns
  `max − min`, which shrinks the fewer campaigns you run. That is what caused this whole
  class of error. Return the standard deviation alongside the range and have callers compare
  against it.
- **[N3](FINDINGS.md#n3)** — state in `docs/METRIC_DEFINITIONS.md`, beside the formula
  table, that ground clearance is exactly `(1 − band) × path height`, so it measures path
  height and scales linearly with the band. Then say "path height" where that is what
  `metrics.py`, RESULTS §6 and RESULTS §8 mean. **No conclusion changes**, and §8's argument
  gets stronger: "25.7 mm cannot come from a 22.46 mm path" becomes exact rather than a
  bound. Claim `A1` in `verify_docs.py` pins the identity to 1e-9.
- **[K1](FINDINGS.md#k1)** — `legsynth/wear.py:107-110`, delete the dead first
  `mean_force` computation.
- **[K2](FINDINGS.md#k2)** — `legsynth/constraints.py:213`, give `check()` a `band`
  parameter and pass it through. Add it to
  `test_the_stance_band_reaches_the_statics_as_well_as_the_metrics`.
- **[K3](FINDINGS.md#k3)** — reconcile the sample-count defaults in `constraints.py`
  (720 / 720 / 360 across three entry points), or document why each differs.
- **[K4](FINDINGS.md#k4)** — `legsynth/dynamics.py:275`, make the touchdown edge mask
  symmetric and re-check the residual, or comment why the asymmetry is intended.
- **[P2](FINDINGS.md#p2)** — `docs/STEPS.md`: "5 tests pass" → "the suite passes", and add
  a Step 8 covering `robustness.py` and `clearance_fit.py`.

---

## Stage E — wire the verifier into CI (S3, ~15 min)

`.github/workflows/tests.yml` has never run. Three changes, from
[R3](FINDINGS.md#r3):

- Add a step running `python scripts/verify_docs.py` — this is the whole point of having
  written it, and it is what stops the docs drifting from the code again.
- Pin `ruff` (`pip install ruff==0.16.6`); the tree is clean on that version and a newer
  one with new default rules will fail the lint job on something cosmetic.
- `pyproject.toml` claims `requires-python = ">=3.9"` but CI tests only 3.10 and 3.12.
  Either add 3.9 to the matrix or raise the floor to 3.10.

`.gitignore` is already fixed — `results/audit/` ships with the repo, so E1's evidence is
checkable. Nothing to do there.

---

## Stage F — register, verify, commit

1. **Register the corrected numbers as claims** in `scripts/verify_docs.py`. Every number
   you change in Stage A and Stage C should get a `Claim` entry so it cannot drift again —
   that is what the registry is for. Add at minimum: the ten-triple spreads, the §7.2 paired
   mean, and the feasibility ranges.
2. `python -m pytest -q` — 91 tests, plus whatever you added.
3. `python -m ruff check .` — must be clean.
4. `python scripts/verify_docs.py --slow` — must be **29/29**. It is 28/29 today; N1 is the
   failure.
5. `python scripts/verify_docs.py --coverage` — read the unpinned numbers in the files you
   edited and pin anything that is a result of ours.
6. Invoke the `audit-claims` skill and re-read the rewritten §7 cold. Ask its four
   questions of your own new text. This is the step most likely to catch a rewrite that
   softened the wording without softening the claim.
7. Commit in logical chunks — the §7 corrections, the feasibility script, the code hygiene,
   the CI changes — with `docs/audit/` and `results/audit/` included so the audit trail
   ships.
8. **Stop.** Do not push. Tell Gabriel what changed and hand the push back to him.

---

## Exit criteria

- Every finding in `FINDINGS.md` is either fixed or has a one-line note in this file saying
  why it was not, and Gabriel has agreed to that.
- `verify_docs.py --slow` is green.
- No document claims §7.2's front movement, §7.3's design guideline, or "0 of 600" as a
  bare fact.
- `docs/NEXT_SESSION.md` reflects the post-fix state, and its P0 (the push) is now the top
  of the list rather than blocked.

## What is deliberately left undone

- **The §7.3 threshold sweep at ten seed triples per threshold** (~2 h). It would locate the
  knee properly instead of stating that this data cannot. The softened §7.3 wording is fully
  supported without it, so this is an upgrade, not a blocker — record it in
  `docs/NEXT_SESSION.md` as a P2 alongside the existing item about sampling 41-44°.
- **The push, and `CITATION.cff`'s guessed repository URL.** Both are Gabriel's, both after
  this session. See `docs/NEXT_SESSION.md` P0.


---

## Done — what the fix session actually did

Every finding in `FINDINGS.md` was fixed. Nothing was skipped, so the "one-line note
saying why not" the exit criteria ask for is empty.

Exit state: `pytest` 91 passed, `ruff` clean on 0.16.6, `verify_docs.py --slow`
**40 passed, 0 failed** (28/29 on arrival; the registry grew from 29 claims to 40 because
Stage F registered the corrected numbers).

Notes on the three places the work differed from the plan:

- **Stage C cost 45 seconds, not 15 minutes.** `scripts/feasibility.py` reproduces the
  audit's table exactly — 103 / 122 / 88 assembling, 0 / 1 / 0 feasible, 2.8 / 5.8 / 4.0%
  under the jitter — which is an independent confirmation of [N2](FINDINGS.md#n2) rather
  than an inherited number. Because it is that cheap it went into the default `STAGES`,
  which is what makes `README.md`'s "every number below" sentence true for §5.
- **`study_objective` now runs every seed triple, not `SEED_TRIPLES[0]`.** Raising
  `SEED_TRIPLES` to ten alone would have left a script that reproduces the single pair the
  write-up just retracted. It reports the paired mean, sd, 95% CI and the count of positive
  differences, in the same shape as `results/audit/objective_replication.json`.
- **`figures/threshold_sweep.png` was regenerated.** It draws the seed-spread band behind
  the curve, and that band was the three-triple 0.0024 — seven times too narrow, which made
  the middle of the sweep look resolved. `make_figures.seed_spread_hypervolume()` now takes
  it from `results/audit/` when present and labels the number of triples.

Still deliberately undone, both recorded in `docs/NEXT_SESSION.md`: the §7.3 threshold sweep
at ten triples per threshold (~2 h, an upgrade rather than a correction), and the push.
