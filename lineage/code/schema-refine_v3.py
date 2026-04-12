"""
refine_v3.py — v3.0.0 → v3.1.0 refinement pass.

Fixes:
  1. Landmark ordering anomalies (bust_peak above armpit_valley but wider)
  2. Inflection points filtered by |κ| significance threshold
  3. Stroke semantics improved with region-aware + multi-feature classification

Additions:
  4. Width profile — clean 1D signal: dx(dy) sampled at 0.01 HU, with derivatives
  5. Area profile — cumulative and per-region silhouette area
  6. Contour normals — outward-facing unit normals at each contour point
  7. Landmark validation — cross-check ordering, flag anomalies
  8. Aspect ratio per body region
  9. Compact shape vector for ML consumption
"""

import json
import numpy as np
from scipy.signal import savgol_filter
from scipy.interpolate import CubicSpline
import warnings
warnings.filterwarnings("ignore")

with open("/home/claude/v3.json") as f:
    data = json.load(f)

contour = np.array(data["contour"])
dx_arr = contour[:, 0]
dy_arr = contour[:, 1]
RIGHT_END = 727

right_dx = dx_arr[:RIGHT_END]
right_dy = dy_arr[:RIGHT_END]

# Build interpolator from original (unsorted) right-side contour
sort_idx = np.argsort(right_dy)
right_dy_sorted = right_dy[sort_idx]
right_dx_sorted = right_dx[sort_idx]
unique_dy, inv = np.unique(right_dy_sorted, return_inverse=True)
unique_dx = np.zeros_like(unique_dy)
for i in range(len(unique_dy)):
    unique_dx[i] = right_dx_sorted[inv == i].mean()
contour_interp = CubicSpline(unique_dy, unique_dx, extrapolate=False)

def width_at(dy_val):
    v = contour_interp(dy_val)
    return float(v) if v is not None and np.isfinite(v) else float("nan")

# ─── Key dy values ───────────────────────────────────────────────
lm_map = {lm["name"]: lm for lm in data["landmarks"]}
crown_dy = lm_map["crown"]["dy"]
sole_dy = lm_map["sole"]["dy"]
neck_dy = lm_map["neck_valley"]["dy"]
shoulder_dy = lm_map["shoulder_peak"]["dy"]
waist_dy = lm_map["waist_valley"]["dy"]
hip_dy = lm_map["hip_peak"]["dy"]
knee_dy = lm_map["knee_valley"]["dy"]
ankle_dy = lm_map["ankle_valley"]["dy"]

# ═══════════════════════════════════════════════════════════════
# 1. LANDMARK VALIDATION & FIX
# ═══════════════════════════════════════════════════════════════
# Check for anatomical ordering anomalies
validation_notes = []

# bust_peak should be wider than armpit_valley
if "bust_peak" in lm_map and "armpit_valley" in lm_map:
    bp = lm_map["bust_peak"]
    av = lm_map["armpit_valley"]
    if bp["dx"] < av["dx"]:
        # On armored figure, "bust" may actually be narrower than the
        # arm-torso junction. Relabel to be honest.
        for lm in data["landmarks"]:
            if lm["name"] == "bust_peak":
                lm["name"] = "chest_inflection"
                lm["description"] = (
                    "Local width maximum between shoulder slope and waist. "
                    "On this armored figure, narrower than the arm-torso junction below — "
                    "not a true anatomical bust peak but a chest plate contour feature."
                )
                lm["note"] = f"Renamed from bust_peak: dx={bp['dx']:.4f} < armpit dx={av['dx']:.4f}"
                validation_notes.append(
                    f"bust_peak renamed to chest_inflection: dx={bp['dx']:.4f} is narrower "
                    f"than armpit_valley dx={av['dx']:.4f}, inconsistent with anatomical bust"
                )
                break

