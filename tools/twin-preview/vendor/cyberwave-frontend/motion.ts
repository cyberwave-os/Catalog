"use client";

import type {
  Animation,
  AnimationStep,
  InterpolationType,
  Keyframe,
} from "@/lib/types/motion";
import { normalizeQuaternion, type Quaternion } from "@/lib/utils/rotation";
import * as THREE from "three";

// Re-export types for convenience
export type { InterpolationType } from "@/lib/types/motion";

/**
 * Centralized motion utilities for animation interpolation and joint manipulation.
 * Used across animation-player, locomotion preview, and motion controls.
 */

// ============================================================================
// Animation Helpers
// ============================================================================

/**
 * Check if an animation uses a specific keyframe.
 * Handles both legacy (startKeyframe/endKeyframe) and new (steps) formats.
 */
export function animationUsesKeyframe(
  animation: Animation,
  keyframeName: string
): boolean {
  return (
    animation.startKeyframe === keyframeName ||
    animation.endKeyframe === keyframeName ||
    (Array.isArray(animation.steps) &&
      animation.steps.some((step) => step.keyframe === keyframeName))
  );
}

// ============================================================================
// Interpolation Functions
// ============================================================================

/**
 * Apply easing function to a normalized progress value (0-1).
 */
export function applyInterpolation(
  t: number,
  type: InterpolationType
): number {
  switch (type) {
    case "linear":
      return t;
    case "ease-in":
      return t * t;
    case "ease-out":
      return t * (2 - t);
    case "ease-in-out":
      return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
    default:
      return t;
  }
}

// ============================================================================
// Joint Angle Interpolation
// ============================================================================

/**
 * Interpolate between two sets of joint angles.
 * Handles joints that may only exist in one set.
 */
export function interpolateJointAngles(
  startAngles: Record<string, number>,
  endAngles: Record<string, number>,
  progress: number
): Record<string, number> {
  const result: Record<string, number> = {};
  const allJoints = new Set([
    ...Object.keys(startAngles),
    ...Object.keys(endAngles),
  ]);

  for (const joint of allJoints) {
    const start = startAngles[joint] ?? 0;
    const end = endAngles[joint] ?? 0;
    result[joint] = start + (end - start) * progress;
  }

  return result;
}

// ============================================================================
// Animation Sequence Helpers
// ============================================================================

export type SequenceSegment = {
  durationMs: number;
  from: Record<string, number>;
  to: Record<string, number>;
  hold: boolean;
};

export function buildSequenceSegments(
  steps: AnimationStep[],
  keyframes: Keyframe[]
) {
  if (!Array.isArray(steps) || steps.length < 2) return null;
  const keyframeMap = new Map(
    keyframes.map((kf) => [kf.name, kf.jointAngles] as const)
  );
  const normalizedSteps = steps.map((step, index) => ({
    keyframe: step.keyframe,
    transition_ms: index === 0 ? 0 : Math.max(0, step.transition_ms ?? 0),
    hold_ms: Math.max(0, step.hold_ms ?? 0),
  }));
  const segments: SequenceSegment[] = [];

  for (let i = 0; i < normalizedSteps.length; i += 1) {
    const step = normalizedSteps[i];
    const joints = keyframeMap.get(step.keyframe);
    if (!joints) return null;

    if (i === 0) {
      if (step.hold_ms > 0) {
        segments.push({
          durationMs: step.hold_ms,
          from: joints,
          to: joints,
          hold: true,
        });
      }
      continue;
    }

    const prevStep = normalizedSteps[i - 1];
    const prevJoints = keyframeMap.get(prevStep.keyframe);
    if (!prevJoints) return null;

    const transitionMs = Math.max(0, step.transition_ms ?? 0);
    if (transitionMs > 0) {
      segments.push({
        durationMs: transitionMs,
        from: prevJoints,
        to: joints,
        hold: false,
      });
    }

    if (step.hold_ms > 0) {
      segments.push({
        durationMs: step.hold_ms,
        from: joints,
        to: joints,
        hold: true,
      });
    }
  }

  const totalDurationMs = segments.reduce(
    (sum, segment) => sum + segment.durationMs,
    0
  );
  if (totalDurationMs <= 0) return null;
  return { segments, totalDurationMs };
}

