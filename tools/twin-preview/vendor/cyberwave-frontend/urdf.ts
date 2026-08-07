import type React from "react";

export interface URDFAssetData {
  uuid: string;
  name?: string;
  joints: Record<string, any>;
  /** Snapshot of joint angles at last structural update. Use jointAnglesRef.current for live values. */
  jointAngles: Record<string, number>;
  /** Ref to live joint angles — reads never cause re-renders in the parent tree. */
  jointAnglesRef: React.MutableRefObject<Record<string, number>>;
  /** Ref to live joint velocities from sim stream — keyed by URDF joint name. */
  jointVelocitiesRef?: React.MutableRefObject<Record<string, number>>;
  jointNames: Record<string, string>;
  /** Link names from the URDF (for docking attachment points) */
  links: string[];
  /** Visual hierarchy (link -> mesh -> material) for appearance editing */
  visualHierarchy?: URDFVisualHierarchy;
  /**
   * URDF joint names whose mimic coupling comes from universal_schema.
   *
   * REQUIRED (pass `[]` when there are none). Mimic slaves must never be
   * independently commandable, and for assets whose coupling lives only in the
   * schema — Kinova + Robotiq, where `create_mimic_patches` stamps it and the
   * URDF carries no `<mimic>` tag — the urdf-loader flags are absent, so this is
   * the ONLY signal. Optionality here silently re-exposed those slaves as
   * sliders in every panel that hand-builds a `URDFAssetData`.
   */
  schemaMimicJointNames: string[];
  /**
   * True when `schemaMimicJointNames` was derived from a present schema `joints`
   * array. REQUIRED — `false` means "no schema available, fall back to the
   * urdf-loader mimic flags", which is a weaker check, not a default.
   */
  schemaMimicSourcePresent: boolean;
  onJointChange: (jointName: string, value: number) => void;
  /**
   * SIM-ONLY: instantly teleport (snap) the robot's joints to a URDF-named
   * pose. Real hardware is never teleported. Present only when a simulation
   * publisher is wired (e.g. the environment 3D viewer).
   */
  onTeleportJoints?: (urdfPose: Record<string, number>) => void;
  /** SIM-ONLY: teleport the robot back to its durable reset preset (home). */
  onResetToPreset?: () => void;
  /**
   * The resolved edit/home pose (URDF joint name -> radians), i.e. the authored
   * `home_position` per controllable joint (0 where unauthored). Used by the
   * Poses panel to list/preview the "Home (edit pose)" and, in live, to drive
   * the real robot to these joints.
   */
  resetPresetPose?: Record<string, number>;
  applyJointAngles?: (jointAngles: Record<string, number>) => void;
}

export interface URDFVisualMeshInfo {
  name: string;
  materials: URDFVisualMaterialInfo[];
}

export interface URDFVisualLinkInfo {
  name: string;
  meshes: URDFVisualMeshInfo[];
}

export interface URDFVisualMaterialInfo {
  name: string;
  color?: string;
  hasTexture?: boolean;
}

export interface URDFVisualHierarchy {
  links: URDFVisualLinkInfo[];
}
