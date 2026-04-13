/**
 * Canvas 2D renderer for the deformed silhouette mesh.
 */

import type {
  BoneState,
  MutVec2,
  SkinWeights,
  StrokeInput,
  Triangle,
} from "./types.js";
import { deformVertex } from "./bones.js";

// ── Coordinate transform ──

let ox = 0;
let oy = 0;
let scale = 1;

export function setViewport(
  canvasWidth: number,
  canvasHeight: number,
): void {
  const figH = 8.4;
  const figW = 3.0;
  scale = Math.min(canvasHeight * 0.88 / figH, canvasWidth * 0.85 / figW);
  ox = canvasWidth / 2;
  oy = canvasHeight * 0.06;
}

function toScreen(dx: number, dy: number): MutVec2 {
  return [ox + dx * scale, oy + dy * scale];
}

// ── Drawing functions ──

export function drawGrid(ctx: CanvasRenderingContext2D, W: number): void {
  ctx.strokeStyle = "rgba(40,55,100,0.12)";
  ctx.lineWidth = 0.5;
  for (let hu = 0; hu <= 8; hu++) {
    const [, sy] = toScreen(0, hu);
    ctx.beginPath(); ctx.moveTo(0, sy); ctx.lineTo(W, sy); ctx.stroke();
  }
  for (let dx = -1.5; dx <= 1.5; dx += 0.5) {
    const [sx] = toScreen(dx, 0);
    ctx.beginPath(); ctx.moveTo(sx, 0); ctx.lineTo(sx, W); ctx.stroke();
  }
  ctx.fillStyle = "rgba(60,80,140,0.25)";
  ctx.font = "9px JetBrains Mono, monospace";
  for (let hu = 0; hu <= 8; hu++) {
    const [sx, sy] = toScreen(-1.5, hu);
    ctx.fillText(`${hu} HU`, sx - 30, sy + 3);
  }
}

export function drawMeshFill(
  ctx: CanvasRenderingContext2D,
  deformed: ReadonlyArray<MutVec2>,
  triangles: ReadonlyArray<Triangle>,
): void {
  const [, y0] = toScreen(0, 0);
  const [, y1] = toScreen(0, 8);
  const grad = ctx.createLinearGradient(ox, y0, ox, y1);
  grad.addColorStop(0, "rgba(35,45,80,0.85)");
  grad.addColorStop(0.3, "rgba(30,40,70,0.9)");
  grad.addColorStop(0.7, "rgba(25,35,65,0.88)");
  grad.addColorStop(1, "rgba(20,30,55,0.85)");
  ctx.fillStyle = grad;

  // Draw each triangle individually — this correctly handles
  // the leg gap because there are no triangles spanning it.
  ctx.beginPath();
  for (const [a, b, c] of triangles) {
    const pa = deformed[a]!;
    const pb = deformed[b]!;
    const pc = deformed[c]!;
    const [ax, ay] = toScreen(pa[0], pa[1]);
    const [bx, by] = toScreen(pb[0], pb[1]);
    const [cx, cy] = toScreen(pc[0], pc[1]);
    ctx.moveTo(ax, ay);
    ctx.lineTo(bx, by);
    ctx.lineTo(cx, cy);
    ctx.closePath();
  }
  ctx.fill();
}

export function drawMeshWireframe(
  ctx: CanvasRenderingContext2D,
  deformed: ReadonlyArray<MutVec2>,
  triangles: ReadonlyArray<Triangle>,
): void {
  ctx.strokeStyle = "rgba(60,90,160,0.15)";
  ctx.lineWidth = 0.3;
  for (const [a, b, c] of triangles) {
    const pa = deformed[a]!;
    const pb = deformed[b]!;
    const pc = deformed[c]!;
    const [ax, ay] = toScreen(pa[0], pa[1]);
    const [bx, by] = toScreen(pb[0], pb[1]);
    const [cx, cy] = toScreen(pc[0], pc[1]);
    ctx.beginPath();
    ctx.moveTo(ax, ay);
    ctx.lineTo(bx, by);
    ctx.lineTo(cx, cy);
    ctx.closePath();
    ctx.stroke();
  }
}

