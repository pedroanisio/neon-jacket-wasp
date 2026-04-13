# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Silhouette 2D animation presets and SVG renderer (`packages/silhouette-2d/`)
- Bilateral skeleton with forward kinematics and linear blend skinning
- Interior detail strokes with deformation and rendering
- Interior hole polygon support in fill rendering and JSON data loading
- Multi-span topology handling for silhouette loader with hip-level filtering
- Conditional contour path generation for mirrored and full silhouette modes
- P2 regression tests for curvature, Fourier descriptors, and contour normals
- Strict validation mode for `generate_v4.py` and `multi_figure_sheet` method
- PALS's Law compliance and verification framework across the SDK
- Mypy strict-mode configuration with Pydantic plugin
- Ruff linter configuration with comprehensive rule set
- Stick figure to 3D mesh pipeline with recursive RL refinement
- Project documentation and README

### Changed
- Fill rendering excludes static interior hole sub-paths; adjusted CoM deformation calculation
- Bone system enhanced to support full bilateral skeleton with forward kinematics
- Gesture line handling refactored for clarity
- Error class documentation and `SilhouetteDocument` method signatures improved
- Schema documentation and validation updated for new contour variants
- Obsolete configuration files removed; project structure consolidated

### Fixed
- Image formatting in README for consistent rendering
- Negative values in spline calculations clamped to prevent NaN propagation
- `fillRule` attribute added to contour SVG path for correct even-odd rendering

## [0.1.0] - 2026-04-12

Initial development release.

### Added
- v4 JSON schema (27 sections) with Pydantic models
- Fluent builder API (`SilhouetteDocument`)
- v2-to-v4 enrichment pipeline
- Verification report for PALS's Law error taxonomy coverage

[Unreleased]: https://github.com/pedroanisio/neon-jacket-wasp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pedroanisio/neon-jacket-wasp/releases/tag/v0.1.0
