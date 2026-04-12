/**
 * Core type definitions for the silhouette skeletal deformation app.
 */

// ── Geometry ──

/** 2D point as [x, y]. */
export type Vec2 = readonly [number, number];

/** Mutable 2D point. */
export type MutVec2 = [number, number];

/** 3x2 affine matrix: [a, b, tx, c, d, ty]. */
export type Mat3x2 = [number, number, number, number, number, number];

/** Triangle as 3 vertex indices. */
export type Triangle = readonly [number, number, number];

// ── Mesh ──

export interface Mesh {
  /** Vertex positions in rest pose (HU space). */
  readonly vertices: ReadonlyArray<Vec2>;
  /** Triangle indices into vertices. */
  readonly triangles: ReadonlyArray<Triangle>;
  /** Boundary vertex indices forming the outer contour (for outline rendering). */
  readonly boundaryLoop: ReadonlyArray<number>;
}

// ── Bone system ──

export interface BoneDef {
  readonly name: string;
  readonly jx: number;
  readonly jy: number;
  readonly parent: number;
}

export interface BoneState extends BoneDef {
  angle: number;
  wm: Mat3x2;
  wj: MutVec2;
}

/** Per-vertex skinning: array of [boneIndex, weight] pairs. */
export type SkinWeights = ReadonlyArray<readonly [number, number]>;

// ── Animation ──

export type BoneAngles = Readonly<Record<string, number>>;
export type PresetFn = (t: number) => BoneAngles;

// ── Display ──

export interface DisplayToggles {
  fill: boolean;
  outline: boolean;
  strokes: boolean;
  skeleton: boolean;
  joints: boolean;
  labels: boolean;
  com: boolean;
  grid: boolean;
  mesh: boolean;
}

// ── Data loading ──

export interface LandmarkDict {
  readonly [name: string]: Vec2 | undefined;
}

export interface SpanData {
  readonly outer_dx: number;
  readonly inner_dx: number;
}

export interface StrokeInput {
  readonly points: ReadonlyArray<Vec2>;
}

export interface SkinningData {
  readonly mesh: Mesh;
  readonly weights: ReadonlyArray<SkinWeights>;
  readonly bones: BoneState[];
  readonly boneIndex: Map<string, number>;
  readonly landmarks: LandmarkDict;
}
