---
title: "Formal Specification: lib/model.py — Pydantic Models for Silhouette v4 Schema"
version: "1.0.0"
date: "2026-04-12"
module: "lib/model.py"
schema: "schema/silhouette_v4.schema.json"
pals_law_version: "1.5.4"
disclaimer: >
  No information within should be taken for granted. Any statement or
  premise not backed by a real logical definition or verifiable reference
  may be invalid, erroneous, or a hallucination. All mathematical claims
  are self-contained derivations — not peer-reviewed. Volumetric and
  biomechanical estimates carry significant approximation error.
---

# Formal Specification: `lib/model.py`

## 1. Purpose and Scope

This specification defines the typed Python data model that implements
the **silhouette_v4.schema.json** document format. The module provides:

1. **Pydantic model classes** — one-to-one mapping from all 27 JSON
   Schema sections to strict, validated Python types.
2. **PALS's Law compliance primitives** — error taxonomy enum, verification
   result/report models, and scope declarations per §5, §8.3, and §9.1.
3. **Type aliases** — lightweight wrappers for JSON Schema `$defs`.

The module is **read-only with respect to domain logic**: it contains no
computation, no I/O, and no mutation beyond Pydantic's own construction
and serialization. All enrichment, building, and pipeline operations
belong to `lib/builder.py`.


## 2. Governing Standards

| Standard | Version | Sections |
|---|---|---|
| PALS's Law | 1.5.4 | §2 (untrusted-by-default), §5 (error taxonomy), §8.3 (scope declaration), §8.4 (silent acceptance), §9.1 (blocking defect) |
| silhouette_v4.schema.json | 4.x | All 27 sections |
| Pydantic | v2 | `BaseModel`, `ConfigDict`, `Field` validators |


## 3. PALS's Law Compliance Layer

### 3.1. Constants

| Symbol | Type | Value | Reference |
|---|---|---|---|
| `PALS_LAW_VERSION` | `str` | `"1.5.4"` | Document version this module conforms to |

### 3.2. `LLMErrorClass(StrEnum)`

**Reference:** PALS's Law §5 — Taxonomy of LLM Errors.

Nine mutually non-exclusive failure modes. Every verification boundary
MUST declare which classes it covers (§8.3, Corollary 3).

| Member | Identifier | Description |
|---|---|---|
| `ERR_HALLUCINATION` | `"ERR_HALLUCINATION"` | Asserting a false factual claim with apparent confidence |
| `ERR_OMISSION` | `"ERR_OMISSION"` | Silently dropping required content or fields |
| `ERR_SCHEMA` | `"ERR_SCHEMA"` | Output structurally non-conformant with the declared format |
| `ERR_TRUNCATION` | `"ERR_TRUNCATION"` | Output cut short due to token budget or streaming interruption |
| `ERR_SYCOPHANCY` | `"ERR_SYCOPHANCY"` | Output shaped by perceived user preference rather than truth |
| `ERR_INSTRUCTION` | `"ERR_INSTRUCTION"` | Violation of explicit constraints stated in the prompt |
| `ERR_CALIBRATION` | `"ERR_CALIBRATION"` | Expressed confidence misaligned with actual reliability |
| `ERR_SEMANTIC` | `"ERR_SEMANTIC"` | Correct surface form, wrong meaning |
| `ERR_REASONING` | `"ERR_REASONING"` | Invalid composition — correct facts, broken inference chain |

**Invariant:** `ALL_ERROR_CLASSES = frozenset(LLMErrorClass)` — always
contains exactly 9 members.

### 3.3. `VerificationResult(BaseModel)`

Per-class verification outcome.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `error_class` | `LLMErrorClass` | required | Which error class was checked |
| `covered` | `bool` | required | Whether this boundary covers the class |
| `method` | `str \| None` | optional | How verification is performed (e.g. `"pydantic_strict"`) |
| `note` | `str \| None` | optional | Free-text rationale or caveat |

### 3.4. `VerificationReport(BaseModel)`

**Reference:** PALS's Law §8.3 — Verification scope declaration.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `pals_law_version` | `str` | default = `PALS_LAW_VERSION` | Version tag for traceability |
| `verified` | `list[VerificationResult]` | required | One entry per error class |
| `schema_errors` | `list[str]` | default = `[]` | Pydantic validation error strings |

**Derived properties:**

| Property | Return Type | Semantics |
|---|---|---|
| `covered_classes` | `frozenset[LLMErrorClass]` | `{r.error_class for r in verified if r.covered}` |
| `uncovered_classes` | `frozenset[LLMErrorClass]` | `ALL_ERROR_CLASSES - covered_classes` |
| `is_fully_verified` | `bool` | `uncovered_classes == frozenset()` |
| `passed` | `bool` | `len(schema_errors) == 0` |

**Invariant:** `covered_classes ∪ uncovered_classes = ALL_ERROR_CLASSES`
and `covered_classes ∩ uncovered_classes = ∅`.


