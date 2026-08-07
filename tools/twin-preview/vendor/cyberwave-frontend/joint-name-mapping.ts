"use client";

/**
 * Utilities for mapping between schema joint names (e.g. "_1", "_2" from recordings/MQTT)
 * and URDF joint names (from the URDF file, used by the loader).
 *
 * Recordings and MQTT from the edge use schema joint names. The URDF loader expects
 * the exact joint names from the URDF XML. This mapping ensures playback and live
 * mode work when names differ.
 */

const CONTROLLABLE_JOINT_TYPES = new Set([
  "revolute",
  "prismatic",
  "continuous",
]);

export type SchemaJointStateValue =
  | number
  | {
      position?: unknown;
      velocity?: unknown;
      effort?: unknown;
    };

/**
 * Get controllable joint names from URDF joints object, in stable order.
 * Order matches URDF traversal (object key insertion order).
 */
export function getControllableUrdfJointNames(
  joints: Record<string, { jointType?: string }>,
): string[] {
  return Object.entries(joints)
    .filter(([, j]) => j?.jointType && CONTROLLABLE_JOINT_TYPES.has(j.jointType))
    .map(([name]) => name);
}

/**
 * Parse schema-style joint name (e.g. "_1", "_2") to 0-based index.
 * Returns -1 if not a schema-style name.
 */
function parseSchemaJointIndex(name: string): number {
  const match = name.match(/^_(\d+)$/);
  if (!match) return -1;
  return parseInt(match[1], 10) - 1; // "_1" -> 0
}

/**
 * Map schema joint name to URDF joint name.
 * - If schema name exists in URDF joints, use it directly (identity).
 * - Otherwise use index-based mapping: "_1" -> first controllable URDF joint, etc.
 *
 * @returns URDF joint name, or null if no mapping found.
 */
export function mapSchemaToUrdfJointName(
  schemaName: string,
  urdfJoints: Record<string, { jointType?: string }>,
): string | null {
  if (schemaName in urdfJoints) {
    return schemaName;
  }
  const urdfControllable = getControllableUrdfJointNames(urdfJoints);
  const index = parseSchemaJointIndex(schemaName);
  if (index >= 0 && index < urdfControllable.length) {
    return urdfControllable[index];
  }
  return null;
}

/**
 * Get the controllable joint names declared in a universal schema
 * (`schema.joints[].name`), in order. These are the REAL joint names the
 * sim / backend resolve against (e.g. "joint_1", or SO101's "_1"). We publish
 * and key by these directly — never by a positional "_N" alias.
 */
export function getControllableSchemaJointNames(
  schema: { joints?: unknown } | null | undefined,
): string[] {
  if (!schema || !Array.isArray((schema as { joints?: unknown }).joints)) {
    return [];
  }
  const names: string[] = [];
  for (const joint of (schema as { joints: unknown[] }).joints) {
    if (!joint || typeof joint !== "object") continue;
    const j = joint as { name?: unknown; type?: unknown };
    if (typeof j.type === "string" && CONTROLLABLE_JOINT_TYPES.has(j.type)) {
      if (typeof j.name === "string" && j.name.length > 0) {
        names.push(j.name);
      }
    }
  }
  return names;
}

/**
 * Resolve an ordinal joint-name placeholder (`_N`) to the twin's REAL
 * controllable joint name at that 1-based index, given the twin's controllable
 * joints in order (e.g. from `getControllableSchemaJointNames`).
 *
 * The universal keyboard controller stores asset-agnostic ordinal bindings
 * (`_1`..`_N`); this resolves each to the actual joint name ONCE (at load) so
 * the runtime keys everything by real names instead of propagating `_N`.
 *
 * - `_N` → `controllableNames[N-1]` (unchanged if out of range / list empty).
 * - Everything else (real names) passes through unchanged. For robots whose
 *   real names ARE `_1`.. (e.g. SO101) this is a no-op, since
 *   `controllableNames[N-1] === "_N"`.
 */
export function resolveOrdinalJointName(
  jointName: string,
  controllableNames: string[],
): string {
  const ordinalMatch = /^_(\d+)$/.exec(jointName);
  if (!ordinalMatch) {
    return jointName;
  }
  const realName = controllableNames[Number(ordinalMatch[1]) - 1];
  return realName ?? jointName;
}

/**
 * Map a URDF joint name to the twin's REAL schema joint name — the name the
 * sim/plant/edge resolve against — using the twin's universal schema.
 *
 * This is the single mapper for ALL joint publishing (live teleop, edit-mode
 * sliders, teleport/direct-set). It returns the actual
 * `universal_schema.joints[].name` (e.g. Kinova "joint_1", SO101 "_1"): it
 * matches directly if the URDF name is already a schema joint name, otherwise
 * falls back to the controllable-joint index correspondence. Returns the URDF
 * name unchanged when the schema is unavailable.
 *
 * We deliberately do NOT force a positional "_N" alias here: those only resolve
 * for robots whose real names happen to be "_N" (e.g. SO101) and silently
 * break every other robot (e.g. Kinova), which is the class of bug this
 * replaced.
 */
