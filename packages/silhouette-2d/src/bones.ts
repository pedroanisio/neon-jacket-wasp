/**
 * Bilateral skeleton: FK, weight computation, and dual-quaternion skinning.
 *
 * Adaptive bone placement:
 * - Uses available landmarks (resolved via alias table in loader.ts)
 * - Derives elbow/arm positions from contour width at shoulder level
 * - Blends weights using actual body-region boundaries when available
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
import type { BodyRegion, WidthSample } from "./loader.js";

// ── Bone definitions ──

/** Lookup a landmark dy, with fallback. */
function lmDy(lm: LandmarkDict, name: string, fallback: number): number {
  return lm[name]?.[1] ?? fallback;
}

/** Lookup a landmark dx, with fallback. */
function lmDx(lm: LandmarkDict, name: string, fallback: number): number {
  return lm[name]?.[0] ?? fallback;
}

/** Find the maximum half-width (dx) near a given dy from the width profile. */
function maxDxNear(
  widthProfile: WidthSample[],
  targetDy: number,
  range: number,
): number {
  let maxDx = 0;
  for (const s of widthProfile) {
    if (Math.abs(s.dy - targetDy) <= range && s.dx > maxDx) {
      maxDx = s.dx;
    }
  }
  return maxDx;
}

export function buildBoneDefs(
  lm: LandmarkDict,
  widthProfile: WidthSample[] = [],
  figureHeight: number = 8.0,
): BoneDef[] {
  const sDy = lmDy(lm, "shoulder_peak", figureHeight * 0.2);
  const sDx = lmDx(lm, "shoulder_peak", 0.5);
  const wDy = lmDy(lm, "waist_valley", figureHeight * 0.35);
  const hDy = lmDy(lm, "hip_peak", figureHeight * 0.5);
  const kDy = lmDy(lm, "knee_valley", figureHeight * 0.66);
  const aDy = lmDy(lm, "ankle_valley", figureHeight * 0.875);
  const nDy = lmDy(lm, "neck_valley", figureHeight * 0.15);
  const crDy = lmDy(lm, "crown", 0);

  const kDx = lmDx(lm, "knee_valley", 0.2);
  const aDx = lmDx(lm, "ankle_valley", 0.1);

  // Derive arm/elbow positions from contour width profile if available,
  // otherwise estimate from shoulder dx.
  let armDx = sDx;
  if (widthProfile.length > 0) {
    const widthAtShoulder = maxDxNear(widthProfile, sDy, 0.15);
    if (widthAtShoulder > 0) armDx = widthAtShoulder;
  }

  // Elbow: use armpit/chest landmark if available, otherwise
  // estimate at 60% from shoulder to hip (anatomically correct).
  const elbDy = lmDy(lm, "armpit", sDy + (hDy - sDy) * 0.6);
  const elbDx = armDx * 0.85;

  // Hip joint offset: use body width at hip level, not the peak dx
  // which for armor includes protruding plates.
  const hpDx = lmDx(lm, "hip_peak", 0.35);
  const hJx = Math.min(hpDx * 0.35, kDx * 1.2);

  return [
    { name: "root",       jx: 0,      jy: wDy,   parent: -1 },
    { name: "spine",      jx: 0,      jy: sDy,   parent: 0 },
    { name: "neck",       jx: 0,      jy: nDy,   parent: 1 },
    { name: "head",       jx: 0,      jy: crDy,  parent: 2 },
    { name: "r_arm",      jx: armDx,  jy: sDy,   parent: 1 },
    { name: "r_forearm",  jx: elbDx,  jy: elbDy, parent: 4 },
    { name: "l_arm",      jx: -armDx, jy: sDy,   parent: 1 },
    { name: "l_forearm",  jx: -elbDx, jy: elbDy, parent: 6 },
    { name: "r_thigh",    jx: hJx,    jy: hDy,   parent: 0 },
    { name: "r_shin",     jx: kDx,    jy: kDy,   parent: 8 },
    { name: "r_foot",     jx: aDx,    jy: aDy,   parent: 9 },
    { name: "l_thigh",    jx: -hJx,   jy: hDy,   parent: 0 },
    { name: "l_shin",     jx: -kDx,   jy: kDy,   parent: 11 },
    { name: "l_foot",     jx: -aDx,   jy: aDy,   parent: 12 },
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

/**
 * Compute blend zone size relative to figure proportions.
 * Larger figures get proportionally larger blend zones.
 */
function blendHu(figureHeight: number): number {
  return figureHeight * 0.044; // ~0.35 for 8 HU figure
}

/**
 * Determine arm threshold dx adaptively:
 * Use width profile at waist level if available, otherwise fall back
 * to waist landmark dx. For armored figures, the width profile gives
 * the actual silhouette width, not the anatomical waist.
 */
function computeArmThreshold(
  lm: LandmarkDict,
  widthProfile: WidthSample[],
): number {
  const wDy = lm["waist_valley"]?.[1] ?? 2.8;

  // Use width profile for accurate contour-based threshold.
  if (widthProfile.length > 0) {
    const waistWidth = maxDxNear(widthProfile, wDy, 0.2);
    if (waistWidth > 0) return waistWidth * 0.95;
  }

  // Fallback to landmark dx.
  return (lm["waist_valley"]?.[0] ?? 0.55) * 1.05;
}

export function computeVertexWeights(
  vertices: ReadonlyArray<Vec2>,
  lm: LandmarkDict,
  boneIndex: Map<string, number>,
  widthProfile: WidthSample[] = [],
  bodyRegions: BodyRegion[] = [],
  figureHeight: number = 8.0,
): SkinWeights[] {
  const armThreshold = computeArmThreshold(lm, widthProfile);
  const bh = blendHu(figureHeight);

  // Build region dy boundaries from body_regions if available.
  const regionBounds = new Map<string, [number, number]>();
  for (const r of bodyRegions) {
    regionBounds.set(r.name, [r.dyStart, r.dyEnd]);
  }

  return vertices.map((v) =>
    getWeights(v[0], v[1], lm, boneIndex, armThreshold, bh, regionBounds),
  );
}

export function getWeights(
  dx: number,
  dy: number,
  lm: LandmarkDict,
  bi: Map<string, number>,
  armThreshold: number,
  bh: number,
  regionBounds: Map<string, [number, number]>,
): SkinWeights {
  const adx = Math.abs(dx);
  const side = dx >= 0 ? "r" : "l";
  const B = (name: string): number => bi.get(name) ?? 0;

  // Use region boundaries if available, otherwise landmark dy.
  const neckDy = regionBounds.get("neck")?.[0]
    ?? lm["neck_valley"]?.[1] ?? 1.2;
  const sDy = regionBounds.get("shoulders")?.[0]
    ?? lm["shoulder_peak"]?.[1] ?? 1.6;
  const wDy = regionBounds.get("upper_torso")?.[1]
    ?? lm["waist_valley"]?.[1] ?? 2.8;
  const hDy = regionBounds.get("upper_leg")?.[0]
    ?? lm["hip_peak"]?.[1] ?? 4.0;
  const kDy = regionBounds.get("lower_leg")?.[0]
    ?? lm["knee_valley"]?.[1] ?? 5.3;
  const aDy = regionBounds.get("foot")?.[0]
    ?? lm["ankle_valley"]?.[1] ?? 7.0;

  // Head
  if (dy <= neckDy) return [[B("head"), 1.0]];

  // Neck blend
  if (dy <= sDy) {
    const t = (dy - neckDy) / Math.max(sDy - neckDy, 0.01);
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
        if (d < bh) {
          const s = smoothstep(d / bh);
          return [[B("spine"), 1 - s], [ab, s]];
        }
        return [[ab, 1.0]];
      }
      return [[B(`${side}_forearm`), 1.0]];
    }
    if (dy <= wDy) return [[B("spine"), 1.0]];
    const hd = hDy - dy;
    if (hd < bh) {
      const s = smoothstep(1 - hd / bh);
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
    if (kd < bh) {
      const s = smoothstep(1 - kd / bh);
      return [[th, 1 - s], [sh, s]];
    }
    return [[th, 1.0]];
  }
  if (dy <= aDy) {
    const ad = aDy - dy;
    if (ad < bh) {
      const s = smoothstep(1 - ad / bh);
      return [[sh, 1 - s], [ft, s]];
    }
    return [[sh, 1.0]];
  }
  return [[ft, 1.0]];
}

// ── Dual-Quaternion Skinning (2D approximation) ──

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

  let totalAngle = 0;
  let totalTx = 0;
  let totalTy = 0;
  let pivotX = 0;
  let pivotY = 0;

  for (const [bi, w] of weights) {
    const b = bones[bi]!;
    const angle = Math.atan2(b.wm[3], b.wm[0]);
    const tx = b.wm[2];
    const ty = b.wm[5];

    totalAngle += w * angle;
    totalTx += w * tx;
    totalTy += w * ty;
    pivotX += w * b.wj[0];
    pivotY += w * b.wj[1];
  }

  const c = Math.cos(totalAngle);
  const s = Math.sin(totalAngle);

  const ddx = px - pivotX;
  const ddy = py - pivotY;
  return [
    c * ddx - s * ddy + pivotX + totalTx,
    s * ddx + c * ddy + pivotY + totalTy,
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
