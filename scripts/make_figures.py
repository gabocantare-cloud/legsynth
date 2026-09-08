"""Generate every figure in the README.

Reads results/pareto.json where it needs optimization output, and skips those
figures with a message if the search has not been run yet.

Run:  python scripts/make_figures.py
"""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from legsynth.kinematics import JansenLeg   # noqa: E402
from legsynth import dynamics as D, wear as W    # noqa: E402
from legsynth import constraints as C, optimize as O           # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "figures")
JANSEN_BRANCH = (-1, -1, 1, -1, 1)

BARS = [("O", "J1"), ("J1", "J2"), ("G", "J2"), ("J2", "J3"), ("G", "J3"),
        ("J1", "J4"), ("G", "J4"), ("J3", "J5"), ("J4", "J5"), ("J4", "F"),
        ("J5", "F")]


def _save(fig, name):
    os.makedirs(FIG, exist_ok=True)
    path = os.path.join(FIG, name)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    print(f"wrote figures/{name}")


def load_results(name="pareto.json"):
    path = os.path.join(ROOT, "results", name)
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return json.load(fh)


# --------------------------------------------------------------------------

def fig_transmission(leg):
    """The extension's key plot: where the shallow angles actually fall."""
    n = 1440
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    pts = leg.solve(theta)
    ta = C.transmission_angles(leg, pts=pts)
    sol = D.solve_statics(leg, theta=theta)
    stance = sol["stance"]
    deg = np.degrees(theta)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6.4), sharex=True)
    for label, _, _, _, _ in C.TRANSMISSION_INTERFACES:
        ax1.plot(deg, ta[label], lw=1.6, label=label)
    per_sample = np.minimum.reduce([ta[k[0]] for k in C.TRANSMISSION_INTERFACES])
    ax1.axhline(C.GOOD_TRANSMISSION_ANGLE, ls="--", color="crimson",
                label=f"{C.GOOD_TRANSMISSION_ANGLE:.0f}° rule of thumb")
    ax1.fill_between(deg, 0, 90, where=stance, color="0.85", zorder=0,
                     label="stance (foot loaded)")
    i = int(np.argmin(per_sample))
    ax1.plot(deg[i], per_sample[i], "v", color="black", ms=9, zorder=5)
    ax1.annotate(f"worst angle {per_sample[i]:.1f}°\n(in swing, pin carries "
                 f"{np.nanmax(sol['forces'], axis=1)[i]:.1f} N)",
                 xy=(deg[i], per_sample[i]), xytext=(deg[i] + 18, 20),
                 fontsize=8, arrowprops=dict(arrowstyle="->", lw=0.8))
    ax1.set_ylabel("transmission angle (deg)")
    ax1.set_ylim(0, 90)
    ax1.set_title("Jansen leg: shallow transmission angles fall in swing, not stance")
    ax1.legend(fontsize=7, ncol=2, loc="lower right")
    ax1.grid(alpha=0.3)

    peak = np.nanmax(sol["forces"], axis=1)
    ax2.plot(deg, peak, color="tab:purple", lw=1.6)
    ax2.fill_between(deg, 0, peak.max() * 1.05, where=stance, color="0.85", zorder=0)
    ax2.axvline(deg[i], ls=":", color="black", lw=1)
    ax2.set_xlabel("crank angle (deg)")
    ax2.set_ylabel("largest pin force (N)")
    ax2.set_xlim(0, 360)
    ax2.set_ylim(0, peak.max() * 1.05)
    ax2.grid(alpha=0.3)
    _save(fig, "transmission_angle.png")


def fig_wear(leg):
    sol = D.solve_statics(leg, n=1440)
    rows = W.breakdown_table(sol)
    names = [r["joint"] for r in rows]
    vals = [r["wear_mm3"] * 1e6 for r in rows]      # picolitres, readable numbers

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
    ax1.bar(names, vals, color="tab:orange")
    ax1.set_ylabel("wear per cycle (10$^{-6}$ mm$^3$)")
    ax1.set_title("Where the Jansen leg wears out")
    ax1.tick_params(axis="x", rotation=45)
    ax1.grid(alpha=0.3, axis="y")

    ax2.scatter([r["rotation_deg"] for r in rows], [r["mean_force_N"] for r in rows],
                s=[60 + 4000 * r["share"] for r in rows], color="tab:orange",
                alpha=0.75, edgecolor="k", linewidth=0.5)
    for r in rows:
        ax2.annotate(r["joint"], (r["rotation_deg"], r["mean_force_N"]),
                     fontsize=7, xytext=(4, 4), textcoords="offset points")
    ax2.set_xlabel("relative rotation per cycle (deg)")
    ax2.set_ylabel("mean pin force (N)")
    ax2.set_title("Wear = force x sliding; marker area is share of total")
    ax2.grid(alpha=0.3)
    _save(fig, "wear_breakdown.png")


