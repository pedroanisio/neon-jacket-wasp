"""
Pydantic models for silhouette_v4.schema.json.

Typed Python representation of all 27 sections of the v4 silhouette
analysis schema.  Use ``SilhouetteV4.model_validate(data)`` to parse
and validate a v4 JSON document, and ``instance.model_dump()`` to
serialize back to a dict.

PALS's Law compliance
---------------------
This module treats all input data as **untrusted by default** per PALS's
Law v1.5.4 (§2).  Pydantic strict-mode validation provides the
verification boundary, covering ``ERR_SCHEMA``, ``ERR_OMISSION``, and
``ERR_TRUNCATION``.  See ``LLMErrorClass`` and ``VerificationReport``
for the full taxonomy and scope declaration required by §8.3.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ═══════════════════════════════════════════════════════════════
# PALS's Law v1.5.4 — Compliance primitives (§5, §8.3, §9.1)
# ═══════════════════════════════════════════════════════════════

PALS_LAW_VERSION: str = "1.5.4"
"""PALS's Law document version this module conforms to."""


class LLMErrorClass(StrEnum):
    """PALS's Law §5 — Taxonomy of LLM Errors.

    Nine mutually non-exclusive failure modes that the error predicate
    ε(y, x) may detect.  Every verification boundary MUST declare which
    classes it covers (§8.3, Corollary 3).
    """

    ERR_HALLUCINATION = "ERR_HALLUCINATION"
    """Asserting a false factual claim with apparent confidence."""

    ERR_OMISSION = "ERR_OMISSION"
    """Silently dropping required content or fields."""

    ERR_SCHEMA = "ERR_SCHEMA"
    """Output structurally non-conformant with the declared format."""

    ERR_TRUNCATION = "ERR_TRUNCATION"
    """Output cut short due to token budget or streaming interruption."""

    ERR_SYCOPHANCY = "ERR_SYCOPHANCY"
    """Output shaped by perceived user preference rather than truth."""

    ERR_INSTRUCTION = "ERR_INSTRUCTION"
    """Violation of explicit constraints stated in the prompt."""

    ERR_CALIBRATION = "ERR_CALIBRATION"
    """Expressed confidence misaligned with actual reliability."""

    ERR_SEMANTIC = "ERR_SEMANTIC"
    """Correct surface form, wrong meaning."""

    ERR_REASONING = "ERR_REASONING"
    """Invalid composition — correct facts, broken inference chain."""


ALL_ERROR_CLASSES: frozenset[LLMErrorClass] = frozenset(LLMErrorClass)


class VerificationResult(BaseModel):
    """Result of checking a single PALS error class."""

    error_class: LLMErrorClass
    covered: bool
    method: str | None = None
    note: str | None = None


class VerificationReport(BaseModel):
    """PALS's Law §8.3 — Verification scope declaration.

    Every verification boundary must produce a report declaring which
    error classes it covers and which remain unchecked (known, accepted
    risks).  Leaving all boxes unchecked with no mitigation note is a
    blocking defect (§9.1).
    """

    pals_law_version: str = PALS_LAW_VERSION
    verified: list[VerificationResult]
    schema_errors: list[str] = Field(default_factory=list)

    @property
    def covered_classes(self) -> frozenset[LLMErrorClass]:
        """Error classes covered by this verification boundary."""
        return frozenset(r.error_class for r in self.verified if r.covered)

    @property
    def uncovered_classes(self) -> frozenset[LLMErrorClass]:
        """Error classes NOT covered — known, accepted risks."""
        return ALL_ERROR_CLASSES - self.covered_classes

    @property
    def is_fully_verified(self) -> bool:
        """True only if every error class is covered."""
        return self.uncovered_classes == frozenset()

    @property
    def passed(self) -> bool:
        """True if covered classes found no violations."""
        return len(self.schema_errors) == 0


# ═══════════════════════════════════════════════════════════════
# Type aliases  ($defs in JSON Schema)
# ═══════════════════════════════════════════════════════════════

Point2d = tuple[float, float]
UnitVector2d = tuple[float, float]
DyRange = tuple[float, float]
ContourVariant = Literal["right_half", "mirrored_full", "original"]


# ═══════════════════════════════════════════════════════════════
# Strict base — mirrors additionalProperties: false
# ═══════════════════════════════════════════════════════════════


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# ═══════════════════════════════════════════════════════════════
# Reusable primitives
# ═══════════════════════════════════════════════════════════════


