---
name: audit-repro
description: Check that a stranger with a clean checkout of legsynth can install it, run it, and get the published numbers back — that every documented command exists and works, that outputs land where the docs say, and that nothing published depends on a file the repo does not ship. Use when auditing reproducibility, the README quickstart, CI, or scripts/reproduce.py.
---

# Auditing reproducibility

The test is not "does it work here". It is **"does it work for somebody who has only
what git ships"** — which excludes `results/*.json`, since `.gitignore` keeps them out.

## What to check

**Every command in every document runs.** Extract them from `README.md`, `docs/*.md` and
`CLAUDE.md` and run them, or at minimum `--help` them. A command with a renamed flag is
a stranger's first impression.

**The `.gitignore` question.** `results/*.json` and `results/cad/*` are ignored. So a
fresh clone has no results at all, and every documented number has to be regenerable
from a script that ships. Walk the table in `audit-numbers` and confirm each source
script is tracked, runs from a clean tree, and writes where the docs say it does.

**Runtime is documented and true.** If a script takes ten minutes, the doc that tells
somebody to run it should say ten minutes. Time the fast ones; for the campaign-scale
ones, check the `runtime_s` recorded in the JSON against what the prose claims.

**`scripts/reproduce.py` is the single entry point.** Check it actually covers the
published set, and that its `--quick` path writes to `*_quick.json` rather than over the
real outputs — this used to overwrite them.

**Determinism.** Seeds are set where they matter. `optimize.run(workers=N)` is claimed
bit-identical to serial; there is a test, so check the test tests that rather than
something adjacent.

**CI.** `.github/workflows/tests.yml` runs pytest on two Python versions plus a lint job,
and it has never run. Read it for the things that only fail on a fresh machine: an
unpinned `ruff` picking up new default rules, a dependency not in `pyproject.toml`, a
path separator assumption, a test that depends on a `results/` file that CI will not
have.

**Version floors.** `pyproject.toml` claims Python 3.9+. `from __future__ import
annotations` is present, but check for syntax and numpy APIs that need more —
`np.ptp` on an array, `numpy.random.default_rng`, and any 3.10+ syntax.

## How to report

A reproducibility finding needs the exact command and the exact failure. "The quickstart
is stale" is not a finding; "`python scripts/gait_report.py --band 0.02` exits 2, the
flag is `--bands`" is.

Separate three severities: it does not run (S1), it runs but does not produce what the
doc says (S1 or S2 depending on whether a published number is involved), it runs and
produces the right thing but the doc does not say how long or where (S3).
