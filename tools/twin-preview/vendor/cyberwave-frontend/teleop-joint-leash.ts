/**
 * A leash between a keyboard-teleop joint accumulator and the robot's measured pose.
 *
 * Keyboard joint teleop is an *integrator*: while a key is held it advances an absolute
 * position target by a fixed step at ~40 Hz. That is ~2.0 rad/s of commanded travel, and
 * nothing about it is aware of how fast the arm can actually move. A Kinova gen3 behind the
 * command smoother tracks at `vlim × speed_scale(0.5)` ≈ 0.5 rad/s, so the target runs away
 * from the arm at ~1.5 rad/s for as long as the key is down. On release the frontend simply
 * stops publishing, leaving that far-ahead target latched as the robot's active goal — and
 * the arm keeps slewing toward it for `lead / 0.5 rad/s` seconds. Hold 5 s, and the arm
 * carries on for ~15 s after you let go (CYB-3007).
 *
 * The leash fixes this at the source: the commanded target may never lead the measured pose
 * by more than `maxLead`. The integrator becomes a velocity-matched follower — it advances
 * exactly as fast as the arm actually moves — and the residual motion after release is
 * bounded by `maxLead / arm speed` regardless of how long the key was held.
 *
 * ## Why this module publishes UNWRAPPED targets
 *
 * For continuous joints we lift the measured angle into the accumulator's frame rather than
 * wrapping the accumulator into the measured one. The Kinova smoother's ramp law uses a
 * plain, deliberately *non*-shortest-path delta (`target - command`) and documents that it
 * requires a monotonic, unwrapped target — see `joint_command_smoother.cpp:423-427`. Handing
 * it a target that jumps from +π to −π makes `delta ≈ −2π` and spins the joint a full
 * revolution backwards. So: lift, never wrap.
 *
 * With the leash in place this is self-consistent. `|target − anchor| ≤ maxLead`, and the
 * smoother's `command_` seeds from the same measured value and never leaves `target_` by more
 * than one step, so `|target − command| ≤ 2·maxLead + step ≈ 0.4 rad ≪ π`. The plain delta is
 * always the short way round and the ±π seam stops being an event at all. The smoother still
 * wraps its own *published* command for the hardware; that is correct and unaffected.
 */

import {
  SOURCE_TYPE_EDGE,
  SOURCE_TYPE_EDGE_FOLLOWER,
} from "@/lib/constants/cyberwave-constants";

/**
 * Does this `source_type` carry the robot's actual measured pose?
 *
 * Only `edge` and `edge_follower`. Notably excluded:
 * - `tele` / `sim_tele` — commands, including our own echoed back by the broker.
 * - `edge_leader` — the teleop *input* device (a leader arm), not the follower's state.
 *   Same rule the live joint ingest already applies in `useMQTTTwin`.
 */
export function isMeasuredSourceType(sourceType: string | undefined): boolean {
  return (
    sourceType === SOURCE_TYPE_EDGE || sourceType === SOURCE_TYPE_EDGE_FOLLOWER
  );
}

/**
 * `control_kind` on a joint command: is this one message of a continuous operator
 * stream, or a standalone move?
 *
 * The edge cannot infer this. A keyboard hold and a Send Pose are byte-identical on the
 * wire — same topic, same `source_type: "tele"`, same absolute positions — so a driver
 * deadman that armed on message cadence would eventually truncate a legitimate one-shot
 * move (two sequential Send Pose nodes, or a retry, look exactly like a stream). Marking
 * the stream explicitly is what makes "stop when the operator's stream dies" safe.
 *
 * - `teleop_stream`: one tick of a held-key stream. Silence means the operator is gone.
 * - `teleop_stop`: the final hold-here target published on key release.
 */
export type JointControlKind = "teleop_stream" | "teleop_stop";

export const CONTROL_KIND_TELEOP_STREAM: JointControlKind = "teleop_stream";
export const CONTROL_KIND_TELEOP_STOP: JointControlKind = "teleop_stop";

/**
 * Escape hatch for the live target leash.
 *
 * The leash requires measured feedback arriving faster than `TELEOP_FEEDBACK_STALE_MS`.
 * A driver publishing joint state more slowly than that would have its teleop stall. Set
 * this while confirming a new robot's real publish rate; the fix is to speed the driver
 * up, not to widen the staleness bound.
 */
export const TELEOP_LEASH_DISABLED =
  process.env.NEXT_PUBLIC_TELEOP_LEASH_DISABLED === "true";

/** Steps of lead the target may hold over measured. 4 × 0.05 rad = 0.20 rad. */
export const TELEOP_LEAD_STEPS = 4;

/**
 * Measured feedback older than this stops teleop for that joint.
 *
 * Six samples at the edge's 10 Hz joint publish rate. This is a tightening of the existing
 * "refuse to move a live joint with no feedback" rule, not a new failure mode: it makes
 * "has feedback" time-bounded instead of latching true forever after the first sample.
 */
