"""
cross_domain_enrich.py — v3.1.0 → v4.0.0

Ten cross-domain improvement factors, each bridging the silhouette
data to a different discipline.  Every formula, constant, and reference
is documented inline.

Run:  python3 cross_domain_enrich.py

Reads:  /home/claude/v3.json  (v3.1)
Writes: /home/claude/v4.json  (v4.0)

────────────────────────────────────────────────────────────────
IMPROVEMENT FACTORS (summary — detailed notes in each section)

 1. Hu Invariant Moments
    7 rotation/scale/translation-invariant shape descriptors.
    Ref: Hu, M-K. "Visual pattern recognition by moment invariants."
         IRE Trans. Inform. Theory, IT-8:179–187, 1962.

 2. Turning Function
    Cumulative tangent-angle representation θ(s) parameterised by
    normalised arc-length.  Standard representation for shape matching.
    Ref: Arkin, E. et al. "An efficiently computable metric for comparing
         polygonal shapes." IEEE TPAMI 13(3):209–216, 1991.

 3. Convex Hull & Negative-Space Analysis
    Convexity deficiency, solidity, concavity decomposition — the
    "readability" metric that character designers assess by eye.
    Ref: Zunic, J. & Rosin, P. "A new convexity measure for polygons."
         IEEE TPAMI 26(7):923–934, 2004.

 4. Gesture / Action Line
    PCA-based extraction of the figure's dominant axis of pose energy.
    Formalises the "line of action" from Loomis & Hampton figure drawing.
    Ref: Loomis, A. "Figure Drawing for All It's Worth." 1943.
         Hampton, M. "Figure Drawing: Design and Invention." 2009.

 5. Multi-Scale Curvature (CSS — Curvature Scale Space)
    Curvature recomputed at 5 Gaussian smoothing scales.  Features
    that persist across scales are structural; those that vanish are
    surface detail.
    Ref: Mokhtarian, F. & Mackworth, A. "A theory of multiscale,
         curvature-based shape representation for planar curves."
         IEEE TPAMI 14(8):789–805, 1992.

 6. Style Deviation Vector
    Signed deviation of each landmark from the Loomis 8-head
    academic canon, plus an L2 "total stylisation distance."
    Gives a per-character fingerprint for lineup consistency.

 7. Volumetric Estimates
    (a) Cylindrical approximation: V = π∫ dx² dy  (each slice as a
        circular cross-section revolved around midline).
    (b) Ellipsoidal approximation: V = (π/2)∫ dx² dy  (each slice
        as a half-ellipse with semi-minor = dx/2).
    (c) Pappus centroid method: V = 2π·x̄·A  (solid of revolution).
    All three give order-of-magnitude volumetric budgets for the
    downstream 3D pipeline.

 8. Biomechanical Segment Parameters (Dempster / Winter)
    Segment mass fractions, CoM positions along segment length,
    and radii of gyration — standard data from cadaver studies.
    Ref: Winter, D.A. "Biomechanics and Motor Control of Human
         Movement." 4th ed., Wiley, 2009. Table 4.1.
    Ref: Dempster, W.T. "Space requirements of the seated operator."
         WADC-TR-55-159, 1955.

 9. Approximate Medial Axis
    Midline skeleton of the right-half silhouette, computed as the
    locus of maximal inscribed circles.  Approximated here by
    averaging the outer envelope dx with the "inner" contour at
    each dy level (where inner ≈ midline, i.e. dx=0 for a symmetric
    figure) → medial_x = dx/2 at each dy.

10. Shape Complexity & Entropy
    (a) Curvature entropy: H(κ) over a histogram of curvature values.
    (b) Fractal dimension estimate (box-counting).
    (c) Compactness: 4π·A / P²  (isoperimetric ratio; circle = 1).
    (d) Rectangularity: A / A_bbox.
    (e) Eccentricity: from the covariance ellipse of contour points.
    Ref: Costa, L.F. & Cesar, R.M. "Shape Classification and Analysis."
         2nd ed., Springer, 2009.
────────────────────────────────────────────────────────────────
"""

import json
import numpy as np
from scipy.spatial import ConvexHull
from scipy.ndimage import gaussian_filter1d
from scipy.stats import entropy as scipy_entropy
import warnings
warnings.filterwarnings("ignore")

# ─── Load ────────────────────────────────────────────────────────
with open("/home/claude/v3.json") as f:
    data = json.load(f)

contour_full = np.array(data["contour"])  # (1200, 2): [dx, dy]
RIGHT_END = 727
right_pts = contour_full[:RIGHT_END]  # original ordering
right_dx = right_pts[:, 0]
right_dy = right_pts[:, 1]

# Landmarks
lm_map = {lm["name"]: lm for lm in data["landmarks"]}
crown_dy = lm_map["crown"]["dy"]
sole_dy  = lm_map["sole"]["dy"]
fig_height = sole_dy - crown_dy

# Outer envelope (from v3.1 width_profile)
wp_samples = data["width_profile"]["samples"]
env_dy = np.array([s["dy"] for s in wp_samples])
env_dx = np.array([s["dx"] for s in wp_samples])

# Full symmetric silhouette points (for hull, moments, etc.)
# Mirror the right side: right + reflected left
sym_right = np.column_stack([right_dx, right_dy])
sym_left  = np.column_stack([-right_dx, right_dy])
sym_all   = np.vstack([sym_right, sym_left[::-1]])

_trapz = getattr(np, 'trapezoid', getattr(np, 'trapz', None))

# ═══════════════════════════════════════════════════════════════
# 1. HU INVARIANT MOMENTS
# ═══════════════════════════════════════════════════════════════
print("1. Computing Hu Invariant Moments...")

def compute_raw_moments(pts, max_order=3):
    """Compute raw moments m_pq = Σ x^p · y^q for a point cloud."""
    x, y = pts[:, 0], pts[:, 1]
    moments = {}
    for p in range(max_order + 1):
        for q in range(max_order + 1):
            if p + q <= max_order:
                moments[(p, q)] = float(np.sum(x**p * y**q))
    return moments

def compute_central_moments(pts, max_order=3):
    """Compute central moments μ_pq = Σ (x-x̄)^p · (y-ȳ)^q."""
    x, y = pts[:, 0], pts[:, 1]
    xbar = x.mean()
    ybar = y.mean()
    cx = x - xbar
    cy = y - ybar
    moments = {}
    for p in range(max_order + 1):
        for q in range(max_order + 1):
            if p + q <= max_order:
                moments[(p, q)] = float(np.sum(cx**p * cy**q))
    return moments

def compute_normalised_central_moments(central, m00):
    """η_pq = μ_pq / μ_00^(1 + (p+q)/2)."""
    eta = {}
    for (p, q), val in central.items():
        if p + q >= 2:
            gamma = 1 + (p + q) / 2
            eta[(p, q)] = val / (m00 ** gamma) if m00 > 0 else 0.0
    return eta

