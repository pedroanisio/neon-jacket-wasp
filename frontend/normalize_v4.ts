/**
 * Normalize a raw v4 silhouette JSON document into the compact format
 * consumed by all frontend renderers.
 *
 * This is the single normalization layer -- the canonical contract between
 * the v4 JSON schema and the frontend rendering components.
 */

import type {
  NormalizedData,
  HUPoint,
  NormalizedStroke,
  NormalizedLandmark,
  NormalizedRegion,
  NormalizedAreaRegion,
  NormalizedWidthSample,
  NormalizedStyleDeviation,
  NormalizedShapeComplexity,
  NormalizedGestureLine,
  NormalizedVolumetric,
  NormalizedHull,
  NormalizedBiomechanics,
  NormalizedMedialSample,
  NormalizedProportion,
  HoleLevel,
} from "./shared/types.ts";

/* eslint-disable @typescript-eslint/no-explicit-any */
type RawDoc = Record<string, any>;

function round3(n: number): number {
  return Math.round(n * 1000) / 1000;
}

export default function normalize(raw: RawDoc): NormalizedData {
  const meta = (raw.meta ?? {}) as RawDoc;
  const cls = (meta.classification ?? {}) as RawDoc;
  const version: string = (meta.schema_version as string | undefined) ?? "unknown";
  const isV4: boolean = !!raw.body_regions;

  // Contour mode: 180deg (mirrored) or 360deg (full).
  const contourRaw = (raw.contour ?? []) as HUPoint[];
  const mirrored: boolean = (meta.mirror as RawDoc | undefined)?.applied !== false;

  let splitIdx = 0;
  for (let i = 1; i < contourRaw.length; i++) {
    if (contourRaw[i]![1] > contourRaw[splitIdx]![1]) splitIdx = i;
  }

  let contour: HUPoint[];
  if (mirrored) {
    const rightContour = contourRaw.slice(0, splitIdx + 1);
    contour = rightContour
      .filter((_, i) => i % 2 === 0 || i === rightContour.length - 1)
      .map(([dx, dy]) => [round3(dx), round3(dy)]);
  } else {
    contour = contourRaw
      .filter((_, i) => i % 2 === 0 || i === contourRaw.length - 1)
      .map(([dx, dy]) => [round3(dx), round3(dy)]);
  }

  // Strokes
  const strokes: NormalizedStroke[] = ((raw.strokes ?? []) as RawDoc[]).map((s) => {
    let pts = (s.points ?? []) as HUPoint[];
    if (pts.length > 20)
      pts = pts.filter((_, i) => i % 2 === 0).concat([pts[pts.length - 1]!]);
    return {
      r: s.region as string,
      p: pts.map(([dx, dy]) => [round3(dx), round3(dy)] as HUPoint),
    };
  });

  // Landmarks
  const landmarks: NormalizedLandmark[] = ((raw.landmarks ?? []) as RawDoc[]).map((l) => ({
    n: l.name as string,
    d: (l.description as string | undefined) ?? "",
    dy: l.dy as number,
    dx: l.dx as number,
  }));

  // Proportions
  const prop = (raw.proportion ?? {}) as RawDoc;
  const pr: NormalizedProportion = {
    hc: (prop.head_count_total as number | undefined) ??
      (prop.head_count_anatomical as number | undefined) ??
      0,
    sr: (prop.segment_ratios as Record<string, number> | undefined) ?? {},
    wr: (prop.width_ratios as Record<string, number> | undefined) ?? {},
    comp: prop.composite_ratios
      ? (Object.fromEntries(
          Object.entries(prop.composite_ratios as Record<string, unknown>)
            .filter(([k]) => k !== "note")
            .map(([k, v]) => [
              k,
              typeof v === "number" ? Math.round(v * 10000) / 10000 : v,
            ]),
        ) as Record<string, number | string>)
      : {},
    canons: prop.canonical_comparisons
      ? (prop.canonical_comparisons as RawDoc[]).map((c) => ({
          sys: c.system as string,
          heads: c.total_heads as number,
        }))
      : [],
  };

  // Body regions
  const br: NormalizedRegion[] = isV4
    ? ((raw.body_regions as RawDoc).regions as RawDoc[]).map((r) => ({
        n: r.name as string,
        s: r.dy_start as number,
        e: r.dy_end as number,
      }))
    : [];

  // Area profile
  const ar: NormalizedAreaRegion[] =
    isV4 && raw.area_profile
      ? ((raw.area_profile as RawDoc).per_region as RawDoc[]).map((r) => ({
          n: r.name as string,
          h: r.height_hu as number,
          a: r.area_hu2 as number,
          f: r.area_fraction as number,
          mw: r.mean_full_width_hu as number,
        }))
      : [];

  // Width profile
  const wp: NormalizedWidthSample[] =
    isV4 && raw.width_profile
      ? ((raw.width_profile as RawDoc).samples as RawDoc[])
          .filter((_, i) => i % 2 === 0)
          .map((s) => ({ dy: s.dy as number, w: s.full_width as number }))
      : [];

  // Style deviation
  let sd: NormalizedStyleDeviation | null = null;
  if (isV4 && raw.style_deviation) {
    const sdd = raw.style_deviation as RawDoc;
    sd = {
      canon: (sdd.canon as string | undefined) ?? "",
      fh: sdd.figure_head_count as number,
      ch: sdd.canon_head_count as number,
      l2: sdd.l2_stylisation_distance as number,
      pos: ((sdd.position_deviations ?? []) as RawDoc[]).map((p) => ({
        n: p.landmark as string,
        m: p.measured_fraction as number,
        c: p.canon_fraction as number,
        d: p.deviation as number,
      })),
      wid: ((sdd.width_deviations ?? []) as RawDoc[]).map((w) => ({
        n: w.feature as string,
        m: w.measured as number,
        c: w.canon as number,
        d: w.deviation as number,
      })),
    };
  }

  // Shape complexity
  let sc: NormalizedShapeComplexity | null = null;
  if (isV4 && raw.shape_complexity) {
    sc = Object.fromEntries(
      Object.entries(raw.shape_complexity as Record<string, unknown>).filter(
        ([k]) => !["note", "reference", "computed_on"].includes(k),
      ),
    ) as NormalizedShapeComplexity;
  }

  // Gesture line
  let gl: NormalizedGestureLine | null = null;
  if (isV4 && raw.gesture_line) {
    const g = raw.gesture_line as RawDoc;
    gl = {
      lean: g.lean_angle_deg as number,
      li: g.lean_interpretation as string,
      cp: g.contrapposto_score as number,
      ci: g.contrapposto_interpretation as string,
      en: g.gesture_energy as number,
      ctr_dx: ((g.centroid as RawDoc | undefined)?.dx as number | undefined) ?? 0,
      ctr_dy: ((g.centroid as RawDoc | undefined)?.dy as number | undefined) ?? 0,
    };
  }

  // Volumetric
  let vol: NormalizedVolumetric | null = null;
  if (isV4 && raw.volumetric_estimates) {
    const v = raw.volumetric_estimates as RawDoc;
    vol = {
      cyl: (v.cylindrical as RawDoc | undefined)?.volume_hu3 as number | undefined,
      ell: (v.ellipsoidal as RawDoc | undefined)?.volume_hu3 as number | undefined,
      pap: (v.pappus as RawDoc | undefined)?.volume_hu3 as number | undefined,
    };
  }

  // Convex hull
  let hull: NormalizedHull | null = null;
  if (isV4 && raw.convex_hull) {
    const h = raw.convex_hull as RawDoc;
    hull = {
      sol: h.solidity as number,
      ha: h.hull_area_hu2 as number,
      sa: h.silhouette_area_hu2 as number,
      na: h.negative_space_area_hu2 as number,
    };
  }

  // Biomechanics
  let bio: NormalizedBiomechanics | null = null;
  if (isV4 && raw.biomechanics) {
    const b = raw.biomechanics as RawDoc;
    bio = {
      hcm: b.canonical_height_cm as number,
      sc: b.scale_cm_per_hu as number,
      com_dy: (b.whole_body_com as RawDoc | undefined)?.dy as number | undefined,
      com_frac: (b.whole_body_com as RawDoc | undefined)?.dy_fraction as number | undefined,
    };
  }

  // Medial axis
  let med: NormalizedMedialSample[] = [];
  if (isV4 && (raw.medial_axis as RawDoc | undefined)?.main_axis) {
    const samples = ((raw.medial_axis as RawDoc).main_axis as RawDoc)
      .samples as RawDoc[] | undefined;
    if (samples) {
      med = samples
        .filter((_, i) => i % 4 === 0)
        .map((p) => ({
          dy: p.dy as number,
          r: p.inscribed_radius as number,
        }));
    }
  }

  // Interior holes from multi-span scanline measurements.
  const holes: HoleLevel[][] = [];
  if (isV4 && (raw.measurements as RawDoc | undefined)?.scanlines) {
    const scanlines = (raw.measurements as RawDoc).scanlines as Record<string, unknown>;
    const multiSpanLevels: HoleLevel[] = [];
    for (const [dk, entry] of Object.entries(scanlines)) {
      let spans: RawDoc[] | null = null;
      if (
        typeof entry === "object" &&
        entry !== null &&
        !Array.isArray(entry) &&
        (entry as RawDoc).topology_detail
      ) {
        spans = (entry as RawDoc).topology_detail as RawDoc[];
      } else if (Array.isArray(entry) && entry.length >= 2) {
        spans = entry as RawDoc[];
      }
      const dy = parseFloat(dk);
      if (
        spans &&
        spans.length === 2 &&
        dy > 4.0 &&
        (spans[0]!.inner_dx as number) > 0 &&
        (spans[1]!.outer_dx as number) < 0
      ) {
        multiSpanLevels.push({
          dy,
          gapLeft: spans[1]!.outer_dx as number,
          gapRight: spans[0]!.inner_dx as number,
        });
      }
    }
    multiSpanLevels.sort((a, b) => a.dy - b.dy);

    if (multiSpanLevels.length >= 2) {
      let group = [multiSpanLevels[0]!];
      for (let i = 1; i < multiSpanLevels.length; i++) {
        if (multiSpanLevels[i]!.dy - multiSpanLevels[i - 1]!.dy <= 0.25) {
          group.push(multiSpanLevels[i]!);
        } else {
          if (group.length >= 2) holes.push(group);
          group = [multiSpanLevels[i]!];
        }
      }
      if (group.length >= 2) holes.push(group);
    }
  }

  const surface: string = (cls.surface as RawDoc | undefined)?.label as string ?? "unknown";
  const gender: string = (cls.gender as RawDoc | undefined)?.label as string ?? "unknown";
  const view: string = (cls.view as RawDoc | undefined)?.label as string ?? "unknown";

  return {
    version,
    isV4,
    mirrored,
    contour,
    strokes,
    landmarks,
    pr,
    br,
    ar,
    wp,
    sd,
    sc,
    gl,
    vol,
    hull,
    bio,
    med,
    holes,
    surface,
    gender,
    view,
  };
}