export function drawOutline(
  ctx: CanvasRenderingContext2D,
  deformed: ReadonlyArray<MutVec2>,
  boundaryLoop: ReadonlyArray<number>,
): void {
  if (boundaryLoop.length < 3) return;
  ctx.strokeStyle = "rgba(90,130,255,0.5)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  const first = deformed[boundaryLoop[0]!]!;
  const [sx0, sy0] = toScreen(first[0], first[1]);
  ctx.moveTo(sx0, sy0);
  for (let i = 1; i < boundaryLoop.length; i++) {
    const p = deformed[boundaryLoop[i]!]!;
    const [sx, sy] = toScreen(p[0], p[1]);
    ctx.lineTo(sx, sy);
  }
  ctx.closePath();
  ctx.stroke();

  // Glow
  ctx.strokeStyle = "rgba(80,120,255,0.12)";
  ctx.lineWidth = 4;
  ctx.stroke();
}

export function drawStrokes(
  ctx: CanvasRenderingContext2D,
  strokes: ReadonlyArray<StrokeInput>,
  strokeWeights: ReadonlyArray<ReadonlyArray<SkinWeights>>,
  bones: ReadonlyArray<BoneState>,
  _mirrored: boolean,
): void {
  ctx.lineWidth = 0.8;
  ctx.strokeStyle = "rgba(120,160,255,0.25)";

  for (let si = 0; si < strokes.length; si++) {
    const pts = strokes[si]!.points;
    const wts = strokeWeights[si]!;
    if (pts.length < 2) continue;

    ctx.beginPath();
    const d0 = deformVertex(pts[0]![0], pts[0]![1], wts[0]!, bones);
    const [sx0, sy0] = toScreen(d0[0], d0[1]);
    ctx.moveTo(sx0, sy0);
    for (let j = 1; j < pts.length; j++) {
      const dj = deformVertex(pts[j]![0], pts[j]![1], wts[j]!, bones);
      const [sx, sy] = toScreen(dj[0], dj[1]);
      ctx.lineTo(sx, sy);
    }
    ctx.stroke();
  }
}

export function drawSkeleton(
  ctx: CanvasRenderingContext2D,
  bones: ReadonlyArray<BoneState>,
): void {
  ctx.lineWidth = 2;
  for (let i = 0; i < bones.length; i++) {
    const b = bones[i]!;
    if (b.parent < 0) continue;
    const p = bones[b.parent]!;
    const [sx1, sy1] = toScreen(p.wj[0], p.wj[1]);
    const [sx2, sy2] = toScreen(b.wj[0], b.wj[1]);

    ctx.strokeStyle = "rgba(255,180,60,0.45)";
    ctx.beginPath();
    ctx.moveTo(sx1, sy1);
    ctx.lineTo(sx2, sy2);
    ctx.stroke();

    ctx.strokeStyle = "rgba(255,160,40,0.1)";
    ctx.lineWidth = 6;
    ctx.stroke();
    ctx.lineWidth = 2;
  }
}

export function drawJoints(
  ctx: CanvasRenderingContext2D,
  bones: ReadonlyArray<BoneState>,
  showLabels: boolean,
): void {
  const PI2 = Math.PI * 2;
  for (let i = 0; i < bones.length; i++) {
    const b = bones[i]!;
    const [sx, sy] = toScreen(b.wj[0], b.wj[1]);
    const r = i === 0 ? 5 : 3.5;

    ctx.fillStyle = i === 0 ? "rgba(255,100,80,0.7)" : "rgba(255,200,80,0.6)";
    ctx.beginPath();
    ctx.arc(sx, sy, r, 0, PI2);
    ctx.fill();

    ctx.fillStyle = i === 0 ? "rgba(255,80,60,0.15)" : "rgba(255,180,60,0.1)";
    ctx.beginPath();
    ctx.arc(sx, sy, r * 2.5, 0, PI2);
    ctx.fill();

    if (showLabels) {
      ctx.fillStyle = "rgba(200,180,140,0.5)";
      ctx.font = "8px JetBrains Mono, monospace";
      ctx.fillText(b.name, sx + 8, sy - 4);
    }
  }
}

export function drawCoM(
  ctx: CanvasRenderingContext2D,
  bones: ReadonlyArray<BoneState>,
  comWeights: SkinWeights,
): void {
  const dcom = deformVertex(0, 3.72, comWeights, bones);
  const [sx, sy] = toScreen(dcom[0], dcom[1]);

  ctx.strokeStyle = "rgba(100,255,150,0.4)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(sx - 6, sy); ctx.lineTo(sx + 6, sy);
  ctx.moveTo(sx, sy - 6); ctx.lineTo(sx, sy + 6);
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(sx, sy, 4, 0, Math.PI * 2);
  ctx.stroke();
}