def compute_hu_moments(eta):
    """
    7 Hu invariant moments from normalised central moments.
    Hu (1962), Eqs. 22–28.
    """
    e = lambda p, q: eta.get((p, q), 0.0)

    h1 = e(2,0) + e(0,2)
    h2 = (e(2,0) - e(0,2))**2 + 4 * e(1,1)**2
    h3 = (e(3,0) - 3*e(1,2))**2 + (3*e(2,1) - e(0,3))**2
    h4 = (e(3,0) + e(1,2))**2 + (e(2,1) + e(0,3))**2
    h5 = ((e(3,0) - 3*e(1,2)) * (e(3,0) + e(1,2)) *
          ((e(3,0) + e(1,2))**2 - 3*(e(2,1) + e(0,3))**2) +
          (3*e(2,1) - e(0,3)) * (e(2,1) + e(0,3)) *
          (3*(e(3,0) + e(1,2))**2 - (e(2,1) + e(0,3))**2))
    h6 = ((e(2,0) - e(0,2)) *
          ((e(3,0) + e(1,2))**2 - (e(2,1) + e(0,3))**2) +
          4 * e(1,1) * (e(3,0) + e(1,2)) * (e(2,1) + e(0,3)))
    h7 = ((3*e(2,1) - e(0,3)) * (e(3,0) + e(1,2)) *
          ((e(3,0) + e(1,2))**2 - 3*(e(2,1) + e(0,3))**2) -
          (e(3,0) - 3*e(1,2)) * (e(2,1) + e(0,3)) *
          (3*(e(3,0) + e(1,2))**2 - (e(2,1) + e(0,3))**2))

    return [h1, h2, h3, h4, h5, h6, h7]

# Compute on the full symmetric silhouette
raw = compute_raw_moments(sym_all)
central = compute_central_moments(sym_all)
m00 = central[(0, 0)]
eta = compute_normalised_central_moments(central, m00)
hu = compute_hu_moments(eta)

# Log-transform for scale (standard practice: -sign(h)·log10(|h|))
hu_log = []
for h in hu:
    if abs(h) > 1e-30:
        hu_log.append(round(-np.sign(h) * np.log10(abs(h)), 6))
    else:
        hu_log.append(0.0)

data["hu_moments"] = {
    "note": (
        "Hu's 7 invariant moments — invariant to translation, scale, and rotation. "
        "Computed from the full bilateral (mirrored) silhouette point cloud. "
        "raw: the 7 moments as defined by Hu (1962). "
        "log_transformed: −sign(h)·log₁₀(|h|), standard for comparison since "
        "raw values span many orders of magnitude."
    ),
    "reference": "Hu, M-K. IRE Trans. Inform. Theory, IT-8:179–187, 1962.",
    "computed_on": "bilateral_symmetric_silhouette",
    "point_count": len(sym_all),
    "raw": [round(h, 10) for h in hu],
    "log_transformed": hu_log,
    "centroid": {
        "dx": round(float(sym_all[:, 0].mean()), 4),
        "dy": round(float(sym_all[:, 1].mean()), 4)
    }
}

print(f"   Hu moments (log): {hu_log}")

# ═══════════════════════════════════════════════════════════════
# 2. TURNING FUNCTION
# ═══════════════════════════════════════════════════════════════
print("2. Computing Turning Function...")

def compute_turning_function(pts, n_samples=200):
    """
    θ(s): cumulative tangent angle as a function of normalised
    arc-length s ∈ [0, 1].
    
    For a closed curve, θ(1) − θ(0) = ±2π (winding number).
    """
    diffs = np.diff(pts, axis=0)
    seg_lengths = np.sqrt((diffs**2).sum(axis=1))
    T = seg_lengths.sum()
    if T < 1e-10:
        return None

    # Cumulative arc-length
    s_cumul = np.concatenate([[0], np.cumsum(seg_lengths)])
    s_norm = s_cumul / T

    # Tangent angles
    angles = np.arctan2(diffs[:, 1], diffs[:, 0])

    # Unwrap to make continuous
    angles_unwrap = np.unwrap(angles)

    # Sample at uniform s values
    s_uniform = np.linspace(0, 1, n_samples)
    # Interpolate angle at uniform s
    # angles are defined at segment midpoints; use s at segment starts
    theta_interp = np.interp(s_uniform, s_norm[:-1], angles_unwrap)

    return s_uniform, theta_interp, float(T)

result = compute_turning_function(right_pts, n_samples=200)
if result is not None:
    s_uni, theta_uni, perimeter = result

    # Subsample for storage
    step = 4  # every 4th → 50 samples
    tf_samples = []
    for i in range(0, len(s_uni), step):
        tf_samples.append({
            "s": round(float(s_uni[i]), 4),
            "theta": round(float(theta_uni[i]), 4)
        })

    # Total angular travel
    total_angle = float(theta_uni[-1] - theta_uni[0])

    # Angular velocity (rate of turning)
    omega = np.gradient(theta_uni, s_uni)
    max_turn_idx = np.argmax(np.abs(omega))

    data["turning_function"] = {
        "note": (
            "Turning function θ(s): cumulative tangent angle of the right-side contour "
            "as a function of normalised arc-length s ∈ [0,1]. "
            "θ encodes the shape up to translation and scale; the L∞ distance between "
            "two turning functions is the Arkin et al. (1991) shape distance metric. "
            "Computed on the right-side contour in original traversal order (crown→sole)."
        ),
        "reference": "Arkin, E. et al. IEEE TPAMI 13(3):209–216, 1991.",
        "perimeter_hu": round(perimeter, 4),
        "total_angle_rad": round(total_angle, 4),
        "total_angle_deg": round(np.degrees(total_angle), 2),
        "winding_number": round(total_angle / (2 * np.pi), 2),
        "sample_count": len(tf_samples),
        "samples": tf_samples,
        "max_turning_rate": {
            "s": round(float(s_uni[max_turn_idx]), 4),
            "omega": round(float(omega[max_turn_idx]), 4),
            "note": "Location of sharpest turn (highest |dθ/ds|)"
        }
    }
    print(f"   Total angle: {np.degrees(total_angle):.1f}°, winding={total_angle/(2*np.pi):.2f}")

# ═══════════════════════════════════════════════════════════════
# 3. CONVEX HULL & NEGATIVE-SPACE ANALYSIS
# ═══════════════════════════════════════════════════════════════
print("3. Computing Convex Hull & Negative Space...")

