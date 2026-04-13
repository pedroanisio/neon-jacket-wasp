/**
 * Normalize a raw v4 silhouette JSON document into the compact format
 * consumed by all frontend renderers.
 *
 * This is the single normalization layer — the canonical contract between
 * the v4 JSON schema and the frontend rendering components.
 */

export default function normalize(raw) {
  const meta = raw.meta || {};
  const cls = meta.classification || {};
  const version = meta.schema_version || "unknown";
  const isV4 = !!raw.body_regions;

  // Contour mode: 180° (mirrored) or 360° (full).
  const contourRaw = raw.contour || [];
  const mirrored = meta.mirror?.applied !== false;

  let splitIdx = 0;
  for (let i = 1; i < contourRaw.length; i++) {
    if (contourRaw[i][1] > contourRaw[splitIdx][1]) splitIdx = i;
  }

  let contour;
  if (mirrored) {
    const rightContour = contourRaw.slice(0, splitIdx + 1);
    contour = rightContour.filter((_,i) => i % 2 === 0 || i === rightContour.length - 1)
      .map(([dx,dy]) => [Math.round(dx*1000)/1000, Math.round(dy*1000)/1000]);
  } else {
    contour = contourRaw.filter((_,i) => i % 2 === 0 || i === contourRaw.length - 1)
      .map(([dx,dy]) => [Math.round(dx*1000)/1000, Math.round(dy*1000)/1000]);
  }

  // Strokes
  const strokes = (raw.strokes || []).map(s => {
    let pts = s.points || [];
    if (pts.length > 20) pts = pts.filter((_,i) => i % 2 === 0).concat([pts[pts.length-1]]);
    return { r: s.region, p: pts.map(([dx,dy]) => [Math.round(dx*1000)/1000, Math.round(dy*1000)/1000]) };
  });

  // Landmarks
  const landmarks = (raw.landmarks || []).map(l => ({
    n: l.name, d: l.description || "", dy: l.dy, dx: l.dx
  }));

  // Proportions
  const prop = raw.proportion || {};
  const pr = {
    hc: prop.head_count_total || prop.head_count_anatomical || 0,
    sr: prop.segment_ratios || {},
    wr: prop.width_ratios || {},
    comp: {},
    canons: []
  };
  if (prop.composite_ratios) {
    pr.comp = Object.fromEntries(Object.entries(prop.composite_ratios).filter(([k]) => k !== "note").map(([k,v]) => [k, typeof v === "number" ? Math.round(v*10000)/10000 : v]));
  }
  if (prop.canonical_comparisons) {
    pr.canons = prop.canonical_comparisons.map(c => ({ sys: c.system, heads: c.total_heads }));
  }

  // Body regions
  const br = isV4 ? (raw.body_regions.regions || []).map(r => ({ n: r.name, s: r.dy_start, e: r.dy_end })) : [];

  // Area profile
  const ar = isV4 && raw.area_profile ? (raw.area_profile.per_region || []).map(r => ({
    n: r.name, h: r.height_hu, a: r.area_hu2, f: r.area_fraction, mw: r.mean_full_width_hu
  })) : [];

  // Width profile
  const wp = isV4 && raw.width_profile ? (raw.width_profile.samples || []).filter((_,i) => i % 2 === 0).map(s => ({
    dy: s.dy, w: s.full_width
  })) : [];

  // Style deviation
  let sd = null;
  if (isV4 && raw.style_deviation) {
    const sdd = raw.style_deviation;
    sd = {
      canon: sdd.canon || "", fh: sdd.figure_head_count, ch: sdd.canon_head_count,
      l2: sdd.l2_stylisation_distance,
      pos: (sdd.position_deviations || []).map(p => ({ n: p.landmark, m: p.measured_fraction, c: p.canon_fraction, d: p.deviation })),
      wid: (sdd.width_deviations || []).map(w => ({ n: w.feature, m: w.measured, c: w.canon, d: w.deviation }))
    };
  }

  // Shape complexity
  let sc = null;
  if (isV4 && raw.shape_complexity) {
    sc = Object.fromEntries(Object.entries(raw.shape_complexity).filter(([k]) => !["note","reference"].includes(k)));
  }

  // Gesture line
  let gl = null;
  if (isV4 && raw.gesture_line) {
    const g = raw.gesture_line;
    gl = {
      lean: g.lean_angle_deg, li: g.lean_interpretation,
      cp: g.contrapposto_score, ci: g.contrapposto_interpretation,
      en: g.gesture_energy,
      ctr_dx: g.centroid?.dx || 0, ctr_dy: g.centroid?.dy || 0
    };
  }

  // Volumetric
  let vol = null;
  if (isV4 && raw.volumetric_estimates) {
    const v = raw.volumetric_estimates;
    vol = {
      cyl: v.cylindrical?.volume_hu3, ell: v.ellipsoidal?.volume_hu3, pap: v.pappus?.volume_hu3
    };
  }

  // Convex hull
  let hull = null;
  if (isV4 && raw.convex_hull) {
    const h = raw.convex_hull;
    hull = { sol: h.solidity, ha: h.hull_area_hu2, sa: h.silhouette_area_hu2, na: h.negative_space_area_hu2 };
  }

  // Biomechanics
  let bio = null;
  if (isV4 && raw.biomechanics) {
    const b = raw.biomechanics;
    bio = {
      hcm: b.canonical_height_cm, sc: b.scale_cm_per_hu,
      com_dy: b.whole_body_com?.dy, com_frac: b.whole_body_com?.dy_fraction
    };
  }

  // Medial axis
  let med = [];
  if (isV4 && raw.medial_axis?.main_axis?.samples) {
    med = raw.medial_axis.main_axis.samples.filter((_,i) => i % 4 === 0).map(p => ({
      dy: p.dy, r: p.inscribed_radius
    }));
  }

  // Interior holes from multi-span scanline measurements.
  const holes = [];
  if (isV4 && raw.measurements?.scanlines) {
    const scanlines = raw.measurements.scanlines;
    const multiSpanLevels = [];
    for (const [dk, entry] of Object.entries(scanlines)) {
      let spans = null;
      if (typeof entry === "object" && !Array.isArray(entry) && entry.topology_detail) {
        spans = entry.topology_detail;
      } else if (Array.isArray(entry) && entry.length >= 2) {
        spans = entry;
      }
      const dy = parseFloat(dk);
      if (spans && spans.length === 2 && dy > 4.0 &&
          spans[0].inner_dx > 0 && spans[1].outer_dx < 0) {
        multiSpanLevels.push({
          dy: parseFloat(dk),
          gapLeft: spans[1].outer_dx,
          gapRight: spans[0].inner_dx,
        });
      }
    }
    multiSpanLevels.sort((a, b) => a.dy - b.dy);

    if (multiSpanLevels.length >= 2) {
      let group = [multiSpanLevels[0]];
      for (let i = 1; i < multiSpanLevels.length; i++) {
        if (multiSpanLevels[i].dy - multiSpanLevels[i - 1].dy <= 0.25) {
          group.push(multiSpanLevels[i]);
        } else {
          if (group.length >= 2) holes.push(group);
          group = [multiSpanLevels[i]];
        }
      }
      if (group.length >= 2) holes.push(group);
    }
  }

  const surface = cls.surface?.label || "unknown";
  const gender = cls.gender?.label || "unknown";
  const view = cls.view?.label || "unknown";

  return { version, isV4, mirrored, contour, strokes, landmarks, pr, br, ar, wp, sd, sc, gl, vol, hull, bio, med, holes, surface, gender, view };
}
