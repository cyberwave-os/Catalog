"""yourdfpy-based structural checks — TWIN_PREVIEW_TOOL_PLAN.md §5.2/§7.

No single existing tool combines these three checks (confirmed by the plan's
prior-art research): every joint's parent/child link exists, every mesh file
referenced actually resolves, and every inertia tensor is physically
plausible. `check_urdf` (ROS's urdfdom) only covers the first two implicitly
by failing to parse; nothing checks inertia plausibility anywhere. This is a
thin, purpose-built doctor pass, not a reimplementation of a bigger tool.

API verified live against yourdfpy (see the plan's §7 research) — Joint.origin
is a 4x4 numpy transform, Limit has {lower, upper, effort, velocity}, and
validate_filenames() is a real built-in method, not something added here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yourdfpy


@dataclass
class DoctorResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def report(self) -> str:
        lines = [f"ok={self.ok}"]
        for e in self.errors:
            lines.append(f"  ERROR: {e}")
        for w in self.warnings:
            lines.append(f"  WARNING: {w}")
        return "\n".join(lines)


def check_structural(urdf: yourdfpy.URDF) -> tuple[list[str], list[str]]:
    """Every joint's parent/child link exists as an actual <link>."""
    errors: list[str] = []
    warnings: list[str] = []
    link_names = set(urdf.link_map.keys())
    for joint_name, joint in urdf.joint_map.items():
        if joint.parent not in link_names:
            errors.append(f"joint '{joint_name}': parent link '{joint.parent}' does not exist")
        if joint.child not in link_names:
            errors.append(f"joint '{joint_name}': child link '{joint.child}' does not exist")
    return errors, warnings


def check_mesh_files(urdf: yourdfpy.URDF) -> tuple[list[str], list[str]]:
    """Every mesh file referenced by a visual/collision geometry resolves on disk.

    Delegates to yourdfpy's own validate_filenames() rather than re-walking
    the tree by hand.
    """
    errors: list[str] = []
    if not urdf.validate_filenames():
        errors.append(
            "one or more mesh files referenced by the URDF do not resolve — "
            "re-run with load_meshes=True to see which via the load exception, "
            "or inspect each link's visual/collision geometry.filename by hand"
        )
    return errors, []


def _inertia_matrix(inertial) -> np.ndarray | None:
    inertia = getattr(inertial, "inertia", None)
    if inertia is None:
        return None
    return np.asarray(inertia, dtype=float).reshape(3, 3)


def check_inertia_plausibility(urdf: yourdfpy.URDF) -> tuple[list[str], list[str]]:
    """Mass must be positive; the inertia tensor must be positive-definite and
    satisfy the triangle inequalities (Ixx+Iyy>=Izz etc.) — no existing tool
    checks this (only computes it), confirmed by the plan's §7 research.
    """
    errors: list[str] = []
    warnings: list[str] = []
    for link_name, link in urdf.link_map.items():
        inertial = getattr(link, "inertial", None)
        if inertial is None:
            continue  # a massless/inertial-less link (e.g. a pure visual frame) is not an error
        mass = getattr(inertial, "mass", None)
        if mass is not None and mass <= 0:
            errors.append(f"link '{link_name}': mass must be positive, got {mass}")

        tensor = _inertia_matrix(inertial)
        if tensor is None:
            continue
        ixx, iyy, izz = tensor[0, 0], tensor[1, 1], tensor[2, 2]
        eigenvalues = np.linalg.eigvalsh(tensor)
        if np.any(eigenvalues <= 0):
            errors.append(
                f"link '{link_name}': inertia tensor is not positive-definite "
                f"(eigenvalues={eigenvalues.tolist()})"
            )
        # Triangle inequalities: each principal moment can't exceed the sum of the other two.
        if ixx + iyy < izz - 1e-9 or ixx + izz < iyy - 1e-9 or iyy + izz < ixx - 1e-9:
            warnings.append(
                f"link '{link_name}': inertia diagonal ({ixx:.3g}, {iyy:.3g}, {izz:.3g}) "
                "violates the triangle inequality — physically implausible for a rigid body"
            )
    return errors, warnings


def run_doctor(urdf_path: str | Path) -> DoctorResult:
    urdf = yourdfpy.URDF.load(str(urdf_path), load_meshes=False, build_scene_graph=False)

    all_errors: list[str] = []
    all_warnings: list[str] = []
    for check in (check_structural, check_mesh_files, check_inertia_plausibility):
        errors, warnings = check(urdf)
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    return DoctorResult(ok=not all_errors, errors=all_errors, warnings=all_warnings)


def _cli() -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("urdf_path")
    args = parser.parse_args()

    result = run_doctor(args.urdf_path)
    print(result.report())
    return 0 if result.ok else 1


if __name__ == "__main__":
    import sys

    sys.exit(_cli())
