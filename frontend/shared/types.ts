/** Shared type definitions for the silhouette v4 frontend. */

/** A [dx, dy] coordinate pair in head-unit space. */
export type HUPoint = [number, number];

/** Normalized landmark. */
export interface NormalizedLandmark {
  readonly n: string;
  readonly d: string;
  readonly dy: number;
  readonly dx: number;
}

/** Normalized stroke path. */
export interface NormalizedStroke {
  readonly r: string;
  readonly p: ReadonlyArray<HUPoint>;
}

/** Body region span. */
export interface NormalizedRegion {
  readonly n: string;
  readonly s: number;
  readonly e: number;
}

/** Area-profile entry per region. */
export interface NormalizedAreaRegion {
  readonly n: string;
  readonly h: number;
  readonly a: number;
  readonly f: number;
  readonly mw: number;
}

/** Width-profile sample. */
export interface NormalizedWidthSample {
  readonly dy: number;
  readonly w: number;
}

/** Style deviation position entry. */
export interface StyleDeviationPosition {
  readonly n: string;
  readonly m: number;
  readonly c: number;
  readonly d: number;
}

/** Style deviation width entry. */
export interface StyleDeviationWidth {
  readonly n: string;
  readonly m: number;
  readonly c: number;
  readonly d: number;
}

/** Normalized style deviation block. */
export interface NormalizedStyleDeviation {
  readonly canon: string;
  readonly fh: number;
  readonly ch: number;
  readonly l2: number;
  readonly pos: ReadonlyArray<StyleDeviationPosition>;
  readonly wid: ReadonlyArray<StyleDeviationWidth>;
}

/** Normalized gesture line block. */
export interface NormalizedGestureLine {
  readonly lean: number;
  readonly li: string;
  readonly cp: number;
  readonly ci: string;
  readonly en: number;
  readonly ctr_dx: number;
  readonly ctr_dy: number;
}

/** Normalized volumetric estimates. */
export interface NormalizedVolumetric {
  readonly cyl: number | undefined;
  readonly ell: number | undefined;
  readonly pap: number | undefined;
}

/** Normalized convex hull. */
export interface NormalizedHull {
  readonly sol: number;
  readonly ha: number;
  readonly sa: number;
  readonly na: number;
}

/** Normalized biomechanics. */
export interface NormalizedBiomechanics {
  readonly hcm: number;
  readonly sc: number;
  readonly com_dy: number | undefined;
  readonly com_frac: number | undefined;
}

/** Medial axis sample. */
export interface NormalizedMedialSample {
  readonly dy: number;
  readonly r: number;
}

/** Interior hole group entry. */
export interface HoleLevel {
  readonly dy: number;
  readonly gapLeft: number;
  readonly gapRight: number;
}

/** Proportion block. */
export interface NormalizedProportion {
  readonly hc: number;
  readonly sr: Readonly<Record<string, number>>;
  readonly wr: Readonly<Record<string, number>>;
  readonly comp: Readonly<Record<string, number | string>>;
  readonly canons: ReadonlyArray<{ readonly sys: string; readonly heads: number }>;
}

/** Shape complexity — flexible key/value from the raw JSON. */
export type NormalizedShapeComplexity = Readonly<
  Record<string, { value: number; units?: string; method?: string } | number>
>;

/**
 * The canonical normalized document returned by normalize().
 * This is the single data contract between the v4 JSON schema
 * and all frontend rendering components.
 */
export interface NormalizedData {
  readonly version: string;
  readonly isV4: boolean;
  readonly mirrored: boolean;
  readonly contour: ReadonlyArray<HUPoint>;
  readonly strokes: ReadonlyArray<NormalizedStroke>;
  readonly landmarks: ReadonlyArray<NormalizedLandmark>;
  readonly pr: NormalizedProportion;
  readonly br: ReadonlyArray<NormalizedRegion>;
  readonly ar: ReadonlyArray<NormalizedAreaRegion>;
  readonly wp: ReadonlyArray<NormalizedWidthSample>;
  readonly sd: NormalizedStyleDeviation | null;
  readonly sc: NormalizedShapeComplexity | null;
  readonly gl: NormalizedGestureLine | null;
  readonly vol: NormalizedVolumetric | null;
  readonly hull: NormalizedHull | null;
  readonly bio: NormalizedBiomechanics | null;
  readonly med: ReadonlyArray<NormalizedMedialSample>;
  readonly holes: ReadonlyArray<ReadonlyArray<HoleLevel>>;
  readonly surface: string;
  readonly gender: string;
  readonly view: string;
}

/** Payload from V4FileLoader when a file is loaded. */
export interface V4LoadPayload {
  readonly data: NormalizedData;
  readonly fileName: string;
  readonly raw: unknown;
}

/** Pipeline-derived data for stick_to_mesh_pipeline. */
export interface PipelineData {
  readonly dy: ReadonlyArray<number>;
  readonly widths: ReadonlyArray<number>;
  readonly prior_ratios: ReadonlyArray<number>;
  readonly final_ratios: ReadonlyArray<number>;
  readonly rewards: ReadonlyArray<[number, number]>;
  readonly landmarks: ReadonlyArray<{ readonly name: string; readonly dy: number }>;
}