class DxDy(_Strict):
    dx: float
    dy: float


class VolumeMethod(_Strict):
    volume_hu3: float = Field(ge=0)
    volume_cm3: float = Field(ge=0)
    volume_liters: float = Field(ge=0)
    method: str


# ═══════════════════════════════════════════════════════════════
# Meta — sub-models
# ═══════════════════════════════════════════════════════════════


class Mirror(_Strict):
    applied: bool
    semantics: str
    description: str | None = None


HuConvention = Literal[
    "crown_to_chin",
    "crown_to_neck_valley",
    "crown_to_c7",
    "custom",
]


class CoordinateSystem(_Strict):
    dx: str
    dy: str
    hu_definition: str
    hu_convention: HuConvention | None = None
    hu_to_standard_factor: float | None = Field(None, gt=0)


class ExtractionScores(_Strict):
    scanline: float = Field(ge=0, le=1)
    floodfill: float = Field(ge=0, le=1)
    direct: float = Field(ge=0, le=1)
    margin: float = Field(ge=0)


class Timing(_Strict):
    algo_elapsed_ms: float = Field(ge=0)
    total_elapsed_ms: float = Field(ge=0)


# -- Classification hierarchy --


class GenderSignals(BaseModel):
    """No additionalProperties constraint in schema."""

    shoulder_hip_ratio: float | None = None
    waist_hip_ratio: float | None = None
    male_prob: float | None = Field(None, ge=0, le=1)
    note: str | None = None


class SurfaceClassification(_Strict):
    label: Literal["armored", "clothed", "nude"]
    confidence: float = Field(ge=0, le=1)
    signals: dict[str, Any] | None = None
    note: str | None = None


class GenderClassification(_Strict):
    label: Literal["female", "male", "ambiguous"]
    confidence: float = Field(ge=0, le=1)
    signals: GenderSignals | None = None
    note: str | None = None


class ViewClassification(_Strict):
    label: Literal["front", "back", "three_quarter", "front_or_back"]
    signals: dict[str, Any] | None = None
    note: str | None = None


class HairSymmetry(_Strict):
    label: Literal["symmetric", "asymmetric"] | None = None
    raw_delta_hu: float | None = None
    note: str | None = None


class SecondaryFigure(BaseModel):
    view: str | None = None
    approximate_position: str | None = None


class Accessories(_Strict):
    label: str | None = None
    items: list[str] | None = None
    max_asymmetry_hu: float | None = None


class AnnotationsClassification(_Strict):
    label: Literal["single_figure", "multi_figure"] | None = None
    outside_ink_ratio: float | None = None
    outside_ink_px: float | None = None
    secondary_figures: list[SecondaryFigure] | None = None
    note: str | None = None


class Classification(_Strict):
    surface: SurfaceClassification
    gender: GenderClassification
    view: ViewClassification
    hair_symmetry: HairSymmetry | None = None
    accessories: Accessories | None = None
    annotations: AnnotationsClassification | None = None


# -- Other Meta sub-objects --


class ContourQuality(_Strict):
    total_perimeter_hu: float = Field(ge=0)
    right_perimeter_hu: float = Field(ge=0)
    mean_segment_length: float = Field(ge=0)
    segment_length_cv: float = Field(ge=0)
    std_segment_length: float | None = Field(None, ge=0)
    min_segment_length: float | None = Field(None, ge=0)
    max_segment_length: float | None = Field(None, ge=0)
    note: str | None = None


class BoundingBox(_Strict):
    dx_min: float
    dx_max: float
    dy_min: float
    dy_max: float
    width: float = Field(ge=0)
    height: float = Field(ge=0)
    aspect_ratio: float = Field(gt=0)


class ImprovementFactors(BaseModel):
    """No additionalProperties constraint in schema."""

    note: str | None = None


class SectionInventory(_Strict):
    total_sections: int = Field(ge=1)
    sections: list[str]
    note: str | None = None
    new_in_v3_1: list[str] | None = Field(None, alias="new_in_v3.1")
    refined_in_v3_1: list[str] | None = Field(None, alias="refined_in_v3.1")
    new_in_v4: list[str] | None = None
    improvement_factors: ImprovementFactors | None = None


class LandmarkValidation(_Strict):
    anomalies_detected: int | None = Field(None, ge=0)
    corrections_applied: list[str] | None = None
    note: str | None = None


# -- Meta top-level --


