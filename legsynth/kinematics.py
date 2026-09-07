"""Planar forward kinematics for the Jansen leg linkage.

Construction follows the dyad cascade in Wang (2026), arXiv:2606.22129, Sec. 2:

    O  = (0, 0)                 crank centre (ground)
    G  = (-a, -l)               frame pivot  (ground)
    J1 = O + m*(cos t, sin t)   crank tip
    J2 = circ(J1, j; G, b)
    J3 = circ(J2, e; G, d)
    J4 = circ(J1, k; G, c)
    J5 = circ(J3, f; J4, g)
    F  = circ(J4, i; J5, h)     foot

`circ` is the branch-selected intersection of two circles.
"""
from __future__ import annotations

import numpy as np

# Theo Jansen's "holy numbers" (mm). Order: a..m.
HOLY = dict(a=38.0, b=41.5, c=39.3, d=40.1, e=55.8, f=39.4,
            g=36.7, h=65.7, i=49.0, j=50.0, k=61.9, l=7.8, m=15.0)

# Link lengths that the optimiser is allowed to vary (b..k, ten values).
DESIGN_KEYS = ("b", "c", "d", "e", "f", "g", "h", "i", "j", "k")


def circ(p1, r1, p2, r2, sign):
    """Branch-selected intersection of circle(p1,r1) and circle(p2,r2).

    Vectorised over leading axes. Returns NaN where the circles do not meet,
    which is how an infeasible (non-assemblable) design announces itself.
    """
    p1 = np.asarray(p1, float)
    p2 = np.asarray(p2, float)
    d = p2 - p1
    dist = np.hypot(d[..., 0], d[..., 1])
    with np.errstate(divide="ignore", invalid="ignore"):
        A = (r1 ** 2 - r2 ** 2 + dist ** 2) / (2 * dist)
        H2 = r1 ** 2 - A ** 2
        H2 = np.where(H2 < 0, np.nan, H2)
        h = np.sqrt(H2)
        ux, uy = d[..., 0] / dist, d[..., 1] / dist
    mx = p1[..., 0] + A * ux
    my = p1[..., 1] + A * uy
    return np.stack([mx - sign * h * uy, my + sign * h * ux], axis=-1)


class JansenLeg:
    """Forward kinematics of one Jansen leg.

    Parameters
    ----------
    lengths : dict
        Link lengths a..m. Defaults to the holy numbers.
    branches : tuple of 5 ints (+1/-1)
        Assembly-mode (branch) selection for J2, J3, J4, J5, F.
    """

    def __init__(self, lengths=None, branches=(1, 1, 1, 1, 1)):
        self.L = dict(HOLY) if lengths is None else dict(lengths)
        self.branches = tuple(branches)

    @property
    def G(self):
        return np.array([-self.L["a"], -self.L["l"]])

    def solve(self, theta):
        """Joint positions for crank angle(s) theta.

        Returns dict of arrays with shape (..., 2).
        """
        L, s = self.L, self.branches
        theta = np.atleast_1d(np.asarray(theta, float))
        O = np.zeros(theta.shape + (2,))
        G = np.broadcast_to(self.G, theta.shape + (2,))
        J1 = np.stack([L["m"] * np.cos(theta), L["m"] * np.sin(theta)], axis=-1)
        J2 = circ(J1, L["j"], G, L["b"], s[0])
        J3 = circ(J2, L["e"], G, L["d"], s[1])
        J4 = circ(J1, L["k"], G, L["c"], s[2])
        J5 = circ(J3, L["f"], J4, L["g"], s[3])
        F = circ(J4, L["i"], J5, L["h"], s[4])
        return dict(O=O, G=G, J1=J1, J2=J2, J3=J3, J4=J4, J5=J5, F=F)

    def foot_path(self, n=360):
        """Foot trajectory over one full crank revolution."""
        theta = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
        return self.solve(theta)["F"]

    def assembles(self, n=360):
        """True if the mechanism closes at every crank angle (full rotatability)."""
        return bool(np.all(np.isfinite(self.foot_path(n))))
