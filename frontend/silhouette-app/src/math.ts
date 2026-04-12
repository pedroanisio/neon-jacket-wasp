/**
 * 2D affine matrix utilities for bone transformations.
 *
 * All matrices are 3×2 stored as [a, b, tx, c, d, ty]:
 *   | a  b  tx |
 *   | c  d  ty |
 *   | 0  0  1  |
 */

import type { Mat3x2, Vec2 } from "./types.js";

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

export function matXform(m: Mat3x2, x: number, y: number): Vec2 {
  return [m[0] * x + m[1] * y + m[2], m[3] * x + m[4] * y + m[5]];
}