class Meta(_Strict):
    schema_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    source: str
    image_size: tuple[int, int]
    crop_rect_px: tuple[int, int, int, int]
    midline_px: float
    y_top_px: int
    y_bot_px: int
    fig_height_px: int = Field(ge=1)
    scale_px_to_hu: float = Field(gt=0)
    contour_points: int = Field(ge=1)
    detail_strokes: int = Field(ge=0)
    extraction_method: Literal["floodfill", "scanline", "direct"]
    mirror: Mirror
    coordinate_system: CoordinateSystem
    scores: ExtractionScores
    timing: Timing
    classification: Classification
    contour_quality: ContourQuality
    bounding_box_hu: BoundingBox
    sections: SectionInventory
    shape_prior: dict[str, Any] | None = None
    binary_payload: str | None = None
    multi_figure_sheet: bool | None = None
    extracted_figure_index: int | None = Field(None, ge=0)
    extracted_figure_view: str | None = None
    landmark_validation: LandmarkValidation | None = None


# ═══════════════════════════════════════════════════════════════
# Landmarks
# ═══════════════════════════════════════════════════════════════

LandmarkSource = Literal[
    "contour_extremum",
    "topological_persistence",
    "derived_extremum",
    "local_minimum_search",
    "interpolated_midpoint",
    "anatomical_heuristic",
]


class Landmark(_Strict):
    name: str
    description: str
    dy: float
    dx: float
    source: LandmarkSource | None = None
    confidence: float | None = Field(None, ge=0, le=1)
    persistence: float | None = Field(None, ge=0)
    caveat: str | None = None
    note: str | None = None


# ═══════════════════════════════════════════════════════════════
# Strokes
# ═══════════════════════════════════════════════════════════════

SemanticType = Literal[
    "detail_mark",
    "vertical_division",
    "horizontal_band",
    "panel_edge",
    "seam",
    "articulation_detail",
    "helmet_detail",
    "boot_ornament",
    "boot_structure",
    "decorative_line",
    "ornamental_curve",
    "surface_detail",
    "contour_detail",
]


class StrokeBbox(_Strict):
    dx_min: float
    dx_max: float
    dy_min: float
    dy_max: float


class Stroke(_Strict):
    id: int = Field(ge=0)
    region: str
    n_points: int = Field(ge=2)
    bbox: StrokeBbox
    points: list[Point2d] = Field(min_length=2)
    arc_length_hu: float | None = Field(None, ge=0)
    chord_length_hu: float | None = Field(None, ge=0)
    sinuosity: float | None = Field(None, ge=1)
    orientation_deg: float | None = None
    mean_curvature: float | None = None
    max_abs_curvature: float | None = None
    semantic_type: SemanticType | None = None
    semantic_confidence: float | None = Field(None, ge=0, le=1)


# ═══════════════════════════════════════════════════════════════
# Symmetry
# ═══════════════════════════════════════════════════════════════


class SymmetrySample(_Strict):
    right_dx: float
    left_dx: float
    delta: float = Field(ge=0)
    source: str | None = None


class Symmetry(_Strict):
    samples: dict[str, SymmetrySample]
    note: str | None = None
    sample_count: int | None = Field(None, ge=0)


# ═══════════════════════════════════════════════════════════════
# Measurements
# ═══════════════════════════════════════════════════════════════


class ScanlineEntry(_Strict):
    right_dx: float
    left_dx: float
    full_width_hu: float = Field(ge=0)
    d_width_d_dy: float | None = None
    curvature: float | None = None


class Measurements(_Strict):
    # Schema specifies object values, but generated data also contains
    # legacy topology entries (lists) at coarser dy keys.  Accept both.
    scanlines: dict[str, ScanlineEntry | list[dict[str, Any]]]
    note: str | None = None
    step_hu: float | None = Field(None, gt=0)
    scanline_count: int | None = Field(None, ge=1)


# ═══════════════════════════════════════════════════════════════
# Parametric
# ═══════════════════════════════════════════════════════════════


class SegmentCurvatureMax(_Strict):
    dy: float | None = None
    dx: float | None = None
    kappa_width: float | None = None


class SegmentWidthRange(_Strict):
    min_dx: float | None = None
    max_dx: float | None = None
    range_dx: float | None = Field(None, ge=0)


