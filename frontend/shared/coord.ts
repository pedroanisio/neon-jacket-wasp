/**
 * Shared coordinate-transform utilities for HU-space to SVG-space mapping.
 */

import type { HUPoint, HoleLevel } from "./types.ts";

/** Default scale: HU to SVG pixels. */
export const SCALE = 68;

/** Default center-X in SVG viewbox. */
export const CENTER_X = 115;

/** Default top padding in SVG viewbox. */
export const PAD_TOP = 6;

/** Convert an HU-space (dx, dy) to SVG pixel coordinates. */
export function huToSvg(
  dx: number,
  dy: number,
  scale = SCALE,
  cx = CENTER_X,
  pt = PAD_TOP,
): [number, number] {
  return [cx + dx * scale, pt + dy * scale];
}

/**
 * Build an SVG path string from a normalized contour.
 *
 * Supports both 180-degree (mirrored) and 360-degree (full) contours,
 * and carves out interior holes using evenodd fill-rule sub-paths.
 */
export function buildContourPath(
  contour: ReadonlyArray<HUPoint>,
  mirrored: boolean,
  holes: ReadonlyArray<ReadonlyArray<HoleLevel>>,
  scale = SCALE,
  cx = CENTER_X,
  pt = PAD_TOP,
): string {
  const toSvg = (dx: number, dy: number): [number, number] => huToSvg(dx, dy, scale, cx, pt);
  const fmt = ([x, y]: [number, number]): string => `${x.toFixed(1)},${y.toFixed(1)}`;

  let path: string;
  if (mirrored) {
    const r = contour.map(([dx, dy]) => toSvg(dx, dy));
    const l = [...contour].reverse().map(([dx, dy]) => toSvg(-dx, dy));
    path = "M " + [...r, ...l].map(fmt).join(" L ") + " Z";
  } else {
    path =
      "M " +
      contour
        .map(([dx, dy]) => {
          const [x, y] = toSvg(dx, dy);
          return `${x.toFixed(1)},${y.toFixed(1)}`;
        })
        .join(" L ") +
      " Z";
  }

  for (const hole of holes) {
    const rightEdge = hole.map((h) => toSvg(h.gapRight, h.dy));
    const leftEdge = [...hole].reverse().map((h) => toSvg(h.gapLeft, h.dy));
    path += " M " + [...rightEdge, ...leftEdge].map(fmt).join(" L ") + " Z";
  }

  return path;
}
