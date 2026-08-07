/// <reference types="vite/client" />

// Ambient shim for the one vendored file (teleop-joint-leash.ts) that reads a
// Next.js env var at module scope. vite.config.ts's `define` substitutes the
// actual value at build time; this just satisfies the type-checker without
// pulling in the full @types/node package for one property access.
declare const process: { env: Record<string, string | undefined> };
