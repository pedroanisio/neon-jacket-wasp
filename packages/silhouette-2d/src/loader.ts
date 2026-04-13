/**
 * V4 JSON loader — parses contour, landmarks, strokes, body regions,
 * width profile, and cross-section topology from silhouette data.
 *
 * Supports diverse humanoid figures (nude, armored, clothed) by resolving
 * landmark names through an alias table — different v4 generators use
 * different naming conventions but mean the same anatomical position.
 */

import type { LandmarkDict, StrokeInput, Vec2 } from "./types.js";

export interface BodyRegion {
  readonly name: string;
  readonly dyStart: number;
  readonly dyEnd: number;
}

export interface WidthSample {
  readonly dy: number;
  readonly dx: number;
  readonly fullWidth: number;
}

export interface LoadedData {
  readonly contour: Vec2[];
  readonly mirrored: boolean;
  readonly landmarks: LandmarkDict;
  readonly strokes: StrokeInput[];
  readonly scanlines: Record<string, unknown> | null;
  readonly crotchDy: number | null;
  readonly bodyRegions: BodyRegion[];
  readonly widthProfile: WidthSample[];
  readonly figureHeight: number;
}

// ── Landmark alias resolution ──
// Maps canonical bone-system names to ordered fallback lists.
// The first match in the v4 landmark set wins.

const LANDMARK_ALIASES: Record<string, readonly string[]> = {
  crown:          ["crown"],
  neck_valley:    ["neck_valley", "c7", "suprasternal"],
  shoulder_peak:  ["shoulder_peak", "acromion_r", "trapezius_peak"],
  waist_valley:   ["waist_valley", "waist", "xiphoid"],
  hip_peak:       ["hip_peak", "great_trochanter_r", "iliac_crest_r", "asis_r"],
  knee_valley:    ["knee_valley", "patella_r", "tibial_tuberosity_r"],
  ankle_valley:   ["ankle_valley", "lateral_malleolus_r", "heel_r"],
  sole:           ["sole"],
  // Optional enrichment landmarks (used when available).
  chin:           ["chin"],
  armpit:         ["armpit_valley", "chest_inflection"],
  navel:          ["navel_estimate", "navel", "pubic_symphysis"],
  mid_thigh:      ["mid_thigh", "mid_thigh_r"],
  calf_peak:      ["calf_peak", "gastrocnemius_r"],
};

const REQUIRED_CANONICAL = [
  "crown", "neck_valley", "shoulder_peak", "waist_valley",
  "hip_peak", "knee_valley", "ankle_valley", "sole",
] as const;

/**
 * Resolve canonical landmark names from whatever the v4 document provides.
 * Returns a LandmarkDict keyed by canonical names.
 */
function resolveLandmarks(
  raw: Record<string, Vec2>,
): LandmarkDict {
  const resolved: Record<string, Vec2> = {};

  // First pass: copy all raw landmarks (preserve originals).
  for (const [name, pos] of Object.entries(raw)) {
    resolved[name] = pos;
  }

  // Second pass: resolve canonical aliases.
  for (const [canonical, aliases] of Object.entries(LANDMARK_ALIASES)) {
    if (resolved[canonical]) continue; // already present
    for (const alias of aliases) {
      if (raw[alias]) {
        resolved[canonical] = raw[alias]!;
        break;
      }
    }
  }

  return resolved;
}

/**
 * Estimate crotch dy from body regions or landmarks.
 */
function estimateCrotchDy(
  landmarks: LandmarkDict,
  bodyRegions: BodyRegion[],
): number | null {
  // Best: use body_regions — the lower_torso/upper_leg boundary IS the crotch.
  const upperLeg = bodyRegions.find((r) => r.name === "upper_leg");
  if (upperLeg) return upperLeg.dyStart;

  const lowerTorso = bodyRegions.find((r) => r.name === "lower_torso");
  if (lowerTorso) return lowerTorso.dyEnd;

  // Fallback: hip_peak + offset scaled to figure proportions.
  const hp = landmarks["hip_peak"];
  const sole = landmarks["sole"];
  if (hp && sole) {
    const figH = sole[1] || 8.0;
    return hp[1] + figH * 0.05;
  }

  return null;
}