# crotch_valley should be above mid_thigh (lower dy)
if "crotch_valley" in lm_map and "mid_thigh" in lm_map:
    cr = lm_map["crotch_valley"]
    mt = lm_map["mid_thigh"]
    if cr["dy"] > mt["dy"]:
        for lm in data["landmarks"]:
            if lm["name"] == "crotch_valley":
                lm["name"] = "thigh_narrowing"
                lm["description"] = (
                    "Local width minimum in the upper leg. Below the geometric mid-thigh — "
                    "on this armored figure, likely the lower edge of thigh armor plates."
                )
                lm["note"] = f"Renamed from crotch_valley: dy={cr['dy']:.4f} is below mid_thigh dy={mt['dy']:.4f}"
                validation_notes.append(
                    f"crotch_valley renamed to thigh_narrowing: dy={cr['dy']:.4f} "
                    f"is below mid_thigh dy={mt['dy']:.4f}"
                )
                break

# Rebuild lm_map after renames
lm_map = {lm["name"]: lm for lm in data["landmarks"]}

# Add validation report
data["meta"]["landmark_validation"] = {
    "anomalies_detected": len(validation_notes),
    "corrections_applied": validation_notes,
    "note": (
        "Landmarks derived from contour extrema may not match anatomical expectations "
        "on armored/stylized figures. Anomalous labels are renamed to describe the actual "
        "geometric feature rather than the assumed anatomy."
    )
}

print(f"Landmark validation: {len(validation_notes)} corrections applied")

# ═══════════════════════════════════════════════════════════════
# 2. FILTER INFLECTION POINTS BY SIGNIFICANCE
# ═══════════════════════════════════════════════════════════════
if "curvature" in data and "inflections" in data["curvature"]:
    raw_inflections = data["curvature"]["inflections"]["points"]
    # Keep only inflections where |κ_before - κ_after| > threshold
    threshold = 0.02
    significant = []
    for inf in raw_inflections:
        delta_k = abs(inf["kappa_before"] - inf["kappa_after"])
        if delta_k > threshold:
            inf["delta_kappa"] = round(delta_k, 6)
            significant.append(inf)

    data["curvature"]["inflections"]["raw_count"] = len(raw_inflections)
    data["curvature"]["inflections"]["significance_threshold"] = threshold
    data["curvature"]["inflections"]["points"] = significant
    data["curvature"]["inflections"]["count"] = len(significant)
    data["curvature"]["inflections"]["note"] = (
        f"Filtered from {len(raw_inflections)} raw sign-changes to {len(significant)} "
        f"significant inflections (|Δκ| > {threshold}). Raw count reflects contour noise; "
        f"significant count reflects actual convex↔concave transitions."
    )
    print(f"Inflections: {len(raw_inflections)} raw → {len(significant)} significant (threshold={threshold})")