export function resolveSequenceJoints(
  segments: SequenceSegment[],
  elapsedMs: number,
  interpolation: InterpolationType
) {
  let cursor = 0;
  for (const segment of segments) {
    const segmentEnd = cursor + segment.durationMs;
    if (elapsedMs <= segmentEnd) {
      if (segment.hold || segment.durationMs <= 0) {
        return segment.to;
      }
      const localProgress = Math.min(
        1,
        Math.max(0, (elapsedMs - cursor) / segment.durationMs)
      );
      const eased = applyInterpolation(localProgress, interpolation);
      return interpolateJointAngles(segment.from, segment.to, eased);
    }
    cursor = segmentEnd;
  }
  return segments[segments.length - 1]?.to ?? null;
}

// ============================================================================
// Math Utilities
// ============================================================================

/**
 * Clamp a value between min and max.
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/**
 * Normalize an angle to [-PI, PI] range.
 */
export function normalizeAngle(value: number): number {
  let result = value;
  while (result > Math.PI) result -= Math.PI * 2;
  while (result < -Math.PI) result += Math.PI * 2;
  return result;
}

/**
 * Extract heading yaw (rotation around Z axis, XY plane) from a quaternion [w, x, y, z].
 * Assumes +X is the forward axis in local space (matches mission simulator).
 * Z-up convention: yaw is measured in the XY plane.
 */
export function getYawFromQuaternion(
  rotation: Quaternion | [number, number, number, number]
): number {
  const normalized = normalizeQuaternion(rotation);
  if (!normalized) return 0;
  const { w, x, y, z } = normalized;
  const quat = new THREE.Quaternion(x, y, z, w);
  const forward = new THREE.Vector3(1, 0, 0).applyQuaternion(quat);
  return Math.atan2(forward.y, forward.x);
}

// ============================================================================
// Joint Utilities
// ============================================================================

export const DEFAULT_ANGULAR_LIMITS = { min: -Math.PI, max: Math.PI };

export interface JointPositionRange {
  min: number;
  max: number;
}

export interface JointLike {
  type?: string;
  jointType?: string;
  limit?: {
    lower?: unknown;
    upper?: unknown;
  };
  limits?: {
    lower?: unknown;
    upper?: unknown;
  };
}

function normalizedJointType(joint: JointLike | null | undefined): string {
  const type = joint?.type ?? joint?.jointType;
  return typeof type === "string" ? type.toLowerCase() : "";
}

