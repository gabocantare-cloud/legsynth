---
name: audit-all
description: Run the full legsynth pre-publication audit and write docs/audit/FINDINGS.md. Use when asked to audit this repo, review it before publishing, check it end to end, or when handed an audit brief. Orchestrates audit-numbers, audit-code, audit-repro, audit-claims and audit-portfolio, then merges their output into one severity-ordered report.
---

# The full audit

This repo is a reproduction of a paper, written by an AI session, documented by the
same AI session. The audit exists because that is a conflict of interest: the prose and
the `results/*.json` it cites came out of one process, so confirming one against the
other proves nothing about either.

## The rule that makes this an audit and not a proofreading pass

**No document in this repo is evidence.** `README.md`, `CLAUDE.md`, `docs/RESULTS.md`,
`docs/NEXT_SESSION.md`, `docs/DEFENDING_THIS.md` and every code comment are the
*subject* of the audit. When you want to know whether something is true, run the code.
When the code and the prose disagree, the prose is wrong until the code is shown to be.

`results/*.json` is a weaker case: it was produced by code in this repo, so it is
evidence of what that code did, but it is *not* evidence that the code was right or
that the prose describes it correctly. Treat a JSON file as a claim about a past run.
Recompute anything cheap. For anything expensive, say in the finding that the number
was inherited rather than regenerated.

## Order of work

Run the five inspectors in this order, because each one narrows what the next has to
consider:

1. **audit-code** — defects in `legsynth/*.py` and `scripts/*.py`. Do this first: a bug
   here invalidates numbers, and a number found wrong later is often this bug.
2. **audit-numbers** — does every published figure recompute? `scripts/verify_docs.py`
   is the mechanical half; the judgement half is in that skill.
3. **audit-claims** — does the evidence support the interpretation? This is the one
   authorised to argue, and the one most likely to find something that matters.
4. **audit-repro** — can a stranger with a clean checkout get the numbers back?
5. **audit-portfolio** — does the repo serve its three audiences at once?

## Severity

- **S1** — a published number is wrong, or a stated conclusion is not supported by the
  evidence offered for it. Someone reading the repo would be misled.
- **S2** — the claim is defensible but the support is thinner than the wording implies,
  or a defect that has not yet corrupted a published number but can.
- **S3** — clarity, consistency, reproducibility friction. Nothing false.

Severity orders the work. It does not decide whether the work happens: **everything
reported is meant to be fixed.** So do not pad the report with trivia, and do not
suppress a real problem because it looks small. If a finding turns out on inspection to
be nothing, delete it rather than downgrading it to S3.

## Deleting a claim is a valid finding

You may recommend that a sentence be weakened or removed. An overstated finding is a
worse outcome for this repo than a missing one, and the author has said so explicitly.
"§7.2's conclusion should be softened to X" is a finding. So is "§7.1's caveat is
already correctly stated and needs no change" — but that one goes in the report's
*confirmed* section, not the findings list.

## Running experiments

You may run new campaigns to settle a contested claim rather than only recommending
one, under two rules:

- **New output goes to `results/audit/`**, never into `results/*.json`, and never into
  `docs/`. You are auditing this repo's evidence; do not become a producer of it.
- **Report the finding either way.** An experiment that confirms the write-up still
  produces a line in the report saying which claim was tested and what came back.

Cost the recommendation. A campaign at `pop=100, gens=80, 3 seeds` is about 10 minutes
on 12 cores; `robustness.py --study X` re-runs whatever that study needs. Annotate each
recommended experiment with its cost so the fix session can order the work — but never
drop a finding because it is expensive to settle.

## The report

Write `docs/audit/FINDINGS.md`. It is read by a session with **no context from this
one**, so every finding carries:

- an ID (`N1`, `C3`, …) and a severity
- the exact file and line, or the exact section and quoted sentence
- what is wrong, in one or two sentences
- **how it was established** — the command that was run, or the reasoning
- **the fix**, concretely enough to apply without re-deriving it, including the option
  of "delete this sentence"
- the cost, if the fix needs compute

End the report with the claims that were checked and *survived*. A fix session that
does not know what was already verified will re-verify it.

## Do not

- Fix anything. This session reports; the next session fixes.
- Push to GitHub, or change git author configuration. Ask first, both times.
- Tune any number to match the paper. A disagreement with Wang (2026) is a result.
- Undo anything on the "Ground rules" list at the bottom of `docs/NEXT_SESSION.md`
  without measuring first — but note that list is prose, so it is also in scope. If a
  ground rule is wrong, that is an S1.