# ═══════════════════════════════════════════════════════════════
# 3. IMPROVED STROKE SEMANTICS
# ═══════════════════════════════════════════════════════════════
# Multi-feature classification with region-aware rules
for stroke in data["strokes"]:
    region = stroke.get("region", "unknown")
    arc = stroke.get("arc_length_hu", 0)
    chord = stroke.get("chord_length_hu", 0)
    sin = stroke.get("sinuosity", 1.0) or 1.0
    orient = stroke.get("orientation_deg")
    n_pts = stroke.get("n_points", 0)
    mean_k = stroke.get("mean_curvature", 0) or 0
    max_k = stroke.get("max_abs_curvature", 0) or 0
    bbox = stroke.get("bbox", {})
    bbox_w = bbox.get("dx_max", 0) - bbox.get("dx_min", 0)
    bbox_h = bbox.get("dy_max", 0) - bbox.get("dy_min", 0)
    bbox_aspect = bbox_h / bbox_w if bbox_w > 1e-4 else float("inf")

    # Classification logic
    stype = "contour_detail"
    confidence = 0.35

    # Tiny marks: rivets, bolts, small detail
    if arc < 0.06:
        stype = "detail_mark"
        confidence = 0.5

    # Long, straight, vertical → zipper line, center seam, panel division
    elif sin < 1.08 and bbox_aspect > 3.0 and orient is not None and abs(abs(orient) - 90) < 20:
        stype = "vertical_division"
        confidence = 0.55

    # Long, straight, horizontal → belt, band, plate edge
    elif sin < 1.08 and bbox_aspect < 0.3 and orient is not None and abs(orient) < 25:
        stype = "horizontal_band"
        confidence = 0.55

    # Long and straight (general) → panel line / armor edge
    elif sin < 1.08 and arc > 0.2:
        stype = "panel_edge"
        confidence = 0.5

    # Short and straight → seam, stitch line, minor edge
    elif sin < 1.12 and arc < 0.2:
        stype = "seam"
        confidence = 0.45

    # High curvature, small → joint articulation detail, rivet ring
    elif max_k > 2.0 and arc < 0.15:
        stype = "articulation_detail"
        confidence = 0.4

    # Region-specific: head strokes with moderate curvature → visor/helmet detail
    elif region == "head" and arc > 0.1:
        stype = "helmet_detail"
        confidence = 0.45

    # Region-specific: feet strokes → boot/sole detail
    elif region == "feet":
        if sin > 1.3:
            stype = "boot_ornament"
            confidence = 0.4
        else:
            stype = "boot_structure"
            confidence = 0.45

    # Moderate sinuosity, longer strokes → contour reinforcement or decorative line
    elif sin > 1.3 and arc > 0.2:
        stype = "decorative_line"
        confidence = 0.4

    # Highly sinuous → ornamental curve
    elif sin > 1.8:
        stype = "ornamental_curve"
        confidence = 0.4

    else:
        stype = "surface_detail"
        confidence = 0.3

    stroke["semantic_type"] = stype
    stroke["semantic_confidence"] = confidence

# Count distribution
from collections import Counter
type_counts = Counter(s["semantic_type"] for s in data["strokes"])
print(f"Stroke semantics (v3.1): {dict(type_counts)}")

# ═══════════════════════════════════════════════════════════════
# 4. WIDTH PROFILE — clean 1D signal at 0.01 HU
# ═══════════════════════════════════════════════════════════════
dy_dense = np.arange(crown_dy + 0.01, sole_dy, 0.01)
dx_dense = np.array([width_at(d) for d in dy_dense])
valid_mask = np.isfinite(dx_dense)
dy_valid = dy_dense[valid_mask]
dx_valid = dx_dense[valid_mask]

# Derivatives
dx_d1 = np.gradient(dx_valid, dy_valid)
dx_d2 = np.gradient(dx_d1, dy_valid)

# Subsample for storage (every 5th point → 0.05 HU effective)
step = 5
width_profile_samples = []
for i in range(0, len(dy_valid), step):
    entry = {
        "dy": round(float(dy_valid[i]), 4),
        "dx": round(float(dx_valid[i]), 4),
        "full_width": round(float(2 * dx_valid[i]), 4),
    }
    if i < len(dx_d1):
        entry["slope"] = round(float(dx_d1[i]), 4)
    if i < len(dx_d2):
        entry["curvature"] = round(float(dx_d2[i]), 4)
    width_profile_samples.append(entry)

# Find all local extrema in the full-resolution profile
width_maxima = []
width_minima = []
for i in range(1, len(dx_valid) - 1):
    if dx_valid[i] > dx_valid[i-1] and dx_valid[i] > dx_valid[i+1]:
        width_maxima.append({
            "dy": round(float(dy_valid[i]), 4),
            "dx": round(float(dx_valid[i]), 4),
            "full_width": round(float(2 * dx_valid[i]), 4)
        })
    if dx_valid[i] < dx_valid[i-1] and dx_valid[i] < dx_valid[i+1]:
        width_minima.append({
            "dy": round(float(dy_valid[i]), 4),
            "dx": round(float(dx_valid[i]), 4),
            "full_width": round(float(2 * dx_valid[i]), 4)
        })

