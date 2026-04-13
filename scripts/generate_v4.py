#!/usr/bin/env python3
"""
generate_v4.py — Complete v2 → v4 silhouette analysis pipeline.

Consolidates enrich.py, refine_v3.py, and cross_domain_enrich.py into
a single in-memory pass.  Reads a v2.json extraction and writes a fully
enriched v4.json conforming to schema/silhouette_v4.schema.json.

Usage:
    python3 generate_v4.py <input_v2.json> <output_v4.json>

Dependencies:
    numpy, scipy
"""

import argparse
import json
import os
import sys
import numpy as np
from collections import Counter
from scipy.interpolate import CubicSpline
from scipy.signal import savgol_filter
from scipy.spatial import ConvexHull, cKDTree
from scipy.ndimage import gaussian_filter1d
from scipy.stats import entropy as scipy_entropy
from numpy.polynomial import polynomial as P
import warnings

from lib.builder import SilhouetteDocument
from lib.constants import RIGHT_END

warnings.filterwarnings("ignore")

_trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def build_contour_interpolator(right_dx, right_dy):
    """Build a cubic-spline interpolator from right-side contour."""
    sort_idx = np.argsort(right_dy)
    rdy_sorted = right_dy[sort_idx]
    rdx_sorted = right_dx[sort_idx]
    unique_dy, inv = np.unique(rdy_sorted, return_inverse=True)
    unique_dx = np.zeros_like(unique_dy)
    for i in range(len(unique_dy)):
        unique_dx[i] = rdx_sorted[inv == i].mean()
    interp = CubicSpline(unique_dy, unique_dx, extrapolate=False)
    return interp, unique_dy, unique_dx, rdy_sorted, rdx_sorted


def width_at(interp, dy_val):
    v = interp(dy_val)
    return float(v) if v is not None and np.isfinite(v) else float("nan")


def find_extremum_in_range(indices, dy_lo, dy_hi, unique_dy, arr):
    return [
        (i, unique_dy[i], arr[i])
        for i in indices
        if dy_lo <= unique_dy[i] <= dy_hi
    ]


def savgol_safe(data, window, order):
    """Apply Savitzky-Golay with automatic window clamping."""
    w = min(window, len(data) - 2)
    if w % 2 == 0:
        w -= 1
    if w >= (order + 2):
        return savgol_filter(data, w, order)
    return data.copy()


def parametric_curvature(x, y):
    """κ = (x'y'' − y'x'') / (x'² + y'²)^(3/2)"""
    t = np.arange(len(x), dtype=float)
    dx = np.gradient(x, t)
    dy = np.gradient(y, t)
    ddx = np.gradient(dx, t)
    ddy = np.gradient(dy, t)
    denom = (dx**2 + dy**2) ** 1.5
    denom[denom < 1e-12] = 1e-12
    return (dx * ddy - dy * ddx) / denom


# ═══════════════════════════════════════════════════════════════════
# PIPELINE PHASES  (v2 → v3 from enrich.py)
# ═══════════════════════════════════════════════════════════════════

def phase_01_landmark_enrichment(data, unique_dy, unique_dx, interp):
    """Expand from 9 to ~20 landmarks using contour extrema."""
    existing_lm = {lm["name"]: lm for lm in data["landmarks"]}
    crown_dy = existing_lm["crown"]["dy"]
    neck_dy = existing_lm["neck_valley"]["dy"]
    shoulder_dy = existing_lm["shoulder_peak"]["dy"]
    waist_dy = existing_lm["waist_valley"]["dy"]
    hip_dy = existing_lm["hip_peak"]["dy"]
    knee_dy = existing_lm["knee_valley"]["dy"]
    ankle_dy = existing_lm["ankle_valley"]["dy"]
    sole_dy = existing_lm["sole"]["dy"]

    # Smooth profile for extrema detection
    dx_smooth = savgol_safe(unique_dx, 51, 3)
    dx_deriv = np.gradient(dx_smooth, unique_dy)
    dx_deriv2 = np.gradient(dx_deriv, unique_dy)

    # Find local maxima / minima / inflections
    local_max_idx, local_min_idx = [], []
    for i in range(1, len(dx_smooth) - 1):
        if dx_smooth[i] > dx_smooth[i - 1] and dx_smooth[i] > dx_smooth[i + 1]:
            local_max_idx.append(i)
        if dx_smooth[i] < dx_smooth[i - 1] and dx_smooth[i] < dx_smooth[i + 1]:
            local_min_idx.append(i)

    find = lambda indices, lo, hi: find_extremum_in_range(
        indices, lo, hi, unique_dy, dx_smooth
    )

    new_landmarks = []

    # chin
    cands = find(local_min_idx, 0.8, neck_dy)
    if cands:
        best = min(cands, key=lambda c: c[2])
        new_landmarks.append({
            "name": "chin",
            "description": "Jaw/chin narrowing before neck — local width minimum",
            "dy": round(float(unique_dy[best[0]]), 4),
            "dx": round(float(unique_dx[best[0]]), 4),
            "source": "derived_extremum",
            "confidence": 0.7,
            "note": "Approximated from contour profile; may correspond to helmet chin guard on armored figure",
        })

    # bust_peak
    cands = find(local_max_idx, shoulder_dy + 0.1, waist_dy - 0.1)
    if cands:
        best = max(cands, key=lambda c: c[2])
        new_landmarks.append({
            "name": "bust_peak",
            "description": "Widest torso width between shoulders and waist (chest/bust level)",
            "dy": round(float(unique_dy[best[0]]), 4),
            "dx": round(float(unique_dx[best[0]]), 4),
            "source": "derived_extremum",
            "confidence": 0.65,
            "note": "On armored figures, corresponds to chest plate maximum width",
        })

    # armpit_valley
    cands = find(local_min_idx, shoulder_dy, shoulder_dy + 0.8)
    if cands:
        best = min(cands, key=lambda c: c[2])
        new_landmarks.append({
            "name": "armpit_valley",
            "description": "Narrowing just below shoulder peak (armpit/arm junction)",
            "dy": round(float(unique_dy[best[0]]), 4),
            "dx": round(float(unique_dx[best[0]]), 4),
            "source": "derived_extremum",
            "confidence": 0.6,
            "caveat": "arms_at_sides_occlusion",
        })

    # crotch_valley
    cands = find(local_min_idx, hip_dy + 0.1, knee_dy - 0.2)
    if cands:
        best = min(cands, key=lambda c: c[2])
        new_landmarks.append({
            "name": "crotch_valley",
            "description": "Narrowest point between hips and knees (inseam level)",
            "dy": round(float(unique_dy[best[0]]), 4),
            "dx": round(float(unique_dx[best[0]]), 4),
            "source": "derived_extremum",
            "confidence": 0.7,
        })

    # calf_peak
    cands = find(local_max_idx, knee_dy + 0.1, ankle_dy - 0.2)
    if cands:
        best = max(cands, key=lambda c: c[2])
        new_landmarks.append({
            "name": "calf_peak",
            "description": "Widest point of calf/lower leg",
            "dy": round(float(unique_dy[best[0]]), 4),
            "dx": round(float(unique_dx[best[0]]), 4),
            "source": "derived_extremum",
            "confidence": 0.65,
        })

    # mid_thigh
    mid_thigh_dy = (hip_dy + knee_dy) / 2
    dx_val = width_at(interp, mid_thigh_dy)
    if np.isfinite(dx_val):
        new_landmarks.append({
            "name": "mid_thigh",
            "description": "Midpoint between hip peak and knee valley",
            "dy": round(mid_thigh_dy, 4),
            "dx": round(dx_val, 4),
            "source": "interpolated_midpoint",
        })

    # mid_shin
    mid_shin_dy = (knee_dy + ankle_dy) / 2
    dx_val = width_at(interp, mid_shin_dy)
    if np.isfinite(dx_val):
        new_landmarks.append({
            "name": "mid_shin",
            "description": "Midpoint between knee valley and ankle valley",
            "dy": round(mid_shin_dy, 4),
            "dx": round(dx_val, 4),
            "source": "interpolated_midpoint",
        })

    # navel_estimate
    navel_dy = shoulder_dy + 0.6 * (hip_dy - shoulder_dy)
    dx_val = width_at(interp, navel_dy)
    if np.isfinite(dx_val):
        new_landmarks.append({
            "name": "navel_estimate",
            "description": "Estimated navel position (60% shoulder→hip, classic anatomical ratio)",
            "dy": round(navel_dy, 4),
            "dx": round(dx_val, 4),
            "source": "anatomical_heuristic",
            "confidence": 0.5,
            "note": "Heuristic placement, not detected from contour features",
        })

    # trapezius
    cands = find(local_max_idx, neck_dy, shoulder_dy)
    if cands:
        best = max(cands, key=lambda c: c[2])
        new_landmarks.append({
            "name": "trapezius_peak",
            "description": "Local width maximum in neck-to-shoulder transition",
            "dy": round(float(unique_dy[best[0]]), 4),
            "dx": round(float(unique_dx[best[0]]), 4),
            "source": "derived_extremum",
            "confidence": 0.6,
        })
    else:
        trap_dy = (neck_dy + shoulder_dy) / 2
        dx_val = width_at(interp, trap_dy)
        if np.isfinite(dx_val):
            new_landmarks.append({
                "name": "trapezius_slope",
                "description": "Midpoint of neck-to-shoulder transition",
                "dy": round(trap_dy, 4),
                "dx": round(dx_val, 4),
                "source": "interpolated_midpoint",
            })

    # boot_top
    cands = find(local_max_idx, ankle_dy, sole_dy)
    if cands:
        best = max(cands, key=lambda c: c[2])
        new_landmarks.append({
            "name": "boot_top",
            "description": "Widest point of boot/footwear above sole",
            "dy": round(float(unique_dy[best[0]]), 4),
            "dx": round(float(unique_dx[best[0]]), 4),
            "source": "derived_extremum",
            "confidence": 0.55,
            "note": "Detected from local width maximum in foot region",
        })

    data["landmarks"] = sorted(
        data["landmarks"] + new_landmarks, key=lambda lm: lm["dy"]
    )
    print(f"  Landmarks: {len(data['landmarks'])} (was 9, added {len(new_landmarks)})")
    return dx_deriv2


def phase_02_dense_scanlines(data, unique_dy, dx_deriv2, interp, sole_dy):
    """Densify scanlines to 0.05 HU step with derivatives."""
    dy_max_scan = float(np.floor(sole_dy * 20) / 20)
    dense_dy = np.arange(0.05, dy_max_scan + 0.001, 0.05)

    new_scanlines = {}
    prev_dx_val = None
    for dy_val in dense_dy:
        dy_key = f"{dy_val:.2f}"
        dx_val = width_at(interp, dy_val)
        if not np.isfinite(dx_val):
            prev_dx_val = None
            continue
        # Clamp to zero: spline can overshoot to negative in re-entrant regions.
        dx_val = max(dx_val, 0.0)
        entry = {
            "right_dx": round(dx_val, 4),
            "left_dx": round(dx_val, 4),
            "full_width_hu": round(2 * dx_val, 4),
        }
        if prev_dx_val is not None and np.isfinite(prev_dx_val):
            entry["d_width_d_dy"] = round((dx_val - prev_dx_val) / 0.05, 4)
        else:
            entry["d_width_d_dy"] = None
        dy_idx = np.searchsorted(unique_dy, dy_val)
        if 1 <= dy_idx < len(dx_deriv2):
            entry["curvature"] = round(float(dx_deriv2[dy_idx]), 4)
        else:
            entry["curvature"] = None
        new_scanlines[dy_key] = entry
        prev_dx_val = dx_val

    # Preserve original multi-pair topology.
    # Raw v2 keys may be '5.0' while dense keys are '5.00' — normalize
    # to the dense format so topology_detail lands on the right entry.
    for dy_key, orig_entries in data["measurements"]["scanlines"].items():
        dense_key = f"{float(dy_key):.2f}"
        if dense_key in new_scanlines:
            if isinstance(orig_entries, list) and len(orig_entries) > 1:
                new_scanlines[dense_key]["contour_pairs"] = len(orig_entries)
                new_scanlines[dense_key]["topology_detail"] = orig_entries
            elif isinstance(orig_entries, list) and len(orig_entries) == 1:
                new_scanlines[dense_key]["topology"] = orig_entries[0].get("topology", "unknown")
        else:
            new_scanlines[dense_key] = orig_entries

    data["measurements"]["scanlines"] = dict(
        sorted(new_scanlines.items(), key=lambda x: float(x[0]))
    )
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
    print(f"  Scanlines: {len(new_scanlines)}")


