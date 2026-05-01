# Neon Jacket Wasp

## Why We Built This

We believe shape analysis should not stop at “it looks right.” When a system turns a human silhouette into numbers, labels, and derived structure, those outputs can easily become over-trusted long before they are well understood. That is a bad foundation for research, tooling, or downstream automation.

We built Neon Jacket Wasp to make silhouette analysis explicit, inspectable, and harder to fake. The goal is not only to capture a figure’s outer shape, but to preserve enough structure that people can examine what was inferred, what was measured, and where confidence should stop. If a document cannot survive validation and visual inspection, it should not quietly pass as truth.

---

## How We Approach This

- **Verification before trust** — Structured output is untrusted by default and must cross a declared validation boundary before the rest of the system treats it as usable.
- **One contract, many consumers** — The silhouette document is the stable center of the project, so generation, parsing, analysis, and visualization all orbit the same source of truth.
- **Math is part of the product** — Geometry, proportion, curvature, symmetry, and derived measures are not decoration; they are the substance of the work.
- **Inspection beats mystique** — The system should make its intermediate structure visible so users can read, render, and challenge the result rather than accept a black box.
- **Drift is a defect** — Schemas, docs, renderers, and fixtures must stay synchronized, because silent divergence destroys trust faster than visible failure.

---

## What It Does

### Core Capabilities

- Defines a rich silhouette document that captures contour, landmarks, proportions, regional structure, and derived measurements.
- Upgrades older extraction output into the current document shape and validates it before reuse.
- Provides typed builder and document APIs for producing, loading, and checking silhouette data.
- Renders and explores the resulting data through frontend views for loading, analysis, and mesh-based interpretation.

### What This Is Not

This project does **not**:
- treat schema-valid output as automatically semantically correct
- optimize for opaque “AI magic” over inspectable geometric evidence
- aim to be a general-purpose anatomy, vision, or medical diagnosis platform

---

## Who This Is For

- **Tool builders** — People who need a stable silhouette contract they can generate, validate, and consume across systems.
- **Researchers and technical artists** — People who want shape-derived measurements and visual feedback, not just a final label.
- **Skeptical engineers** — People who want explicit failure boundaries and auditable structure before trusting automated output.
