"""
enrich.py — Upgrade v2.json → v3.json with substantially more detail.

Additions / improvements:
  1. Landmarks:  9 → ~22+ anatomically-derived landmarks
  2. Scanlines:  0.1 HU step → 0.05 HU step, add width_derivative and curvature
  3. Symmetry:   8 integer samples → dense (matches scanline dy set)
  4. Curvature:  NEW section — discrete curvature along contour, inflection points
  5. Proportion:  add canonical comparisons (Loomis 8-head, heroic), composite ratios
  6. Strokes:    add geometric features (arc_length, mean_curvature, orientation, semantic type estimate)
  7. Parametric: add per-segment curvature extrema and inflection dy values
  8. Body regions: NEW — dy ranges for each anatomical zone
  9. Cross-section topology: NEW — number of contour pairs at each dy
 10. Fourier descriptors: NEW — low-order shape signature
 11. Meta:       add contour quality metrics, smoothness
"""

import json
import numpy as np
from scipy.interpolate import CubicSpline, UnivariateSpline
from scipy.signal import savgol_filter
import warnings
warnings.filterwarnings("ignore")

# ─── Load ───────────────────────────────────────────────────────
with open("/home/claude/v2.json") as f:
    data = json.load(f)

contour = np.array(data["contour"])  # shape (1200, 2): [dx, dy]
dx_arr = contour[:, 0]
dy_arr = contour[:, 1]

# The contour is a closed loop: right side indices 0..726, left (mirrored) 727..1199
RIGHT_END = 727  # from meta.mirror description
right_dx = dx_arr[:RIGHT_END]
right_dy = dy_arr[:RIGHT_END]

# Sort right side by dy for interpolation
sort_idx = np.argsort(right_dy)
right_dy_sorted = right_dy[sort_idx]
right_dx_sorted = right_dx[sort_idx]

# ─── Helper: interpolate contour dx at arbitrary dy ─────────────
# Remove duplicate dy values by averaging dx
unique_dy, inv = np.unique(right_dy_sorted, return_inverse=True)
unique_dx = np.zeros_like(unique_dy)
for i in range(len(unique_dy)):
    unique_dx[i] = right_dx_sorted[inv == i].mean()

contour_interp = CubicSpline(unique_dy, unique_dx, extrapolate=False)

def width_at(dy_val):
    """Return right-side dx at a given dy (or NaN if out of range)."""
    v = contour_interp(dy_val)
    return float(v) if v is not None and np.isfinite(v) else float("nan")

# ─── 1. Enrich Landmarks ────────────────────────────────────────
existing_lm = {lm["name"]: lm for lm in data["landmarks"]}

# Derive additional landmarks from contour shape analysis
# We'll find local extrema in dx(dy) that correspond to anatomical features

# Smooth dx for finding extrema
window = min(51, len(unique_dx) - 2)
if window % 2 == 0:
    window -= 1
if window >= 5:
    dx_smooth = savgol_filter(unique_dx, window, 3)
else:
    dx_smooth = unique_dx.copy()

dx_deriv = np.gradient(dx_smooth, unique_dy)
dx_deriv2 = np.gradient(dx_deriv, unique_dy)

# Find all local maxima and minima in the smoothed profile
local_max_idx = []
local_min_idx = []
for i in range(1, len(dx_smooth) - 1):
    if dx_smooth[i] > dx_smooth[i-1] and dx_smooth[i] > dx_smooth[i+1]:
        local_max_idx.append(i)
    if dx_smooth[i] < dx_smooth[i-1] and dx_smooth[i] < dx_smooth[i+1]:
        local_min_idx.append(i)

# Find inflection points (sign change in second derivative)
inflection_idx = []
for i in range(1, len(dx_deriv2)):
    if dx_deriv2[i-1] * dx_deriv2[i] < 0:
        inflection_idx.append(i)

# Map extrema to anatomical landmarks by dy range heuristics
def find_extremum_in_range(indices, dy_lo, dy_hi, arr=dx_smooth):
    """Find the index in `indices` whose dy falls in [dy_lo, dy_hi]."""
    candidates = [(i, unique_dy[i], arr[i]) for i in indices
                  if dy_lo <= unique_dy[i] <= dy_hi]
    return candidates

# Known landmark dy values
crown_dy = existing_lm["crown"]["dy"]
sole_dy = existing_lm["sole"]["dy"]
neck_dy = existing_lm["neck_valley"]["dy"]
shoulder_dy = existing_lm["shoulder_peak"]["dy"]
waist_dy = existing_lm["waist_valley"]["dy"]
hip_dy = existing_lm["hip_peak"]["dy"]
knee_dy = existing_lm["knee_valley"]["dy"]
ankle_dy = existing_lm["ankle_valley"]["dy"]

# Additional landmarks to derive
new_landmarks = []

