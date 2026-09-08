"""Check the documents against the code, rather than against each other.

Every number in `README.md` and `docs/` was written by the same process that
produced `results/*.json`, so confirming one against the other proves nothing.
This script recomputes from `legsynth` instead, and pins each recomputed value
to the exact sentence that quotes it.

Each claim therefore fails in two independent ways:

  * **stale text** - the phrase is no longer in the document, so either the
    wording changed under a number that is still checked elsewhere, or the
    number was deleted and this claim is now dead weight;
  * **stale number** - the phrase is still there and the value no longer
    agrees with what the code produces today.

Both are reported, because they need different fixes.

A claim marked `inherited` reads `results/*.json` instead of recomputing. That
is a weaker check - it establishes that the document matches the recorded run,
not that the run was right - and the report labels it so. Campaign-scale claims
are inherited because regenerating one costs ten minutes; run
`scripts/robustness.py` if you need them regenerated.

Run:

    python scripts/verify_docs.py             # every fast claim
    python scripts/verify_docs.py --slow      # also the inherited ones
    python scripts/verify_docs.py --coverage  # numbers no claim covers
    python scripts/verify_docs.py --list      # what is registered

Exit status is non-zero if any claim fails, so CI can use this directly.
"""
from __future__ import annotations

import argparse
import functools
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from legsynth import JansenLeg, JANSEN_BRANCH                     # noqa: E402
from legsynth import metrics as M                                 # noqa: E402
from legsynth import dynamics as D                                # noqa: E402
from legsynth import wear as W                                    # noqa: E402
from legsynth import constraints as C                             # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N = M.N_PUBLISHED


# --------------------------------------------------------------------------
# recomputation, done once and shared
# --------------------------------------------------------------------------

@functools.lru_cache(maxsize=None)
def _leg():
    return JansenLeg(branches=JANSEN_BRANCH)


@functools.lru_cache(maxsize=None)
def _path():
    return _leg().foot_path(N)


@functools.lru_cache(maxsize=None)
def _gait():
    return M.gait_metrics(_path())


@functools.lru_cache(maxsize=None)
def _sol():
    return D.solve_statics(_leg(), n=N)


@functools.lru_cache(maxsize=None)
def _wear():
    return W.wear_per_cycle(_sol())


@functools.lru_cache(maxsize=None)
def _angles():
    """Transmission angle per sample, minimised over the three interfaces."""
    ta = C.transmission_angles(_leg(), n=N)
    per = np.minimum.reduce([ta[k[0]] for k in C.TRANSMISSION_INTERFACES])
    return ta, per


def _at_peak_force():
    """Transmission angle at the crank sample carrying the largest pin force."""
    f = _sol()["forces"]
    i = int(np.unravel_index(np.nanargmax(f), f.shape)[0])
    return float(_angles()[1][i])


def _force_at_worst_angle():
    """Largest pin force at the sample where the whole-cycle angle bottoms out."""
    _, per = _angles()
    j = int(np.nanargmin(per))
    return float(np.nanmax(_sol()["forces"][j]))


def _json(name):
    with open(os.path.join(ROOT, "results", name)) as fh:
        return json.load(fh)


@functools.lru_cache(maxsize=None)
def _audit():
    """The twenty campaigns behind RESULTS section 7's corrected numbers.

    Unlike `results/*.json` this one ships with the repo, so the claims that
    read it are checkable from a fresh clone.
    """
    return _json(os.path.join("audit", "objective_replication.json"))


def _spread(rep, key):
    """(range, sample standard deviation) of one field across the ten pairs.

    Both are returned because the range is what the write-up quotes and the sd
    is what makes it comparable across sample sizes - the range of n samples
    grows with n, which is the error these claims exist to prevent recurring.
    """
    v = [pair[key] for pair in rep["pairs"]]
    return float(max(v) - min(v)), float(np.std(v, ddof=1))


# --------------------------------------------------------------------------
# the registry
# --------------------------------------------------------------------------

class Claim:
    """One published number, pinned to the sentence that publishes it."""

    def __init__(self, cid, doc, phrase, value, compute, tol,
                 inherited=False, note=""):
        self.cid, self.doc, self.phrase = cid, doc, phrase
        self.value, self.compute, self.tol = value, compute, tol
        self.inherited, self.note = inherited, note

    def check(self, text):
        found = self.phrase in text
        try:
            got = float(self.compute())
        except Exception as exc:                                  # noqa: BLE001
            return found, None, f"compute raised: {exc.__class__.__name__}: {exc}"
        ok = abs(got - self.value) <= self.tol
        return found, got, None if ok else "value disagrees"