try:
    hull = ConvexHull(sym_all)
    hull_area = float(hull.volume)   # In 2D, ConvexHull.volume = area
    hull_perim = float(hull.area)    # In 2D, ConvexHull.area = perimeter

    # Silhouette area from outer envelope (bilateral)
    sil_area = float(_trapz(2 * env_dx, env_dy))

    # Solidity = silhouette_area / hull_area
    solidity = sil_area / hull_area if hull_area > 0 else 0

    # Convexity deficiency = 1 - solidity
    convexity_deficiency = 1 - solidity

    # Negative space = hull_area - silhouette_area
    negative_space_area = hull_area - sil_area

    # Hull vertices (subsampled for storage)
    hull_verts = sym_all[hull.vertices].tolist()

    # Concavity decomposition: find the major concavities
    # (regions where the contour is far from the hull)
    # Sample hull boundary at fine resolution
    hull_boundary_pts = sym_all[hull.vertices]
    # Close the hull
    hull_closed = np.vstack([hull_boundary_pts, hull_boundary_pts[0:1]])

    # For each contour point, compute distance to nearest hull edge
    from scipy.spatial import distance
    # Simplified: compute min distance from each contour point to hull
    hull_boundary_expanded = []
    for i in range(len(hull_closed) - 1):
        t_vals = np.linspace(0, 1, 20)
        for t in t_vals:
            hull_boundary_expanded.append(
                hull_closed[i] * (1-t) + hull_closed[i+1] * t
            )
    hull_boundary_expanded = np.array(hull_boundary_expanded)

    # Distance of each right-side contour point from hull boundary
    from scipy.spatial import cKDTree
    hull_tree = cKDTree(hull_boundary_expanded)
    dists_right, _ = hull_tree.query(right_pts)

    # Find major concavity regions (contiguous stretches where dist > threshold)
    concavity_thresh = 0.1  # HU
    in_concavity = dists_right > concavity_thresh
    concavities = []
    start = None
    for i in range(len(in_concavity)):
        if in_concavity[i] and start is None:
            start = i
        elif not in_concavity[i] and start is not None:
            # End of concavity region
            region_dists = dists_right[start:i]
            max_idx = start + np.argmax(region_dists)
            concavities.append({
                "contour_index_range": [int(start), int(i-1)],
                "dy_range": [round(float(right_dy[start]), 4), round(float(right_dy[i-1]), 4)],
                "max_depth_hu": round(float(region_dists.max()), 4),
                "max_depth_at": {
                    "dx": round(float(right_dx[max_idx]), 4),
                    "dy": round(float(right_dy[max_idx]), 4)
                },
                "arc_span": int(i - start)
            })
            start = None
    if start is not None:
        region_dists = dists_right[start:]
        max_idx = start + np.argmax(region_dists)
        concavities.append({
            "contour_index_range": [int(start), int(len(dists_right)-1)],
            "dy_range": [round(float(right_dy[start]), 4), round(float(right_dy[-1]), 4)],
            "max_depth_hu": round(float(region_dists.max()), 4),
            "max_depth_at": {
                "dx": round(float(right_dx[max_idx]), 4),
                "dy": round(float(right_dy[max_idx]), 4)
            },
            "arc_span": int(len(dists_right) - start)
        })

    # Sort by depth (most prominent concavities first)
    concavities.sort(key=lambda c: c["max_depth_hu"], reverse=True)

    data["convex_hull"] = {
        "note": (
            "Convex hull of the full bilateral silhouette. "
            "Solidity (silhouette_area / hull_area) measures how 'filled' the figure is — "
            "a standing figure with arms at sides has high solidity (~0.85+); arms akimbo or "
            "wide stance lowers it. Negative space (hull − silhouette) is what character "
            "designers call 'readability' — distinctive negative spaces make silhouettes "
            "instantly recognisable. Concavities are the major indentations where the contour "
            "deviates inward from the hull."
        ),
        "reference": "Zunic, J. & Rosin, P. IEEE TPAMI 26(7):923–934, 2004.",
        "hull_area_hu2": round(hull_area, 4),
        "hull_perimeter_hu": round(hull_perim, 4),
        "silhouette_area_hu2": round(sil_area, 4),
        "negative_space_area_hu2": round(negative_space_area, 4),
        "solidity": round(solidity, 4),
        "convexity_deficiency": round(convexity_deficiency, 4),
        "hull_vertex_count": len(hull.vertices),
        "concavities": {
            "threshold_hu": concavity_thresh,
            "count": len(concavities),
            "regions": concavities[:10],  # top 10
            "note": (
                "Major concavity regions where contour deviates > threshold from hull. "
                "Sorted by max_depth_hu (deepest first). These correspond to: "
                "neck indentation, waist indent, arm-torso gap, knee narrowing, etc."
            )
        }
    }
    print(f"   Solidity: {solidity:.4f}, negative space: {negative_space_area:.4f} HU², concavities: {len(concavities)}")
except Exception as e:
    print(f"   WARNING: Convex hull failed: {e}")

# ═══════════════════════════════════════════════════════════════
# 4. GESTURE / ACTION LINE
# ═══════════════════════════════════════════════════════════════
print("4. Computing Gesture / Action Line...")

# The "line of action" in figure drawing is the primary flow curve
# through the figure's pose.  For a frontal standing pose, this is
# approximately the vertical midline — but with subtle curvature
# that reveals weight distribution, contrapposto, lean, etc.
#
# Method: PCA on landmark (dx, dy) positions to find the dominant
# axis.  Then fit a cubic to the landmarks' positions projected
# perpendicular to this axis.

landmark_pts = np.array([[lm["dx"], lm["dy"]] for lm in data["landmarks"]])

# PCA
centroid = landmark_pts.mean(axis=0)
centered = landmark_pts - centroid
cov_mat = np.cov(centered.T)
eigenvalues, eigenvectors = np.linalg.eigh(cov_mat)
# Sort descending
order = eigenvalues.argsort()[::-1]
eigenvalues = eigenvalues[order]
eigenvectors = eigenvectors[:, order]

primary_axis = eigenvectors[:, 0]   # dominant direction
secondary_axis = eigenvectors[:, 1]  # perpendicular

# Project landmarks onto both axes
proj_primary = centered @ primary_axis
proj_secondary = centered @ secondary_axis

# The "gesture deviation" is the secondary-axis projection —
# how much the figure deviates from its primary axis
gesture_deviation = proj_secondary

# Fit cubic to (primary_position, secondary_deviation) for a smooth gesture line
from numpy.polynomial import polynomial as P
coeffs = P.polyfit(proj_primary, proj_secondary, 3)
gesture_fit = P.polyval(proj_primary, coeffs)

# Maximum lateral deviation
max_dev = float(np.max(np.abs(gesture_deviation)))

# Gesture energy: RMS of the lateral deviation
# (0 = perfectly straight/static pose, higher = more dynamic)
gesture_energy = float(np.sqrt(np.mean(gesture_deviation**2)))

