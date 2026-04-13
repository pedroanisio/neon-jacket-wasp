/**
 * Bilateral skeleton: FK, weight computation, and dual-quaternion skinning.
 */

import {
  matIdentity,
  matMul,
  matRotAround,
  matXform,
  smoothstep,
} from "./math.js";
import type {
  BoneDef,
  BoneState,
  LandmarkDict,
  MutVec2,
  SkinWeights,
  Vec2,
} from "./types.js";

// ── Bone definitions ──

export function buildBoneDefs(lm: LandmarkDict): BoneDef[] {
  const sp = lm["shoulder_peak"]!;
  const hp = lm["hip_peak"]!;
  const kv = lm["knee_valley"]!;
  const av = lm["ankle_valley"]!;
  const sDx = sp[0], sDy = sp[1];
  const hDy = hp[1], hJx = hp[0] * 0.35;
  const elbDy = (sDy + hDy) * 0.5;
  const elbDx = sDx * 0.85;

  return [
    { name: "root",       jx: 0,      jy: lm["waist_valley"]![1], parent: -1 },
    { name: "spine",      jx: 0,      jy: sDy,                    parent: 0 },
    { name: "neck",       jx: 0,      jy: lm["neck_valley"]![1],  parent: 1 },
    { name: "head",       jx: 0,      jy: lm["crown"]![1],        parent: 2 },
    { name: "r_arm",      jx: sDx,    jy: sDy,                    parent: 1 },
    { name: "r_forearm",  jx: elbDx,  jy: elbDy,                  parent: 4 },
    { name: "l_arm",      jx: -sDx,   jy: sDy,                    parent: 1 },
    { name: "l_forearm",  jx: -elbDx, jy: elbDy,                  parent: 6 },
    { name: "r_thigh",    jx: hJx,    jy: hDy,                    parent: 0 },
    { name: "r_shin",     jx: kv[0],  jy: kv[1],                  parent: 8 },
    { name: "r_foot",     jx: av[0],  jy: av[1],                  parent: 9 },
    { name: "l_thigh",    jx: -hJx,   jy: hDy,                    parent: 0 },
    { name: "l_shin",     jx: -kv[0], jy: kv[1],                  parent: 11 },
    { name: "l_foot",     jx: -av[0], jy: av[1],                  parent: 12 },
  ];
}

export function initBones(defs: ReadonlyArray<BoneDef>): BoneState[] {
  return defs.map((d) => ({
    ...d,
    angle: 0,
    wm: matIdentity(),
    wj: [d.jx, d.jy] as MutVec2,
  }));
}

export function buildBoneIndex(bones: ReadonlyArray<BoneState>): Map<string, number> {
  const m = new Map<string, number>();
  bones.forEach((b, i) => m.set(b.name, i));
  return m;
}

// ── Forward kinematics ──

export function updateBones(bones: BoneState[]): void {
  for (let i = 0; i < bones.length; i++) {
    const b = bones[i]!;
    if (b.parent < 0) {
      b.wm = matRotAround(b.jx, b.jy, b.angle);
      b.wj = matXform(b.wm, b.jx, b.jy);
    } else {
      const p = bones[b.parent]!;
      b.wj = matXform(p.wm, b.jx, b.jy);
      b.wm = matMul(matRotAround(b.wj[0], b.wj[1], b.angle), p.wm);
    }
  }
}

// ── Weight computation ──

const BLEND_HU = 0.35;

export function computeVertexWeights(
  vertices: ReadonlyArray<Vec2>,
  lm: LandmarkDict,
  boneIndex: Map<string, number>,
): SkinWeights[] {
  const armThreshold = (lm["waist_valley"]?.[0] ?? 0.55) * 1.05;
  return vertices.map((v) =>
    getWeights(v[0], v[1], lm, boneIndex, armThreshold),
  );
}

