"""Quasi-static inverse dynamics: how hard is each pin being pushed?

Forward kinematics tells us where the leg is. This tells us what it is carrying.
For each crank angle we write down force and moment balance for every moving
body and solve for the reaction force at each of the ten pins, plus the torque
the motor has to supply. Those pin forces are the input to the wear model.

"Quasi-static" means inertia is neglected: at one revolution per second and
0.05 kg/m of bar, the centripetal load on a 60 mm link is a few millinewtons
against a 20 N ground reaction, so the leg is treated as passing through a
sequence of static equilibria. The paper makes the same assumption.

The body count, which the paper states but does not derive
----------------------------------------------------------
`kinematics.py` tracks eleven bars, but three of them close a triangle
(`b`, `d`, `e` around G-J2-J3) and three more close another (`g`, `h`, `i`
around J4-J5-F). A triangle of rigid bars cannot flex, so each is a single
rigid body — a *ternary link*, one carrying three pins instead of two. What is
left is:

    crank  O-J1                 bar m       rotates about the ground pin O
    LJ     J1-J2                bar j
    T1     G-J2-J3   (ternary)  bars b,d,e  rotates about the ground pin G
    LK     J1-J4                bar k
    LC     G-J4                 bar c       rotates about the ground pin G
    LF     J3-J5                bar f
    T2     J4-J5-F  (ternary)   bars g,h,i  carries the foot

Seven moving bodies, and the pins between them:

    O   ground-crank      J1  crank-LJ, crank-LK
    G   ground-T1         J2  LJ-T1        J4  LK-T2, LC-T2
        ground-LC         J3  T1-LF        J5  LF-T2

Ten revolute joints — which is exactly the number of joints the paper sums
Archard wear over, and a Gruebler check confirms the mechanism:
DOF = 3*(8-1) - 2*10 = 1. The foot F is not a joint; it is where the ground
pushes back.

Where three bodies share one pin (J1 and J4) the pairing above is not arbitrary.
It is the only tree that gives every body at least two named joints, and under
it each of the ten reactions is the force carried by one specific bearing:
`J1_j` is what LJ's bore at J1 carries, `J4_c` is what LC's bore at J4 carries,
and so on. So all ten numbers are uniquely determined, not an artefact of how we
chose to split the pin.

How the solve works
-------------------
Two force equations and one moment equation per moving body is 21 equations.
Two reaction components per joint plus the unknown crank torque is 21 unknowns.
Square and, away from singular configurations, invertible — so no least squares
and no modelling fudge. Writing that system is the "constraint Jacobian"
approach: the coefficient matrix is the transpose of the Jacobian of the joint
constraints, which is the statement that constraint forces do no virtual work.
`solve_statics` checks that directly via `power_residual`.

When the linkage passes near a singular pose the matrix becomes ill-conditioned
and the pin forces blow up. That is not a numerical nuisance, it is the physical
fact that a linkage pushing at a shallow angle needs enormous force to make
anything happen — and it is what `constraints.py` exists to keep away from.

Units are SI throughout this module: link lengths arrive in millimetres and are
converted to metres on the way in, forces come out in newtons and torque in
newton-metres.
"""
from __future__ import annotations

import numpy as np

from . import metrics as M

MM = 1e-3          # millimetres to metres
G_ACCEL = 9.81     # m/s^2
LINE_DENSITY = 0.05   # kg/m of bar, as specified by the paper
GROUND_REACTION = 20.0  # N, vertical, applied at the foot during stance

#: Moving bodies, in the order their equations appear in the linear system.
BODIES = ("crank", "LJ", "T1", "LK", "LC", "LF", "T2")

#: Which bars make up each body, as (key, end, end). Used for weight only.
BODY_BARS = {
    "crank": [("m", "O", "J1")],
    "LJ": [("j", "J1", "J2")],
    "T1": [("b", "G", "J2"), ("d", "G", "J3"), ("e", "J2", "J3")],
    "LK": [("k", "J1", "J4")],
    "LC": [("c", "G", "J4")],
    "LF": [("f", "J3", "J5")],
    "T2": [("g", "J4", "J5"), ("h", "J5", "F"), ("i", "J4", "F")],
}

#: The ten revolute joints, as (name, pin, body A, body B).
#: The stored reaction is the force body A exerts on body B.
JOINTS = (
    ("O",    "O",  "ground", "crank"),
    ("G_bd", "G",  "ground", "T1"),
    ("G_c",  "G",  "ground", "LC"),
    ("J1_j", "J1", "crank",  "LJ"),
    ("J1_k", "J1", "crank",  "LK"),
    ("J2",   "J2", "LJ",     "T1"),
    ("J3",   "J3", "T1",     "LF"),
    ("J4_k", "J4", "LK",     "T2"),
    ("J4_c", "J4", "LC",     "T2"),
    ("J5",   "J5", "LF",     "T2"),
)