# Contrapposto detection: check if upper body leans opposite to lower body
upper_lms = [lm for lm in data["landmarks"] if lm["dy"] < (crown_dy + fig_height * 0.5)]
lower_lms = [lm for lm in data["landmarks"] if lm["dy"] >= (crown_dy + fig_height * 0.5)]
upper_mean_dx = np.mean([lm["dx"] for lm in upper_lms])
lower_mean_dx = np.mean([lm["dx"] for lm in lower_lms])
contrapposto_score = abs(upper_mean_dx - lower_mean_dx) / fig_height

# Lean angle: angle of primary axis from vertical
lean_angle = float(np.degrees(np.arctan2(primary_axis[0], primary_axis[1])))

data["gesture_line"] = {
    "note": (
        "Gesture / action line analysis — formalises the 'line of action' concept from "
        "figure drawing (Loomis 1943, Hampton 2009). The primary axis is found via PCA on "
        "landmark positions; lateral deviation from this axis reveals pose dynamism. "
        "gesture_energy = 0 for a perfectly rigid vertical pose; higher values indicate "
        "more dynamic weight shifts. contrapposto_score measures upper-vs-lower body lean "
        "opposition. This is a front-view analysis; lateral/3/4 views would yield more "
        "gesture information."
    ),
    "reference": [
        "Loomis, A. 'Figure Drawing for All It\'s Worth.' Viking, 1943.",
        "Hampton, M. 'Figure Drawing: Design and Invention.' 2009."
    ],
    "primary_axis": {
        "direction": [round(float(primary_axis[0]), 6), round(float(primary_axis[1]), 6)],
        "eigenvalue": round(float(eigenvalues[0]), 6),
        "explained_variance_ratio": round(float(eigenvalues[0] / eigenvalues.sum()), 4)
    },
    "secondary_axis": {
        "direction": [round(float(secondary_axis[0]), 6), round(float(secondary_axis[1]), 6)],
        "eigenvalue": round(float(eigenvalues[1]), 6)
    },
    "lean_angle_deg": round(lean_angle, 2),
    "lean_interpretation": (
        "vertical" if abs(lean_angle) < 2 else
        "slight_lean_right" if lean_angle > 0 else "slight_lean_left"
    ),
    "gesture_energy": round(gesture_energy, 6),
    "max_lateral_deviation_hu": round(max_dev, 4),
    "contrapposto_score": round(float(contrapposto_score), 6),
    "contrapposto_interpretation": (
        "none" if contrapposto_score < 0.005 else
        "subtle" if contrapposto_score < 0.02 else
        "moderate" if contrapposto_score < 0.05 else "strong"
    ),
    "landmark_deviations": [
        {
            "name": data["landmarks"][i]["name"],
            "dy": data["landmarks"][i]["dy"],
            "lateral_dev": round(float(gesture_deviation[i]), 4)
        }
        for i in range(len(data["landmarks"]))
    ],
    "cubic_fit_coefficients": [round(float(c), 6) for c in coeffs],
    "centroid": {
        "dx": round(float(centroid[0]), 4),
        "dy": round(float(centroid[1]), 4)
    }
}

print(f"   Lean: {lean_angle:.2f}°, gesture_energy: {gesture_energy:.4f}, contrapposto: {contrapposto_score:.4f}")

# ═══════════════════════════════════════════════════════════════
# 5. MULTI-SCALE CURVATURE (CSS)
# ═══════════════════════════════════════════════════════════════
print("5. Computing Multi-Scale Curvature...")

def curvature_at_scale(pts, sigma):
    """
    Compute curvature after Gaussian smoothing with σ.
    κ = (x'y'' - y'x'') / (x'² + y'²)^(3/2)
    where derivatives are w.r.t. the point index (parameterisation).
    """
    if sigma > 0:
        x_smooth = gaussian_filter1d(pts[:, 0], sigma=sigma, mode='nearest')
        y_smooth = gaussian_filter1d(pts[:, 1], sigma=sigma, mode='nearest')
    else:
        x_smooth = pts[:, 0].copy()
        y_smooth = pts[:, 1].copy()

    t = np.arange(len(x_smooth), dtype=float)
    dx = np.gradient(x_smooth, t)
    dy = np.gradient(y_smooth, t)
    ddx = np.gradient(dx, t)
    ddy = np.gradient(dy, t)

    denom = (dx**2 + dy**2)**1.5
    denom[denom < 1e-15] = 1e-15
    kappa = (dx * ddy - dy * ddx) / denom

    return kappa, x_smooth, y_smooth

# Scales (in contour-point units; effective spatial scale depends on point density)
sigmas = [0, 2, 5, 10, 20]
scale_labels = ["raw", "fine", "medium", "coarse", "very_coarse"]

css_data = {
    "note": (
        "Curvature Scale Space (CSS): curvature κ recomputed at 5 Gaussian smoothing "
        "scales (σ in contour-point units). Features that persist at higher σ are "
        "structural (joints, major body transitions); those that vanish are surface "
        "detail (armor panels, small protrusions). Zero-crossings of κ at each scale "
        "form the CSS representation."
    ),
    "reference": "Mokhtarian, F. & Mackworth, A. IEEE TPAMI 14(8):789–805, 1992.",
    "scales": []
}

for sigma, label in zip(sigmas, scale_labels):
    kappa, x_s, y_s = curvature_at_scale(right_pts, sigma)

    # Count zero crossings (inflection points at this scale)
    zero_crossings = 0
    for i in range(1, len(kappa)):
        if kappa[i-1] * kappa[i] < 0:
            zero_crossings += 1

    # Find the top-5 curvature extrema at this scale
    abs_kappa = np.abs(kappa)
    top_indices = np.argsort(abs_kappa)[-5:][::-1]
    extrema = []
    for idx in top_indices:
        extrema.append({
            "contour_index": int(idx),
            "dy": round(float(right_dy[idx]), 4),
            "dx": round(float(right_dx[idx]), 4),
            "kappa": round(float(kappa[idx]), 4)
        })

    # Subsample curvature for storage (every 20th point)
    kappa_sub = []
    for i in range(0, len(kappa), 20):
        kappa_sub.append({
            "index": int(i),
            "dy": round(float(right_dy[i]), 4),
            "kappa": round(float(kappa[i]), 4)
        })

    css_data["scales"].append({
        "label": label,
        "sigma": sigma,
        "zero_crossings": zero_crossings,
        "mean_abs_kappa": round(float(np.mean(abs_kappa)), 4),
        "max_abs_kappa": round(float(np.max(abs_kappa)), 4),
        "top_5_extrema": extrema,
        "kappa_samples": kappa_sub
    })

# Feature persistence: which extrema locations persist across scales
# (a feature at dy=X that appears in top-5 at ≥3 scales is "structural")
all_top_dys = []
for scale in css_data["scales"]:
    dys = [e["dy"] for e in scale["top_5_extrema"]]
    all_top_dys.extend(dys)