export function getWeights(
  dx: number,
  dy: number,
  lm: LandmarkDict,
  bi: Map<string, number>,
  armThreshold: number,
): SkinWeights {
  const adx = Math.abs(dx);
  const side = dx >= 0 ? "r" : "l";
  const B = (name: string): number => bi.get(name) ?? 0;

  const neckDy = lm["neck_valley"]![1];
  const sDy = lm["shoulder_peak"]![1];
  const wDy = lm["waist_valley"]![1];
  const hDy = lm["hip_peak"]![1];
  const kDy = lm["knee_valley"]![1];
  const aDy = lm["ankle_valley"]![1];

  // Head
  if (dy <= neckDy) return [[B("head"), 1.0]];

  // Neck blend
  if (dy <= sDy) {
    const t = (dy - neckDy) / (sDy - neckDy);
    if (t > 0.6) {
      const s = smoothstep((t - 0.6) / 0.4);
      return [[B("neck"), 1 - s], [B("spine"), s]];
    }
    return [[B("neck"), 1.0]];
  }

  // Torso/arm region
  if (dy <= hDy) {
    const elbowDy = (sDy + hDy) * 0.5;
    if (adx > armThreshold) {
      if (dy <= elbowDy) {
        const ab = B(`${side}_arm`);
        const d = dy - sDy;
        if (d < BLEND_HU) {
          const s = smoothstep(d / BLEND_HU);
          return [[B("spine"), 1 - s], [ab, s]];
        }
        return [[ab, 1.0]];
      }
      return [[B(`${side}_forearm`), 1.0]];
    }
    if (dy <= wDy) return [[B("spine"), 1.0]];
    const hd = hDy - dy;
    if (hd < BLEND_HU) {
      const s = smoothstep(1 - hd / BLEND_HU);
      return [[B("root"), 1 - s], [B(`${side}_thigh`), s]];
    }
    return [[B("root"), 1.0]];
  }

  // Legs
  const th = B(`${side}_thigh`);
  const sh = B(`${side}_shin`);
  const ft = B(`${side}_foot`);
  if (dy <= kDy) {
    const kd = kDy - dy;
    if (kd < BLEND_HU) {
      const s = smoothstep(1 - kd / BLEND_HU);
      return [[th, 1 - s], [sh, s]];
    }
    return [[th, 1.0]];
  }
  if (dy <= aDy) {
    const ad = aDy - dy;
    if (ad < BLEND_HU) {
      const s = smoothstep(1 - ad / BLEND_HU);
      return [[sh, 1 - s], [ft, s]];
    }
    return [[sh, 1.0]];
  }
  return [[ft, 1.0]];
}

// ── Dual-Quaternion Skinning (2D approximation) ──
//
// True DQS needs quaternions (3D). In 2D, we approximate volume
// preservation by blending in rotation-then-translate space rather
// than raw matrix space. This prevents the "candy wrapper" collapse
// and the volume loss that LBS causes at joints.

export function deformVertex(
  px: number,
  py: number,
  weights: SkinWeights,
  bones: ReadonlyArray<BoneState>,
): MutVec2 {
  if (weights.length === 1) {
    const [bi, _w] = weights[0]!;
    return matXform(bones[bi]!.wm, px, py);
  }

  // For multi-bone blending, decompose each bone's transform into
  // rotation angle + translation, blend those, then recompose.
  // This preserves area better than blending matrices directly.
  let totalAngle = 0;
  let totalTx = 0;
  let totalTy = 0;
  let pivotX = 0;
  let pivotY = 0;

  for (const [bi, w] of weights) {
    const b = bones[bi]!;
    // Extract rotation angle from world matrix
    const angle = Math.atan2(b.wm[3], b.wm[0]);
    // Extract translation component
    const tx = b.wm[2];
    const ty = b.wm[5];

    totalAngle += w * angle;
    totalTx += w * tx;
    totalTy += w * ty;
    pivotX += w * b.wj[0];
    pivotY += w * b.wj[1];
  }

  // Reconstruct blended transform
  const c = Math.cos(totalAngle);
  const s = Math.sin(totalAngle);

  // Rotate around blended pivot, then translate
  const dx = px - pivotX;
  const dy = py - pivotY;
  return [
    c * dx - s * dy + pivotX + totalTx,
    s * dx + c * dy + pivotY + totalTy,
  ];
}

/** Deform all mesh vertices. */
export function deformMesh(
  vertices: ReadonlyArray<Vec2>,
  weights: ReadonlyArray<SkinWeights>,
  bones: ReadonlyArray<BoneState>,
): MutVec2[] {
  return vertices.map((v, i) =>
    deformVertex(v[0], v[1], weights[i]!, bones),
  );
}
