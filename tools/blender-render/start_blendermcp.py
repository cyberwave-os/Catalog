"""Enable the BlenderMCP addon and start its socket server on Blender launch,
so the addon's own "Start Server" UI button never has to be clicked by hand.

Usage:
    blender --python tools/blender-render/start_blendermcp.py

Requires the ahujasid/blender-mcp addon (addon.py) already installed under
Blender's scripts/addons/ — see README.md. Port is whatever
scene.blendermcp_port defaults to (9876 as of addon v1.2) — pinned in
TWIN_PREVIEW_TOOL_PLAN.md §9's port registry, confirmed clear of the real
Cyberwave stack's ports (§1.3).
"""

import bpy

if "addon" not in bpy.context.preferences.addons:
    bpy.ops.preferences.addon_enable(module="addon")
    bpy.ops.wm.save_userpref()

scene = bpy.context.scene
if not getattr(scene, "blendermcp_server_running", False):
    bpy.ops.blendermcp.start_server()

print(f"BlenderMCP server running: {scene.blendermcp_server_running} on port {scene.blendermcp_port}")