class SplineSegment(_Strict):
    label: str
    landmark_start: str
    landmark_end: str
    dy_range: DyRange
    knots: list[float]
    coeffs_dx: list[float]
    degree: int = Field(ge=1)
    n_interior_knots: int | None = Field(None, ge=0)
    n_samples: int | None = Field(None, ge=1)
    segment_max_error: float | None = Field(None, ge=0)
    segment_mean_error: float | None = Field(None, ge=0)
    curvature_max: SegmentCurvatureMax | None = None
    inflection_dy: list[float] | None = None
    width_range: SegmentWidthRange | None = None
    complexity: float | None = Field(None, ge=0)
    complexity_note: str | None = None


class Parametric(_Strict):
    segments: list[SplineSegment]


# ═══════════════════════════════════════════════════════════════
# Proportion
# ═══════════════════════════════════════════════════════════════


class CanonicalComparison(_Strict):
    system: str
    total_heads: float
    landmark_positions_hu: dict[str, float]


class Proportion(_Strict):
    head_count_total: float = Field(gt=0)
    head_height_hu: float = Field(gt=0)
    figure_height_total_hu: float
    segment_ratios: dict[str, float]
    width_ratios: dict[str, float]
    head_count_anatomical: float | None = Field(None, gt=0)
    figure_height_anatomical_hu: float | None = None
    segment_labels: list[str] | None = None
    landmark_names: list[str] | None = None
    dimension: int | None = Field(None, ge=1)
    vector: list[float] | None = None
    validation_errors: list[Any] | None = None
    valid: bool | None = None
    canonical_comparisons: list[CanonicalComparison] | None = None
    composite_ratios: dict[str, float | str] | None = None
    measured_positions_hu: dict[str, float] | None = None


# ═══════════════════════════════════════════════════════════════
# Candidates
# ═══════════════════════════════════════════════════════════════


class CandidateBounds(_Strict):
    midline_px: float
    y_top: int
    y_bot: int
    fig_height_px: int
    scale_px_to_hu: float


class ScoreBreakdown(_Strict):
    wasserstein_distance: float | None = None
    wasserstein_score: float | None = None
    coverage: float | None = Field(None, ge=0, le=1)
    has_head: bool | None = None
    has_legs: bool | None = None
    body_complete: bool | None = None
    coverage_score: float | None = None
    topology_sign_changes: int | None = None
    topology_score: float | None = None
    max_dx: float | None = None
    dy_span: float | None = None


class Candidate(_Strict):
    method: str
    score: float = Field(ge=0, le=1)
    selected: bool
    bounds: CandidateBounds
    score_breakdown: ScoreBreakdown
    full_360_contour: list[Point2d] | None = None


# ═══════════════════════════════════════════════════════════════
# Curvature
# ═══════════════════════════════════════════════════════════════


class CurvatureSample(_Strict):
    dy: float
    dx: float
    kappa: float


class CurvaturePeak(_Strict):
    dy: float
    dx: float
    kappa: float
    abs_kappa: float = Field(ge=0)


class CurvatureExtrema(_Strict):
    count: int = Field(ge=0)
    peaks: list[CurvaturePeak]
    note: str | None = None


class InflectionPoint(_Strict):
    dy: float
    kappa_before: float
    kappa_after: float
    dx: float | None = None
    delta_kappa: float | None = None


class CurvatureInflections(_Strict):
    raw_count: int | None = Field(None, ge=0)
    significance_threshold: float | None = Field(None, ge=0)
    selection_method: str | None = None
    delta_kappa_range: DyRange | None = None
    count: int | None = Field(None, ge=0)
    note: str | None = None
    points: list[InflectionPoint] | None = None


class Curvature(_Strict):
    sample_count: int = Field(ge=1)
    samples: list[CurvatureSample]
    note: str | None = None
    computed_on: ContourVariant | None = None
    extrema: CurvatureExtrema | None = None
    inflections: CurvatureInflections | None = None


# ═══════════════════════════════════════════════════════════════
# Body Regions
# ═══════════════════════════════════════════════════════════════


class BodyRegion(_Strict):
    name: str
    dy_start: float
    dy_end: float
    description: str
    stroke_count: int | None = Field(None, ge=0)
    stroke_ids: list[int] | None = None
    landmarks: list[str] | None = None


class BodyRegions(_Strict):
    regions: list[BodyRegion] = Field(min_length=1)
    note: str | None = None


# ═══════════════════════════════════════════════════════════════
# Cross-Section Topology
# ═══════════════════════════════════════════════════════════════