# Chin / jaw-line: local minimum between head_peak and neck_valley (dy ~0.9–1.1)
chin_candidates = find_extremum_in_range(local_min_idx, 0.8, neck_dy)
if chin_candidates:
    best = min(chin_candidates, key=lambda c: c[2])  # narrowest
    new_landmarks.append({
        "name": "chin",
        "description": "Jaw/chin narrowing before neck — local width minimum",
        "dy": round(float(unique_dy[best[0]]), 4),
        "dx": round(float(unique_dx[best[0]]), 4),
        "source": "derived_extremum",
        "confidence": 0.7,
        "note": "Approximated from contour profile; may correspond to helmet chin guard on armored figure"
    })

# Bust/chest peak: local max between shoulder and waist (dy ~1.6–2.2)
bust_candidates = find_extremum_in_range(local_max_idx, shoulder_dy + 0.1, waist_dy - 0.1)
if bust_candidates:
    best = max(bust_candidates, key=lambda c: c[2])  # widest
    new_landmarks.append({
        "name": "bust_peak",
        "description": "Widest torso width between shoulders and waist (chest/bust level)",
        "dy": round(float(unique_dy[best[0]]), 4),
        "dx": round(float(unique_dx[best[0]]), 4),
        "source": "derived_extremum",
        "confidence": 0.65,
        "note": "On armored figures, corresponds to chest plate maximum width"
    })

# Armpit valley: local min just below shoulder peak
armpit_candidates = find_extremum_in_range(local_min_idx, shoulder_dy, shoulder_dy + 0.8)
if armpit_candidates:
    best = min(armpit_candidates, key=lambda c: c[2])
    new_landmarks.append({
        "name": "armpit_valley",
        "description": "Narrowing just below shoulder peak (armpit/arm junction)",
        "dy": round(float(unique_dy[best[0]]), 4),
        "dx": round(float(unique_dx[best[0]]), 4),
        "source": "derived_extremum",
        "confidence": 0.6,
        "caveat": "arms_at_sides_occlusion"
    })

# Crotch: local minimum between hip peak and knee valley
crotch_candidates = find_extremum_in_range(local_min_idx, hip_dy + 0.1, knee_dy - 0.2)
if crotch_candidates:
    best = min(crotch_candidates, key=lambda c: c[2])
    new_landmarks.append({
        "name": "crotch_valley",
        "description": "Narrowest point between hips and knees (inseam level)",
        "dy": round(float(unique_dy[best[0]]), 4),
        "dx": round(float(unique_dx[best[0]]), 4),
        "source": "derived_extremum",
        "confidence": 0.7
    })

# Calf peak: local max between knee and ankle
calf_candidates = find_extremum_in_range(local_max_idx, knee_dy + 0.1, ankle_dy - 0.2)
if calf_candidates:
    best = max(calf_candidates, key=lambda c: c[2])
    new_landmarks.append({
        "name": "calf_peak",
        "description": "Widest point of calf/lower leg",
        "dy": round(float(unique_dy[best[0]]), 4),
        "dx": round(float(unique_dx[best[0]]), 4),
        "source": "derived_extremum",
        "confidence": 0.65
    })

# Mid-thigh: midpoint between hip_peak and knee_valley
mid_thigh_dy = (hip_dy + knee_dy) / 2
mid_thigh_dx = width_at(mid_thigh_dy)
if np.isfinite(mid_thigh_dx):
    new_landmarks.append({
        "name": "mid_thigh",
        "description": "Midpoint between hip peak and knee valley",
        "dy": round(mid_thigh_dy, 4),
        "dx": round(mid_thigh_dx, 4),
        "source": "interpolated_midpoint"
    })

# Mid-shin: midpoint between knee and ankle
mid_shin_dy = (knee_dy + ankle_dy) / 2
mid_shin_dx = width_at(mid_shin_dy)
if np.isfinite(mid_shin_dx):
    new_landmarks.append({
        "name": "mid_shin",
        "description": "Midpoint between knee valley and ankle valley",
        "dy": round(mid_shin_dy, 4),
        "dx": round(mid_shin_dx, 4),
        "source": "interpolated_midpoint"
    })

# Navel estimate: ~60% of shoulder-to-crotch distance below shoulders
# (classic anatomy: navel at 3 HU in 8-head figure)
navel_dy = shoulder_dy + 0.6 * (hip_dy - shoulder_dy)
navel_dx = width_at(navel_dy)
if np.isfinite(navel_dx):
    new_landmarks.append({
        "name": "navel_estimate",
        "description": "Estimated navel position (60% shoulder→hip, classic anatomical ratio)",
        "dy": round(navel_dy, 4),
        "dx": round(navel_dx, 4),
        "source": "anatomical_heuristic",
        "confidence": 0.5,
        "note": "Heuristic placement, not detected from contour features"
    })

