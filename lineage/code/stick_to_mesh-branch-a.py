"""
stick_to_mesh.py — Stick Figure → 3D Mesh Pipeline
═══════════════════════════════════════════════════════

End-to-end pipeline that transforms a 2D stick figure into a closed
3D triangle mesh, structured as a finite-horizon MDP with heuristic
policies and RL integration points.

Usage:
    python3 stick_to_mesh.py [--rings N] [--output path.obj] [--json path.json]

Stages:
    0  INPUT       Stick figure joint positions (2D)
    1  PROPORTION  Apply anatomical ratios → proportioned skeleton
    2  PROFILE     Generate bilateral width at each dy level
    3  CONTOUR     Create smooth 2D silhouette contour
    4  DEPTH       Estimate anterior-posterior depth per level
    5  MESH        Generate coarse 3D mesh (generalized cylinders)
    6  REFINE      Laplacian smoothing + optional subdivision
    7  EXPORT      Write OBJ + enriched JSON descriptor

Each stage is a class with:
    observe(state) → observation vector
    act(observation) → action vector  (heuristic or RL policy)
    step(state, action) → (next_state, reward, info)
"""

import json
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from scipy.interpolate import CubicSpline
from scipy.ndimage import gaussian_filter1d
import argparse
import sys
import os


# ═══════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════

@dataclass
class Joint:
    """A named joint in the stick figure."""
    name: str
    x: float      # lateral position (0 = midline, + = right)
    y: float      # vertical position (0 = top, + = down)
    parent: Optional[str] = None

@dataclass
class PipelineState:
    """Full pipeline state passed between stages."""
    # Stage 0: Raw input
    joints: List[Joint] = field(default_factory=list)

    # Stage 1: Proportioned skeleton
    segment_lengths: Dict[str, float] = field(default_factory=dict)
    head_height: float = 0.0
    total_height: float = 0.0
    head_count: float = 0.0

    # Stage 2: Width profile
    width_dy: Optional[np.ndarray] = None     # dy sample points
    width_dx: Optional[np.ndarray] = None     # half-width at each dy

    # Stage 3: Contour
    contour: Optional[np.ndarray] = None      # (P, 2) closed contour

    # Stage 4: Depth profile
    depth_dy: Optional[np.ndarray] = None     # dy sample points
    depth_dz: Optional[np.ndarray] = None     # half-depth at each dy

    # Stage 5: 3D Mesh
    vertices: Optional[np.ndarray] = None     # (V, 3)
    faces: Optional[np.ndarray] = None        # (F, 3) triangle indices

    # Metadata
    rewards: Dict[str, float] = field(default_factory=dict)
    actions: Dict[str, np.ndarray] = field(default_factory=dict)
    info: Dict[str, dict] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# RL AGENT BASE CLASS
# ═══════════════════════════════════════════════════════════════

class StageAgent:
    """
    Base class for pipeline stage agents.

    Each stage has three methods:
      observe(state) → flat observation vector
      act(observation) → action vector  (override for RL)
      step(state, action) → (state, reward, info)

    The default act() uses a heuristic policy.
    To train with RL, subclass and override act() with a neural
    network policy.
    """

    def __init__(self, name: str, action_dim: int):
        self.name = name
        self.action_dim = action_dim

    def observe(self, state: PipelineState) -> np.ndarray:
        raise NotImplementedError

    def act(self, observation: np.ndarray) -> np.ndarray:
        """Heuristic policy. Override with learned policy for RL."""
        raise NotImplementedError

    def step(self, state: PipelineState, action: np.ndarray
             ) -> Tuple[PipelineState, float, dict]:
        raise NotImplementedError

    def __call__(self, state: PipelineState) -> Tuple[PipelineState, float, dict]:
        obs = self.observe(state)
        action = self.act(obs)
        state, reward, info = self.step(state, action)
        state.rewards[self.name] = reward
        state.actions[self.name] = action
        state.info[self.name] = info
        return state, reward, info


# ═══════════════════════════════════════════════════════════════
# STAGE 0: INPUT
# ═══════════════════════════════════════════════════════════════

