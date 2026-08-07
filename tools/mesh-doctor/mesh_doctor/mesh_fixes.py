"""Trimesh-based mesh repair — the "safe to auto-apply" half of
TWIN_PREVIEW_TOOL_PLAN.md §5.3: recentering, unit rescale, normal/winding
fixes, and a simplified convex-hull collision mesh. Corrections to
unambiguous defects only — anything where "correct" depends on design intent
(is a gap between two links a bug or the real hardware's mounting geometry?)
belongs in a human/render-loop decision, not here.

API names verified live against trimesh 5.0.0 (see the research referenced
in the plan's §7) — this is not written from memory.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh


def load(path: str | Path) -> trimesh.Trimesh:
    mesh = trimesh.load(str(path), force="mesh")
    if not isinstance(mesh, trimesh.Trimesh):
        raise TypeError(f"{path} did not load as a single Trimesh (got {type(mesh)})")
    return mesh


def bbox_extents(mesh: trimesh.Trimesh) -> np.ndarray:
    """(x, y, z) size of the mesh's own bounding box, in its current units."""
    return mesh.extents


def recenter(mesh: trimesh.Trimesh, method: str = "bbox") -> trimesh.Trimesh:
    """Translate the mesh so its own origin sits at (0, 0, 0).

    method="bbox" (default): axis-aligned bounding-box center — matches how a
    part typically mounts flush against a neighboring link.
    method="centroid": volume-weighted centroid — better for organic/irregular
    shapes where the bbox center may sit outside the solid.
    """
    if method == "bbox":
        offset = mesh.bounding_box.centroid
    elif method == "centroid":
        offset = mesh.centroid
    else:
        raise ValueError(f"unknown method: {method!r}")
    mesh.apply_translation(-offset)
    return mesh


def rescale(mesh: trimesh.Trimesh, factor: float) -> trimesh.Trimesh:
    """Uniform scale, e.g. 0.001 to convert millimetres to metres."""
    if factor <= 0:
        raise ValueError(f"scale factor must be positive, got {factor} (0 collapses the mesh to a point, negative mirrors it)")
    mesh.apply_scale(factor)
    return mesh


def detect_likely_mm_scale(mesh: trimesh.Trimesh, expected_max_extent_m: float = 2.0) -> bool:
    """Heuristic only, per plan §5.3 — flags, does not decide.

    If a mesh's largest bounding-box dimension is implausibly large for a
    single robot part (default threshold: 2 metres), it's *probably* still in
    millimetres. This is a prompt for a human/render-loop check, not proof —
    a genuinely large link (e.g. a mobile base chassis) would also trip it.
    """
    return float(np.max(mesh.extents)) > expected_max_extent_m


def fix_normals(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Winding/normal-consistency repair (trimesh.repair.fix_normals)."""
    trimesh.repair.fix_normals(mesh, multibody=False)
    return mesh


def remove_duplicates(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    mesh.merge_vertices()
    mesh.update_faces(mesh.unique_faces())
    return mesh


def convex_hull_collision(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """A simplified, always-watertight collision mesh for the <collision> tag.

    Requires scipy (pulled in by the "trimesh[easy]" extra, not bare
    "trimesh" — see the plan's §7 research note).
    """
    return mesh.convex_hull


def save(mesh: trimesh.Trimesh, path: str | Path) -> None:
    mesh.export(str(path))


def _cli() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mesh_path")
    parser.add_argument("--recenter", choices=["bbox", "centroid"], default=None)
    parser.add_argument("--rescale", type=float, default=None, help="e.g. 0.001 for mm->m")
    parser.add_argument("--fix-normals", action="store_true")
    parser.add_argument("--collision-hull-out", default=None, help="write a convex-hull collision mesh here")
    parser.add_argument("--out", default=None, help="write the fixed mesh here (in-place if omitted)")
    args = parser.parse_args()

    mesh = load(args.mesh_path)

    print(f"loaded {args.mesh_path}: extents={mesh.extents}, watertight={mesh.is_watertight}")
    if detect_likely_mm_scale(mesh):
        print("warning: largest extent > 2m — this mesh may still be in millimetres")

    if args.recenter:
        recenter(mesh, method=args.recenter)
        print(f"recentered ({args.recenter}); new centroid={mesh.centroid}")
    if args.rescale is not None:
        rescale(mesh, args.rescale)
        print(f"rescaled by {args.rescale}; new extents={mesh.extents}")
    if args.fix_normals:
        fix_normals(mesh)
        print("normals fixed")

    if args.collision_hull_out:
        hull = convex_hull_collision(mesh)
        save(hull, args.collision_hull_out)
        print(f"wrote convex-hull collision mesh to {args.collision_hull_out}")

    out_path = args.out or args.mesh_path
    save(mesh, out_path)
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(_cli())
