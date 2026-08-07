import { physicalPositionRange, wrapToPi } from "@/lib/utils/motion";
import {
  leashJointTarget,
  TELEOP_FEEDBACK_STALE_MS,
  TELEOP_LEAD_STEPS,
  type JointLeashRejection,
  type MeasuredJointSample,
} from "./teleop-joint-leash";

/**
 * Lossless mimic coupling carried on a driver binding. The slave joint follows
 * the URDF mimic law `slave = multiplier × driver + offset`. Emitted by
 * controller autogen (`_build_mimic_groups` in `seed_controllers.py`) so teleop
 * never has to re-derive the coupling from the joint schema or limits.
 */
export interface MimicJoint {
  jointName: string;
  multiplier: number;
  offset: number;
}

export interface KeyboardJointBinding {
  jointName: string;
  direction: "increase" | "decrease";
  key: string;
  mimicJoints?: MimicJoint[];
}

export interface TeleopJointInfo {
  name: string;
  type?: string;
  // The backend emits `{lower, upper, effort, velocity}` (see urdf_utils.py); the extra two
  // were simply never typed here. `velocity` is the URDF ceiling, not the achievable rate —
  // the driver applies its own speed scale on top — so treat it as a sanity bound only.
  limits?: {
    lower?: number;
    upper?: number;
    effort?: number;
    velocity?: number;
  };
}

export interface JointDeltaResult {
  jointName: string;
  previousValue: number;
  newValue: number;
}

function isLosslessMimicJoint(value: unknown): value is MimicJoint {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<MimicJoint>;
  return (
    typeof candidate.jointName === "string" &&
    typeof candidate.multiplier === "number" &&
    Number.isFinite(candidate.multiplier) &&
    typeof candidate.offset === "number" &&
    Number.isFinite(candidate.offset)
  );
}

function losslessMimicJoints(binding: KeyboardJointBinding): MimicJoint[] {
  const rawMimics = binding.mimicJoints ?? [];
  return rawMimics.filter(isLosslessMimicJoint);
}

export function validateKeyboardMimicJoints(
  bindings: KeyboardJointBinding[],
): string[] {
  const errors: string[] = [];
  bindings.forEach((binding, bindingIndex) => {
    const rawMimics = binding.mimicJoints;
    if (rawMimics === undefined) return;
    if (!Array.isArray(rawMimics)) {
      errors.push(`binding #${bindingIndex} mimicJoints must be an array`);
      return;
    }
    rawMimics.forEach((entry, mimicIndex) => {
      if (isLosslessMimicJoint(entry)) return;
      if (typeof entry === "string") {
        errors.push(
          `binding #${bindingIndex} mimicJoints[${mimicIndex}] is legacy name-only; migrate to {jointName, multiplier, offset}`,
        );
        return;
      }
      errors.push(
        `binding #${bindingIndex} mimicJoints[${mimicIndex}] must be {jointName, multiplier, offset}`,
      );
    });
  });
  return errors;
}

export function normalizeTeleopJointName(name: string): string {
  return name.startsWith("_") ? name.substring(1) : name;
}

export function resolveJointCurrentValue(
  jointName: string,
  jointValues: Record<string, number>,
): number | undefined {
  let currentValue = jointValues[jointName];
  if (currentValue !== undefined) {
    return currentValue;
  }
  currentValue = jointValues[`_${jointName}`];
  if (currentValue !== undefined) {
    return currentValue;
  }
  const normalized = normalizeTeleopJointName(jointName);
  if (normalized !== jointName) {
    return jointValues[normalized];
  }
  return undefined;
}

export function clampJointValue(
  value: number,
  joint: TeleopJointInfo | undefined,
): number {
  const range = physicalPositionRange(joint);
  if (!range) {
    // A continuous joint has no finite range. Keep the commanded value WRAPPED
    // into [-π, π] so the teleop accumulator, the target it publishes, and every
    // readout stay bounded while still stepping continuously across the ±π seam.
    // MuJoCo's internal qpos still winds freely — that's correct; the sim servos
    // the joint shortest-path toward this wrapped target.
    return joint?.type === "continuous" ? wrapToPi(value) : value;
  }
  return Math.max(range.min, Math.min(range.max, value));
}

export function getJointStepSize(joint: TeleopJointInfo | undefined): number {
  return joint?.type === "prismatic" ? 0.01 : 0.05;
}

export function collectBindingControlledJointNames(
  bindings: KeyboardJointBinding[],
): string[] {
  const names = new Set<string>();
  for (const binding of bindings) {
    names.add(binding.jointName);
    for (const mimic of losslessMimicJoints(binding)) {
      names.add(mimic.jointName);
    }
  }
  return Array.from(names);
}

export interface ApplyKeyboardJointDeltaContext {
  mode: "live" | "simulate";
  joints: TeleopJointInfo[];
  jointValues: Record<string, number>;
  hasMqttFeedbackForJoint: (jointName: string) => boolean;
  knownJointValueKeys: string[];
  warnMissingBinding?: (jointName: string) => void;
  /**
   * Measured (`source_type: "edge"`) pose per joint, for the target leash. Live only.
   *
   * Omit to disable the leash entirely — that is what simulate mode does, and what the
   * `NEXT_PUBLIC_TELEOP_LEASH_DISABLED` kill switch does. Never populate this from a
   * `tele` payload: those are our own commands echoed back by the broker, and leashing
   * the accumulator against itself is a no-op. See `teleop-joint-leash.ts`.
   */
  measuredJointStates?: Record<string, MeasuredJointSample>;
  leash?: { maxLead?: number; staleAfterMs?: number; now: number };
  onLeashRejected?: (jointName: string, reason: JointLeashRejection) => void;
}