def make_default_stick() -> List[Joint]:
    """
    Default stick figure: 11 joints, frontal standing pose.
    Positions in arbitrary units — Stage 1 will normalise.

    Skeleton hierarchy:
        crown → head_base → neck → shoulders
        neck → spine_mid → pelvis
        pelvis → knee_L/R → ankle_L/R
        shoulders → (arms implicit, not drawn)
    """
    return [
        Joint("crown",     0.0,   0.0,  None),
        Joint("head_base", 0.0,   1.0,  "crown"),
        Joint("neck",      0.0,   1.3,  "head_base"),
        Joint("shoulder_L",-1.5,  1.8,  "neck"),
        Joint("shoulder_R", 1.5,  1.8,  "neck"),
        Joint("spine_mid", 0.0,   3.5,  "neck"),
        Joint("pelvis",    0.0,   4.5,  "spine_mid"),
        Joint("knee_L",   -0.5,   6.5,  "pelvis"),
        Joint("knee_R",    0.5,   6.5,  "pelvis"),
        Joint("ankle_L",  -0.5,   8.3,  "knee_L"),
        Joint("ankle_R",   0.5,   8.3,  "knee_R"),
    ]


# ═══════════════════════════════════════════════════════════════
# STAGE 1: PROPORTION
# ═══════════════════════════════════════════════════════════════

class ProportionAgent(StageAgent):
    """
    Applies anatomical proportion ratios to the raw stick figure.

    Action space: [head_count, waist_fraction, hip_fraction]
      head_count:     target figure height in head-units (e.g., 7.5)
      waist_fraction: dy of waist as fraction of total height
      hip_fraction:   dy of hip as fraction of total height

    Heuristic policy uses Loomis female proportions.

    Ref: Loomis, A. "Figure Drawing for All It's Worth." 1943.
    """

    def __init__(self):
        super().__init__("proportion", action_dim=3)

    def observe(self, state: PipelineState) -> np.ndarray:
        joints = state.joints
        ys = [j.y for j in joints]
        raw_height = max(ys) - min(ys)
        n_joints = len(joints)
        return np.array([raw_height, n_joints])

    def act(self, observation: np.ndarray) -> np.ndarray:
        """Heuristic: Loomis 7.5-head female (slightly heroic)."""
        return np.array([
            7.5,   # head count (7.5 = slightly heroic female)
            0.38,  # waist at 38% of height
            0.50,  # hip/crotch at 50% of height
        ])

    def step(self, state, action):
        head_count = action[0]

        # Normalise joint positions to head-units
        joints = state.joints
        ys = np.array([j.y for j in joints])
        xs = np.array([j.x for j in joints])
        y_min, y_max = ys.min(), ys.max()
        raw_height = y_max - y_min

        # Scale so total height = head_count HU
        scale = head_count / raw_height if raw_height > 0 else 1.0
        for j in joints:
            j.y = (j.y - y_min) * scale
            j.x = j.x * scale

        # Compute segment lengths
        joint_map = {j.name: j for j in joints}
        seg_lengths = {}
        for j in joints:
            if j.parent and j.parent in joint_map:
                p = joint_map[j.parent]
                length = np.sqrt((j.x - p.x)**2 + (j.y - p.y)**2)
                seg_lengths[f"{j.parent}→{j.name}"] = round(length, 4)

        # Head height = crown → head_base
        head_h = abs(joint_map["head_base"].y - joint_map["crown"].y) if \
            "head_base" in joint_map and "crown" in joint_map else 1.0

        state.joints = joints
        state.segment_lengths = seg_lengths
        state.head_height = round(head_h, 4)
        state.total_height = round(head_count, 4)
        state.head_count = round(head_count / head_h, 2) if head_h > 0 else head_count

        # Reward: how close to target head count
        reward = -abs(state.head_count - head_count)

        return state, reward, {
            "head_height_hu": state.head_height,
            "head_count": state.head_count,
            "segments": seg_lengths
        }


# ═══════════════════════════════════════════════════════════════
# STAGE 2: WIDTH PROFILE
# ═══════════════════════════════════════════════════════════════