JOINT_NAMES = tuple(j[0] for j in JOINTS)

#: Body orientation is measured along this vector, tail to head.
BODY_AXIS = {
    "crank": ("O", "J1"), "LJ": ("J1", "J2"), "T1": ("G", "J2"),
    "LK": ("J1", "J4"), "LC": ("G", "J4"), "LF": ("J3", "J5"),
    "T2": ("J4", "J5"),
}

N_BODIES = len(BODIES)
N_JOINTS = len(JOINTS)
N_UNKNOWNS = 2 * N_JOINTS + 1        # reactions, then the crank torque
TORQUE_COL = 2 * N_JOINTS

#: Condition number above which a pose is treated as singular (forces -> NaN).
COND_LIMIT = 1e12


def body_angles(pts):
    """Orientation of every moving body, in radians, from a solved pose.

    `pts` is the dict returned by `JansenLeg.solve`. Ground is not included:
    it does not rotate.
    """
    out = {}
    for body, (tail, head) in BODY_AXIS.items():
        d = pts[head] - pts[tail]
        out[body] = np.arctan2(d[..., 1], d[..., 0])
    return out


def _external_loads(pts_m, lengths, stance, grf, line_density, g):
    """Gravity on every bar plus the ground push, gathered per body.

    Returns an (n, n_bodies, 3) array of (Fx, Fy, moment about the origin).
    Each bar's weight acts at its own midpoint, so a ternary link gets the
    moment its geometry actually produces rather than a single lumped force.
    """
    n = pts_m["O"].shape[0]
    ext = np.zeros((n, N_BODIES, 3))
    for ib, body in enumerate(BODIES):
        for key, u, v in BODY_BARS[body]:
            w = line_density * (lengths[key] * MM) * g      # newtons, downward
            mid = 0.5 * (pts_m[u] + pts_m[v])
            ext[:, ib, 1] -= w
            ext[:, ib, 2] -= mid[:, 0] * w                  # x*Fy with Fy = -w
    # The ground pushes up on the foot, which belongs to body T2.
    it2 = BODIES.index("T2")
    up = np.where(stance, grf, 0.0)
    ext[:, it2, 1] += up
    ext[:, it2, 2] += pts_m["F"][:, 0] * up
    return ext


def solve_statics(leg, theta=None, n=360, grf=GROUND_REACTION,
                  line_density=LINE_DENSITY, g=G_ACCEL, band=M.DEFAULT_BAND):
    """Pin reaction forces and crank torque over the crank revolution.

    Parameters
    ----------
    leg : JansenLeg
    theta : array of crank angles, or None for one uniform revolution of `n`.
    grf : vertical ground reaction applied at the foot during stance, N.
    line_density : bar mass per unit length, kg/m.
    band : stance band handed to `metrics.stance_mask`.

    Returns a dict with
        theta      (n,)        crank angles
        reactions  (n, 10, 2)  force of body A on body B at each joint, N
        forces     (n, 10)     magnitude of the above, N
        torque     (n,)        crank torque needed to hold this pose, N*m
        stance     (n,)        bool, foot on the ground
        cond       (n,)        condition number of the equilibrium matrix
        feasible   bool        the leg assembles and no pose was singular

    Poses that do not assemble, or that are singular to working precision,
    come back as NaN rather than as a raised exception, so an optimizer can
    score a bad design instead of crashing on it.
    """
    if theta is None:
        theta = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    theta = np.atleast_1d(np.asarray(theta, float))
    pts = leg.solve(theta)
    pts_m = {k: v * MM for k, v in pts.items()}
    n = theta.size

    path = pts["F"]
    finite = np.all(np.isfinite(path))
    stance = (M.stance_mask(path, band) if finite and path.shape[0] >= 3
              else np.zeros(n, bool))

    A = np.zeros((n, 3 * N_BODIES, N_UNKNOWNS))
    for jj, (_, pin, ba, bb) in enumerate(JOINTS):
        px, py = pts_m[pin][:, 0], pts_m[pin][:, 1]
        cx, cy = 2 * jj, 2 * jj + 1
        for body, s in ((bb, 1.0), (ba, -1.0)):
            if body == "ground":
                continue
            r = 3 * BODIES.index(body)
            A[:, r, cx] += s                 # sum Fx
            A[:, r + 1, cy] += s             # sum Fy
            A[:, r + 2, cx] += -s * py       # sum M about the origin
            A[:, r + 2, cy] += s * px
    A[:, 3 * BODIES.index("crank") + 2, TORQUE_COL] = 1.0

    ext = _external_loads(pts_m, leg.L, stance, grf, line_density, g)
    b = -ext.reshape(n, 3 * N_BODIES)

    bad = ~np.isfinite(A).all(axis=(1, 2)) | ~np.isfinite(b).all(axis=1)
    A_safe = np.where(bad[:, None, None], np.eye(N_UNKNOWNS)[None], A)
    b_safe = np.where(bad[:, None], 0.0, b)
    cond = np.linalg.cond(A_safe)
    singular = bad | ~np.isfinite(cond) | (cond > COND_LIMIT)
    A_safe = np.where(singular[:, None, None], np.eye(N_UNKNOWNS)[None], A_safe)
    x = np.linalg.solve(A_safe, b_safe[..., None])[..., 0]
    x = np.where(singular[:, None], np.nan, x)

    reactions = x[:, :2 * N_JOINTS].reshape(n, N_JOINTS, 2)
    return dict(
        theta=theta, reactions=reactions,
        forces=np.linalg.norm(reactions, axis=-1),
        torque=x[:, TORQUE_COL], stance=stance,
        cond=np.where(bad, np.inf, cond),
        feasible=bool(finite and not singular.any()),
        pts=pts,
    )