def pct(a, b):
    """Percentage change from b to a, the way the documents write it."""
    return 100.0 * (a - b) / b


CLAIMS = [
    # ---- the Jansen baseline table, README and RESULTS -------------------
    Claim("G1", "README.md", "| Step length | 43.41 mm |", 43.41,
          lambda: _gait()["step_length"], 0.005),
    Claim("G2", "README.md", "| Ground clearance | 22.23 mm |", 22.23,
          lambda: _gait()["ground_clearance"], 0.005),
    Claim("G3", "README.md", "| Stance flatness | 0.0011 |", 0.0011,
          lambda: _gait()["stance_flatness"], 0.00005),
    Claim("G4", "README.md", "| Velocity ripple | 0.0920 |", 0.0920,
          lambda: _gait()["velocity_ripple"], 0.00005),
    Claim("G5", "README.md", "| Duty factor | 31.2% |", 31.2,
          lambda: 100 * _gait()["duty_factor"], 0.05),
    Claim("G6", "README.md", "our entire 22.46 mm\nfoot path", 22.46,
          lambda: M.path_height(_path()), 0.005),

    # ---- mechanics -------------------------------------------------------
    Claim("M1", "README.md", "peak pin force **25.8 N**", 25.8,
          lambda: float(np.nanmax(_sol()["forces"])), 0.05),
    Claim("M2", "README.md", "force amplification **1.29**", 1.29,
          lambda: float(np.nanmax(_sol()["forces"]) / D.GROUND_REACTION), 0.005),
    Claim("M3", "README.md", "peak crank torque **0.026 N·m**", 0.026,
          lambda: float(np.nanmax(np.abs(_sol()["torque"]))), 0.0005),
    Claim("M4", "README.md", "wear\n**4.67 × 10⁻⁵ mm³** per revolution", 4.67,
          lambda: _wear()["total"] * 1e9 * 1e5, 0.005),

    # ---- the mean-force shortcut ----------------------------------------
    Claim("W1", "README.md", "| **Overestimate** | **+51.3%** |", 51.3,
          lambda: pct(_wear()["total"], _wear()["total_integrated"]), 0.05),
    Claim("W2", "README.md", "| Integrated form | 3.09 × 10⁻⁵ mm³ |", 3.09,
          lambda: _wear()["total_integrated"] * 1e9 * 1e5, 0.005),
    Claim("W3", "README.md", "the crank pin they agree to **0.0%**", 0.0,
          lambda: pct(_wear()["per_joint"][D.JOINT_NAMES.index("O")],
                      _wear()["integrated"][D.JOINT_NAMES.index("O")]), 0.05),

    # ---- the extension ---------------------------------------------------
    Claim("T1", "README.md",
          "| Min transmission angle, whole cycle | **8.6°**", 8.6,
          lambda: float(_angles()[0]["min"]), 0.05),
    Claim("T2", "README.md",
          "| Min transmission angle, during stance | **42.7°**", 42.7,
          lambda: float(_angles()[0]["min_stance"]), 0.05),
    Claim("T3", "README.md", "with **0.6 N** in the pin", 0.6,
          _force_at_worst_angle, 0.05),
    Claim("T4", "README.md", "largest pin force, 25.8 N, arrives at\na healthy 48°",
          48.0, _at_peak_force, 0.5),
    # The same sentence in the module that defines the extension. If this one
    # fails and T4 passes, the code comment and the README disagree.
    Claim("T5", "legsynth/constraints.py",
          "arrives at a perfectly healthy 48 degrees.", 48.0,
          _at_peak_force, 0.5,
          note="cross-checks the constraints.py docstring against T4"),

    # ---- the virtual-work check -----------------------------------------
    Claim("V1", "CLAUDE.md", "residual 4e-5", 4e-5,
          lambda: D.power_residual(_leg(), _sol()), 1e-5),

    # ---- band matching: the paper's row is not one definition ------------
    Claim("B1", "README.md", "| Step length 43.3 mm | 0.98% |", 0.98,
          lambda: 100 * M.band_matching(_path(), "step_length", 43.3), 0.01),
    Claim("B2", "README.md", "| Duty factor ≈20% | 0.35% of path height |", 0.35,
          lambda: 100 * M.band_matching(_path(), "duty_factor", 0.20), 0.01),
    Claim("B3", "README.md", "| Velocity ripple 0.0956 | 1.27% |", 1.27,
          lambda: 100 * M.band_matching(_path(), "velocity_ripple", 0.0956), 0.01),

    # ---- an identity the documents treat as a measurement ----------------
    # ground_clearance == (1 - band) * path_height, exactly, by construction:
    # max(y) - (min(y) + band*H) == (1-band)*H. Any claim that clearance
    # "barely moves with the band" is algebra, not evidence. This claim exists
    # so that a fix session cannot quietly make it untrue.
    Claim("A1", "docs/METRIC_DEFINITIONS.md",
          "| **Ground clearance** | `max(y) - y_ground`, which is exactly", 0.99,
          lambda: M.ground_clearance(_path()) / M.path_height(_path()), 1e-9,
          note="ground clearance is (1 - band) x path height identically"),

    # ---- campaign-scale: inherited from results/*.json --------------------
    Claim("P1", "README.md", "| Wear | 56% less | **24% less** |", 24.0,
          lambda: 100 * (1 - min(r["wear_ratio"]
                                 for r in _json("pareto.json")["paper_front"])),
          0.5, inherited=True),
    Claim("P2", "README.md", "All 20 designs\non the front beat it", 20.0,
          lambda: sum(1 for r in _json("pareto.json")["paper_front"]
                      if r["gait_error"] < 1 and r["wear_ratio"] < 1),
          0.0, inherited=True),
    Claim("P3", "README.md",
          "minimum loaded\ntransmission angle runs 41.9°–52.0°, median 48.3°",
          48.3,
          lambda: float(np.median([r["min_transmission_angle"]
                                   for r in _json("pareto.json")["paper_front"]])),
          0.05, inherited=True),
    # The seed-to-seed spreads RESULTS section 7 uses as its yardstick. These
    # read `results/audit/`, not `results/robustness.json`, because the spread
    # is measured over ten triples and the seeds study on disk was run at
    # three - which is the whole point of the correction. `results/audit/`
    # ships with the repo, so unlike the other inherited claims these two are
    # checkable from a fresh clone.
    Claim("R1", "docs/RESULTS.md",
          "| Hypervolume | 0.0170 (sd 0.0052) | 0.0020 |", 0.0170,
          lambda: _spread(_audit(), "hv_mean")[0], 5e-5, inherited=True,
          note="ten-triple range, results/audit/objective_replication.json"),
    Claim("R2", "docs/RESULTS.md",
          "| Best gait error | 0.0810 (sd 0.0255) | 0.0180 |", 0.0810,
          lambda: _spread(_audit(), "best_gait_mean")[0], 5e-5, inherited=True,
          note="ten-triple range, results/audit/objective_replication.json"),
    Claim("R3", "docs/RESULTS.md",
          "| Hypervolume | 0.0170 (sd 0.0052) | 0.0020 |", 0.0052,
          lambda: _spread(_audit(), "hv_mean")[1], 5e-5, inherited=True,
          note="the sd beside R1's range"),
    Claim("R4", "docs/RESULTS.md",
          "| Best gait error | 0.0810 (sd 0.0255) | 0.0180 |", 0.0255,
          lambda: _spread(_audit(), "best_gait_mean")[1], 5e-5, inherited=True,
          note="the sd beside R2's range"),

    # Section 7.2's verdict, which replaced a finding drawn from one pair.
    Claim("R5", "docs/RESULTS.md", "Mean paired difference \u22120.0036",
          -0.0036,
          lambda: _audit()["delta_mean"], 5e-5, inherited=True,
          note="the paired mean across ten seed triples"),
    Claim("R6", "docs/RESULTS.md", "four of ten\npositive", 4.0,
          lambda: _audit()["n_positive"], 0.0, inherited=True),
    Claim("R7", "docs/RESULTS.md", "is the **maximum of the ten**", 0.0520,
          lambda: _audit()["delta_max"], 5e-5, inherited=True,
          note="the +0.052 the section used to be built on"),

    # ---- section 5, from results/feasibility.json ------------------------
    Claim("F1", "docs/RESULTS.md", "| seed 1 | 122 (20.3%) | **1** |", 20.3,
          lambda: 100 * _json("feasibility.json")["uniform"]["assemble_rate_max"],
          0.05, inherited=True),
    Claim("F2", "docs/RESULTS.md", "| seed 2 | 88 (14.7%) | **0** |", 14.7,
          lambda: 100 * _json("feasibility.json")["uniform"]["assemble_rate_min"],
          0.05, inherited=True),
    Claim("F3", "docs/RESULTS.md",
          "0 or 1 in 600 satisfies the paper's", 1.0,
          lambda: _json("feasibility.json")["uniform"]["feasible_max"], 0.0,
          inherited=True,
          note="the bold 0 was one draw; at seed 1 it is 1"),
    Claim("F4", "docs/RESULTS.md", "only **2.8\u20135.8%** of designs feasible",
          5.8,
          lambda: 100 * _json("feasibility.json")["jitter_study"][
              "feasible_rate_max"], 0.05, inherited=True),

    # ---- the two documents that repeat section 7.2's verdict -------------
    # Both used to carry the retracted version ("1.8x the seed-to-seed
    # spread"). Pinned here so the strong wording cannot come back without a
    # failing claim.
    Claim("D1", "docs/DEFENDING_THIS.md", "averages **\u22120.0036**", -0.0036,
          lambda: _audit()["delta_mean"], 5e-5, inherited=True),
    Claim("D2", "CLAUDE.md", "gait error averages \u22120.0036", -0.0036,
          lambda: _audit()["delta_mean"], 5e-5, inherited=True),
    Claim("D3", "docs/DEFENDING_THIS.md", "against `G_bd`'s 5.89 N mean", 5.89,
          lambda: float(_wear()["mean_force"][D.JOINT_NAMES.index("G_bd")]),
          0.005,
          note="was compared against G_bd's 25.8 N peak, a mean against a peak"),
]