def phase_03_dense_symmetry(data, interp, sole_dy):
    """Expand symmetry samples to 0.25 HU intervals."""
    new_samples = {}
    for dy_val in np.arange(0.25, sole_dy, 0.25):
        dy_key = f"{dy_val:.2f}" if dy_val != int(dy_val) else f"{dy_val:.1f}"
        rdx = width_at(interp, dy_val)
        if not np.isfinite(rdx):
            continue
        orig_key = f"{dy_val:.1f}"
        if orig_key in data["symmetry"]["samples"]:
            new_samples[orig_key] = data["symmetry"]["samples"][orig_key]
        else:
            new_samples[dy_key] = {
                "right_dx": round(rdx, 4),
                "left_dx": round(rdx, 4),
                "delta": 0.0,
                "source": "interpolated_mirror",
            }
    for k, v in data["symmetry"]["samples"].items():
        if k not in new_samples:
            new_samples[k] = v

    data["symmetry"]["samples"] = dict(
        sorted(new_samples.items(), key=lambda x: float(x[0]))
    )
    data["symmetry"]["sample_count"] = len(data["symmetry"]["samples"])
    data["symmetry"]["note"] = (
        "Symmetry measured at 0.25 HU intervals. delta = |right_dx - left_dx|. "
        "Samples marked source='interpolated_mirror' are derived from the mirrored contour "
        "and thus have delta=0 by construction. Only samples from the original raw extraction "
        "(without 'source' field) capture true asymmetry. High delta at dy=1.0 is from ponytail."
    )
    print(f"  Symmetry: {len(data['symmetry']['samples'])} samples")