class TopologyEntry(_Strict):
    crossings: int = Field(ge=0)
    pairs: int = Field(ge=0)
    interpretation: str | None = None


class CrossSectionTopology(_Strict):
    profile: dict[str, TopologyEntry]
    note: str | None = None


# ═══════════════════════════════════════════════════════════════
# Fourier Descriptors
# ═══════════════════════════════════════════════════════════════


class EnergyConcentration(_Strict):
    note: str | None = None
    harmonics_1_4: float | None = Field(None, ge=0, le=1)
    harmonics_1_8: float | None = Field(None, ge=0, le=1)


class FourierCoefficient(_Strict):
    harmonic: int = Field(ge=1)
    a_x: float
    b_x: float
    a_y: float
    b_y: float
    amplitude: float = Field(ge=0)


class FourierDescriptors(_Strict):
    n_harmonics: int = Field(ge=1)
    perimeter_hu: float = Field(ge=0)
    coefficients: list[FourierCoefficient]
    note: str | None = None
    computed_on: ContourVariant | None = None
    amplitude_formula: str | None = None
    energy_concentration: EnergyConcentration | None = None


# ═══════════════════════════════════════════════════════════════
# Width Profile
# ═══════════════════════════════════════════════════════════════


class WidthSample(_Strict):
    dy: float
    dx: float
    full_width: float = Field(ge=0)
    slope: float | None = None
    curvature: float | None = None


class ExtremumPoint(_Strict):
    dy: float
    dx: float
    full_width: float
    prominence: float | None = Field(None, ge=0)


class ExtremaGroup(_Strict):
    count: int = Field(ge=0)
    points: list[ExtremumPoint]
    note: str | None = None


class WidthExtrema(_Strict):
    maxima: ExtremaGroup
    minima: ExtremaGroup
    prominence_threshold: float | None = Field(None, ge=0)


class WidthStatistics(_Strict):
    mean_dx: float
    max_dx: float
    min_dx: float
    std_dx: float | None = Field(None, ge=0)
    max_dx_dy: float | None = None
    min_dx_dy: float | None = None
    mean_full_width: float | None = None


class WidthProfile(_Strict):
    resolution_hu: float = Field(gt=0)
    sample_count: int = Field(ge=1)
    samples: list[WidthSample]
    extrema: WidthExtrema
    statistics: WidthStatistics
    note: str | None = None


# ═══════════════════════════════════════════════════════════════
# Area Profile
# ═══════════════════════════════════════════════════════════════


class RegionArea(_Strict):
    name: str
    dy_range: DyRange
    height_hu: float = Field(ge=0)
    area_hu2: float = Field(ge=0)
    area_fraction: float = Field(ge=0, le=1)
    mean_full_width_hu: float | None = Field(None, ge=0)
    max_full_width_hu: float | None = Field(None, ge=0)
    aspect_ratio: float | None = None


class CumulativeArea(_Strict):
    landmark: str
    dy: float
    cumulative_area_hu2: float = Field(ge=0)
    fraction_of_total: float = Field(ge=0, le=1)


class AreaProfile(_Strict):
    total_area_hu2: float = Field(ge=0)
    per_region: list[RegionArea]
    note: str | None = None
    cumulative_at_landmarks: list[CumulativeArea] | None = None


# ═══════════════════════════════════════════════════════════════
# Contour Normals
# ═══════════════════════════════════════════════════════════════


class NormalSample(_Strict):
    index: int = Field(ge=0)
    dx: float
    dy: float
    nx: float
    ny: float


class ContourNormals(_Strict):
    sample_step: int = Field(ge=1)
    sample_count: int = Field(ge=1)
    full_point_count: int = Field(ge=1)
    samples: list[NormalSample]
    note: str | None = None
    computed_on: ContourVariant | None = None


# ═══════════════════════════════════════════════════════════════
# Shape Vector
# ═══════════════════════════════════════════════════════════════


class ShapeNormalization(_Strict):
    width_max_dx: float
    method: str


class ShapeVector(_Strict):
    dimension: int = Field(ge=1)
    vector: list[float]
    dy_sample_points: list[float]
    normalization: ShapeNormalization
    note: str | None = None
    components: list[str] | None = None


# ═══════════════════════════════════════════════════════════════
# Hu Moments
# ═══════════════════════════════════════════════════════════════