export function mapUrdfToSchemaNameFromSchema(
  urdfName: string,
  urdfJoints: Record<string, { jointType?: string }>,
  schema: { joints?: unknown } | null | undefined,
): string {
  const schemaNames = getControllableSchemaJointNames(schema);
  if (schemaNames.length === 0) return urdfName;
  // The URDF name is already a real schema joint name (e.g. Kinova "joint_1").
  if (schemaNames.includes(urdfName)) return urdfName;
  // Positional correspondence: URDF controllable index → schema name.
  const urdfControllable = getControllableUrdfJointNames(urdfJoints);
  const index = urdfControllable.indexOf(urdfName);
  if (index >= 0 && index < schemaNames.length) {
    return schemaNames[index];
  }
  return urdfName;
}

/**
 * TS mirror of `sanitize_name`, which named every joint in `universal_schema`.
 * Wider than `toSchemaJointName`: non-word chars become `_` and ANY digit-leading
 * name is prefixed ("2_link_joint" -> "_2_link_joint", "arm.joint" -> "arm_joint").
 */
export function sanitizeToSchemaJointName(name: string): string {
  let sanitized = name.replace(/[^\w-]/g, "_");
  if (sanitized && /^\d/.test(sanitized)) {
    sanitized = `_${sanitized}`;
  }
  return sanitized || "unnamed";
}

/** Raw name + its full `sanitize_name` form + the de-underscored form.
 *
 * The `sanitize_name` alias is what lets the inspector author a URDF name and still
 * resolve it against the schema domain (SO101 "1" -> "_1"); `toSchemaJointName` was
 * dropped on dev in favour of the schema-driven mapping above. */
export function getJointNameAliases(name: string): string[] {
  const trimmed = name.trim();
  if (!trimmed) {
    return [];
  }

  const aliases = new Set<string>([trimmed]);
  aliases.add(sanitizeToSchemaJointName(trimmed));

  if (trimmed.startsWith("_")) {
    aliases.add(trimmed.slice(1));
  }

  return [...aliases];
}

/**
 * Resolve a joint name against available joint names using alias matching.
 * Returns the first matching name from `availableNames`, preserving the actual
 * runtime key shape (e.g. "_1" vs "1").
 */
export function resolveJointNameAlias(
  name: string,
  availableNames: Iterable<string>,
): string | null {
  const available = new Set<string>(availableNames);
  for (const alias of getJointNameAliases(name)) {
    if (available.has(alias)) {
      return alias;
    }
  }
  return null;
}

/** Outcome of reconciling one channel into the schema joint-name domain. */
export interface JointNameReconcileResult<T> {
  resolved: T;
  /** Input names with no counterpart in the twin's schema, in input order. */
  unresolved: string[];
}

/**
 * Rewrite map keys from the URDF domain (what the inspector authors) into the
 * schema domain (what the wire and drivers use), reporting what didn't resolve
 * rather than dropping it — a dropped joint publishes a partial pose. Mirrors
 * `reconcile_joint_map`. Empty `schemaJointNames` = schema not loaded, so the
 * input passes through unchanged.
 */
export function reconcileJointMapToSchema<V>(
  values: Record<string, V> | null | undefined,
  schemaJointNames: Iterable<string>,
): JointNameReconcileResult<Record<string, V>> {
  const available = [...schemaJointNames];
  if (!values || available.length === 0) {
    return { resolved: { ...(values ?? {}) }, unresolved: [] };
  }
  const resolved: Record<string, V> = {};
  const unresolved: string[] = [];
  for (const [name, value] of Object.entries(values)) {
    const schemaName = resolveJointNameAlias(name, available);
    if (schemaName === null) {
      unresolved.push(name);
      continue;
    }
    resolved[schemaName] = value;
  }
  return { resolved, unresolved };
}

/** As above, for `explicit_joints`: order-preserving and de-duplicated. */
export function reconcileJointNamesToSchema(
  names: string[] | null | undefined,
  schemaJointNames: Iterable<string>,
): JointNameReconcileResult<string[]> {
  const available = [...schemaJointNames];
  if (!names || available.length === 0) {
    return { resolved: [...(names ?? [])], unresolved: [] };
  }
  const resolved: string[] = [];
  const unresolved: string[] = [];
  for (const name of names) {
    const schemaName = resolveJointNameAlias(name, available);
    if (schemaName === null) {
      unresolved.push(name);
      continue;
    }
    if (!resolved.includes(schemaName)) resolved.push(schemaName);
  }
  return { resolved, unresolved };
}

export function jointStatePosition(value: SchemaJointStateValue): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (
    typeof value === "object" &&
    value !== null &&
    typeof value.position === "number" &&
    Number.isFinite(value.position)
  ) {
    return value.position;
  }
  return null;
}

export function normalizeJointStatePositions(
  schemaStates: Record<string, SchemaJointStateValue> | null | undefined,
): Record<string, number> {
  const result: Record<string, number> = {};
  if (!schemaStates) {
    return result;
  }
  for (const [name, value] of Object.entries(schemaStates)) {
    const position = jointStatePosition(value);
    if (position !== null) {
      result[name] = position;
    }
  }
  return result;
}

/**
 * Map a record of schema joint names -> values to URDF joint names -> values.
 */
export function mapSchemaJointStatesToUrdf(
  schemaStates: Record<string, SchemaJointStateValue>,
  urdfJoints: Record<string, { jointType?: string }>,
): Record<string, number> {
  const result: Record<string, number> = {};
  for (const [schemaName, value] of Object.entries(schemaStates)) {
    const position = jointStatePosition(value);
    if (position === null) {
      continue;
    }
    const urdfName = mapSchemaToUrdfJointName(schemaName, urdfJoints);
    if (urdfName) {
      result[urdfName] = position;
    }
  }
  return result;
}
