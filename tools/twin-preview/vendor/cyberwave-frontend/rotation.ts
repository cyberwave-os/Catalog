import * as THREE from "three";

export interface Quaternion {
  w: number;
  x: number;
  y: number;
  z: number;
}

export interface WaypointEulerRotation {
  roll: number;
  pitch: number;
  yaw: number;
}

export interface AssetEulerRotation {
  x: number;
  y: number;
  z: number;
}

export interface MarkerQuaternion {
  x: number;
  y: number;
  z: number;
  w: number;
}

const roundToSixDecimals = (value: number): number =>
  Math.round(value * 1_000_000) / 1_000_000;

const roundToFourDecimals = (value: number): number =>
  parseFloat(value.toFixed(4));

export const quaternionToEuler = (
  q: [number, number, number, number]
): [number, number, number] => {
  const [w, x, y, z] = q;
  const quat = new THREE.Quaternion(x, y, z, w);
  const euler = new THREE.Euler().setFromQuaternion(quat, "XYZ");
  return [euler.x, euler.y, euler.z];
};

export const quaternionFromYaw = (
  yaw: number
): [number, number, number, number] => {
  // Z-up: yaw is rotation around the Z axis.
  const quat = new THREE.Quaternion().setFromAxisAngle(
    new THREE.Vector3(0, 0, 1),
    yaw
  );
  return [quat.w, quat.x, quat.y, quat.z];
};

export const quaternionTupleToObject = (
  q: [number, number, number, number]
): Quaternion => ({
  w: q[0],
  x: q[1],
  y: q[2],
  z: q[3],
});

export const normalizeQuaternion = (
  q: Quaternion | [number, number, number, number] | null | undefined
): Quaternion | null => {
  if (!q) return null;
  if (Array.isArray(q) && q.length === 4) {
    return quaternionTupleToObject(q);
  }
  if (
    typeof q === "object" &&
    "w" in q &&
    "x" in q &&
    "y" in q &&
    "z" in q &&
    Number.isFinite(q.w) &&
    Number.isFinite(q.x) &&
    Number.isFinite(q.y) &&
    Number.isFinite(q.z)
  ) {
    return { w: q.w, x: q.x, y: q.y, z: q.z };
  }
  return null;
};

/**
 * Return a **unit-length** quaternion for `q`, or the identity quaternion when
 * `q` is missing, non-finite, or zero-length.
 *
 * Unlike `normalizeQuaternion` (which only validates/coerces shape and does
 * NOT rescale), this guarantees `|q| === 1`. That is required before feeding a
 * quaternion to THREE's matrix composition (`Matrix4.compose` /
 * `Object3D.quaternion`), which assumes unit length — a non-unit quaternion is
 * otherwise baked in as non-uniform scale/shear, visibly stretching and
 * deforming the object (e.g. a waypoint marker whose w/x/y/z were edited as
 * independent numeric fields).
 */
export const normalizeToUnitQuaternion = (
  q: Quaternion | [number, number, number, number] | null | undefined
): Quaternion => {
  const IDENTITY: Quaternion = { w: 1, x: 0, y: 0, z: 0 };
  const validated = normalizeQuaternion(q);
  if (!validated) return IDENTITY;
  const { w, x, y, z } = validated;
  const len = Math.hypot(w, x, y, z);
  if (!Number.isFinite(len) || len === 0) return IDENTITY;
  return { w: w / len, x: x / len, y: y / len, z: z / len };
};

export const quaternionFromWaypointEuler = ({
  roll,
  pitch,
  yaw,
}: WaypointEulerRotation): Quaternion => {
  // Z-up: Euler(roll=X, pitch=Y, yaw=Z).
  const quat = new THREE.Quaternion().setFromEuler(
    new THREE.Euler(roll, pitch, yaw, "XYZ")
  );
  return { w: quat.w, x: quat.x, y: quat.y, z: quat.z };
};

/** Asset catalog default pose (XYZ Euler) → 3D marker quaternion. */
export const assetEulerToMarkerQuaternion = (
  euler: AssetEulerRotation,
): MarkerQuaternion => {
  const quat = new THREE.Quaternion().setFromEuler(
    new THREE.Euler(euler.x, euler.y, euler.z, "XYZ"),
  );
  return { x: quat.x, y: quat.y, z: quat.z, w: quat.w };
};

/** 3D marker quaternion → asset catalog default pose (XYZ Euler). */
export const markerQuaternionToAssetEuler = (
  quat: MarkerQuaternion,
): AssetEulerRotation => {
  const quaternion = new THREE.Quaternion(quat.x, quat.y, quat.z, quat.w);
  const euler = new THREE.Euler().setFromQuaternion(quaternion, "XYZ");
  return {
    x: roundToFourDecimals(euler.x),
    y: roundToFourDecimals(euler.y),
    z: roundToFourDecimals(euler.z),
  };
};

export const waypointEulerFromQuaternion = (
  q: Quaternion | [number, number, number, number] | null | undefined
): WaypointEulerRotation | null => {
  const normalized = normalizeQuaternion(q);
  if (!normalized) return null;

  const quat = new THREE.Quaternion(
    normalized.x,
    normalized.y,
    normalized.z,
    normalized.w
  );
  const euler = new THREE.Euler().setFromQuaternion(quat, "XYZ");
  const yaw = euler.z;

  return {
    roll: roundToSixDecimals(euler.x),
    pitch: roundToSixDecimals(euler.y),
    yaw: roundToSixDecimals(yaw),
  };
};