def fig_pareto(res):
    paper = res["paper_front"]
    ours = res["constrained_front"]
    fig, ax = plt.subplots(figsize=(7.2, 5.6))
    if paper:
        ax.plot([r["gait_error"] for r in paper], [r["wear_ratio"] for r in paper],
                "o-", color="tab:blue", ms=5, lw=1.4,
                label=f"paper's constraints ({len(paper)} designs)")
    if ours:
        ax.plot([r["gait_error"] for r in ours], [r["wear_ratio"] for r in ours],
                "s-", color="tab:green", ms=5, lw=1.4,
                label=f"+ loaded transmission angle $\\geq$ 40° ({len(ours)})")
    ax.plot(1.0, 1.0, "*", color="crimson", ms=18, zorder=5,
            label="Jansen's original")
    ax.axhline(1.0, color="0.8", lw=0.8, zorder=0)
    ax.axvline(1.0, color="0.8", lw=0.8, zorder=0)
    ax.set_xlabel("gait error (ratio to Jansen, lower is better)")
    ax.set_ylabel("wear per cycle (ratio to Jansen, lower is better)")
    ax.set_title("Jansen is dominated — and our added constraint is nearly free")
    ax.annotate("Jansen's original\n(1.00, 1.00)", xy=(1.0, 1.0),
                xytext=(0.955, 0.955), fontsize=8, color="crimson", ha="center")
    if paper:
        gx = [r["gait_error"] for r in paper]
        wy = [r["wear_ratio"] for r in paper]
        ax.annotate("the fronts nearly coincide: no design on\n"
                    "the paper's front violates the 40° rule",
                    xy=(float(np.median(gx)), float(np.median(wy))),
                    xytext=(0.74, 0.97), fontsize=8, color="0.3",
                    arrowprops=dict(arrowstyle="->", color="0.5", lw=0.8))
    ax.legend(fontsize=8, loc="lower left", framealpha=0.85)
    ax.set_ylim(0.71, 1.03)
    ax.grid(alpha=0.3)
    _save(fig, "pareto.png")


def fig_foot_paths(res):
    jansen = JansenLeg(branches=JANSEN_BRANCH)
    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    p = jansen.foot_path(720)
    ax.plot(p[:, 0], p[:, 1], color="crimson", lw=2.2, label="Jansen original")

    front = res["paper_front"] if res else []
    picks = []
    if front:
        best_gait = min(front, key=lambda r: r["gait_error"])
        best_wear = min(front, key=lambda r: r["wear_ratio"])
        picks = [(best_gait, "tab:blue", "best gait"),
                 (best_wear, "tab:green", "best wear")]
    for row, colour, label in picks:
        leg = O.leg_from_vector(row["x"])
        q = leg.foot_path(720)
        ax.plot(q[:, 0], q[:, 1], color=colour, lw=1.8, alpha=0.9,
                label=f"{label} (gait {row['gait_error']:.2f}, "
                      f"wear {row['wear_ratio']:.2f})")
    ax.set_aspect("equal")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_title("Foot paths: optimized designs against Jansen")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    _save(fig, "foot_paths.png")


