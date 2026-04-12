/**
 * Bilateral skeleton with forward kinematics and linear blend skinning.
 *
 * Hierarchy (14 bones):
 *   root (waist) ─┬─ spine (shoulder) ─┬─ neck ── head
 *                  │                    ├─ r_arm ── r_forearm
 *                  │                    └─ l_arm ── l_forearm
 *                  ├─ r_thigh ── r_shin ── r_foot
 *                  └─ l_thigh ── l_shin ── l_foot
 */

import { matIdentity, matRotAround, matMul, matXform } from "./math.js";
import type {
  BoneDef,
  BoneState,
  BoneWeight,
  LandmarkDict,
  Vec2,
} from "./types.js";

// ── Bone definition builder ──

export function buildBoneDefs(lm: LandmarkDict): BoneDef[] {
  const sDx = lm["shoulder_peak"]![0];
  const sDy = lm["shoulder_peak"]![1];
  const hDy = lm["hip_peak"]![1];
  const hJx = lm["hip_peak"]![0] * 0.35;
  const kDx = lm["knee_valley"]![0];
  const kDy = lm["knee_valley"]![1];
  const aDx = lm["ankle_valley"]![0];
  const aDy = lm["ankle_valley"]![1];
  const elbDy = (sDy + hDy) * 0.5;
  const elbDx = sDx * 0.85;

  return [
    { name: "root",       jx: 0,     jy: lm["waist_valley"]![1], parent: -1 },
    { name: "spine",      jx: 0,     jy: sDy,                    parent: 0 },
    { name: "neck",       jx: 0,     jy: lm["neck_valley"]![1],  parent: 1 },
    { name: "head",       jx: 0,     jy: lm["crown"]![1],        parent: 2 },
    { name: "r_arm",      jx: sDx,   jy: sDy,                    parent: 1 },
    { name: "r_forearm",  jx: elbDx, jy: elbDy,                  parent: 4 },
    { name: "l_arm",      jx: -sDx,  jy: sDy,                    parent: 1 },
    { name: "l_forearm",  jx: -elbDx,jy: elbDy,                  parent: 6 },
    { name: "r_thigh",    jx: hJx,   jy: hDy,                    parent: 0 },
    { name: "r_shin",     jx: kDx,   jy: kDy,                    parent: 8 },
    { name: "r_foot",     jx: aDx,   jy: aDy,                    parent: 9 },
    { name: "l_thigh",    jx: -hJx,  jy: hDy,                    parent: 0 },
    { name: "l_shin",     jx: -kDx,  jy: kDy,                    parent: 11 },
    { name: "l_foot",     jx: -aDx,  jy: aDy,                    parent: 12 },
  ];
}

// ── Bone runtime ──

export function initBones(defs: BoneDef[]): BoneState[] {
  return defs.map((d) => ({
    ...d,
    angle: 0,
    wm: matIdentity(),
    wj: [d.jx, d.jy] as Vec2,
  }));
}

export function buildBoneIndex(bones: BoneState[]): Map<string, number> {
  const idx = new Map<string, number>();
  bones.forEach((b, i) => idx.set(b.name, i));
  return idx;
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

// ── Skinning weight assignment ──

const BLEND_HU = 0.3;
function ss(t: number): number {
  return t * t * (3 - 2 * t);
}

export function getWeights(
  dx: number,
  dy: number,
  lm: LandmarkDict,
  boneIndex: Map<string, number>,
  armThresholdDx: number,
): BoneWeight[] {
  const adx = Math.abs(dx);
  const side = dx >= 0 ? "r" : "l";
  const BI = (name: string): number => boneIndex.get(name) ?? 0;

  const neckDy = lm["neck_valley"]![1];
  const shoulderDy = lm["shoulder_peak"]![1];
  const waistDy = lm["waist_valley"]![1];
  const hipDy = lm["hip_peak"]![1];
  const kneeDy = lm["knee_valley"]![1];
  const ankleDy = lm["ankle_valley"]![1];

  // Head
  if (dy <= neckDy) return [[BI("head"), 1.0]];

  // Neck → spine blend
  if (dy <= shoulderDy) {
    const t = (dy - neckDy) / (shoulderDy - neckDy);
    if (t > 0.7) {
      const s = ss((t - 0.7) / 0.3);
      return [[BI("neck"), 1 - s], [BI("spine"), s]];
    }
    return [[BI("neck"), 1.0]];
  }

  // Shoulder → hip: arms vs torso
  if (dy <= hipDy) {
    const elbowDy = (shoulderDy + hipDy) * 0.5;
    if (adx > armThresholdDx) {
      if (dy <= elbowDy) {
        const ab = BI(`${side}_arm`);
        const d = dy - shoulderDy;
        if (d < BLEND_HU) return [[BI("spine"), 1 - ss(d / BLEND_HU)], [ab, ss(d / BLEND_HU)]];
        return [[ab, 1.0]];
      }
      return [[BI(`${side}_forearm`), 1.0]];
    }
    if (dy <= waistDy) return [[BI("spine"), 1.0]];
    const hd = hipDy - dy;
    if (hd < BLEND_HU) {
      const tb = BI(`${side}_thigh`);
      return [[BI("root"), 1 - ss(1 - hd / BLEND_HU)], [tb, ss(1 - hd / BLEND_HU)]];
    }
    return [[BI("root"), 1.0]];
  }

  // Legs
  const th = BI(`${side}_thigh`);
  const sh = BI(`${side}_shin`);
  const ft = BI(`${side}_foot`);
  if (dy <= kneeDy) {
    const kd = kneeDy - dy;
    if (kd < BLEND_HU) return [[th, 1 - ss(1 - kd / BLEND_HU)], [sh, ss(1 - kd / BLEND_HU)]];
    return [[th, 1.0]];
  }
  if (dy <= ankleDy) {
    const ad = ankleDy - dy;
    if (ad < BLEND_HU) return [[sh, 1 - ss(1 - ad / BLEND_HU)], [ft, ss(1 - ad / BLEND_HU)]];
    return [[sh, 1.0]];
  }
  return [[ft, 1.0]];
}

// ── Linear blend skinning ──

export function deformPoint(
  px: number,
  py: number,
  weights: ReadonlyArray<BoneWeight>,
  bones: ReadonlyArray<BoneState>,
): Vec2 {
  let rx = 0;
  let ry = 0;
  for (const [bi, w] of weights) {
    const [tx, ty] = matXform(bones[bi]!.wm, px, py);
    rx += w * tx;
    ry += w * ty;
  }
  return [rx, ry];
}

export function deformContour(
  contour: ReadonlyArray<Vec2>,
  vertexWeights: ReadonlyArray<ReadonlyArray<BoneWeight>>,
  bones: ReadonlyArray<BoneState>,
): Vec2[] {
  return contour.map((p, i) => deformPoint(p[0], p[1], vertexWeights[i]!, bones));
}