# Filter out noise: only keep extrema with prominence > 0.02 HU
def filter_prominent(extrema, min_prominence=0.02):
    """Keep only extrema whose dx differs from both neighbors' extrema by > min_prominence."""
    if len(extrema) < 2:
        return extrema
    result = []
    for i, e in enumerate(extrema):
        # Check prominence against surrounding extrema
        prev_dx = extrema[i-1]["dx"] if i > 0 else dx_valid[0]
        next_dx = extrema[i+1]["dx"] if i < len(extrema)-1 else dx_valid[-1]
        prom = min(abs(e["dx"] - prev_dx), abs(e["dx"] - next_dx))
        if prom >= min_prominence:
            e_copy = dict(e)
            e_copy["prominence"] = round(prom, 4)
            result.append(e_copy)
    return result

width_maxima_sig = filter_prominent(width_maxima)
width_minima_sig = filter_prominent(width_minima)

data["width_profile"] = {
    "note": (
        "Width profile: right-side dx as a function of dy, sampled at 0.05 HU from the cubic-spline "
        "interpolation of the 727-point right contour. slope = d(dx)/d(dy) — positive means widening "
        "downward. curvature = d²(dx)/d(dy)² — positive = convex (widening accelerates). "
        "Extrema are filtered by prominence > 0.02 HU to suppress noise."
    ),
    "resolution_hu": 0.05,
    "sample_count": len(width_profile_samples),
    "samples": width_profile_samples,
    "extrema": {
        "maxima": {
            "count": len(width_maxima_sig),
            "points": width_maxima_sig,
            "note": "Local width peaks (bumps) — shoulders, hips, calves, armor plates"
        },
        "minima": {
            "count": len(width_minima_sig),
            "points": width_minima_sig,
            "note": "Local width valleys — neck, waist, knee, ankle"
        }
    },
    "statistics": {
        "mean_dx": round(float(dx_valid.mean()), 4),
        "std_dx": round(float(dx_valid.std()), 4),
        "max_dx": round(float(dx_valid.max()), 4),
        "max_dx_dy": round(float(dy_valid[dx_valid.argmax()]), 4),
        "min_dx": round(float(dx_valid.min()), 4),
        "min_dx_dy": round(float(dy_valid[dx_valid.argmin()]), 4),
        "mean_full_width": round(float(2 * dx_valid.mean()), 4)
    }
}

print(f"Width profile: {len(width_profile_samples)} samples, {len(width_maxima_sig)} sig. maxima, {len(width_minima_sig)} sig. minima")

# ═══════════════════════════════════════════════════════════════
# 5. AREA PROFILE — cumulative and per-region silhouette area
# ═══════════════════════════════════════════════════════════════
# Silhouette area up to each dy level (integral of 2*dx w.r.t. dy)
# Using trapezoidal integration on the dense profile
_trapz = getattr(np, 'trapezoid', getattr(np, 'trapz', None))
total_area = float(_trapz(2 * dx_valid, dy_valid))

# Per-region area
region_areas = []
for region in data["body_regions"]["regions"]:
    dy_lo = region["dy_start"]
    dy_hi = region["dy_end"]
    mask = (dy_valid >= dy_lo) & (dy_valid <= dy_hi)
    if mask.sum() > 1:
        region_area = float(_trapz(2 * dx_valid[mask], dy_valid[mask]))
        region_mean_width = float(2 * dx_valid[mask].mean())
        region_max_width = float(2 * dx_valid[mask].max())
        region_height = dy_hi - dy_lo
    else:
        region_area = 0.0
        region_mean_width = 0.0
        region_max_width = 0.0
        region_height = dy_hi - dy_lo

    region_areas.append({
        "name": region["name"],
        "dy_range": [round(dy_lo, 4), round(dy_hi, 4)],
        "height_hu": round(region_height, 4),
        "area_hu2": round(region_area, 4),
        "area_fraction": round(region_area / total_area, 4) if total_area > 0 else 0,
        "mean_full_width_hu": round(region_mean_width, 4),
        "max_full_width_hu": round(region_max_width, 4),
        "aspect_ratio": round(region_height / region_mean_width, 4) if region_mean_width > 0 else None
    })

