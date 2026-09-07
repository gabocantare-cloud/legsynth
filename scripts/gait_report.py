"""Reproduce Wang (2026) Table 4 with our published metric definitions.

Prints three tables and writes results/gait_metrics.json:

  1. Ours vs the paper, at our default 1%-of-path-height stance band.
  2. Sensitivity: every metric across nine stance bands.
  3. Inversion: for each paper number, the band we would need to reproduce it.

Run:  python scripts/gait_report.py
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from legsynth.kinematics import JansenLeg                     # noqa: E402
from legsynth import metrics as M                             # noqa: E402

JANSEN_BRANCH = (-1, -1, 1, -1, 1)
N_SAMPLES = M.N_PUBLISHED   # one sample count behind every published table
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ORDER = ("step_length", "ground_clearance", "stance_flatness",
         "velocity_ripple", "duty_factor")
LABEL = dict(step_length="Step length", ground_clearance="Ground clearance",
             stance_flatness="Stance flatness", velocity_ripple="Velocity ripple",
             duty_factor="Duty factor")


def fmt(key, value):
    if not np.isfinite(value):
        return "n/a"
    if key == "duty_factor":
        return f"{100 * value:.1f}%"
    if M.METRIC_UNITS[key] == "mm":
        return f"{value:.2f} mm"
    return f"{value:.4f}"


def main():
    leg = JansenLeg(branches=JANSEN_BRANCH)
    path = leg.foot_path(N_SAMPLES)
    H = M.path_height(path)
    ours = M.gait_metrics(path)

    print("Jansen baseline, holy numbers, branch", JANSEN_BRANCH)
    print(f"foot path: {np.ptp(path[:, 0]):.2f} mm wide x {H:.2f} mm tall, "
          f"{N_SAMPLES} crank samples")
    print(f"stance band: {M.DEFAULT_BAND:.1%} of path height "
          f"= {M.DEFAULT_BAND * H:.4f} mm\n")

    print("1. OURS vs PAPER (Wang 2026, Table 4)")
    print(f"{'Metric':<18}{'Ours':>12}{'Paper':>12}{'Diff':>10}")
    print("-" * 52)
    for k in ORDER:
        o, p = ours[k], M.PAPER_TABLE4[k]
        rel = 100.0 * (o - p) / p if p else float("nan")
        print(f"{LABEL[k]:<18}{fmt(k, o):>12}{fmt(k, p):>12}{rel:>9.1f}%")

    print("\n2. SENSITIVITY TO THE STANCE BAND")
    rows = M.tolerance_sweep(path)
    print(f"{'band':>7}{'mm':>9}{'step':>10}{'clear':>9}{'flat':>10}"
          f"{'ripple':>9}{'duty':>8}")
    print("-" * 62)
    for r in rows:
        print(f"{r['band']:>6.1%}{r['tol_mm']:>9.3f}{r['step_length']:>10.2f}"
              f"{r['ground_clearance']:>9.2f}{r['stance_flatness']:>10.4f}"
              f"{r['velocity_ripple']:>9.4f}{100 * r['duty_factor']:>7.1f}%")

    print("\n3. WHAT BAND WOULD REPRODUCE EACH PAPER NUMBER?")
    print(f"{'Paper metric':<18}{'target':>10}{'band needed':>14}{'= mm':>10}")
    print("-" * 52)
    needed = {}
    for k in ORDER:
        b = M.band_matching(path, k, M.PAPER_TABLE4[k])
        needed[k] = b
        if np.isfinite(b):
            print(f"{LABEL[k]:<18}{fmt(k, M.PAPER_TABLE4[k]):>10}"
                  f"{b:>13.2%}{b * H:>10.4f}")
        else:
            print(f"{LABEL[k]:<18}{fmt(k, M.PAPER_TABLE4[k]):>10}"
                  f"{'unreachable':>14}{'-':>10}")

    finite = [b for b in needed.values() if np.isfinite(b)]
    if len(finite) > 1:
        spread = max(finite) / min(finite)
        print("\nSpread between the bands the paper's own numbers "
              f"require: {spread:.0f}x.")
        print("No single stance definition reproduces Table 4's Jansen row.")

    out = dict(
        source="legsynth scripts/gait_report.py",
        branch=list(JANSEN_BRANCH), n_samples=N_SAMPLES,
        lengths=leg.L, path_height_mm=H,
        path_width_mm=float(np.ptp(path[:, 0])),
        default_band=M.DEFAULT_BAND, ours=ours, paper=M.PAPER_TABLE4,
        sweep=rows, band_required_for_paper_value=needed,
    )
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    dest = os.path.join(ROOT, "results", "gait_metrics.json")
    with open(dest, "w") as fh:
        json.dump(out, fh, indent=2, default=float)
    print(f"\nwrote {os.path.relpath(dest, ROOT)}")

    _plot(path, rows)


def _plot(path, rows):
    """Sensitivity figure. Skipped silently if matplotlib is not installed."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed - skipped figures/gait_sensitivity.png")
        return

    bands = np.array([r["band"] for r in rows])
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
    ax1.plot(100 * bands, [r["step_length"] for r in rows], "o-", color="tab:blue")
    ax1.axhline(M.PAPER_TABLE4["step_length"], ls="--", color="0.4",
                label="paper 43.3 mm")
    ax1.axvline(100 * M.DEFAULT_BAND, ls=":", color="tab:red", label="our band")
    ax1.set_xlabel("stance band (% of path height)")
    ax1.set_ylabel("step length (mm)")
    ax1.set_title("Step length vs stance definition")
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.3)

    ax2.plot(100 * bands, [100 * r["duty_factor"] for r in rows], "o-",
             color="tab:green")
    ax2.axhline(100 * M.PAPER_TABLE4["duty_factor"], ls="--", color="0.4",
                label="paper ~20%")
    ax2.axvline(100 * M.DEFAULT_BAND, ls=":", color="tab:red", label="our band")
    ax2.set_xlabel("stance band (% of path height)")
    ax2.set_ylabel("duty factor (%)")
    ax2.set_title("Duty factor vs stance definition")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3)

    fig.tight_layout()
    os.makedirs(os.path.join(ROOT, "figures"), exist_ok=True)
    fig.savefig(os.path.join(ROOT, "figures", "gait_sensitivity.png"), dpi=140)
    print("wrote figures/gait_sensitivity.png")


if __name__ == "__main__":
    main()