# --------------------------------------------------------------------------
# coverage: numbers in the documents that no claim touches
# --------------------------------------------------------------------------

DOCS = ("README.md", "CLAUDE.md", "docs/RESULTS.md", "docs/METRIC_DEFINITIONS.md",
        "docs/DEFENDING_THIS.md", "docs/PAPER_GUIDE.md", "docs/STEPS.md")

NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w])")

#: Numbers that are not claims about our own results: the paper's reported
#: figures, the holy numbers, section numbers, years, and physical constants
#: stated as inputs rather than measured as outputs.
NOT_OURS = {
    "2026", "2606.22129", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11",
    "0", "1", "20", "90", "12", "21",
}


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def coverage():
    """Report numeric literals in the documents that no claim pins."""
    covered = {}
    for c in CLAIMS:
        covered.setdefault(c.doc, []).append(c.phrase)
    total_miss = 0
    for rel in DOCS:
        text = read(rel)
        pins = covered.get(rel, [])
        residue = text
        for p in pins:
            residue = residue.replace(p, " ")
        misses = [m for m in NUMBER.findall(residue) if m not in NOT_OURS]
        uniq = sorted(set(misses), key=lambda s: -len(s))
        total_miss += len(uniq)
        print(f"\n{rel}: {len(pins)} claim(s) registered, "
              f"{len(uniq)} distinct unpinned number(s)")
        if uniq:
            print("   " + "  ".join(uniq[:40]) + ("  ..." if len(uniq) > 40 else ""))
    print(f"\n{total_miss} distinct unpinned numbers across {len(DOCS)} documents.")
    print("Most are the paper's own figures or prose rounding. The ones to chase "
          "are results of ours that nobody registered.")
    return 0


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slow", action="store_true",
                    help="also check the claims inherited from results/*.json")
    ap.add_argument("--coverage", action="store_true",
                    help="list numbers in the documents that no claim covers")
    ap.add_argument("--list", action="store_true", help="list the registry")
    args = ap.parse_args()

    if args.list:
        for c in CLAIMS:
            tag = "inherited" if c.inherited else "recomputed"
            print(f"{c.cid:<4} {tag:<10} {c.doc:<28} {c.value!r}")
        return 0
    if args.coverage:
        return coverage()

    texts = {}
    fails, skipped = [], 0
    for c in CLAIMS:
        if c.inherited and not args.slow:
            skipped += 1
            continue
        if c.doc not in texts:
            texts[c.doc] = read(c.doc)
        found, got, err = c.check(texts[c.doc])
        gotstr = "-" if got is None else f"{got:.6g}"
        if not found or err:
            fails.append((c, found, got, err))
            why = []
            if not found:
                why.append("PHRASE NOT FOUND")
            if err:
                why.append(err)
            print(f"FAIL {c.cid:<4} {c.doc:<28} says {c.value!r}, code says "
                  f"{gotstr}   [{'; '.join(why)}]")
        else:
            tag = "~" if c.inherited else " "
            print(f"ok  {tag}{c.cid:<4} {c.doc:<28} {c.value!r} == {gotstr}")
        if c.note:
            print(f"       note: {c.note}")

    print(f"\n{len(CLAIMS) - skipped - len(fails)} passed, {len(fails)} failed"
          + (f", {skipped} inherited claims skipped (use --slow)" if skipped else ""))
    if fails:
        print("\nA failed claim is one of three things: the document is wrong, the "
              "code changed and the document was not updated, or this claim is "
              "stale. Decide which before editing either.")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