# Cumulative area at landmark positions
cumulative_at_landmarks = []
for lm in data["landmarks"]:
    lm_dy = lm["dy"]
    mask = dy_valid <= lm_dy
    if mask.sum() > 1:
        cum_area = float(_trapz(2 * dx_valid[mask], dy_valid[mask]))
    else:
        cum_area = 0.0
    cumulative_at_landmarks.append({
        "landmark": lm["name"],
        "dy": lm["dy"],
        "cumulative_area_hu2": round(cum_area, 4),
        "fraction_of_total": round(cum_area / total_area, 4) if total_area > 0 else 0
    })

data["area_profile"] = {
    "note": (
        "Silhouette area computed as the integral of bilateral width (2·dx) with respect to dy. "
        "Units are HU². per_region shows area contribution of each body zone. "
        "cumulative_at_landmarks shows how area accumulates from crown downward."
    ),
    "total_area_hu2": round(total_area, 4),
    "per_region": region_areas,
    "cumulative_at_landmarks": cumulative_at_landmarks
}

print(f"Area profile: total={total_area:.4f} HU², {len(region_areas)} regions")

# ═══════════════════════════════════════════════════════════════
# 6. CONTOUR NORMALS
# ═══════════════════════════════════════════════════════════════
# Outward-facing unit normals at each right-side contour point
# For a curve (x(t), y(t)), the outward normal on the right side is (+dy/ds, -dx/ds)
# where s is arc length

pts_right = np.column_stack([right_dx, right_dy])  # original order
tangent = np.zeros_like(pts_right)
for i in range(len(pts_right)):
    if i == 0:
        tangent[i] = pts_right[1] - pts_right[0]
    elif i == len(pts_right) - 1:
        tangent[i] = pts_right[-1] - pts_right[-2]
    else:
        tangent[i] = pts_right[i+1] - pts_right[i-1]

# Normalize tangent
tang_len = np.sqrt((tangent**2).sum(axis=1))
tang_len[tang_len < 1e-12] = 1e-12
tangent /= tang_len[:, None]

# Normal = rotate tangent 90° clockwise (outward for right-side contour)
normals = np.column_stack([tangent[:, 1], -tangent[:, 0]])

# Store subsampled (every 10th point for manageable size)
normal_step = 10
contour_normals = []
for i in range(0, len(pts_right), normal_step):
    contour_normals.append({
        "index": i,
        "dx": round(float(pts_right[i, 0]), 4),
        "dy": round(float(pts_right[i, 1]), 4),
        "nx": round(float(normals[i, 0]), 4),
        "ny": round(float(normals[i, 1]), 4)
    })

data["contour_normals"] = {
    "note": (
        "Outward-facing unit normal vectors along the right-side contour, "
        "subsampled every 10 points. Normal is computed as 90° clockwise rotation "
        "of the tangent vector. (nx, ny) points outward from the silhouette surface. "
        "Useful for shading, normal mapping, and offset curve generation."
    ),
    "sample_step": normal_step,
    "sample_count": len(contour_normals),
    "full_point_count": len(pts_right),
    "samples": contour_normals
}

print(f"Contour normals: {len(contour_normals)} samples (every {normal_step}th point)")

# ═══════════════════════════════════════════════════════════════
# 7. COMPACT SHAPE VECTOR FOR ML
# ═══════════════════════════════════════════════════════════════
# A fixed-dimension feature vector summarizing the figure shape
# Useful for nearest-neighbor search, clustering, classification

# Components:
# - Width at 16 evenly-spaced dy levels (normalized by max width)
# - 4 key ratios
# - Head count
# Total dimension: 21

n_width_samples = 16
dy_sample_points = np.linspace(crown_dy + 0.1, sole_dy - 0.1, n_width_samples)
max_width = max(width_at(d) for d in dy_sample_points if np.isfinite(width_at(d)))
width_vector = []
for d in dy_sample_points:
    w = width_at(d)
    width_vector.append(round(float(w / max_width), 4) if np.isfinite(w) and max_width > 0 else 0.0)

# Ratios
prop_data = data["proportion"]
composite = prop_data.get("composite_ratios", {})

