"use client";

import { mapSchemaToUrdfJointName } from "@/lib/utils/joint-name-mapping";

const CONTROLLABLE_JOINT_TYPES = new Set([
  "revolute",
  "continuous",
  "prismatic",
]);

export type UrdfJointLike = {
  jointType?: string;
  mimic?: unknown;
  mimicJoint?: unknown;
};

export function hasSchemaJoints(
  schema: { joints?: unknown } | null | undefined,
): boolean {
  return Array.isArray(schema?.joints);
}

export function getSchemaMimicUrdfJointNames(
  schema: { joints?: unknown } | null | undefined,
  robotJoints: Record<string, { jointType?: string }>,
): Set<string> {
  const schemaJoints = Array.isArray(schema?.joints) ? schema.joints : [];
  const names = new Set<string>();
  schemaJoints.forEach((entry) => {
    if (!entry || typeof entry !== "object") return;
    const joint = entry as { name?: unknown; mimic?: unknown };
    if (!joint.mimic || typeof joint.mimic !== "object") return;
    const schemaJointName = typeof joint.name === "string" ? joint.name : "";
    if (!schemaJointName) return;
    const urdfJointName = mapSchemaToUrdfJointName(schemaJointName, robotJoints);
    if (urdfJointName) names.add(urdfJointName);
  });
  return names;
}

export function isControllableUrdfJoint(
  jointName: string,
  joint: UrdfJointLike,
  options: {
    schemaPresent: boolean;
    schemaMimicJointNames?: Set<string> | string[];
  },
): boolean {
  if (!CONTROLLABLE_JOINT_TYPES.has(joint?.jointType ?? "")) {
    return false;
  }
  const schemaMimicNames =
    options.schemaMimicJointNames instanceof Set
      ? options.schemaMimicJointNames
      : new Set(options.schemaMimicJointNames ?? []);
  if (options.schemaPresent) {
    return !schemaMimicNames.has(jointName);
  }
  return !joint?.mimic && !joint?.mimicJoint && !schemaMimicNames.has(jointName);
}
