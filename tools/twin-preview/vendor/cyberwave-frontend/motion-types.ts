"use client";

/**
 * Centralized motion types for keyframes, animations, and motion plans.
 * Used across environment editor, asset catalog, and motion utilities.
 */

// ============================================================================
// Core Types
// ============================================================================

export type InterpolationType = "linear" | "ease-in" | "ease-out" | "ease-in-out";

export type MotionScope = "environment" | "twin" | "asset";

// ============================================================================
// Keyframe Types
// ============================================================================

export interface Keyframe {
  name: string;
  timestamp: string;
  jointAngles: Record<string, number>;
  description?: string;
  scope?: MotionScope;
}

// ============================================================================
// Animation Types
// ============================================================================

/**
 * Simple two-keyframe animation (legacy/convenience format).
 * For backwards compatibility with existing data.
 */
export interface Animation {
  name: string;
  description?: string;
  startKeyframe: string;
  endKeyframe: string;
  duration: number;
  interpolation: InterpolationType;
  timestamp: string;
  scope?: MotionScope;
  steps?: AnimationStep[];
}

/**
 * A single step in an animation sequence.
 */
export interface AnimationStep {
  keyframe: string;
  transition_ms: number; // Time to transition TO this keyframe (0 for first step)
  hold_ms: number; // Time to hold at this keyframe before next step
}

/**
 * Multi-keyframe animation sequence.
 * Can represent simple A→B or complex A→B→C→D sequences.
 */
export interface AnimationSequence {
  name: string;
  description?: string;
  steps: AnimationStep[];
  interpolation: InterpolationType;
  timestamp: string;
  scope?: MotionScope;
}

/**
 * Convert a simple Animation to AnimationSequence format.
 */
export function animationToSequence(animation: Animation): AnimationSequence {
  if (Array.isArray(animation.steps) && animation.steps.length > 0) {
    const steps = animation.steps.map((step, index) => ({
      keyframe: step.keyframe,
      transition_ms: index === 0 ? 0 : step.transition_ms ?? 0,
      hold_ms: step.hold_ms ?? 0,
    }));
    return {
      name: animation.name,
      description: animation.description,
      steps,
      interpolation: animation.interpolation,
      timestamp: animation.timestamp,
      scope: animation.scope,
    };
  }

  const durationMs = animation.duration * 1000;
  return {
    name: animation.name,
    description: animation.description,
    steps: [
      { keyframe: animation.startKeyframe, transition_ms: 0, hold_ms: 0 },
      { keyframe: animation.endKeyframe, transition_ms: durationMs, hold_ms: 0 },
    ],
    interpolation: animation.interpolation,
    timestamp: animation.timestamp,
    scope: animation.scope,
  };
}

/**
 * Convert AnimationSequence to simple Animation format (if exactly 2 steps).
 * Returns null if sequence has more than 2 steps.
 */
export function sequenceToAnimation(sequence: AnimationSequence): Animation | null {
  if (sequence.steps.length !== 2) return null;
  const [start, end] = sequence.steps;
  return {
    name: sequence.name,
    description: sequence.description,
    startKeyframe: start.keyframe,
    endKeyframe: end.keyframe,
    duration: end.transition_ms / 1000,
    interpolation: sequence.interpolation,
    timestamp: sequence.timestamp,
    scope: sequence.scope,
    steps: sequence.steps,
  };
}

/**
 * Check if data is in sequence format (has steps array) vs simple animation format.
 */
export function isAnimationSequence(
  data: Animation | AnimationSequence
): data is AnimationSequence {
  return "steps" in data && Array.isArray(data.steps);
}

// ============================================================================
// Motion Plan Types (for backend execution)
// ============================================================================

/**
 * @sync cyberwave-backend/src/app/api/motion_schemas.py:MotionPlanStepSchema
 */
export interface MotionPlanStep {
  keyframe?: string | null;
  joints?: Record<string, number> | null;
  transition_ms?: number;
  hold_ms?: number;
  note?: string | null;
}

/**
 * @sync cyberwave-backend/src/app/api/motion_schemas.py:MotionPlanSchema
 */
export interface MotionPlan {
  name?: string | null;
  description?: string | null;
  steps: MotionPlanStep[];
}

export type MotionStep = MotionPlanStep;

// ============================================================================
// Scoped Motion Data (environment/twin/asset level storage)
// ============================================================================

export interface ScopedMotionData {
  keyframes: Keyframe[];
  animations: Animation[];
}

// ============================================================================
// Scope Helpers
// ============================================================================

// Scope hierarchy: asset (most general) -> environment -> twin (most specific)
// Twin can use keyframes from asset + environment + twin
// Environment can use keyframes from asset + environment
// Asset can only use keyframes from asset
export const SCOPE_ORDER: MotionScope[] = ["asset", "environment", "twin"];

export const SCOPE_OPTIONS: Array<{
  value: MotionScope;
  label: string;
  description: string;
}> = [
  {
    value: "asset",
    label: "Asset",
    description: "Saved to the asset catalog (shared)",
  },
  {
    value: "environment",
    label: "Environment",
    description: "Saved to this environment only",
  },
  {
    value: "twin",
    label: "Twin",
    description: "Saved to this twin instance",
  },
];

export const INTERPOLATION_OPTIONS: Array<{
  value: InterpolationType;
  label: string;
}> = [
  { value: "linear", label: "Linear" },
  { value: "ease-in", label: "Ease In" },
  { value: "ease-out", label: "Ease Out" },
  { value: "ease-in-out", label: "Ease In-Out" },
];
