/**
 * Constants used across the Cyberwave platform.
 *
 * This module defines shared constants that are used across all Cyberwave services,
 * SDKs, and clients to ensure consistency.
 *
 * These constants are the single source of truth for source types in MQTT messages
 * and should be imported by all services that need to reference them.
 *
 * IMPORTANT: Keep in sync with shared_constants.py at monorepo root.
 * For Python projects, import from shared_constants.py instead.
 *
 * When adding new constants:
 * 1. Add them to shared_constants.py first (source of truth)
 * 2. Mirror them here for frontend use
 */

// Source types for MQTT messages
// These indicate the origin of a message in the Cyberwave platform
export const SOURCE_TYPE_EDGE = "edge";     // Messages from physical edge devices/robots
export const SOURCE_TYPE_EDGE_LEADER = "edge_leader";   // Messages from teleop leader (input device)
export const SOURCE_TYPE_EDGE_FOLLOWER = "edge_follower"; // Messages from edge follower arm (actual robot state)
export const SOURCE_TYPE_TELE = "tele";     // Messages from frontend teleoperation
export const SOURCE_TYPE_EDIT = "edit";     // Messages from frontend editor
export const SOURCE_TYPE_SIM = "sim";       // Messages from simulators (e.g., MuJoCo)
export const SOURCE_TYPE_SIM_TELE = "sim_tele"; // Simulated teleoperation commands from frontend/cloud
export const SOURCE_TYPE_PREVIEW = "preview"; // Frontend-only preview animations (locomotion, etc.)

/**
 * SOURCE_TYPE_PREVIEW is used for client-side animation previews when:
 * - No real robot (edge) is connected
 * - No simulator is running
 * - User wants to preview locomotion animations in the environment
 * 
 * Example scenarios:
 * - Quadruped walking animation preview using keyboard controls
 * - Arm movement preview before connecting to real hardware
 * - Demo/showcase mode without any backend connection
 */

// List of all valid source types (useful for validation)
export const SOURCE_TYPES = [
  SOURCE_TYPE_EDGE,
  SOURCE_TYPE_EDGE_LEADER,
  SOURCE_TYPE_EDGE_FOLLOWER,
  SOURCE_TYPE_TELE,
  SOURCE_TYPE_EDIT,
  SOURCE_TYPE_SIM,
  SOURCE_TYPE_SIM_TELE,
  SOURCE_TYPE_PREVIEW,
] as const;

// Type for source types
export type SourceType = typeof SOURCE_TYPES[number];

// =============================================================================
// Edge Health Monitoring Constants
// =============================================================================
// These constants define timing for edge device health monitoring.
// Keep in sync with edge health defaults in `cyberwave_edge/health.py`
//
// The edge service publishes health status at EDGE_HEALTH_PUBLISH_INTERVAL.
// The frontend considers a device "stale" if no health received within
// EDGE_HEALTH_STALE_TIMEOUT, and shows "checking" state for up to
// EDGE_HEALTH_CHECK_TIMEOUT when first connecting.

/** Interval in seconds between health status publications from edge to MQTT */
export const EDGE_HEALTH_PUBLISH_INTERVAL_SECONDS = 5;

/** Time in seconds before considering an edge device disconnected (stale) */
export const EDGE_HEALTH_STALE_TIMEOUT_SECONDS = 30;

/** Time in seconds to wait before showing "not connected" on initial load */
export const EDGE_HEALTH_CHECK_TIMEOUT_SECONDS = 10;

/** Time in seconds for local health cache validity */
export const EDGE_HEALTH_CACHE_TTL_SECONDS = 120;

/** Default timeout in seconds for stream staleness detection */
export const EDGE_STREAM_STALE_TIMEOUT_SECONDS = 60;

/** Maximum consecutive errors before stream is considered unhealthy */
export const EDGE_STREAM_MAX_CONSECUTIVE_ERRORS = 5;

// Derived constants in milliseconds for frontend convenience
export const EDGE_HEALTH_STALE_TIMEOUT_MS = EDGE_HEALTH_STALE_TIMEOUT_SECONDS * 1000;
export const EDGE_HEALTH_CHECK_TIMEOUT_MS = EDGE_HEALTH_CHECK_TIMEOUT_SECONDS * 1000;
export const EDGE_HEALTH_CACHE_TTL_MS = EDGE_HEALTH_CACHE_TTL_SECONDS * 1000;

// =============================================================================
// Edge Host Pressure Thresholds
// =============================================================================
// Mirror of the thresholds in
// ``cyberwave-edge-core/cyberwave_edge_core/resource_monitor.py`` so the
// dashboard renders the same pressure pill (green/yellow/red) the edge
// itself logs about.  Keep in lock-step with that module.

export const EDGE_HOST_MEMORY_WARNING_PERCENT = 85;
export const EDGE_HOST_MEMORY_CRITICAL_PERCENT = 92;
export const EDGE_HOST_CPU_TEMP_WARNING_C = 75;
export const EDGE_HOST_CPU_TEMP_CRITICAL_C = 82;

// =============================================================================
// Camera/Edge Device Configuration Constants
// =============================================================================
// Supported camera source types for edge device configuration.
// Used for camera setup UI components.

export const CAMERA_SOURCE_TYPE_RTSP = "RTSP";
export const CAMERA_SOURCE_TYPE_USB = "USB";
export const CAMERA_SOURCE_TYPE_REALSENSE = "RealSense";

export const CAMERA_SOURCE_TYPES = [
  CAMERA_SOURCE_TYPE_RTSP,
  CAMERA_SOURCE_TYPE_USB,
  CAMERA_SOURCE_TYPE_REALSENSE,
] as const;

export type CameraSourceType = typeof CAMERA_SOURCE_TYPES[number];