class WidthProfileAgent(StageAgent):
    """
    Generates bilateral half-width dx at each dy level.

    Action space: R^J — half-width at each joint's dy position.

    Heuristic policy uses anatomical width ratios from Loomis and
    the v4 JSON data (if available).

    The width profile fully determines the 2D silhouette shape.
    """

    # Loomis female width ratios (half-width / head_height)
    # Ref: Loomis (1943), Hampton (2009), Hogarth (1996)
    FEMALE_WIDTHS = {
        "crown":      0.00,
        "temple":     0.33,   # ~1/3 head height
        "head_base":  0.25,   # jaw narrowing
        "neck":       0.15,
        "shoulder":   0.95,   # shoulders ≈ 2 head widths bilateral
        "bust":       0.65,
        "waist":      0.45,
        "hip":        0.75,   # hips slightly narrower than shoulders for female
        "mid_thigh":  0.40,
        "knee":       0.28,
        "calf":       0.30,
        "ankle":      0.14,
        "foot":       0.20,
        "sole":       0.15,
    }

    def __init__(self):
        super().__init__("width_profile", action_dim=14)

    def observe(self, state: PipelineState) -> np.ndarray:
        return np.array([
            state.head_height,
            state.total_height,
            state.head_count
        ])

    def act(self, observation: np.ndarray) -> np.ndarray:
        """Heuristic: Loomis female widths scaled by head height."""
        head_h = observation[0]
        return np.array([v * head_h for v in self.FEMALE_WIDTHS.values()])

    def step(self, state, action):
        # Map width values to dy positions
        total_h = state.total_height
        head_h = state.head_height

        # Canonical dy positions (fraction of total height × total_height)
        # Based on Loomis 7.5-head female
        dy_fractions = [
            0.000,  # crown
            0.040,  # temple
            0.120,  # head_base / jaw
            0.155,  # neck
            0.220,  # shoulder
            0.300,  # bust
            0.380,  # waist
            0.500,  # hip
            0.600,  # mid_thigh
            0.700,  # knee
            0.770,  # calf
            0.870,  # ankle
            0.940,  # foot
            1.000,  # sole
        ]

        dy_vals = np.array(dy_fractions) * total_h
        dx_vals = np.array(action[:len(dy_fractions)])

        # Ensure non-negative widths
        dx_vals = np.maximum(dx_vals, 0.0)

        state.width_dy = dy_vals
        state.width_dx = dx_vals

        # Reward: smoothness of width profile (penalise sharp changes)
        if len(dx_vals) > 2:
            d2 = np.diff(dx_vals, 2)
            smoothness = -np.mean(d2**2)
        else:
            smoothness = 0.0

        return state, smoothness, {
            "n_samples": len(dy_vals),
            "max_width": round(float(dx_vals.max()), 4),
            "min_width": round(float(dx_vals[dx_vals > 0].min()), 4) if (dx_vals > 0).any() else 0
        }


# ═══════════════════════════════════════════════════════════════
# STAGE 3: CONTOUR GENERATION
# ═══════════════════════════════════════════════════════════════

class ContourAgent(StageAgent):
    """
    Generates a smooth 2D contour from the width profile.

    Action space: [n_points, smoothing_sigma, tension]
      n_points: number of contour points (right side)
      smoothing_sigma: Gaussian smoothing of the interpolated profile
      tension: spline tension parameter

    Produces a closed contour (right half + mirrored left half).
    """

    def __init__(self):
        super().__init__("contour", action_dim=3)

    def observe(self, state):
        return np.array([
            len(state.width_dy),
            state.total_height,
            state.width_dx.max() if state.width_dx is not None else 0
        ])

    def act(self, observation):
        """Heuristic: 400 points, light smoothing."""
        return np.array([400, 1.5, 0.0])

    def step(self, state, action):
        n_pts = max(50, int(action[0]))
        sigma = max(0.0, action[1])

        dy_in = state.width_dy
        dx_in = state.width_dx

        # Cubic spline interpolation of width profile
        cs = CubicSpline(dy_in, dx_in, bc_type='clamped')

        # Sample at high resolution
        dy_dense = np.linspace(dy_in[0], dy_in[-1], n_pts)
        dx_dense = cs(dy_dense)
        dx_dense = np.maximum(dx_dense, 0.0)  # clamp negative

        # Smooth
        if sigma > 0 and len(dx_dense) > 5:
            dx_dense = gaussian_filter1d(dx_dense, sigma=sigma)
            dx_dense = np.maximum(dx_dense, 0.0)

        # Build closed contour: right side (top→bottom) + left side (bottom→top)
        right_side = np.column_stack([dx_dense, dy_dense])          # right: +dx
        left_side = np.column_stack([-dx_dense[::-1], dy_dense[::-1]])  # left: -dx, reversed

        contour = np.vstack([right_side, left_side])

        state.contour = contour

        # Reward: contour smoothness (low curvature variance)
        if len(contour) > 4:
            dx_c = np.gradient(contour[:, 0])
            dy_c = np.gradient(contour[:, 1])
            ddx = np.gradient(dx_c)
            ddy = np.gradient(dy_c)
            denom = (dx_c**2 + dy_c**2)**1.5
            denom[denom < 1e-12] = 1e-12
            kappa = (dx_c * ddy - dy_c * ddx) / denom
            reward = -float(np.var(kappa))
        else:
            reward = 0.0

        return state, reward, {
            "contour_points": len(contour),
            "right_points": n_pts,
        }