class HuMoments(_Strict):
    raw: tuple[float, float, float, float, float, float, float]
    log_transformed: tuple[float, float, float, float, float, float, float]
    centroid: DxDy
    note: str | None = None
    reference: str | None = None
    computed_on: ContourVariant | None = None
    point_count: int | None = Field(None, ge=1)


# ═══════════════════════════════════════════════════════════════
# Turning Function
# ═══════════════════════════════════════════════════════════════


class MaxTurningRate(_Strict):
    s: float = Field(ge=0, le=1)
    omega: float
    note: str | None = None


class TurningSample(_Strict):
    s: float = Field(ge=0, le=1)
    theta: float


class TurningFunction(_Strict):
    total_angle_rad: float
    winding_number: float
    sample_count: int = Field(ge=1)
    samples: list[TurningSample]
    note: str | None = None
    reference: str | None = None
    computed_on: ContourVariant | None = None
    perimeter_hu: float | None = Field(None, ge=0)
    total_angle_deg: float | None = None
    max_turning_rate: MaxTurningRate | None = None


# ═══════════════════════════════════════════════════════════════
# Convex Hull
# ═══════════════════════════════════════════════════════════════


class ConcavityDepthAt(_Strict):
    dx: float | None = None
    dy: float | None = None


class ConcavityRegion(_Strict):
    contour_index_range: tuple[int, int]
    dy_range: DyRange
    max_depth_hu: float = Field(ge=0)
    max_depth_at: ConcavityDepthAt | None = None
    arc_span: int | None = Field(None, ge=0)


class Concavities(_Strict):
    count: int = Field(ge=0)
    regions: list[ConcavityRegion]
    threshold_hu: float | None = Field(None, ge=0)
    note: str | None = None


class ConvexHull(_Strict):
    hull_area_hu2: float = Field(ge=0)
    silhouette_area_hu2: float = Field(ge=0)
    solidity: float = Field(ge=0, le=1)
    convexity_deficiency: float = Field(ge=0, le=1)
    note: str | None = None
    reference: str | None = None
    solidity_formula: str | None = None
    boundary_convexity: float | None = Field(None, ge=0, le=1)
    hull_perimeter_hu: float | None = Field(None, ge=0)
    negative_space_area_hu2: float | None = Field(None, ge=0)
    hull_vertex_count: int | None = Field(None, ge=3)
    concavities: Concavities | None = None


# ═══════════════════════════════════════════════════════════════
# Principal Axes (formerly gesture_line — P3-12)
# ═══════════════════════════════════════════════════════════════


class PrimaryAxis(_Strict):
    direction: UnitVector2d
    eigenvalue: float = Field(ge=0)
    explained_variance_ratio: float = Field(ge=0, le=1)


class SecondaryAxis(_Strict):
    direction: UnitVector2d
    eigenvalue: float = Field(ge=0)


class LandmarkDeviation(_Strict):
    name: str
    dy: float
    lateral_dev: float


class PrincipalAxes(_Strict):
    """PCA on contour/landmark point cloud — captures tilt and elongation.

    Renamed from ``GestureLine`` per P3-12: PCA produces a straight axis,
    not the curved 'line of action' that Loomis described.
    """

    primary_axis: PrimaryAxis
    secondary_axis: SecondaryAxis
    lean_angle_deg: float
    gesture_energy: float = Field(ge=0)
    note: str | None = None
    reference: str | list[str] | None = None
    centroid: DxDy | None = None
    cubic_fit_coefficients: tuple[float, float, float, float] | None = None
    lean_interpretation: str | None = None
    max_lateral_deviation_hu: float | None = Field(None, ge=0)
    contrapposto_score: float | None = Field(None, ge=0)
    contrapposto_interpretation: str | None = None
    landmark_deviations: list[LandmarkDeviation] | None = None


# Back-compat alias — existing code referencing GestureLine still works.
GestureLine = PrincipalAxes


# ═══════════════════════════════════════════════════════════════
# Gesture Line (true medial-axis spline — P3-12)
# ═══════════════════════════════════════════════════════════════

GestureLineMethod = Literal[
    "medial_axis_spline",
    "joint_chain_spline",
    "manual",
]

GestureCurvatureClass = Literal["C_curve", "S_curve", "straight", "complex"]


class GestureLineSpline(_Strict):
    """True gesture / line-of-action from the medial axis."""

    method: GestureLineMethod
    control_points: list[Point2d] = Field(min_length=2)
    curvature_class: GestureCurvatureClass | None = None
    max_lateral_deviation_hu: float | None = Field(None, ge=0)
    note: str | None = None


