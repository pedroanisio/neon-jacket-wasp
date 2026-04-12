/**
 * Core type definitions for the silhouette skeletal deformation app.
 */

// ── Geometry ──

/** 2D point as [x, y]. */
export type Vec2 = [number, number];

/** 3x2 affine matrix stored as 6 floats: [a, b, tx, c, d, ty]. */
export type Mat3x2 = [number, number, number, number, number, number];

// ── Bone system ──

export interface BoneDef {
  readonly name: string;
  readonly jx: number;
  readonly jy: number;
  readonly parent: number; // -1 for root
}

export interface BoneState extends BoneDef {
  angle: number;
  wm: Mat3x2;  // world matrix
  wj: Vec2;    // world joint position
}

/** Bone weight: [boneIndex, weight]. */
export type BoneWeight = [number, number];

// ── Animation ──

export type BoneAngles = Record<string, number>;
export type PresetFn = (t: number) => BoneAngles;

// ── Rendering ──

export interface DisplayToggles {
  fill: boolean;
  outline: boolean;
  strokes: boolean;
  skeleton: boolean;
  joints: boolean;
  labels: boolean;
  com: boolean;
  grid: boolean;
}

// ── Data loading ──

export interface LandmarkDict {
  [name: string]: Vec2;
}

export interface StrokeData {
  readonly pts: ReadonlyArray<Vec2>;
  readonly weights: ReadonlyArray<ReadonlyArray<BoneWeight>>;
}

/** V4 schema JSON shape (subset used by this app). */
export interface V4Json {
  readonly meta?: {
    readonly mirror?: { readonly applied?: boolean };
  };
  readonly contour?: ReadonlyArray<[number, number]>;
  readonly landmarks?: ReadonlyArray<{
    readonly name: string;
    readonly dx: number;
    readonly dy: number;
  }>;
  readonly strokes?: ReadonlyArray<{
    readonly points?: ReadonlyArray<[number, number]>;
  }>;
  readonly measurements?: {
    readonly scanlines?: Record<string, unknown>;
  };
}

/** Compact JSON shape. */
export interface CompactJson {
  readonly c: number[];
  readonly l: LandmarkDict;
}

export type InputJson = V4Json | CompactJson;

/** Parsed contour + landmark data ready for the bone system. */
export interface ParsedModel {
  readonly contourFlat: number[];
  readonly landmarks: LandmarkDict;
}