def phase_04_curvature_profile(data, rdy_sorted, rdx_sorted):
    """Discrete curvature along the right-side contour."""
    n = len(rdy_sorted)
    if n <= 10:
        print("  WARNING: not enough contour points for curvature")
        return

    dx_s = savgol_safe(rdx_sorted, 15, 3)
    dy_s = savgol_safe(rdy_sorted, 15, 3)
    kappa = parametric_curvature(dx_s, dy_s)

    # Subsampled curvature profile
    step = max(1, n // 100)
    samples = [
        {"dy": round(float(rdy_sorted[i]), 4),
         "dx": round(float(rdx_sorted[i]), 4),
         "kappa": round(float(kappa[i]), 6)}
        for i in range(0, n, step)
    ]

    # Extrema (top-20 sharpest points)
    kappa_abs = np.abs(kappa)
    peaks = []
    for i in range(1, len(kappa) - 1):
        if kappa_abs[i] > kappa_abs[i - 1] and kappa_abs[i] > kappa_abs[i + 1] and kappa_abs[i] > 0.05:
            peaks.append({
                "dy": round(float(rdy_sorted[i]), 4),
                "dx": round(float(rdx_sorted[i]), 4),
                "kappa": round(float(kappa[i]), 6),
                "abs_kappa": round(float(kappa_abs[i]), 6),
            })
    peaks.sort(key=lambda p: p["abs_kappa"], reverse=True)
    peaks = peaks[:20]
    peaks.sort(key=lambda p: p["dy"])

    # Inflections (sign changes)
    inflections = []
    for i in range(1, len(kappa)):
        if kappa[i - 1] * kappa[i] < 0:
            inflections.append({
                "dy": round(float(rdy_sorted[i]), 4),
                "dx": round(float(rdx_sorted[i]), 4),
                "kappa_before": round(float(kappa[i - 1]), 6),
                "kappa_after": round(float(kappa[i]), 6),
            })

    data["curvature"] = {
        "note": (
            "Discrete curvature κ along the right-side contour. "
            "κ = (x'y'' − y'x'') / (x'² + y'²)^(3/2). "
            "Positive κ = contour curves rightward (convex bump), "
            "negative κ = contour curves leftward (concave indent). "
            "Computed on Savitzky-Golay smoothed contour (window=15, order=3)."
        ),
        "computed_on": "right_half",
        "sample_count": len(samples),
        "samples": samples,
        "extrema": {
            "note": "Top 20 highest-|κ| points — sharp contour features (joints, armor edges, etc.)",
            "count": len(peaks),
            "peaks": peaks,
        },
        "inflections": {
            "note": "Points where curvature sign changes — transitions between convex and concave regions",
            "count": len(inflections),
            "points": inflections,
        },
    }
    print(f"  Curvature: {len(samples)} samples, {len(peaks)} extrema, {len(inflections)} inflections")


def phase_05_proportion(data):
    """Add canonical comparisons and composite ratios."""
    prop = data["proportion"]
    lm = {l["name"]: l for l in data["landmarks"]}

    crown_dy = lm["crown"]["dy"]
    neck_dy = lm["neck_valley"]["dy"]
    shoulder_dy = lm["shoulder_peak"]["dy"]
    waist_dy = lm["waist_valley"]["dy"]
    hip_dy = lm["hip_peak"]["dy"]
    knee_dy = lm["knee_valley"]["dy"]
    ankle_dy = lm["ankle_valley"]["dy"]
    sole_dy = lm["sole"]["dy"]

    torso_len = hip_dy - shoulder_dy
    leg_len = sole_dy - hip_dy
    upper_body = hip_dy - crown_dy
    lower_body = sole_dy - hip_dy
    upper_leg = knee_dy - hip_dy
    lower_leg = ankle_dy - knee_dy
    shoulder_w = lm["shoulder_peak"]["dx"] * 2
    hip_w = lm["hip_peak"]["dx"] * 2
    waist_w = lm["waist_valley"]["dx"] * 2

    prop["canonical_comparisons"] = [
        {
            "system": "Chibi / super-deformed",
            "total_heads": 2.5,
            "landmark_positions_hu": {
                "crown": 0.0, "chin": 1.0, "crotch": 1.5, "sole": 2.5,
            },
        },
        {
            "system": "Standard anime",
            "total_heads": 6.5,
            "landmark_positions_hu": {
                "crown": 0.0, "chin": 1.0, "nipple_line": 1.8,
                "navel": 2.8, "crotch": 3.5, "knee": 5.0, "sole": 6.5,
            },
        },
        {
            "system": "Academic realistic (Richer / Bammes)",
            "total_heads": 7.5,
            "landmark_positions_hu": {
                "crown": 0.0, "chin": 1.0, "nipple_line": 2.0,
                "navel": 3.0, "crotch": 3.75, "mid_thigh": 4.7,
                "knee": 5.6, "mid_shin": 6.5, "sole": 7.5,
            },
        },
        {
            "system": "Loomis 8-head idealized",
            "total_heads": 8.0,
            "landmark_positions_hu": {
                "crown": 0.0, "chin": 1.0, "nipple_line": 2.0,
                "navel": 3.0, "crotch": 4.0, "mid_thigh": 5.0,
                "knee": 6.0, "mid_shin": 7.0, "sole": 8.0,
            },
        },
        {
            "system": "Heroic 8.5-head (comic/concept art)",
            "total_heads": 8.5,
            "landmark_positions_hu": {
                "crown": 0.0, "chin": 1.0, "nipple_line": 2.0,
                "navel": 3.1, "crotch": 4.25, "mid_thigh": 5.3,
                "knee": 6.4, "mid_shin": 7.45, "sole": 8.5,
            },
        },
        {
            "system": "Fashion (9-10 head)",
            "total_heads": 9.5,
            "landmark_positions_hu": {
                "crown": 0.0, "chin": 1.0, "nipple_line": 2.1,
                "navel": 3.2, "crotch": 4.5, "mid_thigh": 5.8,
                "knee": 7.0, "mid_shin": 8.2, "sole": 9.5,
            },
        },
    ]
    prop["composite_ratios"] = {
        "note": "Derived ratios from landmark positions. All distances in HU.",
        "torso_to_leg": round(torso_len / leg_len, 4) if leg_len > 0 else None,
        "upper_to_lower_body": round(upper_body / lower_body, 4) if lower_body > 0 else None,
        "upper_to_lower_leg": round(upper_leg / lower_leg, 4) if lower_leg > 0 else None,
        "shoulder_to_hip_width": round(shoulder_w / hip_w, 4) if hip_w > 0 else None,
        "waist_to_hip_width": round(waist_w / hip_w, 4) if hip_w > 0 else None,
        "shoulder_to_height": round(shoulder_w / sole_dy, 4) if sole_dy > 0 else None,
        "head_to_shoulder_width": round((neck_dy - crown_dy) / shoulder_w, 4) if shoulder_w > 0 else None,
        "leg_fraction_of_height": round(leg_len / sole_dy, 4) if sole_dy > 0 else None,
        "torso_fraction_of_height": round(torso_len / sole_dy, 4) if sole_dy > 0 else None,
    }
    prop["measured_positions_hu"] = {
        "crown": crown_dy, "neck_valley": neck_dy,
        "shoulder_peak": shoulder_dy, "waist_valley": waist_dy,
        "hip_peak": hip_dy, "knee_valley": knee_dy,
        "ankle_valley": ankle_dy, "sole": sole_dy,
    }
    print("  Proportions: canonical + composite ratios")


def phase_06_stroke_enrichment(data):
    """Add geometric features and semantic classification to strokes."""
    for stroke in data["strokes"]:
        pts = np.array(stroke["points"])
        if len(pts) < 2:
            continue

        diffs = np.diff(pts, axis=0)
        seg_lengths = np.sqrt((diffs**2).sum(axis=1))
        arc_len = float(seg_lengths.sum())
        stroke["arc_length_hu"] = round(arc_len, 4)

        chord = float(np.sqrt((pts[-1][0] - pts[0][0])**2 + (pts[-1][1] - pts[0][1])**2))
        stroke["chord_length_hu"] = round(chord, 4)
        stroke["sinuosity"] = round(arc_len / chord, 4) if chord > 1e-6 else None

        if chord > 1e-6:
            stroke["orientation_deg"] = round(
                float(np.degrees(np.arctan2(pts[-1][1] - pts[0][1], pts[-1][0] - pts[0][0]))), 1
            )
        else:
            stroke["orientation_deg"] = None

        if len(pts) >= 5:
            win_s = min(5, len(pts) - 2)
            if win_s % 2 == 0:
                win_s -= 1
            if win_s >= 3:
                sx = savgol_filter(pts[:, 0], win_s, min(2, win_s - 1))
                sy = savgol_filter(pts[:, 1], win_s, min(2, win_s - 1))
                k_s = parametric_curvature(sx, sy)
                stroke["mean_curvature"] = round(float(np.mean(k_s)), 6)
                stroke["max_abs_curvature"] = round(float(np.max(np.abs(k_s))), 6)

    # v3.0 basic semantic type (will be overwritten by phase_09)
    for stroke in data["strokes"]:
        stroke["semantic_type"] = "contour_detail"
        stroke["semantic_confidence"] = 0.4
    print(f"  Strokes: enriched {len(data['strokes'])} with geometry")


def phase_07_parametric_enrichment(data, unique_dy, interp):
    """Add curvature extrema and width range per parametric segment."""
    for seg in data["parametric"]["segments"]:
        dy_lo, dy_hi = seg["dy_range"]
        dy_seg = unique_dy[(unique_dy >= dy_lo) & (unique_dy <= dy_hi)]
        if len(dy_seg) < 5:
            continue
        dx_seg = np.array([width_at(interp, d) for d in dy_seg])
        valid = np.isfinite(dx_seg)
        dy_seg, dx_seg = dy_seg[valid], dx_seg[valid]
        if len(dy_seg) < 5:
            continue

        d1 = np.gradient(dx_seg, dy_seg)
        d2 = np.gradient(d1, dy_seg)
        abs_d2 = np.abs(d2)
        max_k_idx = np.argmax(abs_d2)

        seg["curvature_max"] = {
            "dy": round(float(dy_seg[max_k_idx]), 4),
            "dx": round(float(dx_seg[max_k_idx]), 4),
            "kappa_width": round(float(d2[max_k_idx]), 6),
        }
        seg["inflection_dy"] = [
            round(float(dy_seg[i]), 4)
            for i in range(1, len(d2))
            if d2[i - 1] * d2[i] < 0
        ]
        seg["width_range"] = {
            "min_dx": round(float(dx_seg.min()), 4),
            "max_dx": round(float(dx_seg.max()), 4),
            "range_dx": round(float(dx_seg.max() - dx_seg.min()), 4),
        }

        # complexity score
        n_inflections = len(seg["inflection_dy"])
        d2_std = float(np.std(d2))
        complexity = round(n_inflections * 0.3 + d2_std * 0.7, 4)
        if complexity > 0:
            seg["complexity"] = complexity
            seg["complexity_note"] = "0.3*n_inflections + 0.7*std(d2_width). Higher = more varied contour."

    print(f"  Parametric: enriched {len(data['parametric']['segments'])} segments")


def phase_08_body_regions(data):
    """Define 9 anatomical zones from landmark positions."""
    lm = {l["name"]: l for l in data["landmarks"]}
    crown_dy = lm["crown"]["dy"]
    head_peak_dy = lm["head_peak"]["dy"]
    neck_dy = lm["neck_valley"]["dy"]
    shoulder_dy = lm["shoulder_peak"]["dy"]
    waist_dy = lm["waist_valley"]["dy"]
    hip_dy = lm["hip_peak"]["dy"]
    knee_dy = lm["knee_valley"]["dy"]
    ankle_dy = lm["ankle_valley"]["dy"]
    sole_dy = lm["sole"]["dy"]

    data["body_regions"] = {
        "note": (
            "Anatomical zone boundaries derived from landmark dy positions. "
            "Each region spans [dy_start, dy_end) in head units."
        ),
        "regions": [
            {"name": "cranium",     "dy_start": round(crown_dy, 4),
             "dy_end": round(head_peak_dy, 4),
             "description": "Top of head to widest head point"},
            {"name": "face",        "dy_start": round(head_peak_dy, 4),
             "dy_end": round(neck_dy, 4),
             "description": "Visor/face region to neck valley"},
            {"name": "neck",        "dy_start": round(neck_dy, 4),
             "dy_end": round(shoulder_dy * 0.65 + neck_dy * 0.35, 4),
             "description": "Neck valley to upper shoulder transition"},
            {"name": "shoulders",   "dy_start": round(shoulder_dy * 0.65 + neck_dy * 0.35, 4),
             "dy_end": round(shoulder_dy + 0.15, 4),
             "description": "Shoulder slope to just below shoulder peak"},
            {"name": "upper_torso", "dy_start": round(shoulder_dy + 0.15, 4),
             "dy_end": round(waist_dy, 4),
             "description": "Chest/upper torso to waist"},
            {"name": "lower_torso", "dy_start": round(waist_dy, 4),
             "dy_end": round(hip_dy, 4),
             "description": "Waist to hip peak (abdomen/pelvis)"},
            {"name": "upper_leg",   "dy_start": round(hip_dy, 4),
             "dy_end": round(knee_dy, 4),
             "description": "Hip peak to knee valley (thigh)"},
            {"name": "lower_leg",   "dy_start": round(knee_dy, 4),
             "dy_end": round(ankle_dy, 4),
             "description": "Knee valley to ankle valley (shin/calf)"},
            {"name": "foot",        "dy_start": round(ankle_dy, 4),
             "dy_end": round(sole_dy, 4),
             "description": "Ankle to sole (boot/foot)"},
        ],
    }
    print("  Body regions: 9 zones")


def phase_09_cross_section_topology(data, rdy_sorted, sole_dy):
    """Count contour crossings at each horizontal scanline."""
    profile = {}
    for dy_val in np.arange(0.1, sole_dy, 0.1):
        crossings = 0
        for i in range(len(rdy_sorted) - 1):
            if (rdy_sorted[i] <= dy_val < rdy_sorted[i + 1]) or \
               (rdy_sorted[i + 1] <= dy_val < rdy_sorted[i]):
                crossings += 1
        profile[f"{dy_val:.1f}"] = {
            "crossings": crossings,
            "pairs": crossings // 2,
            "interpretation": (
                "single_body" if crossings <= 2 else
                "arm_separated" if crossings <= 4 else
                "complex_topology"
            ),
        }
    data["cross_section_topology"] = {
        "note": (
            "Number of times the right-side contour crosses each horizontal scanline. "
            "crossings=2 → single body outline; crossings=4 → arm separated from torso; "
            "crossings>4 → complex features (armor plates, weapons, etc.)"
        ),
        "profile": profile,
    }
    print(f"  Topology: {len(profile)} levels")


def phase_10_fourier_descriptors(data, right_dx, right_dy):
    """Compute 12-harmonic Elliptic Fourier Descriptors."""
    pts = np.column_stack([right_dx, right_dy])
    diffs = np.diff(pts, axis=0)
    seg_len = np.sqrt((diffs**2).sum(axis=1))
    T = seg_len.sum()
    t_cumul = np.concatenate([[0], np.cumsum(seg_len)])
    t_norm = t_cumul / T

    n_harmonics = 12
    coeffs = []
    for n in range(1, n_harmonics + 1):
        cos_t = np.cos(2 * np.pi * n * t_norm)
        sin_t = np.sin(2 * np.pi * n * t_norm)
        a_x = 2 * _trapz(right_dx * cos_t, t_norm)
        b_x = 2 * _trapz(right_dx * sin_t, t_norm)
        a_y = 2 * _trapz(right_dy * cos_t, t_norm)
        b_y = 2 * _trapz(right_dy * sin_t, t_norm)
        amp = np.sqrt(a_x**2 + b_x**2 + a_y**2 + b_y**2)
        coeffs.append({
            "harmonic": n,
            "a_x": round(float(a_x), 6), "b_x": round(float(b_x), 6),
            "a_y": round(float(a_y), 6), "b_y": round(float(b_y), 6),
            "amplitude": round(float(amp), 6),
        })

    total_energy = sum(c["amplitude"]**2 for c in coeffs)
    data["fourier_descriptors"] = {
        "note": (
            "Elliptic Fourier Descriptors (EFD) of the right-side contour. "
            "12 harmonics capture the shape signature from coarse to fine."
        ),
        "computed_on": "right_half",
        "amplitude_formula": "frobenius_norm: sqrt(a_x^2 + b_x^2 + a_y^2 + b_y^2)",
        "n_harmonics": n_harmonics,
        "perimeter_hu": round(float(T), 4),
        "coefficients": coeffs,
        "energy_concentration": {
            "note": "Fraction of total shape energy in first N harmonics",
            "harmonics_1_4": round(sum(c["amplitude"]**2 for c in coeffs[:4]) / total_energy, 4),
            "harmonics_1_8": round(sum(c["amplitude"]**2 for c in coeffs[:8]) / total_energy, 4),
        },
    }
    print(f"  Fourier: {n_harmonics} harmonics, perimeter={T:.4f} HU")


def phase_11_meta_enrichment(data, contour, dx_arr, dy_arr):
    """Add contour quality metrics and bounding box."""
    diffs = np.diff(contour, axis=0)
    seg_lens = np.sqrt((diffs**2).sum(axis=1))

    data["meta"]["contour_quality"] = {
        "total_perimeter_hu": round(float(seg_lens.sum()), 4),
        "right_perimeter_hu": round(float(seg_lens[:RIGHT_END - 1].sum()), 4),
        "mean_segment_length": round(float(seg_lens.mean()), 6),
        "std_segment_length": round(float(seg_lens.std()), 6),
        "min_segment_length": round(float(seg_lens.min()), 6),
        "max_segment_length": round(float(seg_lens.max()), 6),
        "segment_length_cv": round(float(seg_lens.std() / seg_lens.mean()), 4) if seg_lens.mean() > 0 else None,
        "note": "Coefficient of variation (CV) < 0.5 indicates uniform point spacing; > 1.0 indicates highly irregular sampling",
    }
    data["meta"]["bounding_box_hu"] = {
        "dx_min": round(float(dx_arr.min()), 4),
        "dx_max": round(float(dx_arr.max()), 4),
        "dy_min": round(float(dy_arr.min()), 4),
        "dy_max": round(float(dy_arr.max()), 4),
        "width": round(float(dx_arr.max() - dx_arr.min()), 4),
        "height": round(float(dy_arr.max() - dy_arr.min()), 4),
        "aspect_ratio": (
            round(float((dy_arr.max() - dy_arr.min()) / (dx_arr.max() - dx_arr.min())), 4)
            if (dx_arr.max() - dx_arr.min()) > 0 else None
        ),
    }
    print("  Meta: quality + bbox")


# ═══════════════════════════════════════════════════════════════════
# PIPELINE PHASES  (v3.0 → v3.1 from refine_v3.py)
# ═══════════════════════════════════════════════════════════════════

def phase_12_landmark_validation(data):
    """Rename anatomically-anomalous landmarks."""
    lm_map = {lm["name"]: lm for lm in data["landmarks"]}
    notes = []

    if "bust_peak" in lm_map and "armpit_valley" in lm_map:
        bp, av = lm_map["bust_peak"], lm_map["armpit_valley"]
        if bp["dx"] < av["dx"]:
            for lm in data["landmarks"]:
                if lm["name"] == "bust_peak":
                    lm["name"] = "chest_inflection"
                    lm["description"] = (
                        "Local width maximum between shoulder slope and waist. "
                        "On this armored figure, narrower than the arm-torso junction below — "
                        "not a true anatomical bust peak but a chest plate contour feature."
                    )
                    lm["note"] = f"Renamed from bust_peak: dx={bp['dx']:.4f} < armpit dx={av['dx']:.4f}"
                    notes.append(
                        f"bust_peak renamed to chest_inflection: dx={bp['dx']:.4f} is narrower "
                        f"than armpit_valley dx={av['dx']:.4f}, inconsistent with anatomical bust"
                    )
                    break

    # re-read after possible rename
    lm_map = {lm["name"]: lm for lm in data["landmarks"]}
    if "crotch_valley" in lm_map and "mid_thigh" in lm_map:
        cr, mt = lm_map["crotch_valley"], lm_map["mid_thigh"]
        if cr["dy"] > mt["dy"]:
            for lm in data["landmarks"]:
                if lm["name"] == "crotch_valley":
                    lm["name"] = "thigh_narrowing"
                    lm["description"] = (
                        "Local width minimum in the upper leg. Below the geometric mid-thigh — "
                        "on this armored figure, likely the lower edge of thigh armor plates."
                    )
                    lm["note"] = f"Renamed from crotch_valley: dy={cr['dy']:.4f} is below mid_thigh dy={mt['dy']:.4f}"
                    notes.append(
                        f"crotch_valley renamed to thigh_narrowing: dy={cr['dy']:.4f} "
                        f"is below mid_thigh dy={mt['dy']:.4f}"
                    )
                    break

    data["meta"]["landmark_validation"] = {
        "anomalies_detected": len(notes),
        "corrections_applied": notes,
        "note": (
            "Landmarks derived from contour extrema may not match anatomical expectations "
            "on armored/stylized figures. Anomalous labels are renamed to describe the actual "
            "geometric feature rather than the assumed anatomy."
        ),
    }
    print(f"  Landmark validation: {len(notes)} corrections")


def phase_13_inflection_filtering(data):
    """Filter inflection points by significance threshold."""
    if "curvature" not in data or "inflections" not in data["curvature"]:
        return
    raw = data["curvature"]["inflections"]["points"]
    threshold = 0.02
    significant = []
    for inf in raw:
        delta_k = abs(inf["kappa_before"] - inf["kappa_after"])
        if delta_k > threshold:
            inf["delta_kappa"] = round(delta_k, 6)
            significant.append(inf)

    dks = [inf["delta_kappa"] for inf in significant] if significant else [0]
    data["curvature"]["inflections"].update({
        "raw_count": len(raw),
        "significance_threshold": threshold,
        "selection_method": f"|Δκ| > {threshold}",
        "delta_kappa_range": [round(min(dks), 6), round(max(dks), 6)],
        "points": significant,
        "count": len(significant),
        "note": (
            f"Filtered from {len(raw)} raw sign-changes to {len(significant)} "
            f"significant inflections (|Δκ| > {threshold})."
        ),
    })
    print(f"  Inflections: {len(raw)} raw → {len(significant)} significant")


def phase_14_improved_stroke_semantics(data):
    """Multi-feature + region-aware stroke classification (overwrites phase_06)."""
    for stroke in data["strokes"]:
        region = stroke.get("region", "unknown")
        arc = stroke.get("arc_length_hu", 0)
        sin = stroke.get("sinuosity", 1.0) or 1.0
        orient = stroke.get("orientation_deg")
        max_k = stroke.get("max_abs_curvature", 0) or 0
        bbox = stroke.get("bbox", {})
        bbox_w = bbox.get("dx_max", 0) - bbox.get("dx_min", 0)
        bbox_h = bbox.get("dy_max", 0) - bbox.get("dy_min", 0)
        bbox_aspect = bbox_h / bbox_w if bbox_w > 1e-4 else float("inf")

        stype, conf = "surface_detail", 0.3

        if arc < 0.06:
            stype, conf = "detail_mark", 0.5
        elif sin < 1.08 and bbox_aspect > 3.0 and orient is not None and abs(abs(orient) - 90) < 20:
            stype, conf = "vertical_division", 0.55
        elif sin < 1.08 and bbox_aspect < 0.3 and orient is not None and abs(orient) < 25:
            stype, conf = "horizontal_band", 0.55
        elif sin < 1.08 and arc > 0.2:
            stype, conf = "panel_edge", 0.5
        elif sin < 1.12 and arc < 0.2:
            stype, conf = "seam", 0.45
        elif max_k > 2.0 and arc < 0.15:
            stype, conf = "articulation_detail", 0.4
        elif region == "head" and arc > 0.1:
            stype, conf = "helmet_detail", 0.45
        elif region == "feet":
            stype, conf = ("boot_ornament", 0.4) if sin > 1.3 else ("boot_structure", 0.45)
        elif sin > 1.3 and arc > 0.2:
            stype, conf = "decorative_line", 0.4
        elif sin > 1.8:
            stype, conf = "ornamental_curve", 0.4

        stroke["semantic_type"] = stype
        stroke["semantic_confidence"] = conf

    counts = Counter(s["semantic_type"] for s in data["strokes"])
    print(f"  Stroke semantics: {dict(counts)}")


def phase_15_width_profile(data, interp, crown_dy, sole_dy):
    """Clean 1D width signal dx(dy) with slope, curvature, filtered extrema."""
    dy_dense = np.arange(crown_dy + 0.01, sole_dy, 0.01)
    dx_dense = np.array([width_at(interp, d) for d in dy_dense])
    valid = np.isfinite(dx_dense)
    dy_v, dx_v = dy_dense[valid], np.maximum(dx_dense[valid], 0.0)

    dx_d1 = np.gradient(dx_v, dy_v)
    dx_d2 = np.gradient(dx_d1, dy_v)

    # Subsample for storage (every 5th → 0.05 HU effective)
    step = 5
    samples = []
    for i in range(0, len(dy_v), step):
        entry = {"dy": round(float(dy_v[i]), 4),
                 "dx": round(float(dx_v[i]), 4),
                 "full_width": round(float(2 * dx_v[i]), 4)}
        if i < len(dx_d1):
            entry["slope"] = round(float(dx_d1[i]), 4)
        if i < len(dx_d2):
            entry["curvature"] = round(float(dx_d2[i]), 4)
        samples.append(entry)

    # Local extrema
    def find_extrema_with_prominence(dx_vals, dy_vals, min_prom=0.02):
        maxima, minima = [], []
        for i in range(1, len(dx_vals) - 1):
            if dx_vals[i] > dx_vals[i - 1] and dx_vals[i] > dx_vals[i + 1]:
                maxima.append({"dy": round(float(dy_vals[i]), 4),
                               "dx": round(float(dx_vals[i]), 4),
                               "full_width": round(float(2 * dx_vals[i]), 4)})
            if dx_vals[i] < dx_vals[i - 1] and dx_vals[i] < dx_vals[i + 1]:
                minima.append({"dy": round(float(dy_vals[i]), 4),
                               "dx": round(float(dx_vals[i]), 4),
                               "full_width": round(float(2 * dx_vals[i]), 4)})

        def filter_prominent(extrema):
            if len(extrema) < 2:
                return extrema
            result = []
            for i, e in enumerate(extrema):
                prev_dx = extrema[i - 1]["dx"] if i > 0 else dx_vals[0]
                next_dx = extrema[i + 1]["dx"] if i < len(extrema) - 1 else dx_vals[-1]
                prom = min(abs(e["dx"] - prev_dx), abs(e["dx"] - next_dx))
                if prom >= min_prom:
                    e_copy = dict(e)
                    e_copy["prominence"] = round(prom, 4)
                    result.append(e_copy)
            return result

        return filter_prominent(maxima), filter_prominent(minima)

    sig_max, sig_min = find_extrema_with_prominence(dx_v, dy_v)

    data["width_profile"] = {
        "note": (
            "Width profile: right-side dx as a function of dy, sampled at 0.05 HU from the cubic-spline "
            "interpolation of the right contour. slope = d(dx)/d(dy). curvature = d²(dx)/d(dy)². "
            "Extrema filtered by prominence > 0.02 HU."
        ),
        "resolution_hu": 0.05,
        "sample_count": len(samples),
        "samples": samples,
        "extrema": {
            "prominence_threshold": 0.02,
            "maxima": {"count": len(sig_max), "points": sig_max,
                       "note": "Local width peaks — shoulders, hips, calves, armor plates"},
            "minima": {"count": len(sig_min), "points": sig_min,
                       "note": "Local width valleys — neck, waist, knee, ankle"},
        },
        "statistics": {
            "mean_dx": round(float(dx_v.mean()), 4),
            "std_dx": round(float(dx_v.std()), 4),
            "max_dx": round(float(dx_v.max()), 4),
            "max_dx_dy": round(float(dy_v[dx_v.argmax()]), 4),
            "min_dx": round(float(dx_v.min()), 4),
            "min_dx_dy": round(float(dy_v[dx_v.argmin()]), 4),
            "mean_full_width": round(float(2 * dx_v.mean()), 4),
        },
    }
    print(f"  Width profile: {len(samples)} samples, {len(sig_max)} maxima, {len(sig_min)} minima")


def phase_16_area_profile(data, interp):
    """Silhouette area: total, per-region, cumulative at landmarks."""
    wp = data["width_profile"]["samples"]
    dy_v = np.array([s["dy"] for s in wp])
    dx_v = np.array([s["dx"] for s in wp])

    total_area = float(_trapz(2 * dx_v, dy_v))

    per_region = []
    for region in data["body_regions"]["regions"]:
        dy_lo, dy_hi = region["dy_start"], region["dy_end"]
        mask = (dy_v >= dy_lo) & (dy_v <= dy_hi)
        if mask.sum() > 1:
            ra = float(_trapz(2 * dx_v[mask], dy_v[mask]))
            rmw = float(2 * dx_v[mask].mean())
            rxw = float(2 * dx_v[mask].max())
        else:
            ra = rmw = rxw = 0.0
        rh = dy_hi - dy_lo
        per_region.append({
            "name": region["name"],
            "dy_range": [round(dy_lo, 4), round(dy_hi, 4)],
            "height_hu": round(rh, 4),
            "area_hu2": round(ra, 4),
            "area_fraction": round(ra / total_area, 4) if total_area > 0 else 0,
            "mean_full_width_hu": round(rmw, 4),
            "max_full_width_hu": round(rxw, 4),
            "aspect_ratio": round(rh / rmw, 4) if rmw > 0 else None,
        })

    cumulative = []
    for lm in data["landmarks"]:
        mask = dy_v <= lm["dy"]
        ca = float(_trapz(2 * dx_v[mask], dy_v[mask])) if mask.sum() > 1 else 0.0
        cumulative.append({
            "landmark": lm["name"], "dy": lm["dy"],
            "cumulative_area_hu2": round(ca, 4),
            "fraction_of_total": round(ca / total_area, 4) if total_area > 0 else 0,
        })

    data["area_profile"] = {
        "note": (
            "Silhouette area computed as the integral of bilateral width (2·dx) with respect to dy. "
            "Units are HU²."
        ),
        "total_area_hu2": round(total_area, 4),
        "per_region": per_region,
        "cumulative_at_landmarks": cumulative,
    }
    print(f"  Area profile: total={total_area:.4f} HU²")


def phase_17_contour_normals(data, right_dx, right_dy):
    """Outward-facing unit normals along the right-side contour."""
    pts = np.column_stack([right_dx, right_dy])
    tangent = np.zeros_like(pts)
    tangent[0] = pts[1] - pts[0]
    tangent[-1] = pts[-1] - pts[-2]
    for i in range(1, len(pts) - 1):
        tangent[i] = pts[i + 1] - pts[i - 1]
    tang_len = np.sqrt((tangent**2).sum(axis=1))
    tang_len[tang_len < 1e-12] = 1e-12
    tangent /= tang_len[:, None]
    normals = np.column_stack([tangent[:, 1], -tangent[:, 0]])

    step = 10
    samples = [
        {"index": i,
         "dx": round(float(pts[i, 0]), 4), "dy": round(float(pts[i, 1]), 4),
         "nx": round(float(normals[i, 0]), 4), "ny": round(float(normals[i, 1]), 4)}
        for i in range(0, len(pts), step)
    ]
    data["contour_normals"] = {
        "note": "Outward-facing unit normal vectors along the right-side contour, subsampled every 10 points.",
        "sample_step": step,
        "sample_count": len(samples),
        "full_point_count": len(pts),
        "samples": samples,
        "computed_on": "right_half",
    }
    print(f"  Contour normals: {len(samples)} samples")


def phase_18_shape_vector(data, interp, crown_dy, sole_dy):
    """Fixed 21-dim shape descriptor for ML."""
    n_w = 16
    dy_pts = np.linspace(crown_dy + 0.1, sole_dy - 0.1, n_w)
    widths = [width_at(interp, d) for d in dy_pts]
    max_w = max(w for w in widths if np.isfinite(w))
    wvec = [round(float(w / max_w), 4) if np.isfinite(w) and max_w > 0 else 0.0 for w in widths]

    comp = data["proportion"].get("composite_ratios", {})
    vector = wvec + [
        comp.get("shoulder_to_hip_width", 0),
        comp.get("waist_to_hip_width", 0),
        comp.get("upper_to_lower_body", 0),
        comp.get("torso_to_leg", 0),
        data["proportion"].get("head_count_total", 0),
    ]
    data["shape_vector"] = {
        "note": "Fixed-dimension shape descriptor for ML. 16 width samples + 5 ratios = 21 dims.",
        "dimension": 21,
        "components": [
            "width_0..width_15: normalized bilateral width at 16 dy levels",
            "shoulder_hip_ratio", "waist_hip_ratio",
            "upper_lower_body_ratio", "torso_leg_ratio", "head_count",
        ],
        "vector": vector,
        "dy_sample_points": [round(float(d), 4) for d in dy_pts],
        "normalization": {"width_max_dx": round(max_w, 4),
                          "method": "divide by max right-side dx across sample points"},
    }
    print("  Shape vector: dim=21")


def phase_19_enrich_body_regions(data):
    """Add stroke counts and landmark lists per body region."""
    for region in data["body_regions"]["regions"]:
        dy_lo, dy_hi = region["dy_start"], region["dy_end"]
        stroke_ids = []
        for s in data["strokes"]:
            bbox = s.get("bbox", {})
            if bbox.get("dy_min", 0) < dy_hi and bbox.get("dy_max", 0) > dy_lo:
                stroke_ids.append(s["id"])
        region["stroke_count"] = len(stroke_ids)
        region["stroke_ids"] = stroke_ids
        region["landmarks"] = [
            lm["name"] for lm in data["landmarks"]
            if dy_lo <= lm["dy"] < dy_hi
        ]
    print("  Body regions: enriched with stroke counts + landmarks")


# ═══════════════════════════════════════════════════════════════════
# PIPELINE PHASES  (v3.1 → v4.0 from cross_domain_enrich.py)
# ═══════════════════════════════════════════════════════════════════

def phase_20_hu_moments(data, sym_all):
    """Hu's 7 invariant moments."""
    x, y = sym_all[:, 0], sym_all[:, 1]
    xbar, ybar = x.mean(), y.mean()
    cx, cy = x - xbar, y - ybar

    mu = {}
    for p in range(4):
        for q in range(4):
            if p + q <= 3:
                mu[(p, q)] = float(np.sum(cx**p * cy**q))
    m00 = mu[(0, 0)]
    eta = {}
    for (p, q), val in mu.items():
        if p + q >= 2:
            eta[(p, q)] = val / (m00 ** (1 + (p + q) / 2)) if m00 > 0 else 0.0

    e = lambda p, q: eta.get((p, q), 0.0)
    hu = [
        e(2,0) + e(0,2),
        (e(2,0) - e(0,2))**2 + 4 * e(1,1)**2,
        (e(3,0) - 3*e(1,2))**2 + (3*e(2,1) - e(0,3))**2,
        (e(3,0) + e(1,2))**2 + (e(2,1) + e(0,3))**2,
        ((e(3,0) - 3*e(1,2)) * (e(3,0) + e(1,2)) *
         ((e(3,0) + e(1,2))**2 - 3*(e(2,1) + e(0,3))**2) +
         (3*e(2,1) - e(0,3)) * (e(2,1) + e(0,3)) *
         (3*(e(3,0) + e(1,2))**2 - (e(2,1) + e(0,3))**2)),
        ((e(2,0) - e(0,2)) *
         ((e(3,0) + e(1,2))**2 - (e(2,1) + e(0,3))**2) +
         4 * e(1,1) * (e(3,0) + e(1,2)) * (e(2,1) + e(0,3))),
        ((3*e(2,1) - e(0,3)) * (e(3,0) + e(1,2)) *
         ((e(3,0) + e(1,2))**2 - 3*(e(2,1) + e(0,3))**2) -
         (e(3,0) - 3*e(1,2)) * (e(2,1) + e(0,3)) *
         (3*(e(3,0) + e(1,2))**2 - (e(2,1) + e(0,3))**2)),
    ]
    hu_log = [round(-np.sign(h) * np.log10(abs(h)), 6) if abs(h) > 1e-30 else 0.0 for h in hu]

    data["hu_moments"] = {
        "note": (
            "Hu's 7 invariant moments — invariant to translation, scale, and rotation. "
            "log_transformed: −sign(h)·log₁₀(|h|)."
        ),
        "reference": "Hu, M-K. IRE Trans. Inform. Theory, IT-8:179–187, 1962.",
        "computed_on": "mirrored_full",
        "point_count": len(sym_all),
        "raw": [round(h, 10) for h in hu],
        "log_transformed": hu_log,
        "centroid": {"dx": round(float(xbar), 4), "dy": round(float(ybar), 4)},
    }
    print(f"  Hu moments (log): {hu_log}")


def phase_21_turning_function(data, contour_pts):
    """Cumulative tangent angle θ(s) parameterised by normalised arc-length.

    Operates on the full closed contour so that winding_number ≈ ±1
    (Hopf Umlaufsatz).
    """
    # Close the contour if not already closed
    if np.linalg.norm(contour_pts[0] - contour_pts[-1]) > 1e-8:
        pts = np.vstack([contour_pts, contour_pts[0:1]])
    else:
        pts = contour_pts

    diffs = np.diff(pts, axis=0)
    seg_lengths = np.sqrt((diffs**2).sum(axis=1))
    T = seg_lengths.sum()
    if T < 1e-10:
        return
    s_cumul = np.concatenate([[0], np.cumsum(seg_lengths)])
    s_norm = s_cumul / T
    angles = np.unwrap(np.arctan2(diffs[:, 1], diffs[:, 0]))
    s_uni = np.linspace(0, 1, 200)
    theta_uni = np.interp(s_uni, s_norm[:-1], angles)
    total_angle = float(theta_uni[-1] - theta_uni[0])
    omega = np.gradient(theta_uni, s_uni)
    max_idx = np.argmax(np.abs(omega))

    data["turning_function"] = {
        "note": (
            "Turning function θ(s): cumulative tangent angle of the full closed contour "
            "as a function of normalised arc-length s ∈ [0,1]."
        ),
        "reference": "Arkin, E. et al. IEEE TPAMI 13(3):209–216, 1991.",
        "computed_on": "mirrored_full",
        "perimeter_hu": round(float(T), 4),
        "total_angle_rad": round(total_angle, 4),
        "total_angle_deg": round(float(np.degrees(total_angle)), 2),
        "winding_number": round(total_angle / (2 * np.pi), 2),
        "sample_count": 50,
        "max_turning_rate": {
            "s": round(float(s_uni[max_idx]), 4),
            "omega": round(float(omega[max_idx]), 4),
            "note": "Location of sharpest turn (highest |dθ/ds|)",
        },
        "samples": [
            {"s": round(float(s_uni[i]), 4), "theta": round(float(theta_uni[i]), 4)}
            for i in range(0, 200, 4)
        ],
    }
    print(f"  Turning function: total={np.degrees(total_angle):.1f}°")


def phase_22_convex_hull(data, sym_all, right_pts, right_dx, right_dy, env_dx, env_dy):
    """Convex hull, solidity, negative space, concavity decomposition."""
    hull = ConvexHull(sym_all)
    hull_area = float(hull.volume)
    hull_perim = float(hull.area)
    sil_area = float(_trapz(2 * env_dx, env_dy))
    solidity = sil_area / hull_area if hull_area > 0 else 0

    # Concavity detection
    hull_boundary = sym_all[hull.vertices]
    hull_closed = np.vstack([hull_boundary, hull_boundary[0:1]])
    expanded = []
    for i in range(len(hull_closed) - 1):
        for t in np.linspace(0, 1, 20):
            expanded.append(hull_closed[i] * (1 - t) + hull_closed[i + 1] * t)
    tree = cKDTree(np.array(expanded))
    dists, _ = tree.query(right_pts)

    thresh = 0.1
    concavities = []
    start = None
    for i in range(len(dists)):
        if dists[i] > thresh and start is None:
            start = i
        elif (dists[i] <= thresh or i == len(dists) - 1) and start is not None:
            end = i if dists[i] <= thresh else i + 1
            rd = dists[start:end]
            mi = start + np.argmax(rd)
            concavities.append({
                "contour_index_range": [int(start), int(end - 1)],
                "dy_range": [round(float(right_dy[start]), 4), round(float(right_dy[end - 1]), 4)],
                "max_depth_hu": round(float(rd.max()), 4),
                "max_depth_at": {"dx": round(float(right_dx[mi]), 4), "dy": round(float(right_dy[mi]), 4)},
                "arc_span": int(end - start),
            })
            start = None
    concavities.sort(key=lambda c: c["max_depth_hu"], reverse=True)

    data["convex_hull"] = {
        "note": (
            "Convex hull of the full bilateral silhouette. "
            "Solidity = silhouette_area / hull_area (area-ratio convexity)."
        ),
        "reference": "Gonzalez, R.C. & Woods, R.E. 'Digital Image Processing.' 3rd ed., Prentice Hall, 2008. §11.3.",
        "solidity_formula": "A_shape / A_hull",
        "hull_area_hu2": round(hull_area, 4),
        "hull_perimeter_hu": round(hull_perim, 4),
        "silhouette_area_hu2": round(sil_area, 4),
        "negative_space_area_hu2": round(hull_area - sil_area, 4),
        "solidity": round(solidity, 4),
        "convexity_deficiency": round(1 - solidity, 4),
        "hull_vertex_count": len(hull.vertices),
        "concavities": {
            "threshold_hu": thresh,
            "count": len(concavities),
            "regions": concavities[:10],
            "note": "Major concavity regions sorted by max_depth_hu (deepest first).",
        },
    }
    print(f"  Convex hull: solidity={solidity:.4f}, concavities={len(concavities)}")


def phase_23_gesture_line(data, crown_dy, fig_height):
    """PCA-based action line, lean, contrapposto."""
    lm_pts = np.array([[l["dx"], l["dy"]] for l in data["landmarks"]])
    centroid = lm_pts.mean(axis=0)
    centered = lm_pts - centroid
    cov_mat = np.cov(centered.T)
    eigenvalues, eigenvectors = np.linalg.eigh(cov_mat)
    order = eigenvalues.argsort()[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]

    primary = eigenvectors[:, 0]
    secondary = eigenvectors[:, 1]
    proj_sec = centered @ secondary
    proj_pri = centered @ primary
    coeffs = P.polyfit(proj_pri, proj_sec, 3)

    max_dev = float(np.max(np.abs(proj_sec)))
    gesture_energy = float(np.sqrt(np.mean(proj_sec**2)))
    lean_angle = float(np.degrees(np.arctan2(primary[0], primary[1])))

    upper = [l for l in data["landmarks"] if l["dy"] < crown_dy + fig_height * 0.5]
    lower = [l for l in data["landmarks"] if l["dy"] >= crown_dy + fig_height * 0.5]
    contra = abs(np.mean([l["dx"] for l in upper]) - np.mean([l["dx"] for l in lower])) / fig_height

    data["gesture_line"] = {
        "note": "PCA on landmark point cloud — captures tilt and elongation (renamed from gesture_line to principal_axes in schema).",
        "reference": "Jolliffe, I.T. 'Principal Component Analysis.' 2nd ed., Springer, 2002.",
        "primary_axis": {
            "direction": [round(float(primary[0]), 6), round(float(primary[1]), 6)],
            "eigenvalue": round(float(eigenvalues[0]), 6),
            "explained_variance_ratio": round(float(eigenvalues[0] / eigenvalues.sum()), 4),
        },
        "secondary_axis": {
            "direction": [round(float(secondary[0]), 6), round(float(secondary[1]), 6)],
            "eigenvalue": round(float(eigenvalues[1]), 6),
        },
        "centroid": {"dx": round(float(centroid[0]), 4), "dy": round(float(centroid[1]), 4)},
        "cubic_fit_coefficients": [round(float(c), 6) for c in coeffs],
        "lean_angle_deg": round(lean_angle, 2),
        "lean_interpretation": (
            "vertical" if abs(lean_angle) < 2 else
            "slight_lean_right" if lean_angle > 0 else "slight_lean_left"
        ),
        "gesture_energy": round(gesture_energy, 6),
        "max_lateral_deviation_hu": round(max_dev, 4),
        "contrapposto_score": round(float(contra), 6),
        "contrapposto_interpretation": (
            "none" if contra < 0.005 else "subtle" if contra < 0.02 else
            "moderate" if contra < 0.05 else "strong"
        ),
        "landmark_deviations": [
            {"name": data["landmarks"][i]["name"],
             "dy": data["landmarks"][i]["dy"],
             "lateral_dev": round(float(proj_sec[i]), 4)}
            for i in range(len(data["landmarks"]))
        ],
    }
    print(f"  Gesture: lean={lean_angle:.2f}°, energy={gesture_energy:.4f}")


def phase_24_curvature_scale_space(data, right_pts, right_dx, right_dy):
    """Multi-scale curvature (CSS) at 5 Gaussian smoothing scales."""
    sigmas = [0, 2, 5, 10, 20]
    labels = ["raw", "fine", "medium", "coarse", "very_coarse"]

    scales = []
    all_top_dys = []
    for sigma, label in zip(sigmas, labels):
        if sigma > 0:
            xs = gaussian_filter1d(right_pts[:, 0], sigma=sigma, mode="nearest")
            ys = gaussian_filter1d(right_pts[:, 1], sigma=sigma, mode="nearest")
        else:
            xs, ys = right_pts[:, 0].copy(), right_pts[:, 1].copy()
        kappa = parametric_curvature(xs, ys)
        abs_k = np.abs(kappa)

        zc = sum(1 for i in range(1, len(kappa)) if kappa[i - 1] * kappa[i] < 0)
        top5 = np.argsort(abs_k)[-5:][::-1]
        extrema = [{"contour_index": int(idx), "dy": round(float(right_dy[idx]), 4),
                     "dx": round(float(right_dx[idx]), 4), "kappa": round(float(kappa[idx]), 4)}
                    for idx in top5]
        all_top_dys.extend(e["dy"] for e in extrema)

        kappa_sub = [{"index": int(i), "dy": round(float(right_dy[i]), 4),
                       "kappa": round(float(kappa[i]), 4)}
                      for i in range(0, len(kappa), 20)]

        scales.append({
            "label": label, "sigma": sigma, "zero_crossings": zc,
            "mean_abs_kappa": round(float(np.mean(abs_k)), 4),
            "max_abs_kappa": round(float(np.max(abs_k)), 4),
            "top_5_extrema": extrema, "kappa_samples": kappa_sub,
        })

    dy_bins = [round(d / 0.3) * 0.3 for d in all_top_dys]
    bin_counts = Counter(dy_bins)
    persistent = [
        {"dy_bin": round(dy, 2), "persistence_count": cnt, "structural": cnt >= 3}
        for dy, cnt in sorted(bin_counts.items()) if cnt >= 2
    ]

    data["curvature_scale_space"] = {
        "note": "Curvature Scale Space (CSS): κ at 5 Gaussian smoothing scales.",
        "computed_on": "right_half",
        "seam_handling": "none",
        "reference": "Mokhtarian, F. & Mackworth, A. IEEE TPAMI 14(8):789–805, 1992.",
        "persistent_features": {
            "note": "dy locations appearing in top-5 across ≥2 scales. structural=true if ≥3.",
            "features": persistent,
        },
        "scales": scales,
    }
    print(f"  CSS: {len(sigmas)} scales, {len(persistent)} persistent features")


def phase_25_style_deviation(data, crown_dy, fig_height):
    """Deviation from Loomis 8-head canon."""
    lm_map = {l["name"]: l for l in data["landmarks"]}

    canon_frac = {"crown": 0, "chin": 1/8, "nipple_line": 2/8, "navel": 3/8,
                  "crotch": 4/8, "mid_thigh": 5/8, "knee": 6/8, "mid_shin": 7/8, "sole": 1}
    canon_width = {"head": 1/8, "shoulders": 2/8, "waist": 1.2/8, "hips": 1.5/8}
    lm_to_canon = {"crown": "crown", "chin": "chin", "navel_estimate": "navel",
                   "mid_thigh": "mid_thigh", "knee_valley": "knee", "mid_shin": "mid_shin", "sole": "sole"}

    measured_frac = {l["name"]: (l["dy"] - crown_dy) / fig_height for l in data["landmarks"]}

    pos_devs = []
    for our, canon in lm_to_canon.items():
        if our in measured_frac and canon in canon_frac:
            m, c = measured_frac[our], canon_frac[canon]
            d = m - c
            pos_devs.append({
                "landmark": our, "canon_name": canon,
                "measured_fraction": round(m, 4), "canon_fraction": round(c, 4),
                "deviation": round(d, 4),
                "interpretation": "higher_than_canon" if d > 0.02 else "lower_than_canon" if d < -0.02 else "matches_canon",
            })

    sw = (lm_map["shoulder_peak"]["dx"] * 2) / fig_height
    hw = (lm_map["hip_peak"]["dx"] * 2) / fig_height
    ww = (lm_map["waist_valley"]["dx"] * 2) / fig_height
    hdw = (lm_map["head_peak"]["dx"] * 2) / fig_height
    width_devs = [
        {"feature": "head_width", "measured": round(hdw, 4), "canon": round(canon_width["head"], 4), "deviation": round(hdw - canon_width["head"], 4)},
        {"feature": "shoulder_width", "measured": round(sw, 4), "canon": round(canon_width["shoulders"], 4), "deviation": round(sw - canon_width["shoulders"], 4)},
        {"feature": "waist_width", "measured": round(ww, 4), "canon": round(canon_width["waist"], 4), "deviation": round(ww - canon_width["waist"], 4)},
        {"feature": "hip_width", "measured": round(hw, 4), "canon": round(canon_width["hips"], 4), "deviation": round(hw - canon_width["hips"], 4)},
    ]

    all_devs = [s["deviation"] for s in pos_devs] + [w["deviation"] for w in width_devs]
    l2 = float(np.sqrt(sum(d**2 for d in all_devs)))

    data["style_deviation"] = {
        "note": "Signed deviation from Loomis 8-head academic canon. Deviations are in the schema's native HU (crown-to-neck_valley).",
        "reference": "Loomis, A. 'Figure Drawing for All It's Worth.' Viking, 1943. pp. 28–30.",
        "canon": "loomis_8_head_academic",
        "figure_head_count": data["proportion"]["head_count_total"],
        "canon_head_count": 8.0,
        "normalized_to_standard_hu": False,
        "position_deviations": pos_devs,
        "width_deviations": width_devs,
        "l2_stylisation_distance": round(l2, 4),
        "interpretation": (
            "near_photorealistic" if l2 < 0.05 else "moderate_stylisation" if l2 < 0.15 else
            "heavy_stylisation" if l2 < 0.25 else "extreme_stylisation"
        ),
    }
    print(f"  Style deviation: L2={l2:.4f} ({data['style_deviation']['interpretation']})")


def phase_26_volumetric_estimates(data, env_dx, env_dy, fig_height):
    """Cylindrical, ellipsoidal, and Pappus volume approximations."""
    vol_cyl = float(np.pi * _trapz(env_dx**2, env_dy))
    vol_ell = vol_cyl / 2
    sil_area = float(_trapz(2 * env_dx, env_dy))
    int_dx = float(_trapz(env_dx, env_dy))
    x_bar = float(_trapz(env_dx * env_dx, env_dy) / int_dx) if int_dx > 0 else 0
    vol_pappus = 2 * np.pi * x_bar * sil_area / 2

    scale_cm = 170.0 / fig_height

    region_vols = []
    for region in data["body_regions"]["regions"]:
        mask = (env_dy >= region["dy_start"]) & (env_dy <= region["dy_end"])
        rv = float(np.pi * _trapz(env_dx[mask]**2, env_dy[mask])) if mask.sum() > 1 else 0.0
        region_vols.append({
            "name": region["name"],
            "volume_hu3_cylindrical": round(rv, 4),
            "volume_cm3_cylindrical": round(rv * scale_cm**3, 1),
            "fraction": round(rv / vol_cyl, 4) if vol_cyl > 0 else 0,
        })

    data["volumetric_estimates"] = {
        "note": "Three volumetric approximations from the 2D silhouette.",
        "assumptions": {
            "canonical_height_cm": 170.0,
            "scale_cm_per_hu": round(scale_cm, 4),
            "figure_height_hu": round(fig_height, 4),
        },
        "cylindrical": {"volume_hu3": round(vol_cyl, 4), "volume_cm3": round(vol_cyl * scale_cm**3, 1),
                        "volume_liters": round(vol_cyl * scale_cm**3 / 1000, 2), "method": "V = π ∫ dx² dy"},
        "ellipsoidal": {"volume_hu3": round(vol_ell, 4), "volume_cm3": round(vol_ell * scale_cm**3, 1),
                        "volume_liters": round(vol_ell * scale_cm**3 / 1000, 2), "method": "V = (π/2) ∫ dx² dy"},
        "pappus": {"volume_hu3": round(float(vol_pappus), 4),
                   "volume_cm3": round(float(vol_pappus * scale_cm**3), 1),
                   "volume_liters": round(float(vol_pappus * scale_cm**3 / 1000), 2),
                   "method": "V = 2π · x̄ · A_right_half", "centroid_x_hu": round(x_bar, 4)},
        "per_region": region_vols,
    }
    print(f"  Volumes: cyl={vol_cyl:.4f} ell={vol_ell:.4f} pappus={vol_pappus:.4f} HU³")


def phase_27_biomechanics(data, fig_height, crown_dy):
    """Dempster/Winter segment mass, CoM, radius of gyration."""
    lm_map = {l["name"]: l for l in data["landmarks"]}
    scale_cm = 170.0 / fig_height

    # CoM fractions re-derived for crown→neck_valley endpoints per
    # de Leva (1996) Table 4 and Plagenhoef et al. (1983).
    # head_neck com_proximal_fraction ≈ 0.50 (crown→neck_valley),
    # NOT Winter's 1.0 which assumes C7-T1→ear-canal endpoints.
    WINTER = {
        "head_neck":  {"mf": 0.0681, "com": 0.5002, "rc": 0.495, "rp": 0.495, "prox": "crown",       "dist": "neck_valley",  "note": "Head+neck. CoM re-derived for crown→neck_valley endpoints (de Leva 1996)."},
        "trunk":      {"mf": 0.4270, "com": 0.3782, "rc": 0.3076,"rp": 0.4890,"prox": "shoulder_peak","dist": "hip_peak",     "note": "Full trunk."},
        "upper_arm":  {"mf": 0.0255, "com": 0.5754, "rc": 0.2610,"rp": 0.2780,"note": "Not measurable from frontal silhouette."},
        "forearm":    {"mf": 0.0138, "com": 0.4559, "rc": 0.2610,"rp": 0.2780,"note": "Not measurable from frontal silhouette."},
        "hand":       {"mf": 0.0056, "com": 0.7474, "rc": 0.2610,"rp": 0.2780,"note": "Not measurable from frontal silhouette."},
        "thigh":      {"mf": 0.1478, "com": 0.3612, "rc": 0.3690,"rp": 0.3690,"prox": "hip_peak",    "dist": "knee_valley"},
        "shank":      {"mf": 0.0481, "com": 0.4416, "rc": 0.2710,"rp": 0.2710,"prox": "knee_valley", "dist": "ankle_valley"},
        "foot":       {"mf": 0.0129, "com": 0.4014, "rc": 0.2990,"rp": 0.2990,"prox": "ankle_valley","dist": "sole"},
    }

    segments = []
    for name, p in WINTER.items():
        entry = {"segment": name, "mass_fraction": p["mf"],
                 "com_proximal_fraction": p["com"], "rog_com_fraction": p["rc"],
                 "rog_proximal_fraction": p["rp"]}
        if "prox" in p:
            entry["proximal_landmark"] = p["prox"]
        if "dist" in p:
            entry["distal_landmark"] = p["dist"]
        if "prox" in p and "dist" in p and p["prox"] in lm_map and p["dist"] in lm_map:
            pdy, ddy = lm_map[p["prox"]]["dy"], lm_map[p["dist"]]["dy"]
            sl = abs(ddy - pdy)
            entry["segment_length_hu"] = round(sl, 4)
            entry["segment_length_cm"] = round(sl * scale_cm, 2)
            com_dy = pdy + p["com"] * (ddy - pdy)
            entry["com_position"] = {"dy": round(com_dy, 4), "dy_cm": round(com_dy * scale_cm, 2)}
            entry["radius_of_gyration_hu"] = round(p["rc"] * sl, 4)
            entry["radius_of_gyration_cm"] = round(p["rc"] * sl * scale_cm, 2)
        if "note" in p:
            entry["note"] = p["note"]
        segments.append(entry)

    total_com, total_mf = 0, 0
    for seg in segments:
        if "com_position" in seg:
            w = seg["mass_fraction"]
            total_com += seg["com_position"]["dy"] * w
            total_mf += w
            if seg["segment"] in ("thigh", "shank", "foot"):
                total_com += seg["com_position"]["dy"] * w
                total_mf += w
    body_com = total_com / total_mf if total_mf > 0 else fig_height * 0.55

    data["biomechanics"] = {
        "note": "Biomechanical segment parameters. Female BSP from de Leva (1996), mass fractions from Winter (2009).",
        "reference": [
            "de Leva, P. 'Adjustments to Zatsiorsky-Seluyanov's segment inertia parameters.' J. Biomech. 29(9):1223–1230, 1996.",
            "Winter, D.A. 'Biomechanics and Motor Control of Human Movement.' 4th ed., Wiley, 2009. Table 4.1.",
            "Dempster, W.T. 'Space requirements of the seated operator.' WADC-TR-55-159, 1955.",
        ],
        "gender_data": "female",
        "endpoint_convention": {
            "source": "schema_landmarks",
            "note": "Segment endpoints use schema landmark names (crown, neck_valley, etc.), not Winter's anatomical landmarks (C7-T1, ear canal, etc.). CoM fractions re-derived accordingly.",
        },
        "canonical_height_cm": 170.0,
        "scale_cm_per_hu": round(scale_cm, 4),
        "whole_body_com": {
            "dy": round(float(body_com), 4),
            "dy_fraction": round(float((body_com - crown_dy) / fig_height), 4),
            "cm_from_crown": round(float((body_com - crown_dy) * scale_cm), 2),
            "note": "Whole-body CoM estimated from segment CoMs × mass fractions. Bilateral segments counted twice.",
        },
        "segments": segments,
    }
    print(f"  Biomechanics: CoM at dy={body_com:.4f}")


def phase_28_medial_axis(data, env_dx, env_dy):
    """Medial axis with inscribed radius and branch points."""
    samples = [
        {"dy": round(float(env_dy[i]), 4), "medial_dx": 0.0,
         "inscribed_radius": round(float(env_dx[i]), 4),
         "inscribed_diameter": round(float(2 * env_dx[i]), 4)}
        for i in range(len(env_dy))
    ]

    topo = data["cross_section_topology"]["profile"]
    branches = []
    prev_pairs = None
    for dk in sorted(topo.keys(), key=float):
        pairs = topo[dk]["pairs"]
        if prev_pairs is not None and pairs != prev_pairs:
            branches.append({
                "dy": float(dk),
                "transition": f"{prev_pairs}_to_{pairs}_pairs",
                "interpretation": (
                    "arm_emergence" if pairs > prev_pairs else "arm_merger"
                ) if abs(pairs - prev_pairs) == 1 else "topology_change",
            })
        prev_pairs = pairs

    data["medial_axis"] = {
        "note": "Approximate medial axis of the bilateral silhouette.",
        "thickness_statistics": {
            "mean_radius_hu": round(float(env_dx.mean()), 4),
            "min_radius_hu": round(float(env_dx.min()), 4),
            "min_radius_dy": round(float(env_dy[env_dx.argmin()]), 4),
            "max_radius_hu": round(float(env_dx.max()), 4),
            "max_radius_dy": round(float(env_dy[env_dx.argmax()]), 4),
            "thinning_ratio": round(float(env_dx.min() / env_dx.max()), 4),
            "note": "thinning_ratio = min/max radius.",
        },
        "branch_points": {
            "count": len(branches), "points": branches,
            "note": "Locations where cross-section topology changes.",
        },
        "main_axis": {
            "start": {"dx": 0.0, "dy": round(float(env_dy[0]), 4)},
            "end": {"dx": 0.0, "dy": round(float(env_dy[-1]), 4)},
            "sample_count": len(samples),
            "samples": samples,
        },
    }
    print(f"  Medial axis: {len(branches)} branch points")


def phase_29_shape_complexity(data, right_pts, sym_all, env_dx, env_dy):
    """Entropy, fractal dimension, compactness, eccentricity, roughness."""
    kappa = parametric_curvature(right_pts[:, 0].copy(), right_pts[:, 1].copy())
    hist, _ = np.histogram(np.abs(kappa), bins=50, density=True)
    hist = hist[hist > 0]
    hn = hist / hist.sum()
    curv_entropy = float(scipy_entropy(hn, base=2))

    # Box-counting fractal dimension
    x_range = right_pts[:, 0].max() - right_pts[:, 0].min()
    y_range = right_pts[:, 1].max() - right_pts[:, 1].min()
    max_range = max(x_range, y_range)
    epsilons = np.logspace(-3, 0, 10) * max_range
    counts = []
    for eps in epsilons:
        xb = np.floor((right_pts[:, 0] - right_pts[:, 0].min()) / eps).astype(int)
        yb = np.floor((right_pts[:, 1] - right_pts[:, 1].min()) / eps).astype(int)
        counts.append(len(set(zip(xb, yb))))
    fractal_dim = float(np.polyfit(np.log(1.0 / epsilons), np.log(np.array(counts, dtype=float)), 1)[0])
    fractal_dim = float(np.clip(fractal_dim, 1.0, 2.0))

    sil_area = float(_trapz(2 * env_dx, env_dy))
    total_perim = data["meta"]["contour_quality"]["total_perimeter_hu"]
    compactness = 4 * np.pi * sil_area / (total_perim**2) if total_perim > 0 else 0

    bbox = data["meta"]["bounding_box_hu"]
    bbox_area = bbox["width"] * bbox["height"]
    rectangularity = min(sil_area / bbox_area, 1.0) if bbox_area > 0 else 0

    cov = np.cov(sym_all.T)
    eigs = sorted(np.linalg.eigvalsh(cov))
    eccentricity = float(np.sqrt(1 - eigs[0] / eigs[1])) if eigs[1] > 0 else 0

    hull_perim = data.get("convex_hull", {}).get("hull_perimeter_hu", 0)
    roughness = total_perim / hull_perim if hull_perim > 0 and total_perim > 0 else 1.0

    data["shape_complexity"] = {
        "note": "Shape complexity metrics from computational geometry.",
        "reference": "Costa, L.F. & Cesar, R.M. 'Shape Classification and Analysis.' 2nd ed., Springer, 2009.",
        "computed_on": "right_half",
        "curvature_entropy": {"value": round(curv_entropy, 4), "units": "bits", "histogram_bins": 50,
                              "note": "Shannon entropy of |κ| histogram."},
        "fractal_dimension": {"value": round(fractal_dim, 4), "method": "box_counting", "n_scales": 10,
                              "note": "1.0 = smooth curve, 1.2+ = significant fine structure."},
        "compactness": {"value": round(float(compactness), 4), "formula": "4π·A / P²",
                        "perimeter_used": "original",
                        "computed_area_hu2": round(sil_area, 4),
                        "computed_perimeter_hu": round(total_perim, 4),
                        "note": "Isoperimetric ratio. Circle=1.0. Uses total_perimeter_hu from contour_quality."},
        "rectangularity": {"value": round(float(rectangularity), 4),
                           "formula": "A_shape / A_MBR per Rosin (2003), must be in [0,1]",
                           "note": "How well the figure fills its bounding box."},
        "eccentricity": {"value": round(float(eccentricity), 4),
                         "note": "Covariance-ellipse eccentricity. 0=circular, →1=elongated."},
        "roughness": {"value": round(float(roughness), 4), "formula": "perimeter / convex_hull_perimeter",
                      "note": "1.0 = convex, >1.0 = indented/detailed outline."},
    }
    print(f"  Complexity: entropy={curv_entropy:.4f}, fractal={fractal_dim:.4f}")


# ═══════════════════════════════════════════════════════════════════
# V2 PREPROCESSING
# ═══════════════════════════════════════════════════════════════════

_LANDMARK_DESCRIPTIONS = {
    "crown": "Top of the head (minimum dy on right-side contour)",
    "head_peak": "Widest point of the head",
    "neck_valley": "Narrowest point at the neck",
    "shoulder_peak": "Widest point at shoulder level",
    "waist_valley": "Narrowest point of the waist",
    "hip_peak": "Widest point at hip level",
    "knee_valley": "Narrowest point at knee level",
    "ankle_valley": "Narrowest point at ankle level",
    "sole": "Bottom of the foot (maximum dy on right-side contour)",
}

_V2_PARAMETRIC_EXTRAS = {
    "max_error", "mean_error", "n_original_points",
    "n_parameters", "compression_ratio",
}


def _preprocess_v2_input(data):
    """Normalise a v2 extraction dict so all pipeline phases can run.

    Handles: missing crown/sole landmarks, bare stroke arrays,
    flat measurements/symmetry, v2 meta layout, v2 proportion keys,
    and v2 parametric extras.  Safe to call on already-preprocessed data.
    """
    contour = data["contour"]
    right_pts = contour[:RIGHT_END]
    names = {lm["name"] for lm in data["landmarks"]}

    # ── Derive crown / sole from contour extrema ──
    if "crown" not in names:
        ci = min(range(len(right_pts)), key=lambda i: right_pts[i][1])
        data["landmarks"].insert(0, {
            "name": "crown",
            "dy": round(right_pts[ci][1], 4),
            "dx": round(right_pts[ci][0], 4),
        })

    if "sole" not in names:
        si = max(range(len(right_pts)), key=lambda i: right_pts[i][1])
        data["landmarks"].append({
            "name": "sole",
            "dy": round(right_pts[si][1], 4),
            "dx": round(right_pts[si][0], 4),
        })

    # ── Add description to landmarks that lack it ──
    for lm in data["landmarks"]:
        if "description" not in lm:
            lm["description"] = _LANDMARK_DESCRIPTIONS.get(
                lm["name"], f"Landmark: {lm['name'].replace('_', ' ')}")

    # ── Strip v2-only landmark fields (index, band_constrained) ──
    for lm in data["landmarks"]:
        for f in ("index", "band_constrained"):
            lm.pop(f, None)

    # ── Convert bare stroke arrays → structured objects ──
    new_strokes = []
    for i, stroke in enumerate(data["strokes"]):
        if isinstance(stroke, list) and stroke and isinstance(stroke[0], list):
            pts = stroke
            dx_vals = [p[0] for p in pts]
            dy_vals = [p[1] for p in pts]
            new_strokes.append({
                "id": i, "region": "unknown", "n_points": len(pts),
                "bbox": {
                    "dx_min": round(min(dx_vals), 4),
                    "dx_max": round(max(dx_vals), 4),
                    "dy_min": round(min(dy_vals), 4),
                    "dy_max": round(max(dy_vals), 4),
                },
                "points": pts,
            })
        else:
            new_strokes.append(stroke)
    data["strokes"] = new_strokes

    # ── Wrap flat measurements → {scanlines: ...} ──
    if "scanlines" not in data["measurements"]:
        data["measurements"] = {"scanlines": data["measurements"]}

    # ── Wrap flat symmetry → {samples: ...} ──
    if "samples" not in data["symmetry"]:
        data["symmetry"] = {"samples": data["symmetry"]}

    # ── Parametric: add dy_range, strip v2 extras ──
    lm_dict = {lm["name"]: lm for lm in data["landmarks"]}
    param = data["parametric"]
    for seg in param["segments"]:
        if "dy_range" not in seg:
            s, e = lm_dict.get(seg["landmark_start"]), lm_dict.get(seg["landmark_end"])
            if s and e:
                seg["dy_range"] = [s["dy"], e["dy"]]
            elif "coeffs_dy" in seg:
                seg["dy_range"] = [seg["coeffs_dy"][0], seg["coeffs_dy"][-1]]
        seg.pop("coeffs_dy", None)
    for f in _V2_PARAMETRIC_EXTRAS:
        param.pop(f, None)

    # ── Meta: mirror bool → object, flat scores/timing → objects ──
    meta = data["meta"]
    if isinstance(meta.get("mirror"), bool):
        applied = meta.pop("mirror")
        meta["mirror"] = {
            "applied": applied,
            "semantics": "right side mirrored to left" if applied else "none",
        }
    if "scores" not in meta:
        meta["scores"] = {
            "scanline": meta.pop("score_scanline", 0.0),
            "floodfill": meta.pop("score_floodfill", 0.0),
            "direct": meta.pop("score_direct", 0.0),
            "margin": meta.pop("score_margin", 0.0),
        }
    if "timing" not in meta:
        meta["timing"] = {
            "algo_elapsed_ms": meta.pop("algo_elapsed_ms", 0.0),
            "total_elapsed_ms": meta.pop("total_elapsed_ms", 0.0),
        }
    if "coordinate_system" not in meta:
        meta["coordinate_system"] = {
            "dx": "horizontal distance from midline, right positive",
            "dy": "vertical position, 0=crown, increasing downward",
            "hu_definition": "head-units: 1 HU = crown-to-sole / head_count",
        }

    # ── Classification: fix v2 field names ──
    cls = meta.get("classification", {})
    hair = cls.get("hair_symmetry")
    if isinstance(hair, dict) and "delta_hu" in hair:
        hair.setdefault("raw_delta_hu", hair.pop("delta_hu"))
    ann = cls.get("annotations")
    if isinstance(ann, dict) and ann.get("label") not in ("single_figure", "multi_figure"):
        ann["label"] = "single_figure"

    # ── Proportion: head_count → head_count_total ──
    prop = data["proportion"]
    if "head_count" in prop and "head_count_total" not in prop:
        prop["head_count_total"] = prop.pop("head_count")
    crown_dy = lm_dict["crown"]["dy"]
    sole_dy = lm_dict["sole"]["dy"]
    fig_height = sole_dy - crown_dy
    if "figure_height_total_hu" not in prop:
        prop["figure_height_total_hu"] = round(fig_height, 4)
    if "head_height_hu" not in prop and prop.get("head_count_total", 0) > 0:
        prop["head_height_hu"] = round(fig_height / prop["head_count_total"], 4)
    prop.pop("standardized_vector", None)

    print(f"  Preprocessed: {len(data['landmarks'])} landmarks, "
          f"{len(data['strokes'])} strokes, "
          f"{len(data['measurements']['scanlines'])} scanlines")


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Generate a v4 silhouette analysis dataset from a v2 extraction."
    )
    parser.add_argument("input", help="Path to v2.json input file")
    parser.add_argument("output", help="Path to write v4.json output")
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit non-zero if the output has any Pydantic constraint violations",
    )
    args = parser.parse_args()

    print(f"Loading {args.input}...")
    with open(args.input) as f:
        data = json.load(f)

    # ── v2 preprocessing (normalise into the format phases expect) ─
    _preprocess_v2_input(data)

    # ── Contour setup ──────────────────────────────────────────
    contour = np.array(data["contour"])
    dx_arr, dy_arr = contour[:, 0], contour[:, 1]
    right_dx = dx_arr[:RIGHT_END]
    right_dy = dy_arr[:RIGHT_END]
    right_pts = np.column_stack([right_dx, right_dy])

    interp, unique_dy, unique_dx, rdy_sorted, rdx_sorted = build_contour_interpolator(right_dx, right_dy)
    existing_lm = {lm["name"]: lm for lm in data["landmarks"]}
    sole_dy = existing_lm["sole"]["dy"]
    crown_dy = existing_lm["crown"]["dy"]
    fig_height = sole_dy - crown_dy

    # Symmetric silhouette (for hull, moments)
    sym_all = np.vstack([right_pts, np.column_stack([-right_dx, right_dy])[::-1]])

    # ── Phase 1–11: v2 → v3 (from enrich.py) ──────────────────
    print("\n── v2 → v3: Enrichment ──")
    dx_deriv2 = phase_01_landmark_enrichment(data, unique_dy, unique_dx, interp)
    phase_02_dense_scanlines(data, unique_dy, dx_deriv2, interp, sole_dy)
    phase_03_dense_symmetry(data, interp, sole_dy)
    phase_04_curvature_profile(data, rdy_sorted, rdx_sorted)
    phase_05_proportion(data)
    phase_06_stroke_enrichment(data)
    phase_07_parametric_enrichment(data, unique_dy, interp)
    phase_08_body_regions(data)
    phase_09_cross_section_topology(data, rdy_sorted, sole_dy)
    phase_10_fourier_descriptors(data, right_dx, right_dy)
    phase_11_meta_enrichment(data, contour, dx_arr, dy_arr)

    # ── Phase 12–19: v3 → v3.1 (from refine_v3.py) ────────────
    print("\n── v3 → v3.1: Refinement ──")
    phase_12_landmark_validation(data)
    phase_13_inflection_filtering(data)
    phase_14_improved_stroke_semantics(data)
    phase_15_width_profile(data, interp, crown_dy, sole_dy)
    phase_16_area_profile(data, interp)
    phase_17_contour_normals(data, right_dx, right_dy)
    phase_18_shape_vector(data, interp, crown_dy, sole_dy)
    phase_19_enrich_body_regions(data)

    # ── Outer envelope (needed for v4 phases) ──────────────────
    wp = data["width_profile"]["samples"]
    env_dy = np.array([s["dy"] for s in wp])
    env_dx = np.array([s["dx"] for s in wp])

    # ── Phase 20–29: v3.1 → v4 (from cross_domain_enrich.py) ──
    print("\n── v3.1 → v4: Cross-domain ──")
    phase_20_hu_moments(data, sym_all)
    phase_21_turning_function(data, contour)
    phase_22_convex_hull(data, sym_all, right_pts, right_dx, right_dy, env_dx, env_dy)
    phase_23_gesture_line(data, crown_dy, fig_height)
    phase_24_curvature_scale_space(data, right_pts, right_dx, right_dy)
    phase_25_style_deviation(data, crown_dy, fig_height)
    phase_26_volumetric_estimates(data, env_dx, env_dy, fig_height)
    phase_27_biomechanics(data, fig_height, crown_dy)
    phase_28_medial_axis(data, env_dx, env_dy)
    phase_29_shape_complexity(data, right_pts, sym_all, env_dx, env_dy)

    # ── Final meta update ──────────────────────────────────────
    data["meta"]["schema_version"] = "4.0.0"
    # P2-9: Document the HU convention and conversion factor.
    # hu_to_standard_factor converts from this schema's HU (crown→neck_valley)
    # to the standard artistic HU (crown→chin). Multiply a schema HU measurement
    # by this factor to get standard-HU values.
    cs = data["meta"].get("coordinate_system", {})
    cs["hu_convention"] = "crown_to_neck_valley"
    neck_dy = existing_lm.get("neck_valley", {}).get("dy", crown_dy)
    head_hu = neck_dy - crown_dy
    if head_hu > 0:
        # Standard head (crown-to-chin) is approximately 85% of crown-to-neck_valley
        # per Richer (1971) and Bammes (1990).
        estimated_standard_head = head_hu * 0.85
        cs["hu_to_standard_factor"] = round(head_hu / estimated_standard_head, 4)
    data["meta"]["coordinate_system"] = cs
    data["meta"]["sections"] = {
        "note": "v4.0 section inventory — 10 cross-domain improvement factors",
        "total_sections": len(data.keys()),
        "sections": sorted(data.keys()),
        "new_in_v4": [
            "hu_moments — 7 rotation/scale/translation-invariant shape descriptors (Hu 1962)",
            "turning_function — θ(s) cumulative tangent angle for shape matching (Arkin 1991)",
            "convex_hull — solidity, negative space, concavity decomposition (Zunic & Rosin 2004)",
            "gesture_line — PCA-based action line, lean, contrapposto (Loomis 1943 formalised)",
            "curvature_scale_space — multi-scale CSS representation (Mokhtarian & Mackworth 1992)",
            "style_deviation — per-landmark deviation from Loomis canon + L2 distance",
            "volumetric_estimates — cylindrical, ellipsoidal, Pappus volume approximations",
            "biomechanics — Dempster/Winter segment mass, CoM, radius of gyration (Winter 2009)",
            "medial_axis — midline skeleton with inscribed radius and branch points",
            "shape_complexity — entropy, fractal dimension, compactness, eccentricity, roughness",
        ],
        "improvement_factors": {
            "note": (
                "Each new section bridges the silhouette data to a different discipline: "
                "computational geometry (hu_moments, convex_hull, shape_complexity), "
                "signal processing (turning_function, curvature_scale_space), "
                "figure drawing theory (gesture_line, style_deviation), "
                "biomechanics (biomechanics, volumetric_estimates), "
                "character rigging (medial_axis, biomechanics)."
            )
        },
    }

    # ── Write via SilhouetteDocument ─────────────────────────
    doc = SilhouetteDocument.from_dict(data, strict=False)
    doc.to_json(args.output)

    size_kb = os.path.getsize(args.output) / 1024
    print(f"\n{'='*60}")
    print(f"Output: {args.output} ({size_kb:.1f} KB, {len(data.keys())} sections)")

    # ── Validation report ─────────────────────────────────────
    report = doc.verification_report()
    errors = report.schema_errors
    if errors:
        print(f"Validation: {len(errors)} constraint violation(s)")
        for err in errors[:5]:
            print(f"  - {err}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more")
    else:
        print("Validation: clean (0 violations)")
    print(f"{'='*60}")

    if args.strict and errors:
        print(f"\nERROR: --strict mode: {len(errors)} violation(s). Aborting.")
        sys.exit(1)


if __name__ == "__main__":
    main()
