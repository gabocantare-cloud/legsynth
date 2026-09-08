---
name: audit-portfolio
description: Assess legsynth as a public artifact for the three audiences it has to serve at once — a hiring manager skimming for two minutes, a mechanism-design expert looking for the mistake, and an open-source contributor deciding whether to touch it. Use when auditing the README, the document set, or the repo's presentation before publishing.
---

# Auditing the repo as a portfolio piece

This repo goes to a robotics-team application and to the public at the same time. It has
to work for three readers with incompatible budgets, and the author has said explicitly
that he wants all three served rather than one chosen.

## Reader 1 — the hiring manager, two minutes, on a phone

Gets as far as the README's first screen. Needs, in that space: what this is, that it
reproduces a real paper, what was found, and that it is checkable.

Check: is the headline result above the fold, with the disagreements next to it rather
than three clicks down? Is the single most interesting figure visible? Does the first
paragraph say "reproduction and extension of a 2026 paper whose author released no code"
without requiring a click to understand? Is there a number in the first screen that a
skimmer can carry away?

Failure mode to look for: the honest caveats are so prominent that a skimmer reads
"didn't work". Honesty is non-negotiable, placement is not.

## Reader 2 — the domain expert, hunting for the mistake

This reader is the reason the repo exists. They will go straight to the definitions and
then to whichever claim looks softest.

Check: are the gait metric formulas written down in full, in one place, where a
mechanism person expects them? Is the loaded-versus-unloaded transmission angle argument
made before the number is quoted, since it is the whole extension? Are the
disagreements with Wang (2026) stated as disagreements with the evidence for each, not
hedged and not overclaimed? Is the negative result presented as a negative result?

Failure mode to look for: a claim stated more confidently in a compressed document
(`README.md`, `docs/DEFENDING_THIS.md`) than in its source. This reader will find the
source and hold the author to the stronger version.

## Reader 3 — the contributor, deciding whether to touch it

Needs: install, run the tests, run one thing that produces output, and know which parts
are load-bearing.

Check: does the quickstart work from a clean clone? Is it obvious which modules are
"do not change without re-running X"? Is `docs/STEPS.md` current, or does it describe a
build order that stopped being true two sessions ago? Are the ground rules that look
like bugs — the seeded population, the branch tuple, the stance band as a fraction —
explained where a contributor will hit them, not only in a handoff document?

## Repo-wide

- **One number, one source.** A figure that appears in two documents should be generated
  once. The test count already went stale in three documents at once; that is why the
  README quotes it beside the `pytest` line and nowhere else does.
- **Documents written for an internal audience are now public.** `CLAUDE.md` and
  `docs/NEXT_SESSION.md` will be read by strangers. Anything in them that reads as an
  admission out of context, or that contradicts a public document, is a finding.
- **Consistency of the story across documents.** Read `README.md`,
  `docs/RESULTS.md` and `docs/DEFENDING_THIS.md` back to back and list every place they
  differ in confidence about the same claim.

## Rules

- Presentation findings never justify weakening an honest statement. If the fix for a
  skimmer is to drop a caveat, the finding is rejected.
- Report placement and emphasis separately from correctness, so the fix session can tell
  which is which.