function finiteNumber(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function declaredLowerUpper(joint: JointLike | null | undefined) {
  const rawLower = joint?.limit?.lower ?? joint?.limits?.lower;
  const rawUpper = joint?.limit?.upper ?? joint?.limits?.upper;
  return {
    lower: finiteNumber(rawLower),
    upper: finiteNumber(rawUpper),
  };
}

/**
 * Physical positional range declared by schema/URDF.
 * Continuous and missing/degenerate lower+upper are unbounded for validation.
 */
export function physicalPositionRange(
  joint: JointLike | null | undefined
): JointPositionRange | null {
  if (!joint || normalizedJointType(joint) === "continuous") {
    return null;
  }

  const { lower, upper } = declaredLowerUpper(joint);
  if (lower === undefined || upper === undefined || lower === upper) {
    return null;
  }

  return { min: Math.min(lower, upper), max: Math.max(lower, upper) };
}

/**
 * UI range for controls/previews. Continuous joints are edited on [-π, π].
 */
export function uiControlRange(
  joint: JointLike | null | undefined
): JointPositionRange {
  if (normalizedJointType(joint) === "continuous") {
    return { ...DEFAULT_ANGULAR_LIMITS };
  }

  return physicalPositionRange(joint) ?? { ...DEFAULT_ANGULAR_LIMITS };
}

/**
 * Resolve joint limits from a URDF joint definition.
 * Handles continuous, revolute, and prismatic joints.
 *
 * @deprecated Prefer physicalPositionRange() for runtime validation and
 * uiControlRange() for controls/previews.
 */
export function resolveJointLimits(
  joint: JointLike | null | undefined
): JointPositionRange {
  return uiControlRange(joint);
}

/**
 * Wrap an angle (radians) into the `[-π, π)` branch, matching the deploy
 * adapter's `wrap_to_pi`. Used to *display* continuous-joint angles so an
 * equivalent pose reported near `+π` and one near `-π` collapse onto the same
 * branch. Non-finite input is returned unchanged.
 */
export function wrapToPi(value: number): number {
  if (!Number.isFinite(value)) return value;
  // Force a non-negative modulo (JS `%` keeps the sign of the dividend, unlike
  // Python's `%` used by the adapter's wrap_to_pi), so negative angles wrap
  // correctly rather than passing through unchanged.
  const twoPi = 2 * Math.PI;
  return ((((value + Math.PI) % twoPi) + twoPi) % twoPi) - Math.PI;
}

/**
 * Number of full revolutions a raw angle is away from its wrapped branch —
 * i.e. how many turns a continuous joint has accumulated. Positive means it
 * wound up past `+π`; negative past `-π`.
 */
export function jointRevolutions(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.round((value - wrapToPi(value)) / (2 * Math.PI));
}

/**
 * Display form for a joint angle. For a *continuous* joint the value is wrapped
 * into `[-π, π)` with the revolution count reported separately, so the UI can
 * show e.g. "0.72 rad (+1 rev)". Any other joint type returns the raw value
 * with zero revolutions (bounded joints never wind up). Display-only — control
 * targets must stay unwrapped (mirrors the adapter's "targets never wrapped").
 */
export function formatContinuousAngle(
  value: number,
  jointType?: string
): { wrapped: number; revolutions: number } {
  if (jointType === "continuous") {
    return { wrapped: wrapToPi(value), revolutions: jointRevolutions(value) };
  }
  return { wrapped: value, revolutions: 0 };
}

/** Calibration entry from twin calibration API (e.g. SO101) */
export interface JointCalibrationEntry {
  range_min: number;
  range_max: number;
  homing_offset: number;
  drive_mode: string;
  id: string;
  /** Joint limit lower bound in radians (from calibration conversion) */
  lower?: number;
  /** Joint limit upper bound in radians (from calibration conversion) */
  upper?: number;
}

export function calibrationPositionRange(
  jointName: string,
  calibration?: Record<string, JointCalibrationEntry> | null,
  jointIndex?: number
): JointPositionRange | null {
  let calib = calibration?.[jointName];

  if (!calib && jointIndex !== undefined && jointIndex > 0 && calibration) {
    calib = calibration[`_${jointIndex}`];
  }

  const lower = finiteNumber(calib?.lower);
  const upper = finiteNumber(calib?.upper);
  if (lower === undefined || upper === undefined || lower >= upper) {
    return null;
  }
  return { min: lower, max: upper };
}

export function effectivePhysicalPositionRange(
  joint: JointLike | null | undefined,
  jointName: string,
  calibration?: Record<string, JointCalibrationEntry> | null,
  jointIndex?: number
): JointPositionRange | null {
  return (
    calibrationPositionRange(jointName, calibration, jointIndex) ??
    physicalPositionRange(joint)
  );
}

/**
 * Resolve effective joint limits, preferring calibration data when available.
 * Calibration (e.g. from SO101 cw_calibrate) overrides URDF limits for physical robots.
 * Uses lower/upper (radians) when present; otherwise falls back to UI control range.
 *
 * @param joint - URDF joint object with jointType and limit
 * @param jointName - URDF joint name (e.g., "shoulder_pan")
 * @param calibration - Calibration data keyed by schema joint names (e.g., "_1", "_2")
 * @param jointIndex - Optional 1-based index of this joint among controllable joints.
 *                     Used to map URDF joint name to calibration key "_N" when jointName lookup fails.
 */
export function getEffectiveJointLimits(
  joint: JointLike | null | undefined,
  jointName: string,
  calibration?: Record<string, JointCalibrationEntry> | null,
  jointIndex?: number
): JointPositionRange {
  return (
    calibrationPositionRange(jointName, calibration, jointIndex) ??
    uiControlRange(joint)
  );
}