# ═══════════════════════════════════════════════════════════════
# STAGE 4: DEPTH ESTIMATION
# ═══════════════════════════════════════════════════════════════

class DepthAgent(StageAgent):
    """
    Estimates anterior-posterior depth at each dy level.

    This is the MOST AMBIGUOUS stage — a single frontal view provides
    NO direct depth information.  The depth profile is entirely
    determined by the prior.

    Action space: R^J — depth ratio at each landmark dy
      depth_ratio = dz / dx  (how deep relative to how wide)

    Heuristic policy uses anatomical depth ratios from anthropometric
    data (average female body cross-sections).

    Ref: Tilley, A.R. "The Measure of Man and Woman." 2002.
    """

    # Female depth/width ratios at key body levels
    # These are approximate anterior-posterior to lateral ratios
    DEPTH_RATIOS = {
        "crown":      1.20,   # head is slightly deeper than wide
        "temple":     1.10,
        "head_base":  0.95,
        "neck":       0.90,   # neck is roughly circular
        "shoulder":   0.45,   # shoulders much wider than deep
        "bust":       0.80,   # torso is oval
        "waist":      0.75,
        "hip":        0.65,
        "mid_thigh":  0.90,   # thighs roughly circular
        "knee":       0.85,
        "calf":       0.75,
        "ankle":      0.85,
        "foot":       0.40,   # feet are wide and flat
        "sole":       0.30,
    }

    def __init__(self):
        super().__init__("depth", action_dim=14)

    def observe(self, state):
        return np.array([state.total_height, state.head_height])

    def act(self, observation):
        """Heuristic: anatomical depth ratios."""
        return np.array(list(self.DEPTH_RATIOS.values()))

    def step(self, state, action):
        # Apply depth ratios to width profile
        dy_vals = state.width_dy
        dx_vals = state.width_dx
        depth_ratios = action[:len(dy_vals)]

        dz_vals = dx_vals * depth_ratios

        state.depth_dy = dy_vals
        state.depth_dz = dz_vals

        # Reward: smoothness of depth profile
        if len(dz_vals) > 2:
            d2 = np.diff(dz_vals, 2)
            reward = -float(np.mean(d2**2))
        else:
            reward = 0.0

        return state, reward, {
            "mean_depth_ratio": round(float(depth_ratios.mean()), 3),
            "max_dz": round(float(dz_vals.max()), 4)
        }


# ═══════════════════════════════════════════════════════════════
# STAGE 5: 3D MESH GENERATION
# ═══════════════════════════════════════════════════════════════

