#!/usr/bin/env python3
"""Extract one controller's dict literal out of cyberwave-backend's
seed_controllers.py, by catalog_key, without importing Django.

Why this exists: TWIN_PREVIEW_TOOL_PLAN.md §3.5 — twin-preview must never
hand-copy keyboard_bindings, because a hand-typed copy is exactly how the
current `unitree/d1-t-with-gripper` controller block went stale in the first
place. This script parses seed_controllers.py as plain Python source (via the
`ast` module — no Django import, no running server needed) and pulls out the
literal dict for a given catalog_key, dumping it as JSON.

Usage:
    python3 export_controller_policy.py controller:keyboard_autogen_d1_t_with_gripper:v1
    python3 export_controller_policy.py <catalog_key> --out ../src/fixtures/<name>.json
    python3 export_controller_policy.py <catalog_key> --seed-file /path/to/seed_controllers.py

Defaults to the seed_controllers.py inside the cyberwave monorepo checkout
path used throughout TWIN_PREVIEW_TOOL_PLAN.md
(~/Documents/monorepos/1-first/cyberwave/) — override with --seed-file or the
CYBERWAVE_MONOREPO env var if your checkout lives elsewhere.
"""

import argparse
import ast
import json
import os
import sys
from pathlib import Path

DEFAULT_MONOREPO = Path(
    os.environ.get(
        "CYBERWAVE_MONOREPO",
        "~/Documents/monorepos/1-first/cyberwave",
    )
).expanduser()

DEFAULT_SEED_FILE = (
    DEFAULT_MONOREPO
    / "cyberwave-backend"
    / "src"
    / "app"
    / "management"
    / "commands"
    / "seed_controllers.py"
)


class UnsupportedNode(ValueError):
    pass


def safe_eval(node: ast.AST):
    """Evaluate a literal-ish AST node without exec/eval.

    Handles what seed_controllers.py actually uses: string/number/bool/None
    constants, lists, dicts, tuples, negative numbers, and dotted enum-style
    references like `ControllerType.TELEOP` (rendered as the string
    "ControllerType.TELEOP" — we don't have the real enum here, and nothing
    downstream needs the real value, only a stable readable label).
    """
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Dict):
        return {
            safe_eval(k): safe_eval(v)
            for k, v in zip(node.keys, node.values)
            if k is not None
        }
    if isinstance(node, ast.List):
        return [safe_eval(e) for e in node.elts]
    if isinstance(node, ast.Tuple):
        return [safe_eval(e) for e in node.elts]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -safe_eval(node.operand)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{safe_eval(node.value)}.{node.attr}"
    raise UnsupportedNode(f"can't safely evaluate node type: {type(node).__name__}")


def find_controller_dict(tree: ast.Module, catalog_key: str) -> ast.Dict:
    """Walk the whole module for a Dict literal whose 'catalog_key' matches."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key_node, value_node in zip(node.keys, node.values):
            if (
                isinstance(key_node, ast.Constant)
                and key_node.value == "catalog_key"
                and isinstance(value_node, ast.Constant)
                and value_node.value == catalog_key
            ):
                return node
    raise KeyError(f"No dict literal with catalog_key={catalog_key!r} found")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog_key", help="e.g. controller:keyboard_autogen_d1_t_with_gripper:v1")
    parser.add_argument("--seed-file", type=Path, default=DEFAULT_SEED_FILE)
    parser.add_argument("--out", type=Path, default=None, help="write JSON here instead of stdout")
    args = parser.parse_args()

    if not args.seed_file.is_file():
        print(f"error: seed file not found: {args.seed_file}", file=sys.stderr)
        print("Set --seed-file or CYBERWAVE_MONOREPO if your checkout lives elsewhere.", file=sys.stderr)
        return 1

    source = args.seed_file.read_text()
    tree = ast.parse(source, filename=str(args.seed_file))

    try:
        dict_node = find_controller_dict(tree, args.catalog_key)
    except KeyError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    policy = safe_eval(dict_node)
    output = json.dumps(policy, indent=2, sort_keys=False)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output + "\n")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
