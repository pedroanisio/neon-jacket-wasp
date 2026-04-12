---
title: "Recursive RL Pipeline: Stick Figure → 3D Mesh"
version: "1.0.0"
date: "2026-04-12"
disclaimer: >
  No information within should be taken for granted. Any statement or
  premise not backed by a real logical definition or verifiable reference
  may be invalid, erroneous, or a hallucination. All mathematical claims
  are self-contained derivations — not peer-reviewed. Volumetric and
  biomechanical estimates carry significant approximation error.
---

# Stick Figure → 3D Mesh via Recursive RL

## 1. Problem Statement

**Given:**
- A stick figure $d_1 \in \mathbb{R}^{J \times 2}$ (J joint positions in 2D)
- A target quality threshold $Q^*$
- A maximum iteration budget $N$

**Produce:**
- A closed, manifold 3D triangle mesh $\mathcal{M} = (V, F)$ where
  $V \in \mathbb{R}^{|V| \times 3}$, $F \in \mathbb{Z}^{|F| \times 3}$

**Via:**
- A sequence of $K$ transformation stages, each parameterised by an
  action chosen by a policy $\pi_k$
- The policies are either heuristic (hand-crafted priors) or learned
  (RL-trained on a corpus of examples)

## 2. Formal MDP Structure

The pipeline is a **finite-horizon, deterministic MDP** with stage-wise
decomposition:

$$\mathcal{M}_{MDP} = (\mathcal{S}, \mathcal{A}, T, R, K, \gamma)$$

| Symbol | Definition |
|---|---|
| $\mathcal{S} = \bigcup_{k=0}^{K} \mathcal{S}_k$ | Union of stage-specific state spaces |
| $\mathcal{A} = \bigcup_{k=0}^{K} \mathcal{A}_k$ | Union of stage-specific action spaces |
| $T_k : \mathcal{S}_k \times \mathcal{A}_k \to \mathcal{S}_{k+1}$ | Deterministic transition at stage $k$ |
| $R_k : \mathcal{S}_{k+1} \to \mathbb{R}$ | Reward after stage $k$ (evaluates result) |
| $K = 8$ | Number of stages |
| $\gamma \in (0, 1]$ | Discount factor (typically 1.0 for finite horizon) |

### 2.1 State Spaces

| Stage $k$ | State $\mathcal{S}_k$ | Representation |
|---|---|---|
| 0 | Stick input | $\mathbb{R}^{J \times 2}$: joint $(x, y)$ positions |
| 1 | Proportioned skeleton | $\mathbb{R}^{J \times 2} \times \mathbb{R}^{J-1}$: joints + segment lengths |
| 2 | Width profile | $\mathbb{R}^{M}$: half-width $dx$ at $M$ dy-levels |
| 3 | 2D contour | $\mathbb{R}^{P \times 2}$: $P$-point closed contour |
| 4 | Enriched descriptor | Structured dict (v4 JSON schema) |
| 5 | Coarse 3D mesh | $(V_c, F_c) \in \mathbb{R}^{V_c \times 3} \times \mathbb{Z}^{F_c \times 3}$ |
| 6 | Refined 3D mesh | $(V_r, F_r)$: subdivided + displaced |
| 7 | Detailed 3D mesh | $(V_d, F_d)$: surface features added |

### 2.2 Action Spaces

| Stage $k$ | Action $\mathcal{A}_k$ | Dimensionality |
|---|---|---|
| 0 | (none — input is given) | 0 |
| 1 | Proportion params: head count, segment ratios | $\mathbb{R}^{J}$ |
| 2 | Width params: half-width at each landmark | $\mathbb{R}^{J}$ |
| 3 | Contour params: resolution, smoothing kernel width | $\mathbb{R}^{3}$ |
| 4 | Enrichment config: which analyses to compute | $\{0,1\}^{10}$ |
| 5 | 3D params: depth ratios, cross-section eccentricity, ring resolution | $\mathbb{R}^{J+2}$ |
| 6 | Refinement params: subdivision level, displacement amplitude | $\mathbb{R}^{3}$ |
| 7 | Detail params: feature density, roughness amplitude | $\mathbb{R}^{5}$ |

### 2.3 Transition Functions

Each $T_k$ is a deterministic, differentiable (almost everywhere) geometric
computation. The composition:

$$s_K = T_{K-1}(T_{K-2}(\ldots T_0(s_0, a_0) \ldots, a_{K-2}), a_{K-1})$$