class MeshAgent(StageAgent):
    """
    Generates a closed 3D triangle mesh from width + depth profiles.

    Method: at each dy level, create a ring of vertices forming an
    elliptical cross-section with semi-axes (dx, dz).  Connect
    adjacent rings with triangle strips. Cap top and bottom.

    Action space: [ring_resolution, cap_rings]
      ring_resolution: vertices per cross-section ring
      cap_rings: number of rings to taper at top/bottom caps
    """

    def __init__(self):
        super().__init__("mesh", action_dim=2)

    def observe(self, state):
        return np.array([
            len(state.width_dy),
            state.width_dx.max(),
            state.depth_dz.max() if state.depth_dz is not None else 0
        ])

    def act(self, observation):
        """Heuristic: 32 vertices per ring, 3 cap rings."""
        return np.array([32, 3])

    def step(self, state, action):
        ring_res = max(8, int(action[0]))
        cap_rings = max(1, int(action[1]))

        dy_vals = state.width_dy
        dx_vals = state.width_dx
        dz_vals = state.depth_dz

        # Interpolate to get smooth profiles
        n_rings = max(len(dy_vals) * 4, 60)
        dy_dense = np.linspace(dy_vals[0], dy_vals[-1], n_rings)

        cs_dx = CubicSpline(dy_vals, dx_vals, bc_type='clamped')
        cs_dz = CubicSpline(dy_vals, dz_vals, bc_type='clamped')

        dx_dense = np.maximum(cs_dx(dy_dense), 0.001)  # min radius
        dz_dense = np.maximum(cs_dz(dy_dense), 0.001)

        # Generate vertices: for each ring, create ring_res vertices
        # on an ellipse with semi-axes (dx, dz) at height dy
        theta = np.linspace(0, 2 * np.pi, ring_res, endpoint=False)

        vertices = []
        for i in range(n_rings):
            dx = dx_dense[i]
            dz = dz_dense[i]
            dy = dy_dense[i]
            for j in range(ring_res):
                x = dx * np.cos(theta[j])
                z = dz * np.sin(theta[j])
                y = dy
                vertices.append([x, y, z])

        # Top cap: single vertex at crown center
        top_idx = len(vertices)
        vertices.append([0, dy_dense[0], 0])

        # Bottom cap: single vertex at sole center
        bot_idx = len(vertices)
        vertices.append([0, dy_dense[-1], 0])

        vertices = np.array(vertices)

        # Generate faces
        faces = []

        # Ring-to-ring quads (split into triangles)
        for i in range(n_rings - 1):
            for j in range(ring_res):
                j_next = (j + 1) % ring_res
                # Current ring vertex indices
                v00 = i * ring_res + j
                v01 = i * ring_res + j_next
                # Next ring vertex indices
                v10 = (i + 1) * ring_res + j
                v11 = (i + 1) * ring_res + j_next
                # Two triangles per quad
                faces.append([v00, v10, v01])
                faces.append([v01, v10, v11])

        # Top cap: fan from top_idx to first ring
        for j in range(ring_res):
            j_next = (j + 1) % ring_res
            faces.append([top_idx, j_next, j])

        # Bottom cap: fan from bot_idx to last ring
        last_ring_start = (n_rings - 1) * ring_res
        for j in range(ring_res):
            j_next = (j + 1) % ring_res
            faces.append([bot_idx,
                          last_ring_start + j,
                          last_ring_start + j_next])

        faces = np.array(faces)

        state.vertices = vertices
        state.faces = faces

        # Reward: mesh quality
        reward = self._mesh_quality(vertices, faces)

        return state, reward, {
            "n_vertices": len(vertices),
            "n_faces": len(faces),
            "n_rings": n_rings,
            "ring_resolution": ring_res,
            "is_watertight": True,  # by construction
        }

    def _mesh_quality(self, verts, faces):
        """
        Mesh quality score based on triangle aspect ratios.
        Perfect equilateral triangle has aspect ratio = 1.0.
        Score = mean(1 / aspect_ratio) ∈ (0, 1].
        """
        qualities = []
        for face in faces[:500]:  # sample for speed
            p0, p1, p2 = verts[face[0]], verts[face[1]], verts[face[2]]
            edges = [np.linalg.norm(p1-p0), np.linalg.norm(p2-p1), np.linalg.norm(p0-p2)]
            if min(edges) < 1e-10:
                qualities.append(0.0)
                continue
            aspect = max(edges) / min(edges)
            qualities.append(1.0 / aspect)
        return float(np.mean(qualities)) if qualities else 0.0


# ═══════════════════════════════════════════════════════════════
# STAGE 6: MESH REFINEMENT
# ═══════════════════════════════════════════════════════════════

