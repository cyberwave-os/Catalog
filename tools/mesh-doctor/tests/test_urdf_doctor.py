"""Regression tests for check_inertia_plausibility.

Uses SimpleNamespace stand-ins for yourdfpy's URDF/Link/Inertial objects
rather than URDF XML strings, specifically so the non-symmetric-tensor case
is testable at all: yourdfpy's own parser (_parse_inertia) mirrors ixy/ixz/iyz
into both symmetric slots, so there's no URDF text that produces an
asymmetric tensor through the real loader. The check still accepts any 3x3
array, so it's tested directly against one that bypasses the parser.
"""

from types import SimpleNamespace

import numpy as np
import pytest

from mesh_doctor.urdf_doctor import check_inertia_plausibility


def _fake_urdf(links: dict) -> SimpleNamespace:
    return SimpleNamespace(link_map=links)


def _link(mass=1.0, inertia=None):
    return SimpleNamespace(inertial=SimpleNamespace(mass=mass, inertia=inertia))


def test_positive_definite_symmetric_tensor_passes():
    urdf = _fake_urdf({"link1": _link(inertia=np.eye(3))})
    errors, warnings = check_inertia_plausibility(urdf)
    assert errors == []


def test_negative_mass_is_an_error():
    urdf = _fake_urdf({"link1": _link(mass=-1.0, inertia=np.eye(3))})
    errors, warnings = check_inertia_plausibility(urdf)
    assert any("mass must be positive" in e for e in errors)


def test_non_positive_definite_tensor_is_an_error():
    # A diagonal matrix with a zero eigenvalue -- degenerate, not physically
    # valid for a rigid body with actual extent in all three axes.
    tensor = np.diag([1.0, 1.0, 0.0])
    urdf = _fake_urdf({"link1": _link(inertia=tensor)})
    errors, warnings = check_inertia_plausibility(urdf)
    assert any("not positive-definite" in e for e in errors)


def test_asymmetric_tensor_is_rejected_before_eigvalsh():
    """Regression test for the eigvalsh-reads-only-half-the-matrix issue:
    a tensor that disagrees between its two off-diagonal halves must be
    flagged as non-symmetric, not silently evaluated using only one half.
    """
    tensor = np.array(
        [
            [1.0, 0.5, 0.0],
            [0.9, 1.0, 0.0],  # 0.9 != 0.5 above -- genuinely asymmetric
            [0.0, 0.0, 1.0],
        ]
    )
    urdf = _fake_urdf({"link1": _link(inertia=tensor)})
    errors, warnings = check_inertia_plausibility(urdf)
    assert any("not symmetric" in e for e in errors)


def test_triangle_inequality_violation_is_a_warning_not_an_error():
    # Positive-definite (all eigenvalues > 0) but Izz > Ixx + Iyy -- violates
    # the rigid-body triangle inequality without being non-positive-definite.
    tensor = np.diag([1.0, 1.0, 3.0])
    urdf = _fake_urdf({"link1": _link(inertia=tensor)})
    errors, warnings = check_inertia_plausibility(urdf)
    assert errors == []
    assert any("triangle inequality" in w for w in warnings)


def test_missing_inertial_is_skipped_not_an_error():
    urdf = _fake_urdf({"link1": SimpleNamespace(inertial=None)})
    errors, warnings = check_inertia_plausibility(urdf)
    assert errors == [] and warnings == []