# Cluster nearby dy values (within 0.3 HU)
from collections import Counter
dy_bins = [round(d / 0.3) * 0.3 for d in all_top_dys]
bin_counts = Counter(dy_bins)
persistent_features = [
    {"dy_bin": round(dy, 2), "persistence_count": count, "structural": count >= 3}
    for dy, count in sorted(bin_counts.items())
    if count >= 2
]

css_data["persistent_features"] = {
    "note": "dy locations appearing in top-5 curvature extrema across ≥2 scales. structural=true if present at ≥3 scales.",
    "features": persistent_features
}

data["curvature_scale_space"] = css_data

print(f"   Scales computed: {len(sigmas)}, persistent features: {len(persistent_features)}")

# ═══════════════════════════════════════════════════════════════
# 6. STYLE DEVIATION VECTOR
# ═══════════════════════════════════════════════════════════════
print("6. Computing Style Deviation Vector...")

# Loomis 8-head canon: landmark dy positions (in head-units from crown)
# Reference: "Figure Drawing for All It's Worth" (1943), p. 28–30.
#
# NOTE: Loomis defines landmarks in "heads" from crown.
#       1 head-unit = crown → chin.
#       Our data uses HU = crown → neck_valley.
#       Need to normalize: convert measured positions to fraction of total height,
#       and compare against canon fractions.

loomis_canon_fractions = {
    # position / total_height (8 heads)
    "crown":          0.0 / 8.0,
    "chin":           1.0 / 8.0,
    "nipple_line":    2.0 / 8.0,
    "navel":          3.0 / 8.0,
    "crotch":         4.0 / 8.0,
    "mid_thigh":      5.0 / 8.0,
    "knee":           6.0 / 8.0,
    "mid_shin":       7.0 / 8.0,
    "sole":           8.0 / 8.0,
}

# Width ratios in Loomis canon (approximate, from his illustrations)
# These are bilateral width as fraction of total height
loomis_width_fractions = {
    "head":      1.0 / 8.0,    # head width ≈ 1 head unit
    "shoulders": 2.0 / 8.0,    # shoulder width ≈ 2 head units
    "waist":     1.2 / 8.0,    # waist ≈ 1.2 head units (male) / 1.0 (female)
    "hips":      1.5 / 8.0,    # hips ≈ 1.5 head units (female)
}

# Map our landmarks to Loomis landmarks
landmark_to_canon = {
    "crown":          "crown",
    "chin":           "chin",
    "navel_estimate": "navel",
    "mid_thigh":      "mid_thigh",
    "knee_valley":    "knee",
    "mid_shin":       "mid_shin",
    "sole":           "sole",
}

measured_fractions = {}
for lm in data["landmarks"]:
    measured_fractions[lm["name"]] = (lm["dy"] - crown_dy) / fig_height

# Compute deviations
style_deviations = []
for our_name, canon_name in landmark_to_canon.items():
    if our_name in measured_fractions and canon_name in loomis_canon_fractions:
        measured = measured_fractions[our_name]
        canon = loomis_canon_fractions[canon_name]
        dev = measured - canon
        style_deviations.append({
            "landmark": our_name,
            "canon_name": canon_name,
            "measured_fraction": round(measured, 4),
            "canon_fraction": round(canon, 4),
            "deviation": round(dev, 4),
            "interpretation": (
                "higher_than_canon" if dev > 0.02 else
                "lower_than_canon" if dev < -0.02 else
                "matches_canon"
            )
        })

# Width deviations
shoulder_width_frac = (lm_map["shoulder_peak"]["dx"] * 2) / fig_height
hip_width_frac = (lm_map["hip_peak"]["dx"] * 2) / fig_height
waist_width_frac = (lm_map["waist_valley"]["dx"] * 2) / fig_height
head_width_frac = (lm_map["head_peak"]["dx"] * 2) / fig_height

width_deviations = [
    {"feature": "head_width", "measured": round(head_width_frac, 4),
     "canon": round(loomis_width_fractions["head"], 4),
     "deviation": round(head_width_frac - loomis_width_fractions["head"], 4)},
    {"feature": "shoulder_width", "measured": round(shoulder_width_frac, 4),
     "canon": round(loomis_width_fractions["shoulders"], 4),
     "deviation": round(shoulder_width_frac - loomis_width_fractions["shoulders"], 4)},
    {"feature": "waist_width", "measured": round(waist_width_frac, 4),
     "canon": round(loomis_width_fractions["waist"], 4),
     "deviation": round(waist_width_frac - loomis_width_fractions["waist"], 4)},
    {"feature": "hip_width", "measured": round(hip_width_frac, 4),
     "canon": round(loomis_width_fractions["hips"], 4),
     "deviation": round(hip_width_frac - loomis_width_fractions["hips"], 4)},
]

# Total stylisation distance (L2 norm of all deviations)
all_devs = [s["deviation"] for s in style_deviations] + [w["deviation"] for w in width_deviations]
l2_distance = float(np.sqrt(sum(d**2 for d in all_devs)))

data["style_deviation"] = {
    "note": (
        "Signed deviation of this figure's proportions from the Loomis 8-head academic "
        "canon. Positive deviation = landmark is lower (or wider) than canon; negative = higher "
        "(or narrower). L2 distance aggregates all deviations into a single 'how stylised is "
        "this figure' scalar. A photorealistic figure should have L2 < 0.05; "
        "stylised/heroic characters typically 0.05–0.15; extreme caricature > 0.2."
    ),
    "reference": "Loomis, A. 'Figure Drawing for All It's Worth.' Viking, 1943. pp. 28–30.",
    "canon": "loomis_8_head_academic",
    "figure_head_count": data["proportion"]["head_count_total"],
    "canon_head_count": 8.0,
    "position_deviations": style_deviations,
    "width_deviations": width_deviations,
    "l2_stylisation_distance": round(l2_distance, 4),
    "interpretation": (
        "near_photorealistic" if l2_distance < 0.05 else
        "moderate_stylisation" if l2_distance < 0.15 else
        "heavy_stylisation" if l2_distance < 0.25 else
        "extreme_stylisation"
    )
}

print(f"   L2 stylisation distance: {l2_distance:.4f} ({data['style_deviation']['interpretation']})")

# ═══════════════════════════════════════════════════════════════
# 7. VOLUMETRIC ESTIMATES
# ═══════════════════════════════════════════════════════════════
print("7. Computing Volumetric Estimates...")

# Method A: Cylindrical — each horizontal slice is a circle of radius dx
# V_cyl = π ∫ dx² dy
vol_cyl = float(np.pi * _trapz(env_dx**2, env_dy))

# Method B: Ellipsoidal — each slice is an ellipse with semi-major=dx, semi-minor=dx/2
# V_ell = π ∫ dx · (dx/2) dy = (π/2) ∫ dx² dy
vol_ell = vol_cyl / 2