shape_vector = {
    "note": (
        "Fixed-dimension shape descriptor for ML. 16 width samples (normalized by max width) "
        "at evenly-spaced dy levels, plus 4 key ratios and head count. "
        "Dimension = 21. All values in [0, ~2] range."
    ),
    "dimension": 21,
    "components": [
        "width_0..width_15: normalized bilateral width at 16 dy levels",
        "shoulder_hip_ratio",
        "waist_hip_ratio",
        "upper_lower_body_ratio",
        "torso_leg_ratio",
        "head_count"
    ],
    "vector": (
        width_vector +
        [
            composite.get("shoulder_to_hip_width", 0),
            composite.get("waist_to_hip_width", 0),
            composite.get("upper_to_lower_body", 0),
            composite.get("torso_to_leg", 0),
            prop_data.get("head_count_total", 0)
        ]
    ),
    "dy_sample_points": [round(float(d), 4) for d in dy_sample_points],
    "normalization": {
        "width_max_dx": round(max_width, 4),
        "method": "divide by max right-side dx across sample points"
    }
}

data["shape_vector"] = shape_vector

# ═══════════════════════════════════════════════════════════════
# 8. ENRICH BODY REGIONS WITH ASPECT RATIO + STROKE COUNTS
# ═══════════════════════════════════════════════════════════════
for region in data["body_regions"]["regions"]:
    dy_lo = region["dy_start"]
    dy_hi = region["dy_end"]

    # Count strokes in this region
    stroke_count = 0
    stroke_ids = []
    for s in data["strokes"]:
        bbox = s.get("bbox", {})
        s_dy_min = bbox.get("dy_min", 0)
        s_dy_max = bbox.get("dy_max", 0)
        # Stroke overlaps region if ranges intersect
        if s_dy_min < dy_hi and s_dy_max > dy_lo:
            stroke_count += 1
            stroke_ids.append(s["id"])
    region["stroke_count"] = stroke_count
    region["stroke_ids"] = stroke_ids

    # Landmark count in this region
    lm_in_region = [lm["name"] for lm in data["landmarks"]
                    if dy_lo <= lm["dy"] < dy_hi]
    region["landmarks"] = lm_in_region

print("Body regions: enriched with stroke counts and landmark lists")

# ═══════════════════════════════════════════════════════════════
# 9. SCHEMA VERSION + SECTION INVENTORY UPDATE
# ═══════════════════════════════════════════════════════════════
data["meta"]["schema_version"] = "3.1.0"

data["meta"]["sections"]["sections"] = [
    "meta", "contour", "landmarks", "midline", "strokes",
    "symmetry", "measurements", "parametric", "proportion",
    "curvature", "body_regions", "cross_section_topology",
    "fourier_descriptors", "width_profile", "area_profile",
    "contour_normals", "shape_vector", "candidates"
]
data["meta"]["sections"]["new_in_v3.1"] = [
    "width_profile — clean 1D dx(dy) signal with slope, curvature, filtered extrema, statistics",
    "area_profile — total and per-region silhouette area (HU²), cumulative at landmarks",
    "contour_normals — outward unit normals along right-side contour (subsampled)",
    "shape_vector — 21-dimensional fixed-size shape descriptor for ML consumption",
    "meta.landmark_validation — anomaly detection and correction report"
]
data["meta"]["sections"]["refined_in_v3.1"] = [
    "landmarks — anomalous labels renamed (bust_peak→chest_inflection, crotch_valley→thigh_narrowing)",
    "curvature.inflections — filtered by |Δκ| significance threshold",
    "strokes.semantic_type — improved multi-feature + region-aware classification",
    "body_regions — enriched with stroke_count, stroke_ids, landmarks per region"
]

# ─── Write ──────────────────────────────────────────────────────
output_path = "/home/claude/v3.json"
with open(output_path, "w") as f:
    json.dump(data, f, indent=2)

import os
print(f"\nOutput: {output_path} ({os.path.getsize(output_path)/1024:.1f} KB)")
print("Done.")