class RefineAgent(StageAgent):
    """
    Refines the mesh with Laplacian smoothing.

    This is the RECURSIVE stage: smoothing is iterated until
    quality converges or budget exhausted.

    Action space: [n_iterations, lambda_smooth]
      n_iterations: number of Laplacian smoothing passes
      lambda_smooth: step size for each pass (0 < λ < 1)
    """

    def __init__(self):
        super().__init__("refine", action_dim=2)

    def observe(self, state):
        return np.array([
            len(state.vertices),
            len(state.faces)
        ])

    def act(self, observation):
        """Heuristic: 3 iterations, λ=0.3."""
        return np.array([3, 0.3])

    def step(self, state, action):
        n_iter = max(0, int(action[0]))
        lam = np.clip(action[1], 0.01, 0.95)

        verts = state.vertices.copy()
        faces = state.faces

        # Build adjacency (vertex → set of neighbor vertices)
        n_verts = len(verts)
        adjacency = [set() for _ in range(n_verts)]
        for f in faces:
            for i in range(3):
                for j in range(3):
                    if i != j:
                        adjacency[f[i]].add(f[j])

        # Iterative Laplacian smoothing
        # v_new = v + λ · (mean(neighbors) - v)
        # This IS the recursive refinement: each iteration refines
        # the previous result.  It's a contraction mapping with
        # λ_contraction ≈ (1 - λ) < 1.
        quality_history = []
        for iteration in range(n_iter):
            new_verts = verts.copy()
            for i in range(n_verts):
                if adjacency[i]:
                    neighbor_mean = np.mean(
                        [verts[n] for n in adjacency[i]], axis=0
                    )
                    new_verts[i] = verts[i] + lam * (neighbor_mean - verts[i])
            verts = new_verts
            # Track convergence
            q = self._smoothness(verts, faces)
            quality_history.append(q)

        state.vertices = verts

        reward = quality_history[-1] if quality_history else 0.0

        return state, reward, {
            "iterations": n_iter,
            "lambda": round(lam, 3),
            "quality_history": [round(q, 4) for q in quality_history],
            "converged": len(quality_history) >= 2 and
                         abs(quality_history[-1] - quality_history[-2]) < 1e-4
        }

    def _smoothness(self, verts, faces):
        """Average face normal consistency with neighbors."""
        # Compute face normals
        if len(faces) == 0:
            return 0.0
        p0 = verts[faces[:, 0]]
        p1 = verts[faces[:, 1]]
        p2 = verts[faces[:, 2]]
        normals = np.cross(p1 - p0, p2 - p0)
        norms = np.linalg.norm(normals, axis=1, keepdims=True)
        norms[norms < 1e-12] = 1e-12
        normals = normals / norms
        # Overall consistency: how aligned are adjacent normals
        # (simplified: variance of normals — lower = smoother)
        return float(1.0 - np.mean(np.var(normals, axis=0)))


# ═══════════════════════════════════════════════════════════════
# STAGE 7: EXPORT
# ═══════════════════════════════════════════════════════════════

def write_obj(path: str, vertices: np.ndarray, faces: np.ndarray):
    """Write a Wavefront OBJ file."""
    with open(path, 'w') as f:
        f.write(f"# Generated by stick_to_mesh.py\n")
        f.write(f"# Vertices: {len(vertices)}, Faces: {len(faces)}\n")
        for v in vertices:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for face in faces:
            # OBJ is 1-indexed
            f.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")