# Trapezius peak: local max between neck and shoulder
trap_candidates = find_extremum_in_range(local_max_idx, neck_dy, shoulder_dy)
if not trap_candidates:
    # If no local max, just find the steepest rise point
    trap_dy = (neck_dy + shoulder_dy) / 2
    trap_dx = width_at(trap_dy)
    if np.isfinite(trap_dx):
        new_landmarks.append({
            "name": "trapezius_slope",
            "description": "Midpoint of neck-to-shoulder transition",
            "dy": round(trap_dy, 4),
            "dx": round(trap_dx, 4),
            "source": "interpolated_midpoint"
        })
else:
    best = max(trap_candidates, key=lambda c: c[2])
    new_landmarks.append({
        "name": "trapezius_peak",
        "description": "Local width maximum in neck-to-shoulder transition",
        "dy": round(float(unique_dy[best[0]]), 4),
        "dx": round(float(unique_dx[best[0]]), 4),
        "source": "derived_extremum",
        "confidence": 0.6
    })

# Boot top: look for width discontinuity between ankle and sole
boot_candidates = find_extremum_in_range(local_max_idx, ankle_dy, sole_dy)
if boot_candidates:
    best = max(boot_candidates, key=lambda c: c[2])
    new_landmarks.append({
        "name": "boot_top",
        "description": "Widest point of boot/footwear above sole",
        "dy": round(float(unique_dy[best[0]]), 4),
        "dx": round(float(unique_dx[best[0]]), 4),
        "source": "derived_extremum",
        "confidence": 0.55,
        "note": "Detected from local width maximum in foot region"
    })

# Merge new landmarks into existing
all_landmarks = data["landmarks"] + new_landmarks
# Sort by dy
all_landmarks.sort(key=lambda lm: lm["dy"])
data["landmarks"] = all_landmarks

print(f"Landmarks: {len(data['landmarks'])} (was 9, added {len(new_landmarks)})")

# ─── 2. Dense Scanlines at 0.05 HU + derivatives ────────────────
dy_min_scan = 0.05
dy_max_scan = float(np.floor(sole_dy * 20) / 20)
dense_dy_values = np.arange(dy_min_scan, dy_max_scan + 0.001, 0.05)

# Also compute width derivative for each scanline
new_scanlines = {}
prev_dx_val = None
for dy_val in dense_dy_values:
    dy_key = f"{dy_val:.2f}"
    dx_val = width_at(dy_val)
    if np.isfinite(dx_val):
        entry = {
            "right_dx": round(dx_val, 4),
            "left_dx": round(dx_val, 4),  # mirrored
            "full_width_hu": round(2 * dx_val, 4),
        }
        # Width derivative (change per HU)
        if prev_dx_val is not None and np.isfinite(prev_dx_val):
            entry["d_width_d_dy"] = round((dx_val - prev_dx_val) / 0.05, 4)
        else:
            entry["d_width_d_dy"] = None
        # Curvature (approximate from second derivative of width profile)
        dy_idx = np.searchsorted(unique_dy, dy_val)
        if 1 <= dy_idx < len(dx_deriv2):
            entry["curvature"] = round(float(dx_deriv2[dy_idx]), 4)
        else:
            entry["curvature"] = None

        new_scanlines[dy_key] = entry
        prev_dx_val = dx_val
    else:
        prev_dx_val = None

# Also preserve the original multi-pair scanlines where they exist
# (the original had topology info for multi-contour crossings)
orig_scanlines = data["measurements"]["scanlines"]
for dy_key, orig_entries in orig_scanlines.items():
    if dy_key in new_scanlines:
        # Merge: keep new dense data but add original topology info
        if isinstance(orig_entries, list) and len(orig_entries) > 1:
            new_scanlines[dy_key]["contour_pairs"] = len(orig_entries)
            new_scanlines[dy_key]["topology_detail"] = orig_entries
        elif isinstance(orig_entries, list) and len(orig_entries) == 1:
            new_scanlines[dy_key]["topology"] = orig_entries[0].get("topology", "unknown")
    else:
        # Keep original entry that fell on non-0.05 boundary
        new_scanlines[dy_key] = orig_entries

data["measurements"]["scanlines"] = dict(sorted(new_scanlines.items(), key=lambda x: float(x[0])))
data["measurements"]["note"] = (
    "Dense scanlines at 0.05 HU intervals. Each entry includes: "
    "right_dx/left_dx (half-width from midline), full_width_hu (total bilateral width), "
    "d_width_d_dy (first derivative of width w.r.t. dy — positive=widening downward), "
    "curvature (second derivative of width profile — positive=convex, negative=concave). "
    "Entries with contour_pairs > 1 indicate multiple contour intersections at that level "
    "(e.g., arms separated from torso). topology_detail preserves original pair data."
)
data["measurements"]["step_hu"] = 0.05
data["measurements"]["scanline_count"] = len(new_scanlines)

