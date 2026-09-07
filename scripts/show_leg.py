"""Draw and animate one Jansen leg. Run:  python scripts/show_leg.py"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from legsynth.kinematics import JansenLeg

JANSEN_BRANCH = (-1, -1, 1, -1, 1)
BARS = [("O","J1"),("J1","J2"),("G","J2"),("J2","J3"),("G","J3"),
        ("J1","J4"),("G","J4"),("J3","J5"),("J4","J5"),("J4","F"),("J5","F")]

leg = JansenLeg(branches=JANSEN_BRANCH)
path = leg.foot_path(720)
N = 120
thetas = np.linspace(0, 2*np.pi, N, endpoint=False)
poses = [{k: v[0] for k, v in leg.solve(t).items()} for t in thetas]

fig, ax = plt.subplots(figsize=(6, 7))
ax.set_aspect("equal"); ax.grid(alpha=0.3)
ax.set_xlim(-115, 30); ax.set_ylim(-100, 45)
ax.set_title("Jansen leg — one crank revolution")
ax.plot(path[:,0], path[:,1], color="tab:blue", lw=2, alpha=0.5, label="foot path")
ax.plot(0, 0, "ro", ms=7, label="crank centre")
ax.plot(*leg.G, "go", ms=7, label="frame pivot")
ax.legend(loc="upper left", fontsize=8)

lines = [ax.plot([], [], "-", color="0.25", lw=2)[0] for _ in BARS]
foot, = ax.plot([], [], "o", color="tab:red", ms=8)

def update(i):
    p = poses[i]
    for ln, (u, v) in zip(lines, BARS):
        ln.set_data([p[u][0], p[v][0]], [p[u][1], p[v][1]])
    foot.set_data([p["F"][0]], [p["F"][1]])
    return lines + [foot]

anim = FuncAnimation(fig, update, frames=N, interval=40, blit=True)
os.makedirs("figures", exist_ok=True)
anim.save("figures/jansen_leg.gif", writer=PillowWriter(fps=25))
print("wrote figures/jansen_leg.gif")