def export_descriptor(state: PipelineState) -> dict:
    """
    Build the enriched JSON descriptor for the generated mesh,
    compatible with the v4 schema.
    """
    joint_map = {j.name: j for j in state.joints}

    desc = {
        "meta": {
            "schema_version": "4.0.0",
            "source": "stick_to_mesh.py",
            "pipeline": "stick → proportion → profile → contour → depth → mesh → refine",
            "generation_method": "parametric_generalized_cylinder",
            "coordinate_system": {
                "x": "lateral (+ = right of midline)",
                "y": "vertical (+ = downward, 0 = crown)",
                "z": "anterior-posterior (+ = forward)"
            }
        },
        "stick_input": {
            "joints": [
                {"name": j.name, "x": round(j.x, 4), "y": round(j.y, 4),
                 "parent": j.parent}
                for j in state.joints
            ]
        },
        "proportion": {
            "head_height_hu": state.head_height,
            "total_height_hu": state.total_height,
            "head_count": state.head_count,
            "segment_lengths": state.segment_lengths
        },
        "width_profile": {
            "sample_count": len(state.width_dy),
            "samples": [
                {"dy": round(float(state.width_dy[i]), 4),
                 "dx": round(float(state.width_dx[i]), 4)}
                for i in range(len(state.width_dy))
            ]
        },
        "depth_profile": {
            "sample_count": len(state.depth_dy) if state.depth_dy is not None else 0,
            "samples": [
                {"dy": round(float(state.depth_dy[i]), 4),
                 "dz": round(float(state.depth_dz[i]), 4)}
                for i in range(len(state.depth_dy))
            ] if state.depth_dy is not None else []
        },
        "mesh": {
            "n_vertices": len(state.vertices),
            "n_faces": len(state.faces),
            "is_watertight": True,
            "bounding_box": {
                "min": [round(float(v), 4) for v in state.vertices.min(axis=0)],
                "max": [round(float(v), 4) for v in state.vertices.max(axis=0)]
            }
        },
        "pipeline_rewards": {
            name: round(r, 6) for name, r in state.rewards.items()
        },
        "pipeline_info": state.info,

        # RL integration metadata
        "rl_architecture": {
            "note": (
                "Each stage has observe/act/step interface. Default policies are "
                "heuristic. To train with RL: (1) collect trajectories using heuristic "
                "policies, (2) define target rewards, (3) train neural network policies "
                "using PPO/SAC/REINFORCE, (4) replace heuristic act() with learned act()."
            ),
            "stages": [
                {
                    "name": "proportion",
                    "action_dim": 3,
                    "observation_dim": 2,
                    "policy": "heuristic_loomis_female",
                    "rl_ready": True
                },
                {
                    "name": "width_profile",
                    "action_dim": 14,
                    "observation_dim": 3,
                    "policy": "heuristic_loomis_female",
                    "rl_ready": True
                },
                {
                    "name": "contour",
                    "action_dim": 3,
                    "observation_dim": 3,
                    "policy": "heuristic_400pts_smooth",
                    "rl_ready": True
                },
                {
                    "name": "depth",
                    "action_dim": 14,
                    "observation_dim": 2,
                    "policy": "heuristic_anthropometric_ratios",
                    "rl_ready": True,
                    "caveat": "Most ambiguous stage — single frontal view provides no depth"
                },
                {
                    "name": "mesh",
                    "action_dim": 2,
                    "observation_dim": 3,
                    "policy": "heuristic_32ring_3cap",
                    "rl_ready": True
                },
                {
                    "name": "refine",
                    "action_dim": 2,
                    "observation_dim": 2,
                    "policy": "heuristic_3iter_03lambda",
                    "rl_ready": True,
                    "is_recursive": True,
                    "contraction_factor": "≈ 1 - λ ≈ 0.7"
                }
            ],
            "training_requirements": {
                "corpus": "Paired (stick_figure, ground_truth_mesh) examples",
                "reward_signals": [
                    "silhouette_reprojection_iou",
                    "mesh_quality_aspect_ratio",
                    "anatomical_plausibility",
                    "surface_smoothness"
                ],
                "suggested_algorithm": "PPO (handles mixed continuous/discrete actions)",
                "estimated_training_samples": "1000-10000 pairs per stage"
            }
        }
    }

    return desc


# ═══════════════════════════════════════════════════════════════
# RL TRAINING SCAFFOLD
# ═══════════════════════════════════════════════════════════════