print(f"Scanlines: {len(new_scanlines)} (was 79)")

# ─── 3. Dense Symmetry ──────────────────────────────────────────
# Expand from 8 samples to matching scanline density
new_symmetry_samples = {}
for dy_val in np.arange(0.25, sole_dy, 0.25):
    dy_key = f"{dy_val:.2f}" if dy_val != int(dy_val) else f"{dy_val:.1f}"
    rdx = width_at(dy_val)
    if np.isfinite(rdx):
        # For true asymmetry we'd need both raw sides; since this is mirrored,
        # delta is 0 except where raw data differs. Preserve original where available.
        orig_key = f"{dy_val:.1f}"
        if orig_key in data["symmetry"]["samples"]:
            orig = data["symmetry"]["samples"][orig_key]
            new_symmetry_samples[orig_key] = orig
        else:
            new_symmetry_samples[dy_key] = {
                "right_dx": round(rdx, 4),
                "left_dx": round(rdx, 4),
                "delta": 0.0,
                "source": "interpolated_mirror"
            }

# Merge with originals
for k, v in data["symmetry"]["samples"].items():
    if k not in new_symmetry_samples:
        new_symmetry_samples[k] = v

data["symmetry"]["samples"] = dict(sorted(new_symmetry_samples.items(), key=lambda x: float(x[0])))
data["symmetry"]["sample_count"] = len(data["symmetry"]["samples"])
data["symmetry"]["note"] = (
    "Symmetry measured at 0.25 HU intervals. delta = |right_dx - left_dx|. "
    "Samples marked source='interpolated_mirror' are derived from the mirrored contour "
    "and thus have delta=0 by construction. Only samples from the original raw extraction "
    "(without 'source' field) capture true asymmetry. High delta at dy=1.0 is from ponytail."
)

print(f"Symmetry samples: {len(data['symmetry']['samples'])} (was 8)")

# ─── 4. Curvature Profile (NEW) ─────────────────────────────────
# Discrete curvature along the right-side contour
# κ = (x'y'' - y'x'') / (x'² + y'²)^(3/2)
# Using the sorted right-side contour

