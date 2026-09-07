import numpy as np
import pytest

from legsynth.kinematics import JansenLeg
from legsynth import cad

JANSEN_BRANCH = (-1, -1, 1, -1, 1)


@pytest.fixture(scope="module")
def leg():
    return JansenLeg(branches=JANSEN_BRANCH)


def _read(path):
    with open(path) as fh:
        return fh.read()


# --------------------------------------------------------------------------
# the geometry has to be right, because someone might actually cut it
# --------------------------------------------------------------------------

def test_link_profile_is_a_closed_strip_of_the_right_size():
    L, w = 50.0, 12.0
    p = cad.link_profile(L, w)
    assert p.ndim == 2 and p.shape[1] == 2
    assert np.ptp(p[:, 1]) == pytest.approx(w, rel=1e-3), "strip is one width tall"
    assert p[:, 0].min() == pytest.approx(-w / 2, rel=1e-3)
    assert p[:, 0].max() == pytest.approx(L + w / 2, rel=1e-3)


def test_link_profile_surrounds_both_pin_centres():
    """Both holes must sit inside the outline with a full wall of material."""
    L, w = 40.0, 10.0
    p = cad.link_profile(L, w)
    for centre in ([0.0, 0.0], [L, 0.0]):
        d = np.linalg.norm(p - np.array(centre), axis=1)
        assert d.min() == pytest.approx(w / 2, rel=1e-3)


def test_placing_a_profile_preserves_the_hole_spacing(leg):
    """Rotating a part onto its pins must not stretch it.

    Hole spacing is the one dimension that has to be exact, because it is the
    link length the whole kinematic model depends on.
    """
    p, q = np.array([10.0, -5.0]), np.array([-30.0, 25.0])
    L = float(np.linalg.norm(q - p))
    placed = cad._place(cad.link_profile(L, 8.0), p, q)
    # The profile's own axis endpoints map to p and q.
    axis = cad._place(np.array([[0.0, 0.0], [L, 0.0]]), p, q)
    assert axis[0] == pytest.approx(p)
    assert axis[1] == pytest.approx(q)
    assert np.isfinite(placed).all()


# --------------------------------------------------------------------------
# the files have to be readable by something that is not us
# --------------------------------------------------------------------------

def test_assembly_dxf_is_structurally_valid(tmp_path, leg):
    path = cad.write_assembly(leg, tmp_path / "a.dxf")
    text = _read(path)
    assert text.startswith("0\nSECTION")
    assert text.rstrip().endswith("EOF")
    assert text.count("\nSECTION\n") == text.count("\nENDSEC\n") == 2
    for layer in ("LINKAGE", "PINS", "GROUND", "FOOTPATH"):
        assert layer in text
    assert text.count("\nLINE\n") >= len(cad.BARS)
    assert text.count("\nCIRCLE\n") == len(cad.PIN_JOINTS) + 2


def test_assembly_contains_every_bar_at_its_true_length(tmp_path, leg):
    """Parse our own LINE entities back and check them against the link lengths.

    A drawing that does not match the model is worse than no drawing.
    """
    path = cad.write_assembly(leg, tmp_path / "a.dxf", theta=0.7)
    text = _read(path)
    pts = {k: np.asarray(v)[0] for k, v in leg.solve(np.array([0.7])).items()}
    lines = []
    tokens = text.split("\n")
    for i, tok in enumerate(tokens):
        if tok != "LINE":
            continue
        vals = {}
        j = i + 1
        while j < len(tokens) - 1 and tokens[j] != "0":   # stop at the next entity
            if tokens[j] in ("10", "20", "11", "21"):
                vals[tokens[j]] = float(tokens[j + 1])
            j += 2
        if len(vals) == 4:
            lines.append(((vals["10"], vals["20"]), (vals["11"], vals["21"])))
    for key, u, v in cad.BARS:
        want = float(np.linalg.norm(pts[u] - pts[v]))
        assert want == pytest.approx(leg.L[key], abs=1e-6)
        assert any(np.isclose(np.linalg.norm(np.array(a) - np.array(b)), want, atol=1e-4)
                   for a, b in lines), f"bar {key} missing from the drawing"


def test_parts_file_has_one_outline_and_two_holes_per_bar(tmp_path, leg):
    path = cad.write_parts(leg, tmp_path / "p.dxf")
    text = _read(path)
    assert text.count("\nCIRCLE\n") == 2 * len(cad.BARS)
    assert "PARTS" in text and "HOLES" in text


def test_coordinates_csv_round_trips(tmp_path, leg):
    path = cad.write_coordinates(leg, tmp_path / "c.csv", n=36)
    rows = _read(path).strip().split("\n")
    assert len(rows) == 37, "header plus one row per crank angle"
    assert rows[0].startswith("theta_deg,O_x,O_y")
    data = np.array([[float(v) for v in r.split(",")] for r in rows[1:]])
    assert data.shape == (36, 1 + 2 * 8)
    # The foot column must match the model.
    fp = leg.foot_path(36)
    assert np.allclose(data[:, -2:], fp, atol=1e-6)


def test_export_all_writes_three_files(tmp_path, leg):
    out = cad.export_all(leg, str(tmp_path), stem="jansen")
    assert set(out) == {"assembly", "parts", "coordinates"}
    for p in out.values():
        assert len(_read(p)) > 100


def test_unassemblable_design_is_refused(tmp_path):
    bad = dict(JansenLeg().L)
    bad["h"] = 500.0
    with pytest.raises(ValueError):
        cad.write_assembly(JansenLeg(bad, branches=JANSEN_BRANCH),
                           tmp_path / "bad.dxf")
