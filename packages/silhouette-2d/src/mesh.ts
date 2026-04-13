/**
 * Mesh generation from contour boundary + scanline topology.
 *
 * Builds a triangulated bilateral mesh that:
 * - Follows the outer contour boundary
 * - Splits into separate left/right leg regions below the crotch
 * - Uses interior cross-section points from scanline data
 * - Produces clean triangle topology for skinning
 *
 * Strategy:
 * 1. Build RIGHT HALF mesh from contour + midline + scanline inner edges
 * 2. Mirror to LEFT HALF
 * 3. Stitch at midline for single-body regions, keep separate for legs
 */

import type { Mesh, MutVec2, SpanData, Triangle, Vec2 } from "./types.js";

// ── Contour processing ──

/** Find the split index (max dy) in a contour array. */
function findSplitIndex(contour: ReadonlyArray<Vec2>): number {
  let idx = 0;
  for (let i = 1; i < contour.length; i++) {
    if (contour[i]![1] > contour[idx]![1]) idx = i;
  }
  return idx;
}

/** Extract right-half contour (0..splitIdx inclusive). */
function extractRightHalf(
  contour: ReadonlyArray<Vec2>,
  mirrored: boolean,
): Vec2[] {
  if (!mirrored) {
    // Full 360° contour — take all points
    return contour.map((p) => [p[0], p[1]] as const);
  }
  const splitIdx = findSplitIndex(contour);
  return contour.slice(0, splitIdx + 1).map((p) => [p[0], p[1]] as const);
}

/** Subsample a contour to targetCount points, preserving first and last. */
function subsample(pts: Vec2[], targetCount: number): Vec2[] {
  if (pts.length <= targetCount) return pts;
  const result: Vec2[] = [pts[0]!];
  const step = (pts.length - 1) / (targetCount - 1);
  for (let i = 1; i < targetCount - 1; i++) {
    result.push(pts[Math.round(i * step)]!);
  }
  result.push(pts[pts.length - 1]!);
  return result;
}

// ── Scanline topology extraction ──

interface ScanlineLevel {
  readonly dy: number;
  readonly spans: ReadonlyArray<SpanData>;
}

function extractScanlineLevels(
  scanlines: Record<string, unknown>,
): ScanlineLevel[] {
  const levels: ScanlineLevel[] = [];
  for (const [dk, entry] of Object.entries(scanlines)) {
    if (entry === null || typeof entry !== "object") continue;
    const dy = parseFloat(dk);
    if (!isFinite(dy)) continue;

    // Dict entry with topology_detail
    if (!Array.isArray(entry) && "topology_detail" in entry) {
      const td = (entry as Record<string, unknown>)["topology_detail"];
      if (Array.isArray(td) && td.length >= 2) {
        levels.push({
          dy,
          spans: td as SpanData[],
        });
      }
    }
    // Raw list entry
    else if (Array.isArray(entry) && entry.length >= 2) {
      levels.push({ dy, spans: entry as SpanData[] });
    }
  }
  levels.sort((a, b) => a.dy - b.dy);
  return levels;
}

// ── Bilateral mesh builder ──

/**
 * Build a triangulated bilateral mesh from contour and scanline data.
 *
 * The mesh uses a strip-based approach:
 * - Horizontal cross-sections at regular dy intervals
 * - At each level, vertices on the outer boundary + midline
 * - Below crotch: separate left/right strips with a gap
 * - Quad strips triangulated into pairs of triangles
 */
