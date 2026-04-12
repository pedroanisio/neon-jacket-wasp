/**
 * 2D affine matrix + vector utilities.
 */

import type { Mat3x2, MutVec2, Vec2 } from "./types.js";

export function matIdentity(): Mat3x2 {
  return [1, 0, 0, 0, 1, 0];
}

export function matMul(A: Mat3x2, B: Mat3x2): Mat3x2 {
  return [
    A[0] * B[0] + A[1] * B[3],
    A[0] * B[1] + A[1] * B[4],
    A[0] * B[2] + A[1] * B[5] + A[2],
    A[3] * B[0] + A[4] * B[3],
    A[3] * B[1] + A[4] * B[4],
    A[3] * B[2] + A[4] * B[5] + A[5],
  ];
}

export function matRot(angle: number): Mat3x2 {
  const c = Math.cos(angle);
  const s = Math.sin(angle);
  return [c, -s, 0, s, c, 0];
}

export function matTrans(tx: number, ty: number): Mat3x2 {
  return [1, 0, tx, 0, 1, ty];
}

export function matRotAround(cx: number, cy: number, angle: number): Mat3x2 {
  return matMul(matTrans(cx, cy), matMul(matRot(angle), matTrans(-cx, -cy)));
}

export function matXform(m: Mat3x2, x: number, y: number): MutVec2 {
  return [m[0] * x + m[1] * y + m[2], m[3] * x + m[4] * y + m[5]];
}

export function vec2Dist(a: Vec2, b: Vec2): number {
  const dx = a[0] - b[0];
  const dy = a[1] - b[1];
  return Math.sqrt(dx * dx + dy * dy);
}

export function vec2Lerp(a: Vec2, b: Vec2, t: number): MutVec2 {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
}

/** Smoothstep interpolation. */
export function smoothstep(t: number): number {
  const c = Math.max(0, Math.min(1, t));
  return c * c * (3 - 2 * c);
}
