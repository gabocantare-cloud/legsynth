"""DXF export, so a design leaves this repo as something you can machine.

The mechanism-synthesis literature stops at a plot. This module takes a solved
design the rest of the way: an assembly drawing you can open in SolidWorks, a
set of individual link profiles ready to be laser cut or waterjet, and a plain
coordinate table for anyone who would rather build the sketch by hand.

Everything is written as ASCII DXF R12. R12 is the oldest and most boring
version of the format, which is exactly why every CAD package still reads it
without complaint, and it is simple enough to emit directly — no dependency,
nothing to install, and the output is a text file you can read yourself.

Three things come out:

  **Assembly** (`write_assembly`) — the eleven bars in one pose, the two ground
  pivots, a circle at every pin, and the foot path traced as a closed curve.
  This is the drawing to look at to check the design is what you think it is.

  **Parts** (`write_parts`) — each bar as a closed outline: a flat strip of the
  right length with rounded ends and a hole at each pin centre, laid out in a
  row clear of each other so they can be nested and cut. Hole spacing is the
  design length, which is the number that actually has to be right.

  **Coordinates** (`write_coordinates`) — joint positions through the cycle as
  CSV, for driving a sketch or checking against your own maths.

Units are millimetres, matching the link lengths everywhere else in the repo.
DXF carries no unit declaration in R12, so the importer has to be told
millimetres — that is a property of the format, not an omission here.
"""
from __future__ import annotations

import os

import numpy as np

from .kinematics import JansenLeg

#: The eleven bars, as (link key, joint, joint).
BARS = (("m", "O", "J1"), ("j", "J1", "J2"), ("b", "G", "J2"),
        ("e", "J2", "J3"), ("d", "G", "J3"), ("k", "J1", "J4"),
        ("c", "G", "J4"), ("f", "J3", "J5"), ("g", "J4", "J5"),
        ("i", "J4", "F"), ("h", "J5", "F"))

PIN_JOINTS = ("O", "G", "J1", "J2", "J3", "J4", "J5", "F")

DEFAULT_PIN_RADIUS = 4.0     # mm, matches wear.R_PIN
DEFAULT_LINK_WIDTH = 12.0    # mm, a plausible strip width for a model-scale leg


# --------------------------------------------------------------------------
# minimal DXF writer
# --------------------------------------------------------------------------

def _tag(code, value):
    return f"{code}\n{value}\n"


def _header(layers):
    s = _tag(0, "SECTION") + _tag(2, "TABLES") + _tag(0, "TABLE") + _tag(2, "LAYER")
    s += _tag(70, len(layers))
    for i, name in enumerate(layers):
        s += (_tag(0, "LAYER") + _tag(2, name) + _tag(70, 0)
              + _tag(62, (i % 7) + 1) + _tag(6, "CONTINUOUS"))
    s += _tag(0, "ENDTAB") + _tag(0, "ENDSEC")
    s += _tag(0, "SECTION") + _tag(2, "ENTITIES")
    return s


def _line(p, q, layer):
    return (_tag(0, "LINE") + _tag(8, layer)
            + _tag(10, f"{p[0]:.6f}") + _tag(20, f"{p[1]:.6f}") + _tag(30, "0.0")
            + _tag(11, f"{q[0]:.6f}") + _tag(21, f"{q[1]:.6f}") + _tag(31, "0.0"))


def _circle(c, r, layer):
    return (_tag(0, "CIRCLE") + _tag(8, layer)
            + _tag(10, f"{c[0]:.6f}") + _tag(20, f"{c[1]:.6f}") + _tag(30, "0.0")
            + _tag(40, f"{r:.6f}"))


def _polyline(points, layer, closed=True):
    """Emit a polyline as individual LINE entities.

    R12's POLYLINE needs a VERTEX list and a SEQEND, and plenty of importers
    handle a run of LINEs more reliably than they handle a malformed polyline.
    Segments are cheap and unambiguous.
    """
    pts = np.asarray(points, float)
    s = ""
    n = len(pts)
    last = n if closed else n - 1
    for i in range(last):
        s += _line(pts[i], pts[(i + 1) % n], layer)
    return s


def _footer():
    return _tag(0, "ENDSEC") + _tag(0, "EOF")


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------

