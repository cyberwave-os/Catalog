import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

const vendorDir = path.resolve(__dirname, "vendor/cyberwave-frontend");

// Port 5173 is pinned and reserved for this tool in TWIN_PREVIEW_TOOL_PLAN.md §9 —
// confirmed clear of the real Cyberwave stack's ports (§1.3). Do not change
// without updating that registry.
//
// Catalog assets (urdf/ + meshes/) live at the repo root, two levels above this
// tool. Rather than copying them in, `public/catalog` is a symlink to the
// Catalog repo root (see README.md) so they're served live at /catalog/... —
// `server.fs.allow` widens the dev server's file-read allowlist to cover the
// symlink target explicitly, since some Vite versions are conservative about
// following symlinks that point outside the project directory.
export default defineConfig({
  plugins: [react()],
  define: {
    // The vendored teleop-joint-leash.ts reads this Next.js env var at module
    // scope. We run in "simulate" mode (Viewer3D.tsx), where the leash is a
    // no-op regardless — this substitution just lets the module load without
    // a real Next.js env at all, without editing the vendored file.
    "process.env.NEXT_PUBLIC_TELEOP_LEASH_DISABLED": JSON.stringify("false"),
  },
  resolve: {
    alias: {
      // The vendored files (vendor/cyberwave-frontend/, unmodified from
      // cyberwave-frontend) use its Next.js "@/..." path alias internally.
      // Rather than editing their import specifiers — which would break the
      // "vendored, unmodified" guarantee §3.6 relies on for drift detection —
      // these map each specifier straight to its vendored copy.
      "@/lib/utils/motion": path.join(vendorDir, "motion.ts"),
      "@/lib/utils/rotation": path.join(vendorDir, "rotation.ts"),
      "@/lib/utils/joint-name-mapping": path.join(vendorDir, "joint-name-mapping.ts"),
      "@/lib/types/motion": path.join(vendorDir, "motion-types.ts"),
      "@/lib/constants/cyberwave-constants": path.join(vendorDir, "cyberwave-constants.ts"),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    fs: {
      allow: ["..", "../.."],
    },
  },
});