def fig_optimized_gif(res):
    front = res.get("paper_front") if res else None
    if not front:
        print("no optimization results - skipped figures/optimized_leg.gif")
        return
    from matplotlib.animation import FuncAnimation, PillowWriter
    row = min(front, key=lambda r: r["gait_error"] + r["wear_ratio"])
    leg = O.leg_from_vector(row["x"])
    N = 120
    thetas = np.linspace(0, 2 * np.pi, N, endpoint=False)
    poses = [{k: v[0] for k, v in leg.solve(t).items()} for t in thetas]
    path = leg.foot_path(720)

    fig, ax = plt.subplots(figsize=(6, 7))
    ax.set_aspect("equal")
    ax.grid(alpha=0.3)
    ax.set_xlim(-130, 40)
    ax.set_ylim(-110, 50)
    ax.set_title(f"Optimized leg — gait {row['gait_error']:.2f}, "
                 f"wear {row['wear_ratio']:.2f} (Jansen = 1.00)")
    ax.plot(path[:, 0], path[:, 1], color="tab:green", lw=2, alpha=0.5)
    ax.plot(0, 0, "ro", ms=7)
    ax.plot(*leg.G, "go", ms=7)
    lines = [ax.plot([], [], "-", color="0.25", lw=2)[0] for _ in BARS]
    foot, = ax.plot([], [], "o", color="tab:red", ms=8)

    def update(i):
        p = poses[i]
        for ln, (u, v) in zip(lines, BARS):
            ln.set_data([p[u][0], p[v][0]], [p[u][1], p[v][1]])
        foot.set_data([p["F"][0]], [p["F"][1]])
        return lines + [foot]

    anim = FuncAnimation(fig, update, frames=N, interval=40, blit=True)
    os.makedirs(FIG, exist_ok=True)
    anim.save(os.path.join(FIG, "optimized_leg.gif"), writer=PillowWriter(fps=25))
    plt.close(fig)
    print("wrote figures/optimized_leg.gif")


def seed_spread_hypervolume():
    """The unconstrained seed-to-seed hypervolume spread, and how many triples.

    Preferred source is `results/audit/objective_replication.json`, ten
    unconstrained triples run to settle RESULTS.md 7.2; the seeds study in
    `robustness.json` is the fallback. Which one is used matters more than it
    looks: `spread()` is a range, and the range of three samples is biased low
    by construction, so the three-triple figure (0.0024) is 7x smaller than the
    ten-triple one (0.0170). Drawing the small band behind this curve is what
    made the middle of the sweep look resolved when it is not.
    """
    rep = load_results(os.path.join("audit", "objective_replication.json"))
    if rep:
        hv = [pair["hv_mean"] for pair in rep["pairs"]]
        if len(hv) >= 2:
            return max(hv) - min(hv), len(hv)
    rob = load_results("robustness.json") or {}
    seeds = rob.get("seeds", {})
    noise = seeds.get("seed_spread_hypervolume")
    if noise:
        return noise, len(seeds.get("campaigns", [])) or 3
    return None, 0


def fig_threshold(rob):
    """What the transmission-angle constraint costs as it is tightened.

    The point of the figure is the *shape*, and specifically its two ends: free
    at 40 deg, and a cliff at 55. The seed-to-seed band is drawn behind it
    because a change smaller than the search's own run-to-run spread is not a
    change at all, and a reader is entitled to see that comparison rather than
    be told it. Measured over ten triples the band swallows 45 and 50 deg, so
    the figure now shows what the sweep can and cannot resolve.
    """
    sweep = rob.get("threshold", {}).get("sweep")
    free = rob.get("threshold", {}).get("unconstrained")
    if not sweep or not free:
        return
    thresholds = [r["threshold"] for r in sweep]
    hv = [r["hypervolume"] for r in sweep]
    hv0 = free["hypervolume"]

    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    noise, n_triples = seed_spread_hypervolume()
    if noise:
        ax.axhspan(hv0 - noise, hv0 + noise, color="tab:blue", alpha=0.12,
                   label=f"seed-to-seed spread, unconstrained "
                         f"({n_triples} triples)")
    ax.axhline(hv0, ls="--", color="tab:blue", lw=1.5,
               label=f"unconstrained ({hv0:.3f})")
    ax.plot(thresholds, hv, "o-", color="tab:red", lw=2, ms=7,
            label="with the constraint")
    ax.set_xlabel("minimum loaded transmission angle enforced (deg)")
    ax.set_ylabel("hypervolume dominated (Jansen = reference)")
    ax.set_title("Free at 40°, impossible at 55°")
    ax.set_ylim(bottom=0.0)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    _save(fig, "threshold_sweep.png")


def main():
    leg = JansenLeg(branches=JANSEN_BRANCH)
    fig_transmission(leg)
    fig_wear(leg)
    rob = load_results("robustness.json")
    if rob is None:
        print("results/robustness.json not found - run scripts/robustness.py "
              "for the threshold figure")
    else:
        fig_threshold(rob)
    res = load_results()
    if res is None:
        print("results/pareto.json not found - run scripts/run_optimization.py "
              "for the Pareto figures")
        return
    fig_pareto(res)
    fig_foot_paths(res)
    fig_optimized_gif(res)


if __name__ == "__main__":
    main()