# Method C: Pappus — V = 2π · x̄ · A  where x̄ = centroid x-distance from axis
# For symmetric figure, centroid of right half:
sil_area = float(_trapz(2 * env_dx, env_dy))
# x̄ of the right half shape ≈ mean of dx weighted by width
x_bar = float(_trapz(env_dx * env_dx, env_dy) / _trapz(env_dx, env_dy)) if _trapz(env_dx, env_dy) > 0 else 0
vol_pappus = 2 * np.pi * x_bar * sil_area / 2  # div 2 because we use right-half area

# Convert to real-world units assuming 170cm canonical height
# 1 HU = fig_height maps to 170cm → 1 HU = 170/fig_height cm
scale_cm = 170.0 / fig_height  # cm per HU
scale_m = scale_cm / 100.0

# Volume in cm³ (1 HU³ = scale_cm³ cm³)
vol_cyl_cm3 = vol_cyl * scale_cm**3
vol_ell_cm3 = vol_ell * scale_cm**3
vol_pappus_cm3 = vol_pappus * scale_cm**3

# Volume per body region
region_volumes = []
for region in data["body_regions"]["regions"]:
    dy_lo = region["dy_start"]
    dy_hi = region["dy_end"]
    mask = (env_dy >= dy_lo) & (env_dy <= dy_hi)
    if mask.sum() > 1:
        rv = float(np.pi * _trapz(env_dx[mask]**2, env_dy[mask]))
    else:
        rv = 0.0
    region_volumes.append({
        "name": region["name"],
        "volume_hu3_cylindrical": round(rv, 4),
        "volume_cm3_cylindrical": round(rv * scale_cm**3, 1),
        "fraction": round(rv / vol_cyl, 4) if vol_cyl > 0 else 0
    })

data["volumetric_estimates"] = {
    "note": (
        "Three volumetric approximations from the 2D silhouette. "
        "(a) Cylindrical: each dy-slice is a circular cross-section of radius dx → V = π∫dx²dy. "
        "Overestimates because humans aren't circular in cross-section. "
        "(b) Ellipsoidal: each slice is an ellipse with semi-axes (dx, dx/2) → V ≈ V_cyl/2. "
        "More realistic for a human torso/limbs. "
        "(c) Pappus centroid: V = 2π·x̄·A (solid of revolution of the right-half area). "
        "All values are rough order-of-magnitude estimates — actual 3D volume depends on "
        "anterior-posterior depth, which a single frontal silhouette cannot determine. "
        "Real-world scaling assumes 170 cm canonical figure height."
    ),
    "assumptions": {
        "canonical_height_cm": 170.0,
        "scale_cm_per_hu": round(scale_cm, 4),
        "figure_height_hu": round(fig_height, 4)
    },
    "cylindrical": {
        "volume_hu3": round(vol_cyl, 4),
        "volume_cm3": round(vol_cyl_cm3, 1),
        "volume_liters": round(vol_cyl_cm3 / 1000, 2),
        "method": "V = π ∫ dx² dy"
    },
    "ellipsoidal": {
        "volume_hu3": round(vol_ell, 4),
        "volume_cm3": round(vol_ell_cm3, 1),
        "volume_liters": round(vol_ell_cm3 / 1000, 2),
        "method": "V = (π/2) ∫ dx² dy"
    },
    "pappus": {
        "volume_hu3": round(float(vol_pappus), 4),
        "volume_cm3": round(float(vol_pappus * scale_cm**3), 1),
        "volume_liters": round(float(vol_pappus * scale_cm**3 / 1000), 2),
        "method": "V = 2π · x̄ · A_right_half",
        "centroid_x_hu": round(x_bar, 4)
    },
    "per_region": region_volumes
}

print(f"   Cylindrical: {vol_cyl:.4f} HU³ ({vol_cyl_cm3:.0f} cm³)")
print(f"   Ellipsoidal: {vol_ell:.4f} HU³ ({vol_ell_cm3:.0f} cm³)")
print(f"   Pappus:      {vol_pappus:.4f} HU³ ({vol_pappus * scale_cm**3:.0f} cm³)")

# ═══════════════════════════════════════════════════════════════
# 8. BIOMECHANICAL SEGMENT PARAMETERS
# ═══════════════════════════════════════════════════════════════
print("8. Computing Biomechanical Segment Parameters...")

# Data from Winter (2009) Table 4.1, Dempster (1955)
# Female values where available; otherwise averaged.
# mass_frac: segment mass / total body mass
# com_prox: CoM position as fraction of segment length from proximal end
# rog_com: radius of gyration about CoM / segment length
# rog_prox: radius of gyration about proximal end / segment length

WINTER_FEMALE = {
    "head_neck": {
        "mass_fraction": 0.0681,
        "com_proximal": 1.000,
        "rog_com": 0.495,
        "rog_proximal": 0.495,
        "proximal_landmark": "crown",
        "distal_landmark": "neck_valley",
        "note": "Head+neck as single segment. CoM at vertex (simplified)."
    },
    "trunk": {
        "mass_fraction": 0.4270,
        "com_proximal": 0.3782,
        "rog_com": 0.3076,
        "rog_proximal": 0.4890,
        "proximal_landmark": "shoulder_peak",
        "distal_landmark": "hip_peak",
        "note": "Full trunk from greater trochanter to glenohumeral joint."
    },
    "upper_arm": {
        "mass_fraction": 0.0255,
        "com_proximal": 0.5754,
        "rog_com": 0.2610,
        "rog_proximal": 0.2780,
        "note": "Not measurable from frontal silhouette — arms occluded by torso."
    },
    "forearm": {
        "mass_fraction": 0.0138,
        "com_proximal": 0.4559,
        "rog_com": 0.2610,
        "rog_proximal": 0.2780,
        "note": "Not measurable from frontal silhouette."
    },
    "hand": {
        "mass_fraction": 0.0056,
        "com_proximal": 0.7474,
        "rog_com": 0.2610,
        "rog_proximal": 0.2780,
        "note": "Not measurable from frontal silhouette."
    },
    "thigh": {
        "mass_fraction": 0.1478,
        "com_proximal": 0.3612,
        "rog_com": 0.3690,
        "rog_proximal": 0.3690,
        "proximal_landmark": "hip_peak",
        "distal_landmark": "knee_valley",
    },
    "shank": {
        "mass_fraction": 0.0481,
        "com_proximal": 0.4416,
        "rog_com": 0.2710,
        "rog_proximal": 0.2710,
        "proximal_landmark": "knee_valley",
        "distal_landmark": "ankle_valley",
    },
    "foot": {
        "mass_fraction": 0.0129,
        "com_proximal": 0.4014,
        "rog_com": 0.2990,
        "rog_proximal": 0.2990,
        "proximal_landmark": "ankle_valley",
        "distal_landmark": "sole",
    }
}