def link_profile(length, width=DEFAULT_LINK_WIDTH, segments=25):
    """Closed outline of one bar: a strip with semicircular ends.

    The bar runs along +x from (0, 0) to (length, 0), which are the two pin
    centres. Returns an (n, 2) array of points tracing the outline once.

    Rounded ends are not decoration: they put material all the way around each
    pin hole, which is where the bearing load goes, and they leave no corner to
    start a crack from.

    The arcs are emitted as polygons, so `segments` is kept odd on purpose: an
    even count omits the point at the far end of each arc and the outline then
    cuts a few hundredths of a millimetre inside the nominal radius, thinning
    the wall exactly where the bearing load is carried.
    """
    if segments % 2 == 0:
        segments += 1
    r = 0.5 * width
    t = np.linspace(-np.pi / 2, np.pi / 2, segments)
    right = np.stack([length + r * np.cos(t), r * np.sin(t)], axis=-1)
    left = np.stack([-r * np.cos(t), -r * np.sin(t)], axis=-1)
    return np.vstack([right, left])


def _place(profile, p, q):
    """Rotate and translate a profile so its (0,0)-(L,0) axis lands on p-q."""
    p, q = np.asarray(p, float), np.asarray(q, float)
    d = q - p
    ang = np.arctan2(d[1], d[0])
    c, s = np.cos(ang), np.sin(ang)
    R = np.array([[c, -s], [s, c]])
    return profile @ R.T + p


# --------------------------------------------------------------------------
# exports
# --------------------------------------------------------------------------

def write_assembly(leg, path, theta=0.0, pin_radius=DEFAULT_PIN_RADIUS,
                   n_path=360):
    """Write an assembly drawing of the leg at one crank angle.

    Layers: LINKAGE (bar centrelines), PINS (pin circles), GROUND (the two
    fixed pivots), FOOTPATH (the foot's closed trajectory).
    """
    pts = {k: np.asarray(v)[0] for k, v in leg.solve(np.array([theta])).items()}
    if not all(np.all(np.isfinite(v)) for v in pts.values()):
        raise ValueError("design does not assemble at this crank angle")

    s = _header(["LINKAGE", "PINS", "GROUND", "FOOTPATH"])
    for _, u, v in BARS:
        s += _line(pts[u], pts[v], "LINKAGE")
    for j in PIN_JOINTS:
        s += _circle(pts[j], pin_radius, "PINS")
    for j in ("O", "G"):
        s += _circle(pts[j], pin_radius * 1.8, "GROUND")
    fp = leg.foot_path(n_path)
    if np.all(np.isfinite(fp)):
        s += _polyline(fp, "FOOTPATH", closed=True)
    s += _footer()

    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w") as fh:
        fh.write(s)
    return path


def write_parts(leg, path, width=DEFAULT_LINK_WIDTH,
                pin_radius=DEFAULT_PIN_RADIUS, gap=10.0):
    """Write every bar as a separate cuttable outline, laid out in a row.

    Each part is drawn along +x with its two holes at the ends, spaced apart
    so nothing overlaps. Layers: PARTS (outlines), HOLES (pin holes).
    """
    s = _header(["PARTS", "HOLES"])
    y = 0.0
    for key, u, v in BARS:
        L = float(leg.L[key])
        prof = link_profile(L, width)
        s += _polyline(prof + np.array([0.0, y]), "PARTS", closed=True)
        s += _circle(np.array([0.0, y]), pin_radius, "HOLES")
        s += _circle(np.array([L, y]), pin_radius, "HOLES")
        y -= width + gap
    s += _footer()

    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w") as fh:
        fh.write(s)
    return path


def write_coordinates(leg, path, n=72):
    """Write joint coordinates through the cycle as CSV, in millimetres."""
    theta = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    pts = leg.solve(theta)
    names = ["O", "G", "J1", "J2", "J3", "J4", "J5", "F"]
    header = "theta_deg," + ",".join(f"{j}_x,{j}_y" for j in names)
    rows = [header]
    for i in range(n):
        vals = [f"{np.degrees(theta[i]):.4f}"]
        for j in names:
            vals += [f"{pts[j][i, 0]:.6f}", f"{pts[j][i, 1]:.6f}"]
        rows.append(",".join(vals))

    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w") as fh:
        fh.write("\n".join(rows) + "\n")
    return path


def export_all(leg, directory, stem="leg", theta=0.0):
    """Write the assembly, the parts and the coordinate table for one design."""
    os.makedirs(directory, exist_ok=True)
    return dict(
        assembly=write_assembly(leg, os.path.join(directory, f"{stem}_assembly.dxf"),
                                theta=theta),
        parts=write_parts(leg, os.path.join(directory, f"{stem}_parts.dxf")),
        coordinates=write_coordinates(leg, os.path.join(directory,
                                                        f"{stem}_coordinates.csv")),
    )