n_right = len(right_dy_sorted)
if n_right > 10:
    win = min(15, n_right - 2)
    if win % 2 == 0:
        win -= 1
    if win >= 5:
        dx_s = savgol_filter(right_dx_sorted, win, 3)
        dy_s = savgol_filter(right_dy_sorted, win, 3)
    else:
        dx_s = right_dx_sorted.copy()
        dy_s = right_dy_sorted.copy()

    # Parametric derivatives w.r.t. arc-length parameter
    t = np.arange(n_right, dtype=float)
    dx_dt = np.gradient(dx_s, t)
    dy_dt = np.gradient(dy_s, t)
    dx_dt2 = np.gradient(dx_dt, t)
    dy_dt2 = np.gradient(dy_dt, t)

    denom = (dx_dt**2 + dy_dt**2)**1.5
    denom[denom < 1e-12] = 1e-12
    kappa = (dx_dt * dy_dt2 - dy_dt * dx_dt2) / denom

    # Sample curvature at landmark dy values and find extrema
    curvature_samples = []
    step = max(1, n_right // 100)
    for i in range(0, n_right, step):
        curvature_samples.append({
            "dy": round(float(right_dy_sorted[i]), 4),
            "dx": round(float(right_dx_sorted[i]), 4),
            "kappa": round(float(kappa[i]), 6)
        })

    # Find curvature extrema (high-curvature points = sharp features)
    kappa_abs = np.abs(kappa)
    curvature_peaks = []
    for i in range(1, len(kappa) - 1):
        if kappa_abs[i] > kappa_abs[i-1] and kappa_abs[i] > kappa_abs[i+1] and kappa_abs[i] > 0.05:
            curvature_peaks.append({
                "dy": round(float(right_dy_sorted[i]), 4),
                "dx": round(float(right_dx_sorted[i]), 4),
                "kappa": round(float(kappa[i]), 6),
                "abs_kappa": round(float(kappa_abs[i]), 6)
            })

    # Sort peaks by absolute curvature, keep top 20
    curvature_peaks.sort(key=lambda p: p["abs_kappa"], reverse=True)
    curvature_peaks = curvature_peaks[:20]
    curvature_peaks.sort(key=lambda p: p["dy"])

    # Find inflection points (sign changes in kappa)
    curvature_inflections = []
    for i in range(1, len(kappa)):
        if kappa[i-1] * kappa[i] < 0:
            curvature_inflections.append({
                "dy": round(float(right_dy_sorted[i]), 4),
                "dx": round(float(right_dx_sorted[i]), 4),
                "kappa_before": round(float(kappa[i-1]), 6),
                "kappa_after": round(float(kappa[i]), 6)
            })

    data["curvature"] = {
        "note": (
            "Discrete curvature κ along the right-side contour. "
            "κ = (x'y'' − y'x'') / (x'² + y'²)^(3/2). "
            "Positive κ = contour curves rightward (convex bump), "
            "negative κ = contour curves leftward (concave indent). "
            "Computed on Savitzky-Golay smoothed contour (window=15, order=3)."
        ),
        "sample_count": len(curvature_samples),
        "samples": curvature_samples,
        "extrema": {
            "note": "Top 20 highest-|κ| points — sharp contour features (joints, armor edges, etc.)",
            "count": len(curvature_peaks),
            "peaks": curvature_peaks
        },
        "inflections": {
            "note": "Points where curvature sign changes — transitions between convex and concave regions",
            "count": len(curvature_inflections),
            "points": curvature_inflections
        }
    }
    print(f"Curvature: {len(curvature_samples)} samples, {len(curvature_peaks)} extrema, {len(curvature_inflections)} inflections")
else:
    print("WARNING: not enough contour points for curvature analysis")

# ─── 5. Proportion: canonical comparisons + composite ratios ────
prop = data["proportion"]

# Canonical proportions (Loomis 8-head, heroic 8.5-head)
# In Loomis 8-head: each segment is 1 HU
# chin at 1, nipple at 2, navel at 3, crotch at 4, mid-thigh at 5, knee at 6, mid-shin at 7, sole at 8
loomis_8 = {
    "system": "Loomis 8-head academic",
    "total_heads": 8.0,
    "landmark_positions_hu": {
        "crown": 0.0, "chin": 1.0, "nipple_line": 2.0,
        "navel": 3.0, "crotch": 4.0, "mid_thigh": 5.0,
        "knee": 6.0, "mid_shin": 7.0, "sole": 8.0
    }
}
heroic_85 = {
    "system": "Heroic 8.5-head (comic/concept art)",
    "total_heads": 8.5,
    "landmark_positions_hu": {
        "crown": 0.0, "chin": 1.0, "nipple_line": 2.0,
        "navel": 3.1, "crotch": 4.25, "mid_thigh": 5.3,
        "knee": 6.4, "mid_shin": 7.45, "sole": 8.5
    }
}

# Measured figure's key positions in HU (from landmarks)
measured_positions = {
    "crown": crown_dy,
    "neck_valley": neck_dy,
    "shoulder_peak": shoulder_dy,
    "waist_valley": waist_dy,
    "hip_peak": hip_dy,
    "knee_valley": knee_dy,
    "ankle_valley": ankle_dy,
    "sole": sole_dy
}

# Composite anatomical ratios
head_height = neck_dy - crown_dy  # HU by definition ≈ 1.0 (since scale is in HU)
torso_length = hip_dy - shoulder_dy
leg_length = sole_dy - hip_dy
upper_body = hip_dy - crown_dy
lower_body = sole_dy - hip_dy
upper_leg = knee_dy - hip_dy
lower_leg = ankle_dy - knee_dy
shoulder_width = existing_lm["shoulder_peak"]["dx"] * 2
hip_width = existing_lm["hip_peak"]["dx"] * 2
waist_width = existing_lm["waist_valley"]["dx"] * 2

prop["canonical_comparisons"] = [loomis_8, heroic_85]
prop["composite_ratios"] = {
    "note": "Derived ratios from landmark positions. All distances in HU.",
    "torso_to_leg": round(torso_length / leg_length, 4) if leg_length > 0 else None,
    "upper_to_lower_body": round(upper_body / lower_body, 4) if lower_body > 0 else None,
    "upper_to_lower_leg": round(upper_leg / lower_leg, 4) if lower_leg > 0 else None,
    "shoulder_to_hip_width": round(shoulder_width / hip_width, 4) if hip_width > 0 else None,
    "waist_to_hip_width": round(waist_width / hip_width, 4) if hip_width > 0 else None,
    "shoulder_to_height": round(shoulder_width / sole_dy, 4) if sole_dy > 0 else None,
    "head_to_shoulder_width": round((neck_dy - crown_dy) / shoulder_width, 4) if shoulder_width > 0 else None,
    "leg_fraction_of_height": round(leg_length / sole_dy, 4) if sole_dy > 0 else None,
    "torso_fraction_of_height": round(torso_length / sole_dy, 4) if sole_dy > 0 else None
}
prop["measured_positions_hu"] = measured_positions

print("Proportion: added canonical comparisons and composite ratios")

# ─── 6. Stroke enrichment ───────────────────────────────────────
for stroke in data["strokes"]:
    pts = np.array(stroke["points"])
    if len(pts) < 2:
        continue

    # Arc length
    diffs = np.diff(pts, axis=0)
    seg_lengths = np.sqrt((diffs**2).sum(axis=1))
    arc_len = float(seg_lengths.sum())
    stroke["arc_length_hu"] = round(arc_len, 4)

    # Chord length (start to end)
    chord = np.sqrt((pts[-1][0] - pts[0][0])**2 + (pts[-1][1] - pts[0][1])**2)
    stroke["chord_length_hu"] = round(float(chord), 4)

    # Sinuosity (arc_length / chord_length — 1.0 = straight line)
    if chord > 1e-6:
        stroke["sinuosity"] = round(arc_len / chord, 4)
    else:
        stroke["sinuosity"] = None  # degenerate (closed loop or point)

    # Orientation (angle of chord from horizontal, in degrees)
    if chord > 1e-6:
        angle = np.degrees(np.arctan2(pts[-1][1] - pts[0][1], pts[-1][0] - pts[0][0]))
        stroke["orientation_deg"] = round(float(angle), 1)
    else:
        stroke["orientation_deg"] = None

    # Mean curvature along stroke
    if len(pts) >= 5:
        win_s = min(5, len(pts) - 2)
        if win_s % 2 == 0:
            win_s -= 1
        if win_s >= 3:
            sx = savgol_filter(pts[:, 0], win_s, min(2, win_s-1))
            sy = savgol_filter(pts[:, 1], win_s, min(2, win_s-1))
            t_s = np.arange(len(pts), dtype=float)
            dxdt = np.gradient(sx, t_s)
            dydt = np.gradient(sy, t_s)
            dxdt2 = np.gradient(dxdt, t_s)
            dydt2 = np.gradient(dydt, t_s)
            den = (dxdt**2 + dydt**2)**1.5
            den[den < 1e-12] = 1e-12
            k_stroke = (dxdt * dydt2 - dydt * dxdt2) / den
            stroke["mean_curvature"] = round(float(np.mean(k_stroke)), 6)
            stroke["max_abs_curvature"] = round(float(np.max(np.abs(k_stroke))), 6)

    # Semantic type heuristic based on geometry and region
    region = stroke.get("region", "unknown")
    orient = stroke.get("orientation_deg")
    sin = stroke.get("sinuosity")

    # Heuristic classification
    stype = "unknown"
    if sin is not None and sin < 1.05 and arc_len > 0.3:
        stype = "panel_line"  # long, straight → armor panel edge
    elif sin is not None and sin < 1.1 and arc_len < 0.3:
        stype = "seam"  # short, straight → seam or edge detail
    elif sin is not None and sin > 1.5:
        stype = "decorative_curve"  # very curved → ornamental
    elif orient is not None and abs(orient) < 15 and region == "torso":
        stype = "horizontal_band"  # near-horizontal on torso → belt/band
    elif orient is not None and 75 < abs(orient) < 105:
        stype = "vertical_line"  # near-vertical → zipper, center line
    elif arc_len < 0.1:
        stype = "detail_mark"  # tiny → rivets, bolts, small detail
    else:
        stype = "contour_detail"

    stroke["semantic_type"] = stype
    stroke["semantic_confidence"] = 0.4  # low — purely heuristic

print(f"Strokes: enriched {len(data['strokes'])} strokes with geometry + semantic type")

# ─── 7. Parametric: add curvature extrema per segment ───────────
for seg in data["parametric"]["segments"]:
    dy_lo, dy_hi = seg["dy_range"]
    # Sample the contour in this segment range
    dy_seg = unique_dy[(unique_dy >= dy_lo) & (unique_dy <= dy_hi)]
    if len(dy_seg) < 5:
        continue
    dx_seg = np.array([width_at(d) for d in dy_seg])
    valid = np.isfinite(dx_seg)
    dy_seg = dy_seg[valid]
    dx_seg = dx_seg[valid]
    if len(dy_seg) < 5:
        continue

    # Curvature of width profile within segment
    d1 = np.gradient(dx_seg, dy_seg)
    d2 = np.gradient(d1, dy_seg)

    # Max curvature point
    abs_d2 = np.abs(d2)
    max_k_idx = np.argmax(abs_d2)
    seg["curvature_max"] = {
        "dy": round(float(dy_seg[max_k_idx]), 4),
        "dx": round(float(dx_seg[max_k_idx]), 4),
        "kappa_width": round(float(d2[max_k_idx]), 6)
    }

    # Inflection points within segment
    seg_inflections = []
    for i in range(1, len(d2)):
        if d2[i-1] * d2[i] < 0:
            seg_inflections.append(round(float(dy_seg[i]), 4))
    seg["inflection_dy"] = seg_inflections

    # Width range within segment
    seg["width_range"] = {
        "min_dx": round(float(dx_seg.min()), 4),
        "max_dx": round(float(dx_seg.max()), 4),
        "range_dx": round(float(dx_seg.max() - dx_seg.min()), 4)
    }

print(f"Parametric: enriched {len(data['parametric']['segments'])} segments with curvature + width range")

# ─── 8. Body Region Map (NEW) ───────────────────────────────────
data["body_regions"] = {
    "note": (
        "Anatomical zone boundaries derived from landmark dy positions. "
        "Each region spans [dy_start, dy_end) in head units. "
        "Useful for mapping strokes, scanlines, and other features to body zones."
    ),
    "regions": [
        {"name": "cranium", "dy_start": round(crown_dy, 4), "dy_end": round(existing_lm["head_peak"]["dy"], 4),
         "description": "Top of head to widest head point"},
        {"name": "face", "dy_start": round(existing_lm["head_peak"]["dy"], 4), "dy_end": round(neck_dy, 4),
         "description": "Visor/face region to neck valley"},
        {"name": "neck", "dy_start": round(neck_dy, 4), "dy_end": round(shoulder_dy * 0.65 + neck_dy * 0.35, 4),
         "description": "Neck valley to upper shoulder transition"},
        {"name": "shoulders", "dy_start": round(shoulder_dy * 0.65 + neck_dy * 0.35, 4), "dy_end": round(shoulder_dy + 0.15, 4),
         "description": "Shoulder slope to just below shoulder peak"},
        {"name": "upper_torso", "dy_start": round(shoulder_dy + 0.15, 4), "dy_end": round(waist_dy, 4),
         "description": "Chest/upper torso to waist"},
        {"name": "lower_torso", "dy_start": round(waist_dy, 4), "dy_end": round(hip_dy, 4),
         "description": "Waist to hip peak (abdomen/pelvis)"},
        {"name": "upper_leg", "dy_start": round(hip_dy, 4), "dy_end": round(knee_dy, 4),
         "description": "Hip peak to knee valley (thigh)"},
        {"name": "lower_leg", "dy_start": round(knee_dy, 4), "dy_end": round(ankle_dy, 4),
         "description": "Knee valley to ankle valley (shin/calf)"},
        {"name": "foot", "dy_start": round(ankle_dy, 4), "dy_end": round(sole_dy, 4),
         "description": "Ankle to sole (boot/foot)"},
    ]
}

print("Body regions: 9 zones defined")

# ─── 9. Cross-Section Topology (NEW) ────────────────────────────
# At each scanline dy, count how many times the contour crosses that level
# This reveals where arms separate from torso, etc.
topology_profile = {}
for dy_val in np.arange(0.1, sole_dy, 0.1):
    dy_key = f"{dy_val:.1f}"
    # Count crossings: how many contour segments cross this dy level
    crossings = 0
    for i in range(len(right_dy_sorted) - 1):
        if (right_dy_sorted[i] <= dy_val < right_dy_sorted[i+1]) or \
           (right_dy_sorted[i+1] <= dy_val < right_dy_sorted[i]):
            crossings += 1
    topology_profile[dy_key] = {
        "crossings": crossings,
        "pairs": crossings // 2,
        "interpretation": (
            "single_body" if crossings <= 2 else
            "arm_separated" if crossings <= 4 else
            "complex_topology"
        )
    }

data["cross_section_topology"] = {
    "note": (
        "Number of times the right-side contour crosses each horizontal scanline. "
        "crossings=2 → single body outline; crossings=4 → arm separated from torso; "
        "crossings>4 → complex features (armor plates, weapons, etc.)"
    ),
    "profile": topology_profile
}

print(f"Cross-section topology: {len(topology_profile)} levels profiled")

# ─── 10. Fourier Descriptors (NEW) ──────────────────────────────
# Elliptic Fourier Descriptors of the contour — compact shape signature
# Using only the right-side contour
try:
    # Use ORIGINAL contour ordering (not dy-sorted) for correct arc-length
    pts_right_orig = np.column_stack([right_dx, right_dy])  # original index order
    diffs_r = np.diff(pts_right_orig, axis=0)
    seg_len_r = np.sqrt((diffs_r**2).sum(axis=1))
    T = seg_len_r.sum()  # total perimeter
    t_cumul = np.concatenate([[0], np.cumsum(seg_len_r)])
    t_norm = t_cumul / T  # normalized to [0, 1]

    # Compute Fourier coefficients
    _trapz = getattr(np, 'trapezoid', getattr(np, 'trapz', None))
    n_harmonics = 12
    fd_coeffs = []
    for n in range(1, n_harmonics + 1):
        an_x = 2 * _trapz(right_dx * np.cos(2 * np.pi * n * t_norm), t_norm)
        bn_x = 2 * _trapz(right_dx * np.sin(2 * np.pi * n * t_norm), t_norm)
        an_y = 2 * _trapz(right_dy * np.cos(2 * np.pi * n * t_norm), t_norm)
        bn_y = 2 * _trapz(right_dy * np.sin(2 * np.pi * n * t_norm), t_norm)
        amplitude = np.sqrt(an_x**2 + bn_x**2 + an_y**2 + bn_y**2)
        fd_coeffs.append({
            "harmonic": n,
            "a_x": round(float(an_x), 6),
            "b_x": round(float(bn_x), 6),
            "a_y": round(float(an_y), 6),
            "b_y": round(float(bn_y), 6),
            "amplitude": round(float(amplitude), 6)
        })

    data["fourier_descriptors"] = {
        "note": (
            "Elliptic Fourier Descriptors (EFD) of the right-side contour. "
            "12 harmonics capture the shape signature from coarse to fine. "
            "Low harmonics encode overall body proportion; high harmonics encode surface detail. "
            "Can be used for shape matching, classification, and parametric reconstruction."
        ),
        "n_harmonics": n_harmonics,
        "perimeter_hu": round(float(T), 4),
        "coefficients": fd_coeffs,
        "energy_concentration": {
            "note": "Fraction of total shape energy in first N harmonics",
            "harmonics_1_4": round(sum(c["amplitude"]**2 for c in fd_coeffs[:4]) /
                                    sum(c["amplitude"]**2 for c in fd_coeffs), 4),
            "harmonics_1_8": round(sum(c["amplitude"]**2 for c in fd_coeffs[:8]) /
                                    sum(c["amplitude"]**2 for c in fd_coeffs), 4)
        }
    }
    print(f"Fourier descriptors: {n_harmonics} harmonics, perimeter={T:.4f} HU")
except Exception as e:
    print(f"WARNING: Fourier descriptors failed: {e}")

# ─── 11. Meta Enrichment ────────────────────────────────────────
# Contour quality metrics
pts_full = contour.copy()
diffs_full = np.diff(pts_full, axis=0)
seg_lens_full = np.sqrt((diffs_full**2).sum(axis=1))

data["meta"]["contour_quality"] = {
    "total_perimeter_hu": round(float(seg_lens_full.sum()), 4),
    "right_perimeter_hu": round(float(seg_lens_full[:RIGHT_END-1].sum()), 4),
    "mean_segment_length": round(float(seg_lens_full.mean()), 6),
    "std_segment_length": round(float(seg_lens_full.std()), 6),
    "min_segment_length": round(float(seg_lens_full.min()), 6),
    "max_segment_length": round(float(seg_lens_full.max()), 6),
    "segment_length_cv": round(float(seg_lens_full.std() / seg_lens_full.mean()), 4) if seg_lens_full.mean() > 0 else None,
    "note": "Coefficient of variation (CV) < 0.5 indicates uniform point spacing; > 1.0 indicates highly irregular sampling"
}

# Bounding box in HU
data["meta"]["bounding_box_hu"] = {
    "dx_min": round(float(dx_arr.min()), 4),
    "dx_max": round(float(dx_arr.max()), 4),
    "dy_min": round(float(dy_arr.min()), 4),
    "dy_max": round(float(dy_arr.max()), 4),
    "width": round(float(dx_arr.max() - dx_arr.min()), 4),
    "height": round(float(dy_arr.max() - dy_arr.min()), 4),
    "aspect_ratio": round(float((dy_arr.max() - dy_arr.min()) / (dx_arr.max() - dx_arr.min())), 4)
        if (dx_arr.max() - dx_arr.min()) > 0 else None
}

# Schema version bump
data["meta"]["schema_version"] = "3.0.0"

# ─── 12. Update section order note ──────────────────────────────
data["meta"]["sections"] = {
    "note": "v3.0 section inventory",
    "sections": [
        "meta", "contour", "landmarks", "midline", "strokes",
        "symmetry", "measurements", "parametric", "proportion",
        "curvature", "body_regions", "cross_section_topology",
        "fourier_descriptors", "candidates"
    ],
    "new_in_v3": [
        "curvature — discrete curvature profile with extrema and inflection points",
        "body_regions — anatomical zone map with dy boundaries",
        "cross_section_topology — contour crossing count per scanline level",
        "fourier_descriptors — 12-harmonic elliptic Fourier shape signature"
    ],
    "enriched_in_v3": [
        "landmarks — expanded from 9 to ~20 with derived anatomical points",
        "measurements.scanlines — 0.05 HU step (was 0.1), added width derivative and curvature",
        "symmetry — 0.25 HU step (was 1.0 HU), with source provenance",
        "strokes — added arc_length, chord_length, sinuosity, orientation, curvature, semantic_type",
        "parametric — added per-segment curvature_max, inflection_dy, width_range",
        "proportion — added canonical_comparisons (Loomis, heroic), composite_ratios, measured_positions_hu",
        "meta — added contour_quality metrics, bounding_box_hu, sections inventory"
    ]
}

# ─── Write ──────────────────────────────────────────────────────
output_path = "/home/claude/v3.json"
with open(output_path, "w") as f:
    json.dump(data, f, indent=2)

import os
size_kb = os.path.getsize(output_path) / 1024
print(f"\nOutput: {output_path} ({size_kb:.1f} KB)")
print("Done.")