export function loadV4Json(json: Record<string, unknown>): LoadedData {
  // V4 schema format
  if (Array.isArray(json["contour"]) && Array.isArray(json["landmarks"])) {
    const pts = json["contour"] as [number, number][];
    const meta = json["meta"] as Record<string, unknown> | undefined;
    const mirror = meta?.["mirror"] as Record<string, unknown> | undefined;
    const mirrored = mirror?.["applied"] !== false;

    const contour: Vec2[] = pts.map((p) => [p[0], p[1]] as const);

    // Parse raw landmarks.
    const rawLandmarks: Record<string, Vec2> = {};
    for (const lm of json["landmarks"] as Array<Record<string, unknown>>) {
      const name = lm["name"] as string;
      rawLandmarks[name] = [lm["dx"] as number, lm["dy"] as number] as const;
    }

    // Resolve canonical names via alias table.
    const landmarks = resolveLandmarks(rawLandmarks);

    // Validate required canonical landmarks exist (after resolution).
    for (const name of REQUIRED_CANONICAL) {
      if (!landmarks[name]) {
        throw new Error(
          `Missing required landmark: ${name}. ` +
          `Available: ${Object.keys(rawLandmarks).join(", ")}`,
        );
      }
    }

    // Extract strokes.
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

    // Extract scanlines.
    const measurements = json["measurements"] as Record<string, unknown> | undefined;
    const scanlines = measurements?.["scanlines"] as Record<string, unknown> | null ?? null;

    // Extract body regions.
    const bodyRegions: BodyRegion[] = [];
    const br = json["body_regions"] as Record<string, unknown> | undefined;
    if (br && Array.isArray(br["regions"])) {
      for (const r of br["regions"] as Array<Record<string, unknown>>) {
        bodyRegions.push({
          name: r["name"] as string,
          dyStart: r["dy_start"] as number,
          dyEnd: r["dy_end"] as number,
        });
      }
    }

    // Extract width profile.
    const widthProfile: WidthSample[] = [];
    const wp = json["width_profile"] as Record<string, unknown> | undefined;
    if (wp && Array.isArray(wp["samples"])) {
      for (const s of wp["samples"] as Array<Record<string, unknown>>) {
        widthProfile.push({
          dy: s["dy"] as number,
          dx: s["dx"] as number,
          fullWidth: (s["full_width"] as number) || 0,
        });
      }
    }

    // Figure height from sole landmark or last contour point.
    const figureHeight = landmarks["sole"]?.[1] ?? pts[pts.length - 1]?.[1] ?? 8.0;

    // Estimate crotch level.
    const crotchDy = estimateCrotchDy(landmarks, bodyRegions);

    return { contour, mirrored, landmarks, strokes, scanlines, crotchDy, bodyRegions, widthProfile, figureHeight };
  }

  // Compact format
  if ("c" in json && "l" in json) {
    const flat = json["c"] as number[];
    const lmDict = json["l"] as Record<string, [number, number]>;

    const contour: Vec2[] = [];
    for (let i = 0; i < flat.length; i += 2) {
      contour.push([flat[i]!, flat[i + 1]!] as const);
    }

    const rawLandmarks: Record<string, Vec2> = {};
    for (const [name, pos] of Object.entries(lmDict)) {
      rawLandmarks[name] = [pos[0], pos[1]] as const;
    }

    const landmarks = resolveLandmarks(rawLandmarks);

    for (const name of REQUIRED_CANONICAL) {
      if (!landmarks[name]) {
        throw new Error(`Missing required landmark: ${name}`);
      }
    }

    return {
      contour,
      mirrored: false,
      landmarks,
      strokes: [],
      scanlines: null,
      crotchDy: null,
      bodyRegions: [],
      widthProfile: [],
      figureHeight: landmarks["sole"]?.[1] ?? 8.0,
    };
  }

  throw new Error("Unrecognized format: needs 'contour'+'landmarks' or 'c'+'l'");
}