export function buildMesh(
  contour: ReadonlyArray<Vec2>,
  mirrored: boolean,
  scanlines?: Record<string, unknown>,
  crotchDy?: number,
): Mesh {
  const rightHalf = extractRightHalf(contour, mirrored);
  const subRight = subsample(rightHalf, 200);

  // Determine crotch level from scanline topology or use estimate
  const levels = scanlines ? extractScanlineLevels(scanlines) : [];
  const legLevels = levels.filter(
    (l) =>
      l.spans.length === 2 &&
      l.spans[0]!.inner_dx > 0 &&
      l.spans[1]!.outer_dx < 0,
  );

  const effectiveCrotchDy =
    crotchDy ??
    (legLevels.length > 0 ? legLevels[0]!.dy : 8.0);

  // Build vertex rows at regular dy intervals
  const dyMin = subRight[0]![1];
  const dyMax = subRight[subRight.length - 1]![1];
  const dyStep = 0.08; // ~100 rows across 8 HU

  const vertices: MutVec2[] = [];
  const rows: number[][] = []; // row i → vertex indices at that dy
  const boundaryIndices: number[] = [];

  // For each dy level, find the outer contour dx at that level
  function getOuterDx(dy: number): number {
    // Linear interpolation on the right-half contour
    for (let i = 0; i < subRight.length - 1; i++) {
      const p0 = subRight[i]!;
      const p1 = subRight[i + 1]!;
      if (p0[1] <= dy && p1[1] >= dy) {
        const t = (dy - p0[1]) / (p1[1] - p0[1] || 1e-10);
        return p0[0] + (p1[0] - p0[0]) * t;
      }
      // Handle re-entrant (dy temporarily decreasing)
      if (p1[1] < p0[1] && p0[1] >= dy && p1[1] <= dy) {
        const t = (p0[1] - dy) / (p0[1] - p1[1] || 1e-10);
        return p0[0] + (p1[0] - p0[0]) * t;
      }
    }
    return 0;
  }

  // Get inner dx for leg region from scanline data
  function getLegInnerDx(dy: number): number {
    // Find closest leg-level scanline
    let closest: ScanlineLevel | null = null;
    let bestDist = Infinity;
    for (const l of legLevels) {
      const dist = Math.abs(l.dy - dy);
      if (dist < bestDist) {
        bestDist = dist;
        closest = l;
      }
    }
    if (closest && bestDist < 0.2) {
      return closest.spans[0]!.inner_dx;
    }
    // Estimate: taper from 0 at crotch to outer_dx * 0.4 at sole
    const t = Math.min(1, (dy - effectiveCrotchDy) / (dyMax - effectiveCrotchDy));
    return getOuterDx(dy) * 0.4 * t;
  }

  const nCols = 8; // vertices per half-row (midline to outer edge)

  for (let dy = dyMin; dy <= dyMax; dy += dyStep) {
    const row: number[] = [];
    const isLegRegion = dy > effectiveCrotchDy;
    const outerDx = getOuterDx(dy);

    if (isLegRegion) {
      const innerDx = getLegInnerDx(dy);

      // LEFT LEG: -outerDx to -innerDx
      for (let j = 0; j < nCols; j++) {
        const t = j / (nCols - 1);
        const dx = -outerDx + (-innerDx - -outerDx) * t;
        const vi = vertices.length;
        vertices.push([dx, dy]);
        row.push(vi);
        if (j === 0) boundaryIndices.push(vi);
      }

      // GAP (no vertices)

      // RIGHT LEG: innerDx to outerDx
      for (let j = 0; j < nCols; j++) {
        const t = j / (nCols - 1);
        const dx = innerDx + (outerDx - innerDx) * t;
        const vi = vertices.length;
        vertices.push([dx, dy]);
        row.push(vi);
        if (j === nCols - 1) boundaryIndices.push(vi);
      }
    } else {
      // SINGLE BODY: -outerDx to +outerDx
      const totalCols = nCols * 2 - 1;
      for (let j = 0; j < totalCols; j++) {
        const t = j / (totalCols - 1);
        const dx = -outerDx + 2 * outerDx * t;
        const vi = vertices.length;
        vertices.push([dx, dy]);
        row.push(vi);
        if (j === 0 || j === totalCols - 1) boundaryIndices.push(vi);
      }
    }

    rows.push(row);
  }

  // Triangulate: connect adjacent rows with triangle strips
  const triangles: Triangle[] = [];

  for (let r = 0; r < rows.length - 1; r++) {
    const top = rows[r]!;
    const bot = rows[r + 1]!;

    if (top.length === bot.length) {
      // Same topology — simple quad strip
      for (let j = 0; j < top.length - 1; j++) {
        triangles.push([top[j]!, top[j + 1]!, bot[j]!]);
        triangles.push([top[j + 1]!, bot[j + 1]!, bot[j]!]);
      }
    } else {
      // Topology transition (single body → legs or vice versa)
      // Fan triangulation from the row with fewer vertices
      const fewer = top.length < bot.length ? top : bot;
      const more = top.length < bot.length ? bot : top;
      const isTopFewer = top.length < bot.length;

      // Simple fan: connect each vertex of the fewer row to
      // corresponding segment of the more row
      const ratio = (more.length - 1) / (fewer.length - 1 || 1);
      for (let j = 0; j < fewer.length - 1; j++) {
        const mStart = Math.round(j * ratio);
        const mEnd = Math.round((j + 1) * ratio);
        for (let k = mStart; k < mEnd; k++) {
          if (isTopFewer) {
            triangles.push([top[j]!, bot[k + 1]!, bot[k]!]);
          } else {
            triangles.push([top[k]!, top[k + 1]!, bot[j]!]);
          }
        }
        // Connect the last triangle of this fan segment
        if (isTopFewer) {
          triangles.push([top[j]!, top[j + 1]!, bot[mEnd]!]);
        } else {
          triangles.push([top[Math.round((j + 1) * ratio)]!, bot[j]!, bot[j + 1]!]);
        }
      }
    }
  }

  // Build boundary loop from contour (for outline rendering)
  // Use the original contour vertices projected to nearest mesh vertices
  const boundaryLoop = buildBoundaryLoop(vertices, subRight, mirrored);

  return {
    vertices: vertices as Vec2[],
    triangles,
    boundaryLoop,
  };
}

/** Build boundary loop by tracing outer mesh vertices. */
function buildBoundaryLoop(
  vertices: ReadonlyArray<MutVec2>,
  rightHalf: ReadonlyArray<Vec2>,
  mirrored: boolean,
): number[] {
  // Find vertices closest to the contour path
  const loop: number[] = [];
  const used = new Set<number>();

  // Trace right side (top to bottom) then left side (bottom to top)
  const contourPts = mirrored
    ? [...rightHalf, ...rightHalf.slice().reverse().map((p) => [-p[0], p[1]] as const)]
    : rightHalf;

  for (const cp of contourPts) {
    let bestIdx = 0;
    let bestDist = Infinity;
    for (let i = 0; i < vertices.length; i++) {
      if (used.has(i)) continue;
      const v = vertices[i]!;
      const d = (v[0] - cp[0]) ** 2 + (v[1] - cp[1]) ** 2;
      if (d < bestDist) {
        bestDist = d;
        bestIdx = i;
      }
    }
    if (!used.has(bestIdx)) {
      loop.push(bestIdx);
      used.add(bestIdx);
    }
  }
  return loop;
}
