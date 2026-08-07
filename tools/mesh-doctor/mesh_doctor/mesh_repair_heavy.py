"""PyMeshLab fallback for repairs trimesh can't do — non-manifold cleanup,
hole-filling, quality-aware decimation. See TWIN_PREVIEW_TOOL_PLAN.md §5.2;
use mesh_fixes.py (trimesh) first, reach for this only when a specific asset
actually needs one of these.

Filter names verified live against pymeshlab 2025.7 (plan §7 research) —
confirmed headless-clean on macOS, no GUI/Qt dependency at runtime.
"""

from __future__ import annotations

from pathlib import Path

import pymeshlab


def load(path: str | Path) -> pymeshlab.MeshSet:
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(str(path))
    return ms


def repair_non_manifold(ms: pymeshlab.MeshSet) -> pymeshlab.MeshSet:
    ms.meshing_remove_duplicate_vertices()
    ms.meshing_remove_duplicate_faces()
    ms.meshing_repair_non_manifold_edges()
    ms.meshing_repair_non_manifold_vertices()
    return ms


def close_holes(ms: pymeshlab.MeshSet, max_hole_size: int = 30) -> pymeshlab.MeshSet:
    ms.meshing_close_holes(maxholesize=max_hole_size)
    return ms


def reorient_normals(ms: pymeshlab.MeshSet) -> pymeshlab.MeshSet:
    ms.meshing_re_orient_faces_coherently()
    return ms


def decimate_for_collision(ms: pymeshlab.MeshSet, target_face_num: int = 500) -> pymeshlab.MeshSet:
    """Quality-aware simplification — for a <collision> mesh that needs to be
    cheap to simulate but shouldn't lose its silhouette. For a mesh that just
    needs to be watertight-simple, prefer mesh_fixes.convex_hull_collision
    instead — this is for cases where a convex hull would be too different
    from the real shape (e.g. a concave chassis) to serve as collision geometry.
    """
    ms.meshing_decimation_quadric_edge_collapse(
        targetfacenum=target_face_num,
        preservetopology=True,
        preserveboundary=True,
        planarquadric=True,
    )
    return ms


def save(ms: pymeshlab.MeshSet, path: str | Path) -> None:
    ms.save_current_mesh(str(path))


def _cli() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mesh_path")
    parser.add_argument("--repair-non-manifold", action="store_true")
    parser.add_argument("--close-holes", action="store_true")
    parser.add_argument("--reorient-normals", action="store_true")
    parser.add_argument("--decimate-for-collision", type=int, default=None, metavar="TARGET_FACE_NUM")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    ms = load(args.mesh_path)
    if args.repair_non_manifold:
        repair_non_manifold(ms)
    if args.close_holes:
        close_holes(ms)
    if args.reorient_normals:
        reorient_normals(ms)
    if args.decimate_for_collision is not None:
        decimate_for_collision(ms, args.decimate_for_collision)

    out_path = args.out or args.mesh_path
    save(ms, out_path)
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(_cli())
