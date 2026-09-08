"""How much of the paper's design box is actually usable, across several draws.

`docs/RESULTS.md` section 5 reports that of 600 designs drawn uniformly from the
paper's own +/-30% box, about a sixth assemble at all and essentially none
satisfy the paper's own constraints. That is the number licensing
`optimize.seeded_population`, which is this repo's one documented deviation from
the paper, so it is worth being able to regenerate rather than remember.

It is also a number that has to be quoted as a *range*. Both figures are
properties of a random draw, not of the box: at one seed zero of 600 designs are
feasible, at another it is one. Quoting a single draw as "0 of 600" makes a
sampling accident look like a property of the mechanism. So this script draws at
several seeds and reports the spread.

Two experiments:

  uniform   designs drawn uniformly across the whole box. Answers "could you
            search this box without knowing where Jansen is?"
  jitter    designs drawn by perturbing Jansen's own lengths by a small
            percentage. Answers "how thin is the feasible shell around a design
            that is already good?"

Feasibility is the paper's own constraint set, exactly as `optimize.evaluate`
applies it in the search: step length, ground clearance and duty factor each at
least 0.85x Jansen's, plus a branch-margin floor. Our transmission-angle
extension is *not* enforced here - the point is what the paper's box gives you
under the paper's rules.

Writes results/feasibility.json. Run:

    python scripts/feasibility.py              # 600 designs at seeds 0, 1, 2
    python scripts/feasibility.py --quick      # smoke test, writes *_quick.json
"""
import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from legsynth.kinematics import HOLY, DESIGN_KEYS             # noqa: E402
from legsynth import optimize as O                            # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Designs per draw. 600 is what section 5 published; it is large enough that
#: the assembly rate is stable to about a percentage point and small enough that
#: three seeds cost about ten minutes.
N_DESIGNS = 600

#: Seeds to draw at. Three is the minimum that shows a range rather than a
#: point, and the feasible count is small enough that the range is the whole
#: story.
SEEDS = (0, 1, 2)

#: Relative jitter on each of Jansen's ten lengths for the second experiment.
JITTER = 0.02


def draw_uniform(n, seed):
    """`n` design vectors drawn uniformly across the paper's +/-30% box."""
    lo, hi = O.bounds()
    return np.random.default_rng(seed).uniform(lo, hi, size=(n, len(lo)))


def draw_jitter(n, seed, jitter=JITTER):
    """`n` design vectors from Jansen's lengths, each perturbed by `jitter`."""
    rng = np.random.default_rng(seed)
    base = np.array([HOLY[k] for k in DESIGN_KEYS], float)
    X = base * (1.0 + rng.normal(0.0, jitter, size=(n, len(base))))
    lo, hi = O.bounds()
    return np.clip(X, lo, hi)


def score(X, baseline):
    """Assembly and feasibility counts for a block of design vectors.

    A design "assembles" when the dyad cascade closes at every crank angle and
    every metric it needs comes back finite - `evaluate` returns its penalty row
    otherwise. It is "feasible" when it also satisfies the paper's four
    constraints, which is `g <= 0` on every entry.
    """
    n_assemble = n_feasible = 0
    for x in X:
        f, g, raw = O.evaluate(x, baseline)
        if not (raw["assembles"] and np.all(np.isfinite(f))):
            continue
        n_assemble += 1
        if np.all(g <= 0.0):
            n_feasible += 1
    return n_assemble, n_feasible


def study(label, drawer, n, seeds, baseline):
    """Run one experiment at every seed and summarise the spread."""
    rows = []
    for seed in seeds:
        t = time.perf_counter()
        n_assemble, n_feasible = score(drawer(n, seed), baseline)
        rows.append(dict(seed=seed, n=n, assemble=n_assemble,
                         feasible=n_feasible,
                         assemble_rate=n_assemble / n,
                         feasible_rate=n_feasible / n,
                         seconds=time.perf_counter() - t))
        print(f"  {label:8s} seed {seed}: {n_assemble:4d}/{n} assemble "
              f"({100 * n_assemble / n:.1f}%), {n_feasible:3d} feasible "
              f"({100 * n_feasible / n:.1f}%)   [{rows[-1]['seconds']:.0f}s]",
              flush=True)
    a = [r["assemble_rate"] for r in rows]
    f = [r["feasible_rate"] for r in rows]
    return dict(label=label, n=n, seeds=list(seeds), draws=rows,
                assemble_rate_min=min(a), assemble_rate_max=max(a),
                feasible_min=min(r["feasible"] for r in rows),
                feasible_max=max(r["feasible"] for r in rows),
                feasible_rate_min=min(f), feasible_rate_max=max(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=N_DESIGNS,
                    help=f"designs per draw (default {N_DESIGNS})")
    ap.add_argument("--seeds", type=int, nargs="+", default=list(SEEDS),
                    help="seeds to draw at")
    ap.add_argument("--quick", action="store_true",
                    help="60 designs at two seeds; writes feasibility_quick.json")
    args = ap.parse_args()

    n = 60 if args.quick else args.n
    seeds = [0, 1] if args.quick else args.seeds

    print(f"{n} designs per draw, seeds {seeds}, "
          f"scored at n={O.N_EVAL} crank samples")
    baseline = O.jansen_baseline()

    t0 = time.perf_counter()
    out = dict(
        n=n, seeds=list(seeds), jitter=JITTER, n_eval=O.N_EVAL,
        uniform=study("uniform", draw_uniform, n, seeds, baseline),
        jitter_study=study(f"{100 * JITTER:.0f}% jitter",
                           lambda k, s: draw_jitter(k, s), n, seeds, baseline),
    )
    out["runtime_s"] = time.perf_counter() - t0

    u, j = out["uniform"], out["jitter_study"]
    print(f"\nuniform: {100 * u['assemble_rate_min']:.1f}-"
          f"{100 * u['assemble_rate_max']:.1f}% assemble; "
          f"{u['feasible_min']}-{u['feasible_max']} of {n} feasible")
    print(f"{100 * JITTER:.0f}% jitter: "
          f"{100 * j['feasible_rate_min']:.1f}-"
          f"{100 * j['feasible_rate_max']:.1f}% feasible")

    name = "feasibility_quick.json" if args.quick else "feasibility.json"
    path = os.path.join(ROOT, "results", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"wrote results/{name} ({out['runtime_s']:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