# ═══════════════════════════════════════════════════════════════
# Curvature Scale Space
# ═══════════════════════════════════════════════════════════════


class CSSExtremum(_Strict):
    contour_index: int = Field(ge=0)
    dy: float
    dx: float
    kappa: float


class CSSKappaSample(_Strict):
    index: int = Field(ge=0)
    dy: float
    kappa: float


class CSSScale(_Strict):
    label: str
    sigma: float = Field(ge=0)
    zero_crossings: int = Field(ge=0)
    mean_abs_kappa: float = Field(ge=0)
    max_abs_kappa: float = Field(ge=0)
    top_5_extrema: list[CSSExtremum] | None = Field(None, max_length=5)
    kappa_samples: list[CSSKappaSample] | None = None


class PersistentFeature(_Strict):
    dy_bin: float
    persistence_count: int = Field(ge=1)
    structural: bool


class PersistentFeatures(_Strict):
    features: list[PersistentFeature]
    note: str | None = None


SeamHandling = Literal["none", "blended", "windowed"]


class CurvatureScaleSpace(_Strict):
    scales: list[CSSScale] = Field(min_length=1)
    note: str | None = None
    reference: str | None = None
    computed_on: ContourVariant | None = None
    seam_handling: SeamHandling | None = None
    persistent_features: PersistentFeatures | None = None


# ═══════════════════════════════════════════════════════════════
# Style Deviation
# ═══════════════════════════════════════════════════════════════


class PositionDeviation(_Strict):
    landmark: str
    canon_name: str
    measured_fraction: float
    canon_fraction: float
    deviation: float
    interpretation: str | None = None


class WidthDeviation(_Strict):
    feature: str
    measured: float
    canon: float
    deviation: float


class StyleDeviation(_Strict):
    canon: str
    position_deviations: list[PositionDeviation]
    l2_stylisation_distance: float = Field(ge=0)
    note: str | None = None
    reference: str | None = None
    figure_head_count: float | None = None
    canon_head_count: float | None = None
    normalized_to_standard_hu: bool | None = None
    width_deviations: list[WidthDeviation] | None = None
    interpretation: str | None = None


# ═══════════════════════════════════════════════════════════════
# Volumetric Estimates
# ═══════════════════════════════════════════════════════════════


class VolumetricAssumptions(_Strict):
    canonical_height_cm: float = Field(gt=0)
    scale_cm_per_hu: float = Field(gt=0)
    figure_height_hu: float = Field(gt=0)


class PappusVolume(_Strict):
    volume_hu3: float = Field(ge=0)
    volume_cm3: float = Field(ge=0)
    volume_liters: float = Field(ge=0)
    method: str
    centroid_x_hu: float | None = None


class RegionVolume(_Strict):
    name: str
    volume_hu3_cylindrical: float = Field(ge=0)
    volume_cm3_cylindrical: float = Field(ge=0)
    fraction: float = Field(ge=0, le=1)


class VolumetricEstimates(_Strict):
    assumptions: VolumetricAssumptions
    cylindrical: VolumeMethod
    ellipsoidal: VolumeMethod
    pappus: PappusVolume
    note: str | None = None
    per_region: list[RegionVolume] | None = None


# ═══════════════════════════════════════════════════════════════
# Biomechanics
# ═══════════════════════════════════════════════════════════════


class ComPosition(_Strict):
    dy: float | None = None
    dy_cm: float | None = None


class WholeBodyCom(_Strict):
    dy: float
    dy_fraction: float = Field(ge=0, le=1)
    cm_from_crown: float | None = Field(None, ge=0)
    note: str | None = None


class SegmentEndpointConvention(_Strict):
    source: str
    note: str | None = None


class BioSegment(_Strict):
    segment: str
    mass_fraction: float = Field(ge=0, le=1)
    com_proximal_fraction: float = Field(ge=0, le=1)
    rog_com_fraction: float = Field(ge=0)
    rog_proximal_fraction: float = Field(ge=0)
    proximal_landmark: str | None = None
    distal_landmark: str | None = None
    segment_length_hu: float | None = Field(None, ge=0)
    segment_length_cm: float | None = Field(None, ge=0)
    com_position: ComPosition | None = None
    radius_of_gyration_hu: float | None = Field(None, ge=0)
    radius_of_gyration_cm: float | None = Field(None, ge=0)
    note: str | None = None