class RLTrainer:
    """
    Scaffold for training RL policies on the pipeline.

    This defines the training loop structure.  Actual training requires:
    (a) a neural network policy (e.g., PyTorch MLP)
    (b) a training corpus of (stick, target_mesh) pairs
    (c) a differentiable reward function or a simulator

    The scaffold shows WHERE learning plugs in, not HOW the network
    is trained (that depends on the RL library: Stable-Baselines3,
    RLlib, CleanRL, etc.).
    """

    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.trajectory_buffer = []

    def collect_trajectory(self, stick_input):
        """Run pipeline once, record (obs, action, reward) at each stage."""
        state = PipelineState(joints=stick_input)
        trajectory = []

        for agent in self.pipeline:
            obs = agent.observe(state)
            action = agent.act(obs)
            state, reward, info = agent.step(state, action)
            trajectory.append({
                "stage": agent.name,
                "observation": obs.tolist(),
                "action": action.tolist(),
                "reward": reward,
            })

        self.trajectory_buffer.append(trajectory)
        return state, trajectory

    def compute_returns(self, trajectory, gamma=1.0):
        """Compute discounted returns for policy gradient."""
        returns = []
        G = 0
        for step in reversed(trajectory):
            G = step["reward"] + gamma * G
            returns.insert(0, G)
        return returns

    def policy_gradient_update(self, trajectory, returns, learning_rate=1e-3):
        """
        PLACEHOLDER: In a real implementation, this would:
        1. Forward-pass observations through the policy network
        2. Compute log π(a|s) for each (observation, action) pair
        3. Compute loss = -Σ log π(a|s) · G_t  (REINFORCE)
        4. Backpropagate and update network weights

        Requires: PyTorch/JAX + neural network policy.
        """
        print(f"  [RL] Would update policy using {len(trajectory)} steps")
        print(f"  [RL] Returns: {[round(r, 3) for r in returns]}")
        print(f"  [RL] (Placeholder — needs neural network policy)")

    def train_epoch(self, stick_inputs, n_epochs=1):
        """Run one training epoch over a batch of stick inputs."""
        for epoch in range(n_epochs):
            epoch_rewards = []
            for stick in stick_inputs:
                state, traj = self.collect_trajectory(stick)
                returns = self.compute_returns(traj)
                self.policy_gradient_update(traj, returns)
                epoch_rewards.append(sum(s["reward"] for s in traj))
            mean_reward = np.mean(epoch_rewards)
            print(f"  [RL] Epoch {epoch}: mean_reward={mean_reward:.4f}")


# ═══════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════

def run_pipeline(joints=None, ring_resolution=32,
                 output_obj="figure.obj", output_json="figure_descriptor.json",
                 verbose=True):
    """
    Execute the full stick → mesh pipeline.

    Returns: (PipelineState, descriptor_dict)
    """
    if joints is None:
        joints = make_default_stick()

    state = PipelineState(joints=joints)

    # Define pipeline stages
    stages = [
        ProportionAgent(),
        WidthProfileAgent(),
        ContourAgent(),
        DepthAgent(),
        MeshAgent(),
        RefineAgent(),
    ]

    # Override mesh ring resolution
    original_mesh_act = stages[4].act
    def custom_mesh_act(obs):
        return np.array([ring_resolution, 3])
    stages[4].act = custom_mesh_act

    # Execute pipeline
    if verbose:
        print("═" * 60)
        print("  STICK → MESH PIPELINE")
        print("═" * 60)

    for i, agent in enumerate(stages):
        state, reward, info = agent(state)
        if verbose:
            print(f"\n  Stage {i}: {agent.name}")
            print(f"    Reward: {reward:.6f}")
            for k, v in info.items():
                if not isinstance(v, (list, dict)):
                    print(f"    {k}: {v}")

    # Export OBJ
    obj_path = os.path.join("/home/claude", output_obj)
    write_obj(obj_path, state.vertices, state.faces)
    if verbose:
        print(f"\n  OBJ written: {obj_path}")
        print(f"    Vertices: {len(state.vertices)}")
        print(f"    Faces: {len(state.faces)}")

    # Export descriptor JSON
    descriptor = export_descriptor(state)
    json_path = os.path.join("/home/claude", output_json)
    with open(json_path, 'w') as f:
        json.dump(descriptor, f, indent=2)
    if verbose:
        print(f"  JSON written: {json_path}")

    # Show RL training scaffold
    if verbose:
        print(f"\n{'═' * 60}")
        print("  RL TRAINING SCAFFOLD")
        print("═" * 60)
        trainer = RLTrainer(stages)
        # Demo: collect one trajectory with the default stick
        print("\n  Collecting demonstration trajectory...")
        _, traj = trainer.collect_trajectory(make_default_stick())
        returns = trainer.compute_returns(traj)
        print(f"\n  Trajectory: {len(traj)} stages")
        for step, G in zip(traj, returns):
            print(f"    {step['stage']:20s} reward={step['reward']:+.4f}  return={G:+.4f}")
        trainer.policy_gradient_update(traj, returns)

    return state, descriptor


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stick figure → 3D mesh pipeline")
    parser.add_argument("--rings", type=int, default=32, help="Vertices per ring")
    parser.add_argument("--output", default="figure.obj", help="Output OBJ path")
    parser.add_argument("--json", default="figure_descriptor.json", help="Output JSON path")
    args = parser.parse_args()

    state, desc = run_pipeline(
        ring_resolution=args.rings,
        output_obj=args.output,
        output_json=args.json
    )