is well-defined because each $T_k$ maps $\mathcal{S}_k \times \mathcal{A}_k$
into $\mathcal{S}_{k+1}$ and each $\mathcal{S}_k$ is a metric space.

### 2.4 Reward Functions

| Stage | Reward $R_k(s_{k+1})$ | Range |
|---|---|---|
| 1 | $-\|p_{measured} - p_{canon}\|_2$ (proportion deviation) | $(-\infty, 0]$ |
| 2 | $-\sum_i (w_i - w_{target,i})^2$ (width profile error) | $(-\infty, 0]$ |
| 3 | Contour smoothness: $-\frac{1}{P}\sum_{j}\kappa_j^2$ | $(-\infty, 0]$ |
| 5 | Mesh quality: $\alpha \cdot Q_{aspect} + \beta \cdot Q_{silhouette}$ | $[0, 1]$ |
| 6 | Silhouette reprojection IoU | $[0, 1]$ |
| 7 | Surface detail variance (target: match training distribution) | $(-\infty, 0]$ |

### 2.5 The Recursion

The "recursive" aspect operates at two levels:

**Level 1 — Stage recursion (the pipeline):**

$$s_{k+1} = T_k(s_k, \pi_k(s_k)), \quad k = 0, 1, \ldots, K-1$$

This is a forward pass through $K$ stages. Not recursive in the
computer-science sense, but compositional.

**Level 2 — Iterative refinement (the RL loop):**

At each stage $k$, the agent may perform $n_k$ refinement iterations:

$$s_k^{(t+1)} = T_k^{refine}(s_k^{(t)}, \pi_k(s_k^{(t)}))$$
$$\text{until } R_k(s_k^{(t)}) > R_k^{threshold} \text{ or } t > n_k^{max}$$

This IS recursive: each refinement step takes the output of the previous
refinement as input. The policy $\pi_k$ learns which refinement action to
take given the current quality.

**Convergence (Level 2):**

If $T_k^{refine}$ is a contraction mapping in some metric $d_k$:

$$d_k(T_k^{refine}(s, a), T_k^{refine}(s', a)) \leq \lambda_k \cdot d_k(s, s'), \quad \lambda_k < 1$$

then by the Banach fixed-point theorem, the iteration converges to a
unique fixed point. For geometric operations (smoothing, subdivision,
Laplacian relaxation), this condition is typically satisfied with
$\lambda_k \approx 0.5\text{–}0.9$.

For operations that are NOT contractions (displacement, detail addition),
convergence is not guaranteed and the iteration budget $n_k^{max}$ acts
as a hard stop. The RL agent learns to terminate early when further
refinement degrades quality (the reward signal).

## 3. What Can Be Implemented Now vs. What Requires Training

| Component | Status | Requirement |
|---|---|---|
| Pipeline architecture ($T_k$ functions) | **Implementable now** | Geometry + linear algebra |
| Heuristic policies ($\pi_k^{heuristic}$) | **Implementable now** | Anatomical priors (Loomis, Winter) |
| Reward functions ($R_k$) | **Implementable now** | Mesh quality metrics |
| RL training loop | **Scaffold implementable** | Needs training corpus |
| Trained RL policies ($\pi_k^{learned}$) | **Not implementable without data** | Corpus of stick→mesh pairs |

## 4. Honest Assessment of Limitations

1. **Depth ambiguity.** A single frontal stick figure provides ZERO
   anterior-posterior depth information. The depth at each cross-section
   is fully determined by the prior (heuristic or learned). Without
   side-view or 3/4-view input, any 3D reconstruction is one of
   infinitely many valid solutions.

2. **Surface detail.** A stick figure contains no information about
   surface features (armor panels, muscle definition, clothing folds).
   These must come entirely from the prior. The RL agent can learn to
   generate plausible details from a training corpus, but cannot
   recover details that aren't implied by the stick input.

3. **Training data.** RL training requires a reward signal. For stages
   5-7, the natural reward is "does the 3D mesh match a ground-truth?"
   — which requires ground-truth 3D meshes paired with stick inputs.
   Without this corpus, the RL agent cannot be trained beyond the
   heuristic baseline.

4. **Differentiability.** Some transitions (mesh topology changes,
   boolean operations) are not differentiable, preventing gradient-based
   RL methods (e.g., DDPG). Policy-gradient methods (PPO, REINFORCE)
   work but have higher variance.

## 5. Implementation

See `stick_to_mesh.py` for the full working implementation.
The pipeline produces a 3D OBJ mesh from a stick figure input using
heuristic policies, with clearly marked RL integration points.
