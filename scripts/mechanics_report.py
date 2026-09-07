"""Regenerate every mechanical number quoted in docs/RESULTS.md.

Prints the pin forces, the wear breakdown, the mean-force-versus-integrated
comparison and the transmission-angle result for the Jansen baseline, and
writes results/mechanics.json.

Run:  python scripts/mechanics_report.py
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from legsynth.kinematics import JansenLeg              # noqa: E402
from legsynth import dynamics as D, wear as W          # noqa: E402
from legsynth import constraints as C, metrics as M    # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JANSEN_BRANCH = (-1, -1, 1, -1, 1)
N = 1440


def main():
    leg = JansenLeg(branches=JANSEN_BRANCH)
    theta = np.linspace(0.0, 2 * np.pi, N, endpoint=False)
    sol = D.solve_statics(leg, theta=theta)
    w = W.wear_per_cycle(sol)
    ta = C.transmission_angles(leg, pts=sol["pts"])
    rows = W.breakdown_table(sol)
    residual = D.power_residual(leg, sol)

    print(f"Jansen baseline, branch {JANSEN_BRANCH}, {N} crank samples")
    print(f"7 moving bodies, {len(D.JOINTS)} revolute joints, "
          f"Grubler DOF = {3 * (len(D.BODIES) + 1 - 1) - 2 * len(D.JOINTS)}")

    print("\n1. STATICS")
    print(f"  peak pin force        {np.nanmax(sol['forces']):.2f} N "
          f"at {D.JOINT_NAMES[int(np.nanargmax(np.nanmax(sol['forces'], axis=0)))]}"
          f"  (ground reaction {D.GROUND_REACTION:.0f} N)")
    print(f"  force amplification   {np.nanmax(sol['forces']) / D.GROUND_REACTION:.3f}")
    print(f"  peak crank torque     {np.nanmax(np.abs(sol['torque'])):.4f} N*m")
    print(f"  worst condition no.   {np.nanmax(sol['cond']):.3e}")
    print(f"  virtual-work residual {residual:.2e}   "
          f"(independent check; nothing in the solver enforces it)")

    print("\n2. WEAR PER CYCLE, BY JOINT")
    print(f"  {'joint':<7}{'mean F (N)':>11}{'rotation':>10}{'sliding':>10}"
          f"{'wear (mm3)':>13}{'share':>8}")
    for r in rows:
        print(f"  {r['joint']:<7}{r['mean_force_N']:>11.2f}"
              f"{r['rotation_deg']:>8.0f}d{r['sliding_mm']:>9.1f}mm"
              f"{r['wear_mm3']:>13.3e}{100 * r['share']:>7.1f}%")
    print(f"  {'TOTAL':<7}{'':>11}{'':>10}{'':>10}{w['total'] * 1e9:>13.3e}")

    err = w["total"] / w["total_integrated"] - 1.0
    print("\n3. THE PAPER'S MEAN-FORCE SHORTCUT")
    print(f"  mean-force form (paper's)  {w['total'] * 1e9:.4e} mm3/cycle")
    print(f"  integrated form            {w['total_integrated'] * 1e9:.4e} mm3/cycle")
    print(f"  overestimate               {100 * err:+.1f}%   "
          f"(the paper claims 3-4%)")
    i = D.JOINT_NAMES.index("O")
    print(f"  cross-check at the crank pin, where they must agree analytically: "
          f"{100 * (w['per_joint'][i] / w['integrated'][i] - 1):+.3f}%")

    print("\n4. TRANSMISSION ANGLE")
    for label, _, _, _, _ in C.TRANSMISSION_INTERFACES:
        print(f"  {label:<12} min over cycle {ta[label].min():6.2f} deg   "
              f"min in stance {ta[label][ta['stance']].min():6.2f} deg")
    per_sample = np.minimum.reduce([ta[k[0]] for k in C.TRANSMISSION_INTERFACES])
    j = int(np.argmin(per_sample))
    peak = np.nanmax(sol["forces"], axis=1)
    print(f"  overall      whole cycle   {ta['min']:6.2f} deg   "
          f"loaded (stance) {ta['min_stance']:6.2f} deg")
    print(f"  the {ta['min']:.1f} deg minimum falls at crank {np.degrees(theta[j]):.0f} deg, "
          f"in {'stance' if sol['stance'][j] else 'swing'}, "
          f"with {peak[j]:.1f} N in the pin")
    k = int(np.argmax(peak))
    print(f"  the {peak[k]:.1f} N peak force falls at crank "
          f"{np.degrees(theta[k]):.0f} deg, at {per_sample[k]:.1f} deg")
    print(f"  verdict: {'FAILS' if ta['min'] < C.GOOD_TRANSMISSION_ANGLE else 'passes'} "
          f"the {C.GOOD_TRANSMISSION_ANGLE:.0f} deg rule over the whole cycle, "
          f"{'FAILS' if ta['min_stance'] < C.GOOD_TRANSMISSION_ANGLE else 'passes'} it loaded")

    out = dict(
        n_samples=N, branch=list(JANSEN_BRANCH),
        gait=M.gait_metrics(sol["pts"]["F"]),
        peak_pin_force_N=float(np.nanmax(sol["forces"])),
        force_amplification=float(np.nanmax(sol["forces"]) / D.GROUND_REACTION),
        peak_torque_Nm=float(np.nanmax(np.abs(sol["torque"]))),
        virtual_work_residual=residual,
        wear_total_mm3=float(w["total"] * 1e9),
        wear_integrated_mm3=float(w["total_integrated"] * 1e9),
        mean_force_overestimate=float(err),
        per_joint=rows,
        min_transmission_angle_cycle=ta["min"],
        min_transmission_angle_stance=ta["min_stance"],
        branch_margin=C.branch_margin(leg, N),
    )
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    dest = os.path.join(ROOT, "results", "mechanics.json")
    with open(dest, "w") as fh:
        json.dump(out, fh, indent=2, default=float)
    print(f"\nwrote {os.path.relpath(dest, ROOT)}")


if __name__ == "__main__":
    main()