/**
 * Measured sample for a joint, tolerating the `_`-prefixed name variants that
 * `resolveJointCurrentValue` handles.
 */
function resolveMeasuredSample(
  jointName: string,
  measured: Record<string, MeasuredJointSample> | undefined,
): MeasuredJointSample | undefined {
  if (!measured) return undefined;
  return (
    measured[jointName] ??
    measured[`_${jointName}`] ??
    measured[normalizeTeleopJointName(jointName)]
  );
}

/**
 * Apply the target leash to a proposed absolute joint target.
 *
 * Returns the proposed value untouched when the leash is not configured (simulate mode,
 * kill switch), and `null` when the leash refuses to command this joint at all.
 */
function leashTarget(
  jointName: string,
  proposed: number,
  joint: TeleopJointInfo | undefined,
  context: ApplyKeyboardJointDeltaContext,
): number | null {
  if (!context.leash || !context.measuredJointStates) return proposed;

  const outcome = leashJointTarget(
    proposed,
    resolveMeasuredSample(jointName, context.measuredJointStates),
    {
      isContinuous: joint?.type === "continuous",
      maxLead:
        context.leash.maxLead ?? TELEOP_LEAD_STEPS * getJointStepSize(joint),
      staleAfterMs: context.leash.staleAfterMs ?? TELEOP_FEEDBACK_STALE_MS,
      now: context.leash.now,
    },
  );

  if ("rejected" in outcome) {
    context.onLeashRejected?.(jointName, outcome.rejected);
    return null;
  }
  return outcome.value;
}

function shouldSkipJointInLiveMode(
  jointName: string,
  context: ApplyKeyboardJointDeltaContext,
  options?: { mimicDriverJointName?: string },
): boolean {
  if (context.mode === "simulate") {
    return false;
  }

  // Mimic slave: driver edge feedback is sufficient to command the coupled joint
  // even when the edge never publishes telemetry for the slave alone.
  if (
    options?.mimicDriverJointName &&
    context.hasMqttFeedbackForJoint(options.mimicDriverJointName)
  ) {
    return false;
  }

  const currentValue = resolveJointCurrentValue(jointName, context.jointValues);
  if (currentValue === undefined) {
    return true;
  }
  return !context.hasMqttFeedbackForJoint(jointName);
}

function coupledMimicPosition(
  driverPosition: number,
  mimic: MimicJoint,
  slaveJoint: TeleopJointInfo | undefined,
): number {
  return clampJointValue(
    mimic.multiplier * driverPosition + mimic.offset,
    slaveJoint,
  );
}

export function applyKeyboardJointBindingDelta(
  binding: KeyboardJointBinding,
  context: ApplyKeyboardJointDeltaContext,
): JointDeltaResult[] {
  const primaryJoint = context.joints.find((j) => j.name === binding.jointName);
  const step = getJointStepSize(primaryJoint);

  if (shouldSkipJointInLiveMode(binding.jointName, context)) {
    return [];
  }

  let primaryCurrent = resolveJointCurrentValue(
    binding.jointName,
    context.jointValues,
  );

  if (primaryCurrent === undefined) {
    if (context.mode !== "simulate") {
      return [];
    }
    primaryCurrent = 0;
    if (context.knownJointValueKeys.length > 0 && context.warnMissingBinding) {
      context.warnMissingBinding(binding.jointName);
    }
  } else if (
    context.mode !== "simulate" &&
    !context.hasMqttFeedbackForJoint(binding.jointName)
  ) {
    return [];
  }

  const delta = binding.direction === "increase" ? step : -step;
  // Leash BEFORE the movement gate below, so a saturated accumulator reads as "no
  // movement" and publishes nothing, rather than re-publishing the same runaway target.
  // Mimic slaves are then derived from the leashed primary (never leashed independently),
  // or a coupled pair would drift out of its mimic law.
  const primaryNew = leashTarget(
    binding.jointName,
    clampJointValue(primaryCurrent + delta, primaryJoint),
    primaryJoint,
    context,
  );
  if (primaryNew === null) {
    return [];
  }
  const results: JointDeltaResult[] = [];

  if (Math.abs(primaryNew - primaryCurrent) > 0.0001) {
    results.push({
      jointName: binding.jointName,
      previousValue: primaryCurrent,
      newValue: primaryNew,
    });
  }

  const mirrorDelta = primaryNew - primaryCurrent;
  if (Math.abs(mirrorDelta) < 0.0001) {
    return results;
  }

  for (const mimic of losslessMimicJoints(binding)) {
    const mirrorName = mimic.jointName;
    if (
      shouldSkipJointInLiveMode(mirrorName, context, {
        mimicDriverJointName: binding.jointName,
      })
    ) {
      continue;
    }

    // Coupling travels with the binding — apply the URDF mimic law directly,
    // clamping the slave to its own limits. No schema/limit rederivation.
    const mirrorJoint = context.joints.find((j) => j.name === mirrorName);
    const mirrorCurrent = coupledMimicPosition(primaryCurrent, mimic, mirrorJoint);
    const mirrorNew = coupledMimicPosition(primaryNew, mimic, mirrorJoint);
    if (Math.abs(mirrorNew - mirrorCurrent) > 0.0001) {
      results.push({
        jointName: mirrorName,
        previousValue: mirrorCurrent,
        newValue: mirrorNew,
      });
    }
  }

  return results;
}