## 4. Type Aliases

Derived from JSON Schema `$defs`:

| Alias | Underlying Type | Semantics |
|---|---|---|
| `Point2d` | `tuple[float, float]` | `(dx, dy)` coordinate in head-unit space |
| `UnitVector2d` | `tuple[float, float]` | Unit-length direction vector |
| `DyRange` | `tuple[float, float]` | `(dy_start, dy_end)` vertical interval |
| `ContourVariant` | `Literal["right_half", "mirrored_full", "original"]` | Which contour representation was used |


## 5. Strict Base Model

### 5.1. `_Strict(BaseModel)`

All section models inherit from `_Strict` unless the JSON Schema
explicitly permits additional properties.

```python
model_config = ConfigDict(extra="forbid", populate_by_name=True)
```

| Config Key | Value | JSON Schema Equivalent |
|---|---|---|
| `extra` | `"forbid"` | `additionalProperties: false` |
| `populate_by_name` | `True` | Accept both field name and alias |

**Rationale:** `extra="forbid"` enforces `ERR_SCHEMA` detection — any
unexpected key in input data raises a `ValidationError`.

Models that do **not** inherit from `_Strict` (i.e., use bare `BaseModel`):
- `GenderSignals` — schema has no `additionalProperties` constraint
- `ImprovementFactors` — schema has no `additionalProperties` constraint
- `SecondaryFigure` — schema has no `additionalProperties` constraint


## 6. Reusable Primitives

### 6.1. `DxDy(_Strict)`

| Field | Type | Constraints |
|---|---|---|
| `dx` | `float` | required |
| `dy` | `float` | required |

### 6.2. `VolumeMethod(_Strict)`

| Field | Type | Constraints |
|---|---|---|
| `volume_hu3` | `float` | `>= 0` |
| `volume_cm3` | `float` | `>= 0` |
| `volume_liters` | `float` | `>= 0` |
| `method` | `str` | required |


## 7. Section Models (27 Sections)

The v4 document is composed of 27 top-level sections, each represented
by a dedicated Pydantic model. Below is the exhaustive specification of
every section, its sub-models, fields, types, and constraints.

---

### 7.1. `Meta` — Document Metadata

**Path:** `$.meta`

#### 7.1.1. Sub-models

**`Mirror(_Strict)`**

| Field | Type | Constraints | Description |
|---|---|---|---|
| `applied` | `bool` | required | Whether mirroring was applied |
| `semantics` | `str` | required | What the mirror operation means |
| `description` | `str \| None` | optional | Human-readable note |

**`CoordinateSystem(_Strict)`**

| Field | Type | Constraints | Description |
|---|---|---|---|
| `dx` | `str` | required | Horizontal axis semantics |
| `dy` | `str` | required | Vertical axis semantics |
| `hu_definition` | `str` | required | Head-unit definition |
| `hu_convention` | `HuConvention \| None` | optional | One of `"crown_to_chin"`, `"crown_to_neck_valley"`, `"crown_to_c7"`, `"custom"` |
| `hu_to_standard_factor` | `float \| None` | `> 0` if present | Conversion factor |

