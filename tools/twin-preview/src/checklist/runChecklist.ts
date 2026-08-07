// Codifies TWIN_PREVIEW_TOOL_PLAN.md §3.7 — the same rules the real frontend
// applies (§1.1), run against the parsed URDF + the controller policy that
// will eventually be seeded (never hand-typed — see export_controller_policy.py).

export interface ParsedJoint {
  name: string;
  jointType: string; // urdf-loader's own field name: revolute | continuous | prismatic | fixed | ...
  limit?: { lower?: number; upper?: number };
  mimic?: unknown; // present when urdf-loader parsed a native <mimic> tag
}

export interface KeyboardBinding {
  key: string;
  direction: "increase" | "decrease";
  jointName: string;
  mimicJoints?: { jointName: string; multiplier: number; offset: number }[];
}

export interface ControllerPolicy {
  catalog_key: string;
  name: string;
  metadata: {
    keyboard_bindings: KeyboardBinding[];
  };
}

export type CheckSeverity = "error" | "warning";

export interface CheckResult {
  id: string;
  severity: CheckSeverity;
  message: string;
}

export interface ChecklistResult {
  ok: boolean;
  jointCount: number;
  boundJointCount: number;
  results: CheckResult[];
}

const CONTROLLABLE_JOINT_TYPES = new Set(["revolute", "prismatic", "continuous"]);

export function runChecklist(
  joints: Record<string, ParsedJoint>,
  policy: ControllerPolicy | null,
): ChecklistResult {
  const results: CheckResult[] = [];
  const jointNames = new Set(Object.keys(joints));

  if (!policy) {
    return {
      ok: false,
      jointCount: jointNames.size,
      boundJointCount: 0,
      results: [{ id: "no-policy", severity: "error", message: "No controller policy loaded" }],
    };
  }

  const boundNames = new Set<string>();
  for (const binding of policy.metadata.keyboard_bindings) {
    boundNames.add(binding.jointName);
    for (const mimic of binding.mimicJoints ?? []) {
      boundNames.add(mimic.jointName);
    }
  }

  for (const binding of policy.metadata.keyboard_bindings) {
    checkBoundJoint(binding.jointName, joints, results, `binding "${binding.key}"`);
  }
  for (const binding of policy.metadata.keyboard_bindings) {
    for (const mimic of binding.mimicJoints ?? []) {
      checkBoundJoint(mimic.jointName, joints, results, `mimicJoints of binding "${binding.key}"`);
    }
  }

  const ok = !results.some((r) => r.severity === "error");
  return { ok, jointCount: jointNames.size, boundJointCount: boundNames.size, results };
}

function checkBoundJoint(
  jointName: string,
  joints: Record<string, ParsedJoint>,
  results: CheckResult[],
  context: string,
) {
  const joint = joints[jointName];
  if (!joint) {
    results.push({
      id: `missing:${jointName}`,
      severity: "error",
      message: `${context} references joint "${jointName}", which does not exist in the URDF (case-sensitive match)`,
    });
    return;
  }
  if (!CONTROLLABLE_JOINT_TYPES.has(joint.jointType)) {
    results.push({
      id: `wrong-type:${jointName}`,
      severity: "error",
      message: `${context}: joint "${jointName}" has type "${joint.jointType}" — must be revolute, prismatic, or continuous`,
    });
  }
  if (joint.mimic) {
    results.push({
      id: `is-mimic-slave:${jointName}`,
      severity: "error",
      message: `${context}: joint "${jointName}" is a native URDF <mimic> slave — it cannot be independently controlled`,
    });
  }
  if (joint.jointType !== "continuous") {
    const lower = joint.limit?.lower;
    const upper = joint.limit?.upper;
    if (lower === undefined || upper === undefined || lower === upper) {
      results.push({
        id: `degenerate-limits:${jointName}`,
        severity: "warning",
        message: `${context}: joint "${jointName}" has degenerate lower/upper limits (${lower} / ${upper}) — will render as unbounded`,
      });
    }
  }
}
