/**
 * V4 JSON loader — parses contour, landmarks, strokes from silhouette data.
 */

import type { LandmarkDict, StrokeInput, Vec2 } from "./types.js";

export interface LoadedData {
  readonly contour: Vec2[];
  readonly mirrored: boolean;
  readonly landmarks: LandmarkDict;
  readonly strokes: StrokeInput[];
  readonly scanlines: Record<string, unknown> | null;
  readonly crotchDy: number | null;
}

const REQUIRED_LANDMARKS = [
  "crown", "neck_valley", "shoulder_peak", "waist_valley",
  "hip_peak", "knee_valley", "ankle_valley", "sole",
] as const;

export function loadV4Json(json: Record<string, unknown>): LoadedData {
  // V4 schema format
  if (Array.isArray(json["contour"]) && Array.isArray(json["landmarks"])) {
    const pts = json["contour"] as [number, number][];
    const meta = json["meta"] as Record<string, unknown> | undefined;
    const mirror = meta?.["mirror"] as Record<string, unknown> | undefined;
    const mirrored = mirror?.["applied"] !== false;

    const contour: Vec2[] = pts.map((p) => [p[0], p[1]] as const);

    const landmarks: Record<string, Vec2> = {};
    for (const lm of json["landmarks"] as Array<Record<string, unknown>>) {
      const name = lm["name"] as string;
      landmarks[name] = [lm["dx"] as number, lm["dy"] as number] as const;
    }

    // Validate required landmarks
    for (const name of REQUIRED_LANDMARKS) {
      if (!landmarks[name]) {
        throw new Error(`Missing required landmark: ${name}`);
      }
    }

    // Extract strokes
    const strokes: StrokeInput[] = [];
    const rawStrokes = json["strokes"] as Array<Record<string, unknown>> | undefined;
    if (rawStrokes) {
      for (const s of rawStrokes) {
        const spts = s["points"] as [number, number][] | undefined;
        if (spts && spts.length >= 2) {
          strokes.push({
            points: spts.map((p) => [p[0], p[1]] as const),
          });
        }
      }
    }

    // Extract scanlines
    const measurements = json["measurements"] as Record<string, unknown> | undefined;
    const scanlines = measurements?.["scanlines"] as Record<string, unknown> | null ?? null;

    // Detect crotch level from hip_peak landmark
    const hipDy = landmarks["hip_peak"]?.[1] ?? null;
    const crotchDy = hipDy ? hipDy + 0.4 : null;

    return { contour, mirrored, landmarks, strokes, scanlines, crotchDy };
  }

  // Compact format
  if ("c" in json && "l" in json) {
    const flat = json["c"] as number[];
    const lmDict = json["l"] as Record<string, [number, number]>;

    const contour: Vec2[] = [];
    for (let i = 0; i < flat.length; i += 2) {
      contour.push([flat[i]!, flat[i + 1]!] as const);
    }

    const landmarks: Record<string, Vec2> = {};
    for (const [name, pos] of Object.entries(lmDict)) {
      landmarks[name] = [pos[0], pos[1]] as const;
    }

    for (const name of REQUIRED_LANDMARKS) {
      if (!landmarks[name]) {
        throw new Error(`Missing required landmark: ${name}`);
      }
    }

    return {
      contour,
      mirrored: false, // compact format is already bilateral
      landmarks,
      strokes: [],
      scanlines: null,
      crotchDy: null,
    };
  }

  throw new Error("Unrecognized format: needs 'contour'+'landmarks' or 'c'+'l'");
}