**`ExtractionScores(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `scanline` | `float` | `[0, 1]` |
| `floodfill` | `float` | `[0, 1]` |
| `direct` | `float` | `[0, 1]` |
| `margin` | `float` | `>= 0` |

**`Timing(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `algo_elapsed_ms` | `float` | `>= 0` |
| `total_elapsed_ms` | `float` | `>= 0` |

**`Classification(_Strict)`** — composite of:

| Sub-model | Field | Type / Constraints |
|---|---|---|
| `SurfaceClassification` | `label` | `Literal["armored", "clothed", "nude"]` |
| | `confidence` | `float [0, 1]` |
| | `signals` | `dict[str, Any] \| None` |
| | `note` | `str \| None` |
| `GenderClassification` | `label` | `Literal["female", "male", "ambiguous"]` |
| | `confidence` | `float [0, 1]` |
| | `signals` | `GenderSignals \| None` |
| | `note` | `str \| None` |
| `ViewClassification` | `label` | `Literal["front", "back", "three_quarter", "front_or_back"]` |
| | `signals` | `dict[str, Any] \| None` |
| | `note` | `str \| None` |
| `HairSymmetry` | `label` | `Literal["symmetric", "asymmetric"] \| None` |
| | `raw_delta_hu` | `float \| None` |
| | `note` | `str \| None` |
| `Accessories` | `label` | `str \| None` |
| | `items` | `list[str] \| None` |
| | `max_asymmetry_hu` | `float \| None` |
| `AnnotationsClassification` | `label` | `Literal["single_figure", "multi_figure"] \| None` |
| | `outside_ink_ratio` | `float \| None` |
| | `outside_ink_px` | `float \| None` |
| | `secondary_figures` | `list[SecondaryFigure] \| None` |
| | `note` | `str \| None` |

**`ContourQuality(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `total_perimeter_hu` | `float` | `>= 0` |
| `right_perimeter_hu` | `float` | `>= 0` |
| `mean_segment_length` | `float` | `>= 0` |
| `segment_length_cv` | `float` | `>= 0` |
| `std_segment_length` | `float \| None` | `>= 0` if present |
| `min_segment_length` | `float \| None` | `>= 0` if present |
| `max_segment_length` | `float \| None` | `>= 0` if present |
| `note` | `str \| None` | optional |

**`BoundingBox(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `dx_min` | `float` | required |
| `dx_max` | `float` | required |
| `dy_min` | `float` | required |
| `dy_max` | `float` | required |
| `width` | `float` | `>= 0` |
| `height` | `float` | `>= 0` |
| `aspect_ratio` | `float` | `> 0` |

**`SectionInventory(_Strict)`**

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `total_sections` | `int` | `>= 1` | |
| `sections` | `list[str]` | required | |
| `note` | `str \| None` | optional | |
| `new_in_v3_1` | `list[str] \| None` | optional | alias: `"new_in_v3.1"` |
| `refined_in_v3_1` | `list[str] \| None` | optional | alias: `"refined_in_v3.1"` |
| `new_in_v4` | `list[str] \| None` | optional | |
| `improvement_factors` | `ImprovementFactors \| None` | optional | |

**`LandmarkValidation(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `anomalies_detected` | `int \| None` | `>= 0` if present |
| `corrections_applied` | `list[str] \| None` | optional |
| `note` | `str \| None` | optional |

#### 7.1.2. `Meta(_Strict)` — Top-level Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `schema_version` | `str` | pattern: `^\d+\.\d+\.\d+$` | Semver string |
| `source` | `str` | required | Source image identifier |
| `image_size` | `tuple[int, int]` | required | `(width, height)` in pixels |
| `crop_rect_px` | `tuple[int, int, int, int]` | required | `(x, y, w, h)` crop rectangle |
| `midline_px` | `float` | required | Vertical midline x-position |
| `y_top_px` | `int` | required | Top of figure in pixels |
| `y_bot_px` | `int` | required | Bottom of figure in pixels |
| `fig_height_px` | `int` | `>= 1` | Figure height in pixels |
| `scale_px_to_hu` | `float` | `> 0` | Pixels-to-head-unit conversion factor |
| `contour_points` | `int` | `>= 1` | Number of contour sample points |
| `detail_strokes` | `int` | `>= 0` | Number of interior detail strokes |
| `extraction_method` | `Literal[...]` | `"floodfill" \| "scanline" \| "direct"` | Algorithm used |
| `mirror` | `Mirror` | required | Mirror configuration |
| `coordinate_system` | `CoordinateSystem` | required | Axis definitions |
| `scores` | `ExtractionScores` | required | Quality scores per method |
| `timing` | `Timing` | required | Execution timing |
| `classification` | `Classification` | required | Composite classifier outputs |
| `contour_quality` | `ContourQuality` | required | Contour statistics |
| `bounding_box_hu` | `BoundingBox` | required | Bounding box in head units |
| `sections` | `SectionInventory` | required | Section manifest |
| `shape_prior` | `dict[str, Any] \| None` | optional | Pre-processing shape prior |
| `binary_payload` | `str \| None` | optional | Encoded binary attachment |
| `multi_figure_sheet` | `bool \| None` | optional | Whether source has multiple figures |
| `extracted_figure_index` | `int \| None` | `>= 0` if present | Which figure was extracted |
| `extracted_figure_view` | `str \| None` | optional | View of extracted figure |
| `landmark_validation` | `LandmarkValidation \| None` | optional | Validation pass results |

---

### 7.2. `contour` — Contour Points

**Path:** `$.contour`
**Type:** `list[Point2d]`
**Constraint:** `min_length=3`

Ordered sequence of `(dx, dy)` coordinates forming the closed silhouette
boundary in head-unit space.

---

### 7.3. `landmarks` — Anatomical Landmarks

**Path:** `$.landmarks`
**Type:** `list[Landmark]`
**Constraint:** `min_length=1`

**`LandmarkSource`** — `Literal["contour_extremum", "topological_persistence", "derived_extremum", "local_minimum_search", "interpolated_midpoint", "anatomical_heuristic"]`

**`Landmark(_Strict)`**

| Field | Type | Constraints | Description |
|---|---|---|---|
| `name` | `str` | required | Canonical landmark identifier |
| `description` | `str` | required | Human-readable description |
| `dy` | `float` | required | Vertical position (head units) |
| `dx` | `float` | required | Horizontal position (head units) |
| `source` | `LandmarkSource \| None` | optional | Detection algorithm |
| `confidence` | `float \| None` | `[0, 1]` if present | Detection confidence |
| `persistence` | `float \| None` | `>= 0` if present | Topological persistence |
| `caveat` | `str \| None` | optional | Known limitation |
| `note` | `str \| None` | optional | Free-text annotation |

---

### 7.4. `midline` — Vertical Midline

**Path:** `$.midline`
**Type:** `list[Point2d]`
**Constraint:** `min_length=2`

Polyline representing the figure's vertical axis of symmetry.

---

### 7.5. `strokes` — Detail Strokes

**Path:** `$.strokes`
**Type:** `list[Stroke]`

**`SemanticType`** — `Literal["detail_mark", "vertical_division", "horizontal_band", "panel_edge", "seam", "articulation_detail", "helmet_detail", "boot_ornament", "boot_structure", "decorative_line", "ornamental_curve", "surface_detail", "contour_detail"]`

**`StrokeBbox(_Strict)`**

| Field | Type |
|---|---|
| `dx_min` | `float` |
| `dx_max` | `float` |
| `dy_min` | `float` |
| `dy_max` | `float` |

**`Stroke(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `id` | `int` | `>= 0` |
| `region` | `str` | required |
| `n_points` | `int` | `>= 2` |
| `bbox` | `StrokeBbox` | required |
| `points` | `list[Point2d]` | `min_length=2` |
| `arc_length_hu` | `float \| None` | `>= 0` if present |
| `chord_length_hu` | `float \| None` | `>= 0` if present |
| `sinuosity` | `float \| None` | `>= 1` if present |
| `orientation_deg` | `float \| None` | optional |
| `mean_curvature` | `float \| None` | optional |
| `max_abs_curvature` | `float \| None` | optional |
| `semantic_type` | `SemanticType \| None` | optional |
| `semantic_confidence` | `float \| None` | `[0, 1]` if present |

---

### 7.6. `symmetry` — Bilateral Symmetry

**Path:** `$.symmetry`

**`SymmetrySample(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `right_dx` | `float` | required |
| `left_dx` | `float` | required |
| `delta` | `float` | `>= 0` |
| `source` | `str \| None` | optional |

**`Symmetry(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `samples` | `dict[str, SymmetrySample]` | required, keyed by dy-level |
| `note` | `str \| None` | optional |
| `sample_count` | `int \| None` | `>= 0` if present |

---

### 7.7. `measurements` — Scanline Measurements

**Path:** `$.measurements`

**`ScanlineEntry(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `right_dx` | `float` | required |
| `left_dx` | `float` | required |
| `full_width_hu` | `float` | `>= 0` |
| `d_width_d_dy` | `float \| None` | optional |
| `curvature` | `float \| None` | optional |

**`Measurements(_Strict)`**

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `scanlines` | `dict[str, ScanlineEntry \| list[dict[str, Any]]]` | required | Accepts legacy topology entries |
| `note` | `str \| None` | optional | |
| `step_hu` | `float \| None` | `> 0` if present | |
| `scanline_count` | `int \| None` | `>= 1` if present | |

---

### 7.8. `parametric` — Spline Parametric Fit

**Path:** `$.parametric`

**`SplineSegment(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `label` | `str` | required |
| `landmark_start` | `str` | required |
| `landmark_end` | `str` | required |
| `dy_range` | `DyRange` | required |
| `knots` | `list[float]` | required |
| `coeffs_dx` | `list[float]` | required |
| `degree` | `int` | `>= 1` |
| `n_interior_knots` | `int \| None` | `>= 0` if present |
| `n_samples` | `int \| None` | `>= 1` if present |
| `segment_max_error` | `float \| None` | `>= 0` if present |
| `segment_mean_error` | `float \| None` | `>= 0` if present |
| `curvature_max` | `SegmentCurvatureMax \| None` | optional |
| `inflection_dy` | `list[float] \| None` | optional |
| `width_range` | `SegmentWidthRange \| None` | optional |
| `complexity` | `float \| None` | `>= 0` if present |
| `complexity_note` | `str \| None` | optional |

**`Parametric(_Strict)`**

| Field | Type |
|---|---|
| `segments` | `list[SplineSegment]` |

---

### 7.9. `proportion` — Body Proportions

**Path:** `$.proportion`

**`Proportion(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `head_count_total` | `float` | `> 0` |
| `head_height_hu` | `float` | `> 0` |
| `figure_height_total_hu` | `float` | required |
| `segment_ratios` | `dict[str, float]` | required |
| `width_ratios` | `dict[str, float]` | required |
| `head_count_anatomical` | `float \| None` | `> 0` if present |
| `figure_height_anatomical_hu` | `float \| None` | optional |
| `segment_labels` | `list[str] \| None` | optional |
| `landmark_names` | `list[str] \| None` | optional |
| `dimension` | `int \| None` | `>= 1` if present |
| `vector` | `list[float] \| None` | optional |
| `validation_errors` | `list[Any] \| None` | optional |
| `valid` | `bool \| None` | optional |
| `canonical_comparisons` | `list[CanonicalComparison] \| None` | optional |
| `composite_ratios` | `dict[str, float \| str] \| None` | optional |
| `measured_positions_hu` | `dict[str, float] \| None` | optional |

---

### 7.10. `candidates` — Extraction Candidates

**Path:** `$.candidates`
**Type:** `list[Candidate]`

**`Candidate(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `method` | `str` | required |
| `score` | `float` | `[0, 1]` |
| `selected` | `bool` | required |
| `bounds` | `CandidateBounds` | required |
| `score_breakdown` | `ScoreBreakdown` | required |
| `full_360_contour` | `list[Point2d] \| None` | optional |

---

### 7.11. `curvature` — Discrete Curvature Profile

**Path:** `$.curvature`

**`CurvatureSample(_Strict)`**

| Field | Type |
|---|---|
| `dy` | `float` |
| `dx` | `float` |
| `kappa` | `float` |

**`CurvatureExtrema(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `count` | `int` | `>= 0` |
| `peaks` | `list[CurvaturePeak]` | each peak has `abs_kappa >= 0` |
| `note` | `str \| None` | optional |

**`CurvatureInflections(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `raw_count` | `int \| None` | `>= 0` if present |
| `significance_threshold` | `float \| None` | `>= 0` if present |
| `selection_method` | `str \| None` | optional |
| `delta_kappa_range` | `DyRange \| None` | optional |
| `count` | `int \| None` | `>= 0` if present |
| `note` | `str \| None` | optional |
| `points` | `list[InflectionPoint] \| None` | optional |

**`Curvature(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `sample_count` | `int` | `>= 1` |
| `samples` | `list[CurvatureSample]` | required |
| `note` | `str \| None` | optional |
| `computed_on` | `ContourVariant \| None` | optional |
| `extrema` | `CurvatureExtrema \| None` | optional |
| `inflections` | `CurvatureInflections \| None` | optional |

---

### 7.12. `body_regions` — Anatomical Body Regions

**Path:** `$.body_regions`

**`BodyRegion(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `name` | `str` | required |
| `dy_start` | `float` | required |
| `dy_end` | `float` | required |
| `description` | `str` | required |
| `stroke_count` | `int \| None` | `>= 0` if present |
| `stroke_ids` | `list[int] \| None` | optional |
| `landmarks` | `list[str] \| None` | optional |

**`BodyRegions(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `regions` | `list[BodyRegion]` | `min_length=1` |
| `note` | `str \| None` | optional |

---

### 7.13. `cross_section_topology` — Cross-Section Topology

**Path:** `$.cross_section_topology`

**`TopologyEntry(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `crossings` | `int` | `>= 0` |
| `pairs` | `int` | `>= 0` |
| `interpretation` | `str \| None` | optional |

**`CrossSectionTopology(_Strict)`**

| Field | Type |
|---|---|
| `profile` | `dict[str, TopologyEntry]` |
| `note` | `str \| None` |

---

### 7.14. `fourier_descriptors` — Elliptic Fourier Descriptors

**Path:** `$.fourier_descriptors`

**`FourierCoefficient(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `harmonic` | `int` | `>= 1` |
| `a_x` | `float` | required |
| `b_x` | `float` | required |
| `a_y` | `float` | required |
| `b_y` | `float` | required |
| `amplitude` | `float` | `>= 0` |

**`FourierDescriptors(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `n_harmonics` | `int` | `>= 1` |
| `perimeter_hu` | `float` | `>= 0` |
| `coefficients` | `list[FourierCoefficient]` | required |
| `note` | `str \| None` | optional |
| `computed_on` | `ContourVariant \| None` | optional |
| `amplitude_formula` | `str \| None` | optional |
| `energy_concentration` | `EnergyConcentration \| None` | optional |

---

### 7.15. `width_profile` — Width Profile

**Path:** `$.width_profile`

**`WidthProfile(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `resolution_hu` | `float` | `> 0` |
| `sample_count` | `int` | `>= 1` |
| `samples` | `list[WidthSample]` | required |
| `extrema` | `WidthExtrema` | required |
| `statistics` | `WidthStatistics` | required |
| `note` | `str \| None` | optional |

---

### 7.16. `area_profile` — Area Profile

**Path:** `$.area_profile`

**`AreaProfile(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `total_area_hu2` | `float` | `>= 0` |
| `per_region` | `list[RegionArea]` | required |
| `note` | `str \| None` | optional |
| `cumulative_at_landmarks` | `list[CumulativeArea] \| None` | optional |

**Invariant:** `sum(r.area_fraction for r in per_region) ≈ 1.0`
(within floating-point tolerance).

---

### 7.17. `contour_normals` — Contour Normal Vectors

**Path:** `$.contour_normals`

**`NormalSample(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `index` | `int` | `>= 0` |
| `dx` | `float` | required |
| `dy` | `float` | required |
| `nx` | `float` | required |
| `ny` | `float` | required |

**Invariant:** `(nx, ny)` should approximate a unit vector:
`nx² + ny² ≈ 1.0`.

**`ContourNormals(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `sample_step` | `int` | `>= 1` |
| `sample_count` | `int` | `>= 1` |
| `full_point_count` | `int` | `>= 1` |
| `samples` | `list[NormalSample]` | required |
| `note` | `str \| None` | optional |
| `computed_on` | `ContourVariant \| None` | optional |

---

### 7.18. `shape_vector` — Shape Descriptor Vector

**Path:** `$.shape_vector`

**`ShapeVector(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `dimension` | `int` | `>= 1` |
| `vector` | `list[float]` | required |
| `dy_sample_points` | `list[float]` | required |
| `normalization` | `ShapeNormalization` | required |
| `note` | `str \| None` | optional |
| `components` | `list[str] \| None` | optional |

**Invariant:** `len(vector) == dimension`.

---

### 7.19. `hu_moments` — Hu Invariant Moments

**Path:** `$.hu_moments`

**`HuMoments(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `raw` | `tuple[float, ×7]` | exactly 7 elements |
| `log_transformed` | `tuple[float, ×7]` | exactly 7 elements |
| `centroid` | `DxDy` | required |
| `note` | `str \| None` | optional |
| `reference` | `str \| None` | optional |
| `computed_on` | `ContourVariant \| None` | optional |
| `point_count` | `int \| None` | `>= 1` if present |

---

### 7.20. `turning_function` — Turning Function

**Path:** `$.turning_function`

**`TurningSample(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `s` | `float` | `[0, 1]` — normalized arc-length |
| `theta` | `float` | required — cumulative angle |

**`TurningFunction(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `total_angle_rad` | `float` | required |
| `winding_number` | `float` | required |
| `sample_count` | `int` | `>= 1` |
| `samples` | `list[TurningSample]` | required |
| `note` | `str \| None` | optional |
| `reference` | `str \| None` | optional |
| `computed_on` | `ContourVariant \| None` | optional |
| `perimeter_hu` | `float \| None` | `>= 0` if present |
| `total_angle_deg` | `float \| None` | optional |
| `max_turning_rate` | `MaxTurningRate \| None` | optional |

**Invariant:** `winding_number ≈ total_angle_rad / (2π)`.

---

### 7.21. `convex_hull` — Convex Hull Analysis

**Path:** `$.convex_hull`

**`ConvexHull(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `hull_area_hu2` | `float` | `>= 0` |
| `silhouette_area_hu2` | `float` | `>= 0` |
| `solidity` | `float` | `[0, 1]` |
| `convexity_deficiency` | `float` | `[0, 1]` |
| `note` | `str \| None` | optional |
| `reference` | `str \| None` | optional |
| `solidity_formula` | `str \| None` | optional |
| `boundary_convexity` | `float \| None` | `[0, 1]` if present |
| `hull_perimeter_hu` | `float \| None` | `>= 0` if present |
| `negative_space_area_hu2` | `float \| None` | `>= 0` if present |
| `hull_vertex_count` | `int \| None` | `>= 3` if present |
| `concavities` | `Concavities \| None` | optional |

**Invariant:** `solidity = silhouette_area_hu2 / hull_area_hu2`.
**Invariant:** `convexity_deficiency = 1.0 - solidity`.

---

### 7.22. `principal_axes` — Principal Component Axes

**Path:** `$.principal_axes` (alias: `$.gesture_line`)

**`PrincipalAxes(_Strict)`**

| Field | Type | Constraints | Description |
|---|---|---|---|
| `primary_axis` | `PrimaryAxis` | required | First PCA eigenvector |
| `secondary_axis` | `SecondaryAxis` | required | Second PCA eigenvector |
| `lean_angle_deg` | `float` | required | Tilt from vertical |
| `gesture_energy` | `float` | `>= 0` | Total variance explained |
| `note` | `str \| None` | optional | |
| `reference` | `str \| list[str] \| None` | optional | |
| `centroid` | `DxDy \| None` | optional | PCA centroid |
| `cubic_fit_coefficients` | `tuple[float, ×4] \| None` | optional | Cubic polynomial fit |
| `lean_interpretation` | `str \| None` | optional | |
| `max_lateral_deviation_hu` | `float \| None` | `>= 0` if present | |
| `contrapposto_score` | `float \| None` | `>= 0` if present | |
| `contrapposto_interpretation` | `str \| None` | optional | |
| `landmark_deviations` | `list[LandmarkDeviation] \| None` | optional | |

**Backward-compatibility alias:** `GestureLine = PrincipalAxes`
(per P3-12 rename).

---

### 7.23. `gesture_line_spline` — True Gesture Line

**Path:** `$.gesture_line_spline`
**Type:** `GestureLineSpline | None` (optional section)

| Field | Type | Constraints |
|---|---|---|
| `method` | `GestureLineMethod` | `"medial_axis_spline" \| "joint_chain_spline" \| "manual"` |
| `control_points` | `list[Point2d]` | `min_length=2` |
| `curvature_class` | `GestureCurvatureClass \| None` | `"C_curve" \| "S_curve" \| "straight" \| "complex"` |
| `max_lateral_deviation_hu` | `float \| None` | `>= 0` if present |
| `note` | `str \| None` | optional |

---

### 7.24. `curvature_scale_space` — Curvature Scale Space

**Path:** `$.curvature_scale_space`

**`CSSScale(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `label` | `str` | required |
| `sigma` | `float` | `>= 0` |
| `zero_crossings` | `int` | `>= 0` |
| `mean_abs_kappa` | `float` | `>= 0` |
| `max_abs_kappa` | `float` | `>= 0` |
| `top_5_extrema` | `list[CSSExtremum] \| None` | `max_length=5` |
| `kappa_samples` | `list[CSSKappaSample] \| None` | optional |

**`CurvatureScaleSpace(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `scales` | `list[CSSScale]` | `min_length=1` |
| `note` | `str \| None` | optional |
| `reference` | `str \| None` | optional |
| `computed_on` | `ContourVariant \| None` | optional |
| `seam_handling` | `SeamHandling \| None` | `"none" \| "blended" \| "windowed"` |
| `persistent_features` | `PersistentFeatures \| None` | optional |

---

### 7.25. `style_deviation` — Style Deviation from Canon

**Path:** `$.style_deviation`

**`StyleDeviation(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `canon` | `str` | required — canonical reference name |
| `position_deviations` | `list[PositionDeviation]` | required |
| `l2_stylisation_distance` | `float` | `>= 0` |
| `note` | `str \| None` | optional |
| `reference` | `str \| None` | optional |
| `figure_head_count` | `float \| None` | optional |
| `canon_head_count` | `float \| None` | optional |
| `normalized_to_standard_hu` | `bool \| None` | optional |
| `width_deviations` | `list[WidthDeviation] \| None` | optional |
| `interpretation` | `str \| None` | optional |

---

### 7.26. `volumetric_estimates` — Volumetric Estimates

**Path:** `$.volumetric_estimates`

**`VolumetricEstimates(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `assumptions` | `VolumetricAssumptions` | required |
| `cylindrical` | `VolumeMethod` | required |
| `ellipsoidal` | `VolumeMethod` | required |
| `pappus` | `PappusVolume` | required |
| `note` | `str \| None` | optional |
| `per_region` | `list[RegionVolume] \| None` | optional |

**Invariant:** `sum(r.fraction for r in per_region) ≈ 1.0` when present.

---

### 7.27. `biomechanics` — Biomechanical Segment Parameters

**Path:** `$.biomechanics`

**`BioSegment(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `segment` | `str` | required |
| `mass_fraction` | `float` | `[0, 1]` |
| `com_proximal_fraction` | `float` | `[0, 1]` |
| `rog_com_fraction` | `float` | `>= 0` |
| `rog_proximal_fraction` | `float` | `>= 0` |
| `proximal_landmark` | `str \| None` | optional |
| `distal_landmark` | `str \| None` | optional |
| `segment_length_hu` | `float \| None` | `>= 0` if present |
| `segment_length_cm` | `float \| None` | `>= 0` if present |
| `com_position` | `ComPosition \| None` | optional |
| `radius_of_gyration_hu` | `float \| None` | `>= 0` if present |
| `radius_of_gyration_cm` | `float \| None` | `>= 0` if present |
| `note` | `str \| None` | optional |

**`Biomechanics(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `gender_data` | `Literal["female", "male"]` | required |
| `segments` | `list[BioSegment]` | `min_length=1` |
| `note` | `str \| None` | optional |
| `reference` | `str \| list[str] \| None` | optional |
| `endpoint_convention` | `SegmentEndpointConvention \| None` | optional |
| `canonical_height_cm` | `float \| None` | `> 0` if present |
| `scale_cm_per_hu` | `float \| None` | `> 0` if present |
| `whole_body_com` | `WholeBodyCom \| None` | optional |

---

### 7.28. `medial_axis` — Medial Axis Transform

**Path:** `$.medial_axis`

**`MedialAxis(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `main_axis` | `MainAxis` | required |
| `note` | `str \| None` | optional |
| `thickness_statistics` | `ThicknessStatistics \| None` | optional |
| `branch_points` | `BranchPoints \| None` | optional |

---

### 7.29. `shape_complexity` — Shape Complexity Metrics

**Path:** `$.shape_complexity`

**`ShapeComplexity(_Strict)`**

| Field | Type | Constraints |
|---|---|---|
| `curvature_entropy` | `CurvatureEntropy` | required; `value >= 0` |
| `fractal_dimension` | `FractalDimension` | required; `value ∈ [1, 2]` |
| `compactness` | `Compactness` | required; `value ∈ [0, 1]` |
| `eccentricity` | `Eccentricity` | required; `value ∈ [0, 1]` |
| `note` | `str \| None` | optional |
| `reference` | `str \| None` | optional |
| `computed_on` | `ContourVariant \| None` | optional |
| `rectangularity` | `Rectangularity \| None` | `value ∈ [0, 1]` if present |
| `roughness` | `Roughness \| None` | `value >= 0` if present |


## 8. Top-Level Document Model

### 8.1. `SilhouetteV4(_Strict)`

The root model. All 27 sections are composed here.

| # | Field | Type | Constraints | Required |
|---|---|---|---|---|
| 1 | `meta` | `Meta` | — | yes |
| 2 | `contour` | `list[Point2d]` | `min_length=3` | yes |
| 3 | `landmarks` | `list[Landmark]` | `min_length=1` | yes |
| 4 | `midline` | `list[Point2d]` | `min_length=2` | yes |
| 5 | `strokes` | `list[Stroke]` | — | yes |
| 6 | `symmetry` | `Symmetry` | — | yes |
| 7 | `measurements` | `Measurements` | — | yes |
| 8 | `parametric` | `Parametric` | — | yes |
| 9 | `proportion` | `Proportion` | — | yes |
| 10 | `candidates` | `list[Candidate]` | — | yes |
| 11 | `curvature` | `Curvature` | — | yes |
| 12 | `body_regions` | `BodyRegions` | — | yes |
| 13 | `cross_section_topology` | `CrossSectionTopology` | — | yes |
| 14 | `fourier_descriptors` | `FourierDescriptors` | — | yes |
| 15 | `width_profile` | `WidthProfile` | — | yes |
| 16 | `area_profile` | `AreaProfile` | — | yes |
| 17 | `contour_normals` | `ContourNormals` | — | yes |
| 18 | `shape_vector` | `ShapeVector` | — | yes |
| 19 | `hu_moments` | `HuMoments` | — | yes |
| 20 | `turning_function` | `TurningFunction` | — | yes |
| 21 | `convex_hull` | `ConvexHull` | — | yes |
| 22 | `principal_axes` | `PrincipalAxes` | alias: `"gesture_line"` | yes |
| 23 | `curvature_scale_space` | `CurvatureScaleSpace` | — | yes |
| 24 | `style_deviation` | `StyleDeviation` | — | yes |
| 25 | `volumetric_estimates` | `VolumetricEstimates` | — | yes |
| 26 | `biomechanics` | `Biomechanics` | — | yes |
| 27 | `medial_axis` | `MedialAxis` | — | yes |
| 28 | `shape_complexity` | `ShapeComplexity` | — | yes |
| — | `gesture_line_spline` | `GestureLineSpline \| None` | — | no |

### 8.2. Entry Points

```python
# Parse and validate (strict mode — ERR_SCHEMA boundary)
doc = SilhouetteV4.model_validate(data)

# Serialize back to dict
data = doc.model_dump()

# Serialize to JSON string
json_str = doc.model_dump_json()
```


## 9. PALS's Law Verification Boundary Summary

This module, together with `lib/builder.py`, forms a **verification
boundary** per PALS's Law §8.3. The boundary coverage is:

| Error Class | Covered | Method | Notes |
|---|---|---|---|
| `ERR_SCHEMA` | **Yes** | Pydantic strict-mode validation (`extra="forbid"`, `Field` constraints) | Structural conformance |
| `ERR_OMISSION` | **Yes** | Pydantic required fields (missing → `ValidationError`) | Required-field enforcement |
| `ERR_TRUNCATION` | **Yes** | `min_length` constraints on lists (`contour ≥ 3`, `landmarks ≥ 1`, etc.) | Minimum-size guarantees |
| `ERR_HALLUCINATION` | No | — | Requires domain knowledge beyond schema |
| `ERR_SYCOPHANCY` | No | — | Requires prompt-level analysis |
| `ERR_INSTRUCTION` | No | — | Requires prompt constraint tracking |
| `ERR_CALIBRATION` | No | — | Requires confidence calibration data |
| `ERR_SEMANTIC` | No | — | Structural validation only |
| `ERR_REASONING` | No | — | No cross-field logical consistency checks |

**Compliance status:** 3/9 classes covered. Uncovered classes are
**known, accepted risks** per §8.4. Callers consuming LLM-generated
JSON MUST layer additional verification for uncovered classes.


## 10. Global Invariants

1. **Strict mode default.** All models except `GenderSignals`,
   `ImprovementFactors`, and `SecondaryFigure` use `extra="forbid"`.
2. **No domain logic.** The module defines structure only — no
   computation, transformation, or I/O.
3. **Alias stability.** The `principal_axes` field accepts JSON key
   `"gesture_line"` via Pydantic alias. The Python-level alias
   `GestureLine = PrincipalAxes` preserves backward compatibility.
4. **Versioned contour variants.** Sections that compute on a specific
   contour form (`curvature`, `fourier_descriptors`, `contour_normals`,
   `hu_moments`, `turning_function`, `curvature_scale_space`,
   `shape_complexity`) declare the variant via the `computed_on` field.
5. **Unit consistency.** All spatial values are in **head units (hu)**
   unless a field name explicitly contains `_px`, `_cm`, `_deg`, or
   `_rad`.