export const TELEOP_FEEDBACK_STALE_MS = 600;

/** Steps of lead permitted to survive a key release. */
export const TELEOP_STOP_LEAD_STEPS = 1;

const TWO_PI = 2 * Math.PI;

export interface MeasuredJointSample {
  position: number;
  velocity?: number;
  /** `Date.now()` when the last measured (`source_type: "edge"`) sample arrived. */
  receivedAt: number;
}

export type JointLeashRejection = "no-feedback" | "stale-feedback";

export interface JointLeashConfig {
  isContinuous: boolean;
  maxLead: number;
  staleAfterMs: number;
  now: number;
}

export type JointLeashResult =
  | { value: number }
  | { rejected: JointLeashRejection };

/** Wrap to `[-π, π]` with `std::remainder` semantics (ties toward even, exact at ±π). */
export function wrapToPi(angle: number): number {
  if (!Number.isFinite(angle)) return angle;
  return angle - TWO_PI * Math.round(angle / TWO_PI);
}

/**
 * Lift a wrapped angle into `reference`'s continuous frame — the nearest representation of
 * `angle` to `reference`, differing from it by less than π.
 *
 * Mirrors `lift_angle_into_frame` in the driver's `pd_smoothing.hpp`, so both ends of the
 * wire agree on what "the same physical angle" means for a joint that has wound past ±π.
 */
export function liftIntoFrame(reference: number, angle: number): number {
  if (!Number.isFinite(reference) || !Number.isFinite(angle)) return angle;
  return reference + wrapToPi(angle - reference);
}

/**
 * The frame-correct measured anchor for a joint, or `undefined` if there is no usable one.
 *
 * Continuous joints are lifted into `reference`'s frame; revolute joints are NOT. A revolute
 * joint reading −3.10 against an accumulator at 3.10 is a genuine 6.2 rad error, not a wrap,
 * and lifting it would silently swallow a real fault.
 */
function anchorFor(
  reference: number,
  measured: MeasuredJointSample,
  isContinuous: boolean,
): number {
  return isContinuous
    ? liftIntoFrame(reference, measured.position)
    : measured.position;
}

function feedbackRejection(
  measured: MeasuredJointSample | undefined,
  staleAfterMs: number,
  now: number,
): JointLeashRejection | null {
  if (!measured || !Number.isFinite(measured.position)) return "no-feedback";
  if (now - measured.receivedAt > staleAfterMs) return "stale-feedback";
  return null;
}

/**
 * Clamp a proposed absolute joint target so it never leads measured by more than `maxLead`.
 *
 * Returns a rejection instead of a value when feedback is missing or stale. We deliberately
 * do NOT fall back to dead-reckoning at an assumed velocity — open-loop reasoning is what
 * caused CYB-3007, and a smaller version of it is still that bug. Note the leash already
 * degrades gracefully on its own: if feedback merely slows, the anchor stops advancing and
 * the accumulator saturates, so the arm coasts at most `maxLead` and holds.
 */
export function leashJointTarget(
  proposed: number,
  measured: MeasuredJointSample | undefined,
  config: JointLeashConfig,
): JointLeashResult {
  const rejection = feedbackRejection(
    measured,
    config.staleAfterMs,
    config.now,
  );
  if (rejection) return { rejected: rejection };

  const anchor = anchorFor(proposed, measured!, config.isContinuous);
  const lead = Math.abs(config.maxLead);
  return {
    value: Math.min(Math.max(proposed, anchor - lead), anchor + lead),
  };
}

/**
 * The single target to publish when a key is released: stop here, do not come back.
 *
 * Snapping straight to measured would command a *reversal* of up to `maxLead` on every
 * keypress. That reversal is real, not cosmetic — the frontend's measured sample is already
 * one publish interval plus a round trip old, so the arm is genuinely further along than the
 * sample says, and driving it back to a stale reading would visibly rebound.
 *
 * So we clamp toward measured but never past it in the direction of travel: the arm gives
 * back the accumulated lead and stops, and never moves backwards.
 *
 * Returns `null` when there is nothing safe to publish (no usable feedback), in which case
 * the caller should leave the last commanded target standing — the edge deadman is the
 * backstop for that case.
 */
export function releaseJointTarget(
  accumulated: number,
  measured: MeasuredJointSample | undefined,
  config: JointLeashConfig & { stopLead: number },
): number | null {
  if (!Number.isFinite(accumulated)) return null;
  if (feedbackRejection(measured, config.staleAfterMs, config.now)) return null;

  const anchor = anchorFor(accumulated, measured!, config.isContinuous);
  const stopLead = Math.abs(config.stopLead);

  // Forward-only: pull toward the anchor along the direction we were already travelling,
  // and stop there. Never cross the anchor.
  if (accumulated > anchor) {
    return Math.max(anchor, Math.min(accumulated, anchor + stopLead));
  }
  return Math.min(anchor, Math.max(accumulated, anchor - stopLead));
}
