"""
Builder SDK for creating valid SilhouetteV4 JSON documents.

Provides a fluent builder API on top of the Pydantic models in
``lib.model``.  Three main entry points:

- **MetaBuilder** — incremental builder for the complex ``meta`` section.
- **SilhouetteBuilder** — top-level builder that assembles all 27 sections.
- **SilhouetteDocument** — immutable validated wrapper with JSON I/O.

Quick start::

    from lib.builder import SilhouetteBuilder, MetaBuilder, SilhouetteDocument

    # Build from scratch
    doc = (
        SilhouetteBuilder()
        .meta(MetaBuilder("my_tool", (1024, 2048)).crop_rect(...).build())
        .contour(points)
        .landmarks(landmark_list)
        ...
        .build()
    )
    doc.to_json("output.json")

    # Load and re-validate existing JSON
    doc = SilhouetteDocument.from_json("existing.json")

    # Load without strict constraint checking (e.g. pipeline outputs
    # with minor floating-point violations like negative widths)
    doc = SilhouetteDocument.from_json("existing.json", strict=False)

ARCHITECTURAL CONTRACT -- PALS's LAW
-------------------------------------
Principle authored by: Pedro Anisio de Luna e Silva

PALS_LAW_VERSION: 1.5.4

INVARIANT (operative form):
    E[ε(M(x), x)] >= δ > 0

ERROR CLASSES COVERED BY THIS SDK's VERIFIER:
    [x] ERR_SCHEMA       — Pydantic strict-mode: type, structure, constraints
    [x] ERR_OMISSION      — Pydantic required fields + SilhouetteBuilder.missing_sections()
    [x] ERR_TRUNCATION    — min_length on contour/midline/landmarks/strokes

ERROR CLASSES NOT COVERED (known, accepted risks):
    [ ] ERR_HALLUCINATION — No factual/semantic ground truth at schema level
    [ ] ERR_SYCOPHANCY    — Not applicable to structured data ingestion
    [ ] ERR_INSTRUCTION   — Upstream concern; SDK validates output, not prompt
    [ ] ERR_CALIBRATION   — No confidence calibration at schema level
    [ ] ERR_SEMANTIC      — Structural validation only; no semantic checks
    [ ] ERR_REASONING     — No cross-field logical consistency verification

Unchecked boxes are known, accepted risks.  Callers consuming LLM-
generated JSON MUST layer additional verification for uncovered classes.
See ``SilhouetteDocument.verification_report()`` for programmatic access.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import ValidationError

if TYPE_CHECKING:
    from collections.abc import Sequence

from lib.model import (
    ALL_ERROR_CLASSES,
    PALS_LAW_VERSION,
    AreaProfile,
    Biomechanics,
    BodyRegions,
    BoundingBox,
    Candidate,
    Classification,
    ContourNormals,
    ContourQuality,
    ConvexHull,
    CoordinateSystem,
    CrossSectionTopology,
    Curvature,
    CurvatureScaleSpace,
    ExtractionScores,
    FourierDescriptors,
    GenderClassification,
    GestureLine,
    HairSymmetry,
    HuMoments,
    LLMErrorClass,
    Landmark,
    LandmarkValidation,
    Measurements,
    MedialAxis,
    Meta,
    Mirror,
    Parametric,
    Point2d,
    Proportion,
    SectionInventory,
    ShapeComplexity,
    ShapeVector,
    SilhouetteV4,
    Stroke,
    StyleDeviation,
    SurfaceClassification,
    Symmetry,
    Timing,
    TurningFunction,
    VerificationReport,
    VerificationResult,
    ViewClassification,
    VolumetricEstimates,
    WidthProfile,
)

__all__ = [
    "MetaBuilder",
    "SilhouetteBuilder",
    "SilhouetteDocument",
]

# ──────────────────────────────────────────────────────────
# PALS's Law — Verification scope (§8.3)
# ──────────────────────────────────────────────────────────

# Error classes covered by Pydantic strict-mode validation.
_COVERED_CLASSES: dict[LLMErrorClass, str] = {
    LLMErrorClass.ERR_SCHEMA: (
        "Pydantic strict-mode: extra='forbid', type checks, "
        "field constraints (ge, le, gt, pattern, min_length)"
    ),
    LLMErrorClass.ERR_OMISSION: (
        "Required fields enforced by Pydantic; "
        "SilhouetteBuilder.missing_sections() guards completeness"
    ),
    LLMErrorClass.ERR_TRUNCATION: (
        "min_length constraints on contour (≥3), midline (≥2), "
        "landmarks (≥1), strokes points (≥2)"
    ),
}

# Error classes NOT covered — known, accepted risks per §9.1.
_UNCOVERED_CLASSES: dict[LLMErrorClass, str] = {
    LLMErrorClass.ERR_HALLUCINATION: (
        "No factual ground truth available at schema level"
    ),
    LLMErrorClass.ERR_SYCOPHANCY: (
        "Not applicable to structured data ingestion"
    ),
    LLMErrorClass.ERR_INSTRUCTION: (
        "Upstream concern; SDK validates output, not prompt adherence"
    ),
    LLMErrorClass.ERR_CALIBRATION: (
        "No confidence calibration verification at schema level"
    ),
    LLMErrorClass.ERR_SEMANTIC: (
        "Structural validation only; semantic plausibility unchecked"
    ),
    LLMErrorClass.ERR_REASONING: (
        "No cross-field logical consistency verification"
    ),
}


def _build_verification_report(
    schema_errors: list[str] | None = None,
    *,
    strict: bool = True,
) -> VerificationReport:
    """Build a ``VerificationReport`` for the SDK's verification boundary.

    In strict mode, ERR_SCHEMA/ERR_OMISSION/ERR_TRUNCATION are covered.
    In lenient mode (``strict=False``), NO error classes are covered —
    this is explicit risk acceptance per PALS's Law §8.4 (Corollary 4).
    """
    results: list[VerificationResult] = []

    if strict:
        for cls, method in _COVERED_CLASSES.items():
            results.append(
                VerificationResult(error_class=cls, covered=True, method=method)
            )
        for cls, note in _UNCOVERED_CLASSES.items():
            results.append(
                VerificationResult(error_class=cls, covered=False, note=note)
            )
    else:
        # PALS's Law §8.4: Silent acceptance is an architectural defect.
        # Lenient mode explicitly declares ZERO coverage.
        for cls in ALL_ERROR_CLASSES:
            results.append(
                VerificationResult(
                    error_class=cls,
                    covered=False,
                    note="Lenient mode: all verification bypassed (§8.4 risk acceptance)",
                )
            )

    return VerificationReport(
        verified=results,
        schema_errors=schema_errors or [],
    )


# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────

# Type used for section-method overloads: accept model or raw dict.
type _ModelOrDict = object


def _coerce[T](model_cls: type[T], value: _ModelOrDict) -> T:
    """Return a validated model instance from *value* (model or dict)."""
    if isinstance(value, model_cls):
        return value
    result: T = model_cls.model_validate(value)  # type: ignore[attr-defined]
    return result


def _coerce_list[T](model_cls: type[T], values: Sequence[_ModelOrDict]) -> list[T]:
    """Validate each element in *values* against *model_cls*."""
    return [_coerce(model_cls, v) for v in values]


# ──────────────────────────────────────────────────────────
# MetaBuilder
# ──────────────────────────────────────────────────────────


class MetaBuilder:
    """Incremental builder for the ``Meta`` section.

    Required calls before ``build()``:

    - Constructor (``source``, ``image_size``)
    - ``crop_rect``
    - ``midline``
    - ``y_range``
    - ``scale``
    - ``contour_info``
    - ``extraction``
    - ``timing``
    - ``classify`` (at least ``surface``, ``gender``, ``view``)
    - ``contour_quality``
    - ``bounding_box``
    - ``sections``

    Everything else has sensible defaults.
    """

    def __init__(
        self,
        source: str,
        image_size: tuple[int, int],
        schema_version: str = "4.0.0",
    ) -> None:
        self._data: dict[str, Any] = {
            "schema_version": schema_version,
            "source": source,
            "image_size": image_size,
        }
        self._classification: dict[str, Any] = {}

    # ── Required setters (chainable) ──

    def crop_rect(self, x0: int, y0: int, x1: int, y1: int) -> MetaBuilder:
        self._data["crop_rect_px"] = (x0, y0, x1, y1)
        return self

    def midline(self, px: float) -> MetaBuilder:
        self._data["midline_px"] = px
        return self

    def y_range(self, y_top: int, y_bot: int) -> MetaBuilder:
        self._data["y_top_px"] = y_top
        self._data["y_bot_px"] = y_bot
        self._data["fig_height_px"] = y_bot - y_top
        return self

    def scale(self, px_to_hu: float) -> MetaBuilder:
        self._data["scale_px_to_hu"] = px_to_hu
        return self

    def contour_info(self, points: int, detail_strokes: int = 0) -> MetaBuilder:
        self._data["contour_points"] = points
        self._data["detail_strokes"] = detail_strokes
        return self

    def extraction(
        self,
        method: str,
        *,
        scanline: float = 0.0,
        floodfill: float = 0.0,
        direct: float = 0.0,
        margin: float = 0.0,
    ) -> MetaBuilder:
        self._data["extraction_method"] = method
        self._data["scores"] = ExtractionScores(
            scanline=scanline,
            floodfill=floodfill,
            direct=direct,
            margin=margin,
        )
        return self

    def timing(self, algo_ms: float, total_ms: float) -> MetaBuilder:
        self._data["timing"] = Timing(algo_elapsed_ms=algo_ms, total_elapsed_ms=total_ms)
        return self

    def classify(
        self,
        *,
        surface: Literal["armored", "clothed", "nude"],
        gender: Literal["female", "male", "ambiguous"],
        view: Literal["front", "back", "three_quarter", "front_or_back"],
        surface_confidence: float = 1.0,
        gender_confidence: float = 1.0,
    ) -> MetaBuilder:
        self._classification["surface"] = SurfaceClassification(
            label=surface, confidence=surface_confidence
        )
        self._classification["gender"] = GenderClassification(
            label=gender, confidence=gender_confidence
        )
        self._classification["view"] = ViewClassification(label=view)
        return self

    def contour_quality(self, value: ContourQuality | dict[str, Any]) -> MetaBuilder:
        self._data["contour_quality"] = _coerce(ContourQuality, value)
        return self

    def bounding_box(self, value: BoundingBox | dict[str, Any]) -> MetaBuilder:
        self._data["bounding_box_hu"] = _coerce(BoundingBox, value)
        return self

    def sections(self, value: SectionInventory | dict[str, Any]) -> MetaBuilder:
        self._data["sections"] = _coerce(SectionInventory, value)
        return self

    # ── Optional setters ──

    def mirror(
        self,
        *,
        applied: bool = False,
        semantics: str = "none",
        description: str | None = None,
    ) -> MetaBuilder:
        self._data["mirror"] = Mirror(applied=applied, semantics=semantics, description=description)
        return self

    def coordinate_system(
        self,
        dx: str = "right positive",
        dy: str = "down positive, 0=crown",
        hu_definition: str = "fraction of figure height",
    ) -> MetaBuilder:
        self._data["coordinate_system"] = CoordinateSystem(
            dx=dx, dy=dy, hu_definition=hu_definition
        )
        return self

    def hair_symmetry(self, value: HairSymmetry | dict[str, Any]) -> MetaBuilder:
        self._classification["hair_symmetry"] = _coerce(HairSymmetry, value)
        return self

    def shape_prior(self, value: dict[str, Any]) -> MetaBuilder:
        self._data["shape_prior"] = value
        return self

    def multi_figure_sheet(
        self,
        *,
        is_multi: bool,
        figure_index: int | None = None,
        figure_view: str | None = None,
    ) -> MetaBuilder:
        self._data["multi_figure_sheet"] = is_multi
        if figure_index is not None:
            self._data["extracted_figure_index"] = figure_index
        if figure_view is not None:
            self._data["extracted_figure_view"] = figure_view
        return self

    def landmark_validation(self, value: LandmarkValidation | dict[str, Any]) -> MetaBuilder:
        self._data["landmark_validation"] = _coerce(LandmarkValidation, value)
        return self

    # ── Build ──

    def build(self) -> Meta:
        """Validate and return a ``Meta`` instance.

        Raises ``pydantic.ValidationError`` on invalid or missing data.
        """
        if "mirror" not in self._data:
            self.mirror()
        if "coordinate_system" not in self._data:
            self.coordinate_system()
        self._data["classification"] = Classification(**self._classification)
        return Meta.model_validate(self._data)


# ──────────────────────────────────────────────────────────
# SilhouetteBuilder
# ──────────────────────────────────────────────────────────

# Mapping of section name → expected Pydantic model class.
# Sections whose values are plain lists (contour, midline, landmarks,
# strokes, candidates) are handled by dedicated methods.
_SECTION_MODELS: dict[str, type] = {
    "meta": Meta,
    "symmetry": Symmetry,
    "measurements": Measurements,
    "parametric": Parametric,
    "proportion": Proportion,
    "curvature": Curvature,
    "body_regions": BodyRegions,
    "cross_section_topology": CrossSectionTopology,
    "fourier_descriptors": FourierDescriptors,
    "width_profile": WidthProfile,
    "area_profile": AreaProfile,
    "contour_normals": ContourNormals,
    "shape_vector": ShapeVector,
    "hu_moments": HuMoments,
    "turning_function": TurningFunction,
    "convex_hull": ConvexHull,
    "gesture_line": GestureLine,
    "curvature_scale_space": CurvatureScaleSpace,
    "style_deviation": StyleDeviation,
    "volumetric_estimates": VolumetricEstimates,
    "biomechanics": Biomechanics,
    "medial_axis": MedialAxis,
    "shape_complexity": ShapeComplexity,
}


class SilhouetteBuilder:
    """Fluent builder for ``SilhouetteV4`` documents.

    Each section method accepts either a pre-built Pydantic model
    instance **or** a plain ``dict`` (forwarded to ``model_validate``).
    """

    def __init__(self) -> None:
        self._sections: dict[str, object] = {}

    # ── Generic object-section setter ──

    def _set_object(self, name: str, value: _ModelOrDict) -> SilhouetteBuilder:
        model_cls = _SECTION_MODELS[name]
        self._sections[name] = _coerce(model_cls, value)
        return self

    # ── List-of-point sections ──

    def contour(self, points: Sequence[Point2d]) -> SilhouetteBuilder:
        self._sections["contour"] = list(points)
        return self

    def midline(self, points: Sequence[Point2d]) -> SilhouetteBuilder:
        self._sections["midline"] = list(points)
        return self

    # ── List-of-model sections ──

    def landmarks(self, values: Sequence[Landmark | dict[str, Any]]) -> SilhouetteBuilder:
        self._sections["landmarks"] = _coerce_list(Landmark, values)
        return self

    def strokes(self, values: Sequence[Stroke | dict[str, Any]]) -> SilhouetteBuilder:
        self._sections["strokes"] = _coerce_list(Stroke, values)
        return self

    def candidates(self, values: Sequence[Candidate | dict[str, Any]]) -> SilhouetteBuilder:
        self._sections["candidates"] = _coerce_list(Candidate, values)
        return self

    # ── Object sections (one method per section) ──

    def meta(self, value: Meta | dict[str, Any]) -> SilhouetteBuilder:
        return self._set_object("meta", value)

    def symmetry(self, value: Symmetry | dict[str, Any]) -> SilhouetteBuilder:
        return self._set_object("symmetry", value)

    def measurements(self, value: Measurements | dict[str, Any]) -> SilhouetteBuilder:
        return self._set_object("measurements", value)

    def parametric(self, value: Parametric | dict[str, Any]) -> SilhouetteBuilder:
        return self._set_object("parametric", value)

    def proportion(self, value: Proportion | dict[str, Any]) -> SilhouetteBuilder:
        return self._set_object("proportion", value)

    def curvature(self, value: Curvature | dict[str, Any]) -> SilhouetteBuilder:
        return self._set_object("curvature", value)

    def body_regions(self, value: BodyRegions | dict[str, Any]) -> SilhouetteBuilder:
        return self._set_object("body_regions", value)

    def cross_section_topology(
        self, value: CrossSectionTopology | dict[str, Any]
    ) -> SilhouetteBuilder:
        return self._set_object("cross_section_topology", value)

    def fourier_descriptors(self, value: FourierDescriptors | dict[str, Any]) -> SilhouetteBuilder:
        return self._set_object("fourier_descriptors", value)

    def width_profile(self, value: WidthProfile | dict[str, Any]) -> SilhouetteBuilder:
        return self._set_object("width_profile", value)

    def area_profile(self, value: AreaProfile | dict[str, Any]) -> SilhouetteBuilder:
        return self._set_object("area_profile", value)

    def contour_normals(self, value: ContourNormals | dict[str, Any]) -> SilhouetteBuilder:
        return self._set_object("contour_normals", value)

    def shape_vector(self, value: ShapeVector | dict[str, Any]) -> SilhouetteBuilder:
        return self._set_object("shape_vector", value)

    def hu_moments(self, value: HuMoments | dict[str, Any]) -> SilhouetteBuilder:
        return self._set_object("hu_moments", value)

    def turning_function(self, value: TurningFunction | dict[str, Any]) -> SilhouetteBuilder:
        return self._set_object("turning_function", value)

    def convex_hull(self, value: ConvexHull | dict[str, Any]) -> SilhouetteBuilder:
        return self._set_object("convex_hull", value)

    def gesture_line(self, value: GestureLine | dict[str, Any]) -> SilhouetteBuilder:
        return self._set_object("gesture_line", value)

    def curvature_scale_space(
        self, value: CurvatureScaleSpace | dict[str, Any]
    ) -> SilhouetteBuilder:
        return self._set_object("curvature_scale_space", value)

    def style_deviation(self, value: StyleDeviation | dict[str, Any]) -> SilhouetteBuilder:
        return self._set_object("style_deviation", value)

    def volumetric_estimates(
        self, value: VolumetricEstimates | dict[str, Any]
    ) -> SilhouetteBuilder:
        return self._set_object("volumetric_estimates", value)

    def biomechanics(self, value: Biomechanics | dict[str, Any]) -> SilhouetteBuilder:
        return self._set_object("biomechanics", value)

    def medial_axis(self, value: MedialAxis | dict[str, Any]) -> SilhouetteBuilder:
        return self._set_object("medial_axis", value)

    def shape_complexity(self, value: ShapeComplexity | dict[str, Any]) -> SilhouetteBuilder:
        return self._set_object("shape_complexity", value)

    # ── Bulk setter ──

    def set_section(self, name: str, value: _ModelOrDict) -> SilhouetteBuilder:
        """Set an arbitrary section by name.

        Useful for pipeline code that iterates over section dicts::

            for name, data in pipeline_output.items():
                builder.set_section(name, data)
        """
        # Delegate to the typed method if one exists.
        method = getattr(self, name, None)
        if method is not None and callable(method):
            result: SilhouetteBuilder = method(value)
            return result
        msg = f"Unknown section: {name!r}"
        raise ValueError(msg)

    # ── Introspection ──

    def missing_sections(self) -> list[str]:
        """Return names of required sections not yet set."""
        required = set(SilhouetteV4.model_fields.keys())
        return sorted(required - set(self._sections.keys()))

    def set_sections(self) -> list[str]:
        """Return names of sections already set."""
        return sorted(self._sections.keys())

    # ── Build ──

    def build(self) -> SilhouetteDocument:
        """Validate all sections and return a ``SilhouetteDocument``.

        Raises ``ValueError`` if required sections are missing.
        Raises ``pydantic.ValidationError`` if data is invalid.
        """
        missing = self.missing_sections()
        if missing:
            msg = f"Cannot build: {len(missing)} required section(s) missing: {missing}"
            raise ValueError(msg)
        model = SilhouetteV4.model_validate(self._sections)
        return SilhouetteDocument(model)

    def build_partial(self) -> dict[str, Any]:
        """Return the current state as a plain dict (no final validation).

        Useful for debugging or inspecting what has been set so far.
        Individual sections are still validated at set-time.
        """
        result: dict[str, Any] = {}
        for k, v in self._sections.items():
            result[k] = v.model_dump(by_alias=True) if hasattr(v, "model_dump") else v
        return result


# ──────────────────────────────────────────────────────────
# SilhouetteDocument
# ──────────────────────────────────────────────────────────


class SilhouetteDocument:
    """Immutable wrapper around a ``SilhouetteV4`` document.

    // PALS's LAW: LLM output is untrusted by default. Verify before use.

    Provides JSON serialization and deserialization, including a
    ``strict=False`` mode for loading pipeline outputs that may have
    minor floating-point constraint violations (e.g. negative widths
    from interpolation artifacts).

    In **strict** mode (the default), the document is fully validated
    by Pydantic and ``model`` returns a ``SilhouetteV4`` instance.
    This covers ERR_SCHEMA, ERR_OMISSION, and ERR_TRUNCATION per
    PALS's Law §5.

    In **lenient** mode (``strict=False``), the raw dict is preserved
    as-is — no constraint validators run.  ``model`` is ``None``, but
    ``to_dict()`` / ``to_json()`` work normally.  Use ``validate()`` to
    check which constraints (if any) are violated.

    .. warning:: PALS's Law §8.4 (Corollary 4)

       Lenient mode is **explicit risk acceptance**: no error classes
       are verified.  Any system that passes lenient-mode output to
       downstream consumers without additional verification has an
       architectural omission.
    """

    def __init__(
        self,
        model: SilhouetteV4 | None = None,
        *,
        _raw: dict[str, Any] | None = None,
    ) -> None:
        self._model = model
        self._raw = _raw

    @property
    def model(self) -> SilhouetteV4 | None:
        """The validated Pydantic model, or ``None`` for lenient documents."""
        return self._model

    @property
    def is_strict(self) -> bool:
        """``True`` if this document was fully validated."""
        return self._model is not None

    # ── Serialization ──

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (using schema aliases)."""
        if self._model is not None:
            return self._model.model_dump(by_alias=True)
        # Lenient: raw dict is already JSON-compatible.
        if self._raw is None:
            msg = "Document has neither a validated model nor raw data"
            raise RuntimeError(msg)
        return self._raw

    def to_json(self, path: str | Path, *, indent: int = 2) -> None:
        """Write JSON to *path*."""
        Path(path).write_text(
            json.dumps(self.to_dict(), indent=indent, ensure_ascii=False),
            encoding="utf-8",
        )

    def to_json_str(self, *, indent: int = 2) -> str:
        """Serialize to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    # ── Deserialization ──

    @classmethod
    def from_json(
        cls, path: str | Path, *, strict: bool = True
    ) -> SilhouetteDocument:
        """Load and validate a JSON file.

        Parameters
        ----------
        path : str | Path
            Path to the JSON file.
        strict : bool
            If ``True`` (default), Pydantic constraints (``ge``, ``le``,
            etc.) are enforced and ``ValidationError`` is raised on
            violations.  Covers ERR_SCHEMA, ERR_OMISSION, ERR_TRUNCATION
            per PALS's Law §5.

            If ``False``, the raw dict is preserved without constraint
            checking — useful for pipeline outputs with minor floating-
            point artifacts.  **This is explicit risk acceptance per
            PALS's Law §8.4** — call ``verification_report()`` on the
            returned document to inspect uncovered error classes.
        """
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data, strict=strict)

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], *, strict: bool = True
    ) -> SilhouetteDocument:
        """Create from a plain dict.

        See ``from_json`` for the meaning of *strict*.

        .. note:: PALS's Law §8.2 (Corollary 2)

           A prior call with ``strict=True`` that succeeded does NOT
           justify calling with ``strict=False`` on subsequent inputs.
           Trust accumulation is prohibited.
        """
        if strict:
            return cls(SilhouetteV4.model_validate(data))
        return cls(_raw=data)

    @classmethod
    def from_json_str(cls, text: str, *, strict: bool = True) -> SilhouetteDocument:
        """Create from a JSON string."""
        return cls.from_dict(json.loads(text), strict=strict)

    # ── Verification boundary (PALS's Law §8.3) ──

    def validate(self) -> list[str]:
        """Re-validate the document and return a list of error messages.

        Returns an empty list if the document is fully valid.
        Covers ERR_SCHEMA, ERR_OMISSION, and ERR_TRUNCATION.
        """
        try:
            SilhouetteV4.model_validate(self.to_dict())
        except ValidationError as exc:
            return [str(e) for e in exc.errors()]
        return []

    def verification_report(self) -> VerificationReport:
        """Return a PALS's Law §8.3 verification scope declaration.

        The report declares which of the nine LLM error classes (§5)
        are covered by this SDK's validation boundary and which are
        known, accepted risks.

        In **strict** mode, the report covers:
          - ERR_SCHEMA (type/structure/constraint validation)
          - ERR_OMISSION (required field enforcement)
          - ERR_TRUNCATION (minimum length constraints)

        In **lenient** mode (``strict=False``), the report declares
        ZERO coverage — explicit risk acceptance per §8.4.

        Returns
        -------
        VerificationReport
            Includes ``schema_errors`` if any Pydantic violations were
            detected, plus full coverage/non-coverage declarations.
        """
        schema_errors = self.validate()
        return _build_verification_report(schema_errors, strict=self.is_strict)

    # ── Convenience ──

    def __repr__(self) -> str:
        if self._model is not None:
            src = self._model.meta.source
            ver = self._model.meta.schema_version
        elif self._raw is not None:
            meta = self._raw.get("meta", {})
            src = meta.get("source", "?")
            ver = meta.get("schema_version", "?")
        else:
            src = ver = "?"
        return f"<SilhouetteDocument v{ver} source={src!r}>"