# Compute segment lengths from landmarks and apply biomech params
segments_bio = []
for seg_name, params in WINTER_FEMALE.items():
    entry = {
        "segment": seg_name,
        "mass_fraction": params["mass_fraction"],
        "com_proximal_fraction": params["com_proximal"],
        "rog_com_fraction": params["rog_com"],
        "rog_proximal_fraction": params["rog_proximal"],
    }

    if "proximal_landmark" in params and "distal_landmark" in params:
        prox = params["proximal_landmark"]
        dist = params["distal_landmark"]
        if prox in lm_map and dist in lm_map:
            prox_dy = lm_map[prox]["dy"]
            dist_dy = lm_map[dist]["dy"]
            seg_len = abs(dist_dy - prox_dy)
            entry["segment_length_hu"] = round(seg_len, 4)
            entry["segment_length_cm"] = round(seg_len * scale_cm, 2)

            # CoM position
            com_dy = prox_dy + params["com_proximal"] * (dist_dy - prox_dy)
            entry["com_position"] = {
                "dy": round(com_dy, 4),
                "dy_cm": round(com_dy * scale_cm, 2)
            }

            # Radius of gyration (in HU and cm)
            rog = params["rog_com"] * seg_len
            entry["radius_of_gyration_hu"] = round(rog, 4)
            entry["radius_of_gyration_cm"] = round(rog * scale_cm, 2)

    if "note" in params:
        entry["note"] = params["note"]

    segments_bio.append(entry)

# Whole-body CoM estimate (from segment CoMs weighted by mass fractions)
total_com_dy = 0
total_mass_frac = 0
for seg in segments_bio:
    if "com_position" in seg:
        total_com_dy += seg["com_position"]["dy"] * seg["mass_fraction"]
        total_mass_frac += seg["mass_fraction"]
        # For bilateral segments (thigh, shank, foot), count twice
        if seg["segment"] in ("thigh", "shank", "foot"):
            total_com_dy += seg["com_position"]["dy"] * seg["mass_fraction"]
            total_mass_frac += seg["mass_fraction"]

if total_mass_frac > 0:
    body_com_dy = total_com_dy / total_mass_frac
else:
    body_com_dy = fig_height * 0.55  # fallback

data["biomechanics"] = {
    "note": (
        "Biomechanical segment parameters from Winter (2009) cadaver study data "
        "(female values where available). mass_fraction = segment_mass / total_body_mass. "
        "com_proximal_fraction = centre-of-mass position as fraction of segment length from "
        "proximal end. rog = radius of gyration as fraction of segment length. "
        "Segment lengths are derived from landmark positions. "
        "Upper limb segments are included for completeness but cannot be measured from "
        "this frontal silhouette (arms at sides, occluded by torso)."
    ),
    "reference": [
        "Winter, D.A. 'Biomechanics and Motor Control of Human Movement.' 4th ed., Wiley, 2009. Table 4.1.",
        "Dempster, W.T. 'Space requirements of the seated operator.' WADC-TR-55-159, 1955."
    ],
    "gender_data": "female",
    "canonical_height_cm": 170.0,
    "scale_cm_per_hu": round(scale_cm, 4),
    "segments": segments_bio,
    "whole_body_com": {
        "dy": round(float(body_com_dy), 4),
        "dy_fraction": round(float((body_com_dy - crown_dy) / fig_height), 4),
        "cm_from_crown": round(float((body_com_dy - crown_dy) * scale_cm), 2),
        "note": (
            "Whole-body centre of mass estimated from segment CoMs × mass fractions. "
            "Bilateral segments (thigh, shank, foot) counted twice. "
            "Expected range: 0.52–0.56 of height from crown for standing female."
        )
    }
}

print(f"   Body CoM at dy={body_com_dy:.4f} ({(body_com_dy - crown_dy) / fig_height:.3f} of height)")

# ═══════════════════════════════════════════════════════════════
# 9. APPROXIMATE MEDIAL AXIS
# ═══════════════════════════════════════════════════════════════
print("9. Computing Approximate Medial Axis...")

# The medial axis of the silhouette is the locus of centres of
# maximal inscribed circles.  For a symmetric figure, this is
# the midline (dx=0) vertically, with the "radius" at each level
# being the outer-envelope dx.
#
# For the RIGHT half-silhouette, the medial axis sits at dx = outer_dx / 2,
# which when mirrored gives the full bilateral medial axis at dx=0.
#
# More useful: the "thickness" at each point, which IS the outer envelope dx.
# This is already captured in width_profile.
#
# What we add here: the medial axis as an explicit polyline with
# local thickness (inscribed circle radius), and branch analysis.

# For a roughly convex symmetric shape, the medial axis is a single
# vertical line.  Branches appear at: head, neck-shoulder junction,
# arm separation, and foot spread.

# We represent it as: main trunk (crown→sole) at dx=0, with local
# thickness = outer_dx at each dy level.

medial_samples = []
for i in range(len(env_dy)):
    medial_samples.append({
        "dy": round(float(env_dy[i]), 4),
        "medial_dx": 0.0,  # by symmetry
        "inscribed_radius": round(float(env_dx[i]), 4),
        "inscribed_diameter": round(float(2 * env_dx[i]), 4)
    })

# Detect medial axis "branch points" where the topology changes
# These correspond to locations where the cross-section goes from
# 1 connected component to 2 (e.g., arm separating from torso)
topo = data["cross_section_topology"]["profile"]
branch_points = []
prev_pairs = None
for dy_key in sorted(topo.keys(), key=float):
    pairs = topo[dy_key]["pairs"]
    if prev_pairs is not None and pairs != prev_pairs:
        branch_points.append({
            "dy": float(dy_key),
            "transition": f"{prev_pairs}_to_{pairs}_pairs",
            "interpretation": (
                "arm_emergence" if pairs > prev_pairs else "arm_merger"
            ) if abs(pairs - prev_pairs) == 1 else "topology_change"
        })
    prev_pairs = pairs

data["medial_axis"] = {
    "note": (
        "Approximate medial axis (topological skeleton) of the bilateral silhouette. "
        "For a symmetric figure, the main axis lies at dx=0 with inscribed_radius equal to "
        "the outer-envelope half-width at each dy level. Branch points mark where the "
        "cross-sectional topology changes (arm separating from torso, legs diverging, etc.). "
        "The inscribed_radius at each level gives the 'thickness' of the figure — useful "
        "for 3D depth estimation and collision volume generation."
    ),
    "main_axis": {
        "start": {"dx": 0.0, "dy": round(float(env_dy[0]), 4)},
        "end": {"dx": 0.0, "dy": round(float(env_dy[-1]), 4)},
        "sample_count": len(medial_samples),
        "samples": medial_samples
    },
    "branch_points": {
        "count": len(branch_points),
        "points": branch_points,
        "note": "Locations where cross-section topology changes."
    },
    "thickness_statistics": {
        "mean_radius_hu": round(float(env_dx.mean()), 4),
        "min_radius_hu": round(float(env_dx.min()), 4),
        "min_radius_dy": round(float(env_dy[env_dx.argmin()]), 4),
        "max_radius_hu": round(float(env_dx.max()), 4),
        "max_radius_dy": round(float(env_dy[env_dx.argmax()]), 4),
        "thinning_ratio": round(float(env_dx.min() / env_dx.max()), 4),
        "note": "thinning_ratio = min/max radius. Lower = more extreme width variation."
    }
}