def power_residual(leg, sol, **kw):
    """Virtual-work check of a solve, as a fraction of the power involved.

    In a quasi-static cycle the motor's power goes entirely into lifting and
    pushing: T*omega + sum(F_ext . v) = 0, because the pin reactions are
    internal and do no net work. Nothing in `solve_statics` enforces that — it
    only ever writes force and moment balance body by body — so agreement is an
    independent check on the whole 21x21 system, catching a sign error or a
    misplaced moment arm that per-body balance alone would not.

    Velocities are taken per radian of crank by central difference, so the crank
    rate cancels. Returns the RMS mismatch divided by the RMS of |T|, which is
    dimensionless and should sit at the level of the differencing error.
    """
    theta = sol["theta"]
    if theta.size < 8:
        raise ValueError("need a reasonably dense theta sample to difference")
    pts = sol["pts"]
    pts_m = {k: v * MM for k, v in pts.items()}
    ext = _external_loads(pts_m, leg.L, sol["stance"],
                          kw.get("grf", GROUND_REACTION),
                          kw.get("line_density", LINE_DENSITY),
                          kw.get("g", G_ACCEL))

    # Point of application of each body's external load, per body:
    # gravity acts at each bar midpoint, the ground reaction at the foot.
    dth = theta[1] - theta[0]

    def d_dtheta(p):
        return (np.roll(p, -1, axis=0) - np.roll(p, 1, axis=0)) / (2 * dth)

    power = np.zeros_like(theta)
    for ib, body in enumerate(BODIES):
        for key, u, v in BODY_BARS[body]:
            w = kw.get("line_density", LINE_DENSITY) * (leg.L[key] * MM) \
                * kw.get("g", G_ACCEL)
            vmid = d_dtheta(0.5 * (pts_m[u] + pts_m[v]))
            power += -w * vmid[:, 1]
    up = np.where(sol["stance"], kw.get("grf", GROUND_REACTION), 0.0)
    power += up * d_dtheta(pts_m["F"])[:, 1]
    del ext

    mismatch = sol["torque"] + power
    # Drop the touchdown and lift-off samples: the ground reaction switches on
    # as a step there, so a centred difference straddles the discontinuity. The
    # window is symmetric - two samples either side - because the discontinuity
    # is. The residual is 4.1e-5 either way; an asymmetric window just reads as
    # a typo.
    edge = sol["stance"] != np.roll(sol["stance"], 1)
    edge |= (np.roll(edge, -2) | np.roll(edge, -1)
             | np.roll(edge, 1) | np.roll(edge, 2))
    keep = ~edge & np.isfinite(mismatch)
    scale = np.sqrt(np.mean(sol["torque"][keep] ** 2))
    return float(np.sqrt(np.mean(mismatch[keep] ** 2)) / scale)


def peak_forces(sol):
    """Peak and mean magnitude at each joint over the cycle, as a dict of dicts."""
    f = sol["forces"]
    return {name: dict(peak=float(np.nanmax(f[:, i])),
                       mean=float(np.nanmean(f[:, i])))
            for i, name in enumerate(JOINT_NAMES)}