class Biomechanics(_Strict):
    gender_data: Literal["female", "male"]
    segments: list[BioSegment] = Field(min_length=1)
    note: str | None = None
    reference: str | list[str] | None = None
    endpoint_convention: SegmentEndpointConvention | None = None
    canonical_height_cm: float | None = Field(None, gt=0)
    scale_cm_per_hu: float | None = Field(None, gt=0)
    whole_body_com: WholeBodyCom | None = None


# ═══════════════════════════════════════════════════════════════
# Medial Axis
# ═══════════════════════════════════════════════════════════════


class ThicknessStatistics(_Strict):
    mean_radius_hu: float = Field(ge=0)
    min_radius_hu: float = Field(ge=0)
    max_radius_hu: float = Field(ge=0)
    thinning_ratio: float = Field(ge=0)
    min_radius_dy: float | None = None
    max_radius_dy: float | None = None
    note: str | None = None


class BranchPoints(_Strict):
    count: int = Field(ge=0)
    points: list[dict[str, Any]]
    note: str | None = None


class MedialAxisSample(_Strict):
    dy: float
    medial_dx: float
    inscribed_radius: float = Field(ge=0)
    inscribed_diameter: float = Field(ge=0)


class MainAxis(_Strict):
    start: DxDy
    end: DxDy
    sample_count: int = Field(ge=1)
    samples: list[MedialAxisSample]


class MedialAxis(_Strict):
    main_axis: MainAxis
    note: str | None = None
    thickness_statistics: ThicknessStatistics | None = None
    branch_points: BranchPoints | None = None


# ═══════════════════════════════════════════════════════════════
# Shape Complexity
# ═══════════════════════════════════════════════════════════════


class CurvatureEntropy(_Strict):
    value: float = Field(ge=0)
    units: str | None = None
    histogram_bins: int | None = Field(None, ge=1)
    note: str | None = None


class FractalDimension(_Strict):
    value: float = Field(ge=1, le=2)
    method: str
    n_scales: int | None = Field(None, ge=1)
    note: str | None = None


class Compactness(_Strict):
    value: float = Field(ge=0, le=1)
    formula: str | None = None
    perimeter_used: ContourVariant | None = None
    computed_area_hu2: float | None = Field(None, ge=0)
    computed_perimeter_hu: float | None = Field(None, ge=0)
    note: str | None = None


class Rectangularity(_Strict):
    value: float = Field(ge=0, le=1)
    formula: str | None = None
    note: str | None = None


class Eccentricity(_Strict):
    value: float = Field(ge=0, le=1)
    note: str | None = None


class Roughness(_Strict):
    value: float = Field(ge=0)
    formula: str | None = None
    note: str | None = None


class ShapeComplexity(_Strict):
    curvature_entropy: CurvatureEntropy
    fractal_dimension: FractalDimension
    compactness: Compactness
    eccentricity: Eccentricity
    note: str | None = None
    reference: str | None = None
    computed_on: ContourVariant | None = None
    rectangularity: Rectangularity | None = None
    roughness: Roughness | None = None


# ═══════════════════════════════════════════════════════════════
# Top-level document
# ═══════════════════════════════════════════════════════════════


class SilhouetteV4(_Strict):
    """Complete v4 silhouette analysis document."""

    meta: Meta
    contour: list[Point2d] = Field(min_length=3)
    landmarks: list[Landmark] = Field(min_length=1)
    midline: list[Point2d] = Field(min_length=2)
    strokes: list[Stroke]
    symmetry: Symmetry
    measurements: Measurements
    parametric: Parametric
    proportion: Proportion
    candidates: list[Candidate]
    curvature: Curvature
    body_regions: BodyRegions
    cross_section_topology: CrossSectionTopology
    fourier_descriptors: FourierDescriptors
    width_profile: WidthProfile
    area_profile: AreaProfile
    contour_normals: ContourNormals
    shape_vector: ShapeVector
    hu_moments: HuMoments
    turning_function: TurningFunction
    convex_hull: ConvexHull
    # P3-12: renamed from gesture_line; accepts both names via alias
    principal_axes: PrincipalAxes = Field(alias="gesture_line")
    curvature_scale_space: CurvatureScaleSpace
    style_deviation: StyleDeviation
    volumetric_estimates: VolumetricEstimates
    biomechanics: Biomechanics
    medial_axis: MedialAxis
    shape_complexity: ShapeComplexity
    gesture_line_spline: GestureLineSpline | None = None