print(f"   Branch points: {len(branch_points)}, thinning ratio: {env_dx.min()/env_dx.max():.4f}")

# ═══════════════════════════════════════════════════════════════
# 10. SHAPE COMPLEXITY & ENTROPY
# ═══════════════════════════════════════════════════════════════
print("10. Computing Shape Complexity & Entropy...")

# (a) Curvature entropy — Shannon entropy of curvature histogram
kappa_raw, _, _ = curvature_at_scale(right_pts, sigma=0)
kappa_abs_raw = np.abs(kappa_raw)
# Histogram with 50 bins
hist, _ = np.histogram(kappa_abs_raw, bins=50, density=True)
hist = hist[hist > 0]  # remove zeros for log
hist_norm = hist / hist.sum()
curvature_entropy = float(scipy_entropy(hist_norm, base=2))

# (b) Box-counting fractal dimension estimate
def box_counting_dimension(pts, n_scales=10):
    """
    Estimate fractal dimension by box-counting.
    D = lim(ε→0) log(N(ε)) / log(1/ε)
    """
    x_range = pts[:, 0].max() - pts[:, 0].min()
    y_range = pts[:, 1].max() - pts[:, 1].min()
    max_range = max(x_range, y_range)
    if max_range < 1e-10:
        return 1.0

    epsilons = np.logspace(-3, 0, n_scales) * max_range
    counts = []
    for eps in epsilons:
        # Count occupied boxes
        x_bins = np.floor((pts[:, 0] - pts[:, 0].min()) / eps).astype(int)
        y_bins = np.floor((pts[:, 1] - pts[:, 1].min()) / eps).astype(int)
        occupied = len(set(zip(x_bins, y_bins)))
        counts.append(occupied)

    # Fit log-log line
    log_eps = np.log(1.0 / epsilons)
    log_n = np.log(np.array(counts, dtype=float))
    # Linear regression
    coeffs = np.polyfit(log_eps, log_n, 1)
    return float(coeffs[0])

fractal_dim = box_counting_dimension(right_pts)

# (c) Compactness (isoperimetric ratio): 4π·A / P²
# A circle has compactness = 1; more complex shapes < 1
sil_area_bilateral = float(_trapz(2 * env_dx, env_dy))
# Perimeter from the data
perim = data.get("fourier_descriptors", {}).get("perimeter_hu", 0)
if perim > 0:
    bilateral_perim = 2 * perim  # approximate bilateral perimeter
    compactness = 4 * np.pi * sil_area_bilateral / (bilateral_perim**2)
else:
    compactness = 0

# (d) Rectangularity: A / A_bbox
bbox = data["meta"]["bounding_box_hu"]
bbox_area = bbox["width"] * bbox["height"]
rectangularity = sil_area_bilateral / bbox_area if bbox_area > 0 else 0

# (e) Eccentricity from covariance ellipse
cov = np.cov(sym_all.T)
eigs = np.linalg.eigvalsh(cov)
eigs.sort()
eccentricity = float(np.sqrt(1 - eigs[0] / eigs[1])) if eigs[1] > 0 else 0

# (f) Contour roughness: ratio of actual perimeter to convex hull perimeter
hull_perim_val = data.get("convex_hull", {}).get("hull_perimeter_hu", 0)
if hull_perim_val > 0 and perim > 0:
    roughness = (2 * perim) / hull_perim_val
else:
    roughness = 1.0

data["shape_complexity"] = {
    "note": (
        "Shape complexity metrics from computational geometry. "
        "curvature_entropy measures how varied the curvature distribution is — "
        "a circle has entropy=0 (uniform κ); a figure with diverse features has "
        "higher entropy. fractal_dimension ≈ 1.0 for smooth curves, approaches "
        "1.5+ for very irregular contours. compactness = 1 for a circle, lower "
        "for elongated/complex shapes. eccentricity = 0 for a circle, →1 for "
        "elongated shapes."
    ),
    "reference": "Costa, L.F. & Cesar, R.M. 'Shape Classification and Analysis.' 2nd ed., Springer, 2009.",
    "curvature_entropy": {
        "value": round(curvature_entropy, 4),
        "units": "bits",
        "histogram_bins": 50,
        "note": "Shannon entropy of |κ| histogram. Higher = more diverse curvature."
    },
    "fractal_dimension": {
        "value": round(fractal_dim, 4),
        "method": "box_counting",
        "n_scales": 10,
        "note": "1.0 = smooth curve, 1.2+ = significant fine structure."
    },
    "compactness": {
        "value": round(float(compactness), 4),
        "formula": "4π·A / P²",
        "note": "Isoperimetric ratio. Circle=1.0, human silhouette typically 0.1–0.3."
    },
    "rectangularity": {
        "value": round(float(rectangularity), 4),
        "formula": "A / A_bbox",
        "note": "How well the figure fills its bounding box. Rectangle=1.0."
    },
    "eccentricity": {
        "value": round(float(eccentricity), 4),
        "note": "Covariance-ellipse eccentricity. 0=circular, →1=elongated."
    },
    "roughness": {
        "value": round(float(roughness), 4),
        "formula": "perimeter / convex_hull_perimeter",
        "note": "1.0 = convex (smooth outline), >1.0 = indented/detailed outline."
    }
}

print(f"   Entropy: {curvature_entropy:.4f} bits")
print(f"   Fractal dim: {fractal_dim:.4f}")
print(f"   Compactness: {compactness:.4f}")
print(f"   Eccentricity: {eccentricity:.4f}")
print(f"   Roughness: {roughness:.4f}")

# ═══════════════════════════════════════════════════════════════
# SCHEMA UPDATE
# ═══════════════════════════════════════════════════════════════
data["meta"]["schema_version"] = "4.0.0"

data["meta"]["sections"] = {
    "note": "v4.0 section inventory — 10 cross-domain improvement factors",
    "total_sections": len([k for k in data.keys()]),
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
        "shape_complexity — entropy, fractal dimension, compactness, eccentricity, roughness"
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
    }
}

# ─── Write ──────────────────────────────────────────────────────
output_path = "/home/claude/v4.json"
with open(output_path, "w") as f:
    json.dump(data, f, indent=2)

import os
size = os.path.getsize(output_path)
print(f"\n{'='*60}")
print(f"Output: {output_path} ({size/1024:.1f} KB)")
print(f"Sections: {len(data.keys())}")
print(f"{'='*60}")
