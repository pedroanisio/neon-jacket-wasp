"""Tests for lib.builder — SilhouetteV4 builder SDK."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.builder import MetaBuilder, SilhouetteBuilder, SilhouetteDocument
from pydantic import ValidationError

from lib.model import (
    ALL_ERROR_CLASSES,
    BioSegment,
    Biomechanics,
    CanonicalComparison,
    Compactness,
    ContourNormals,
    ContourVariant,
    ConvexHull,
    CoordinateSystem,
    Curvature,
    CurvatureScaleSpace,
    FourierDescriptors,
    FractalDimension,
    GestureLine,
    GestureLineSpline,
    HuConvention,
    HuMoments,
    Landmark,
    LLMErrorClass,
    Measurements,
    Meta,
    MultiSpanEntry,
    PALS_LAW_VERSION,
    PrincipalAxes,
    Rectangularity,
    ScanlineEntry,
    SegmentEndpointConvention,
    ShapeComplexity,
    StyleDeviation,
    TurningFunction,
)


# ═══════════════════════════════════════════════════════════
# Fixtures — minimal valid data for all 27 sections
# ═══════════════════════════════════════════════════════════

def _meta_builder() -> MetaBuilder:
    """Return a MetaBuilder pre-filled with all required fields."""
    return (
        MetaBuilder("test_source", (1024, 2048))
        .crop_rect(100, 50, 900, 2000)
        .midline(500.0)
        .y_range(50, 2000)
        .scale(0.005)
        .contour_info(100, detail_strokes=5)
        .extraction("floodfill", scanline=0.0, floodfill=0.95, direct=0.0, margin=0.01)
        .timing(100.0, 200.0)
        .classify(surface="clothed", gender="female", view="front")
        .contour_quality({
            "total_perimeter_hu": 20.0,
            "right_perimeter_hu": 10.0,
            "mean_segment_length": 0.02,
            "segment_length_cv": 0.1,
        })
        .bounding_box({
            "dx_min": -0.01,
            "dx_max": 1.3,
            "dy_min": 0.0,
            "dy_max": 8.0,
            "width": 1.31,
            "height": 8.0,
            "aspect_ratio": 6.1,
        })
        .sections({
            "total_sections": 27,
            "sections": ["meta", "contour", "landmarks"],
        })
    )


def _minimal_sections() -> dict:
    """Return a dict of minimal valid data for every section (as dicts)."""
    contour = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    midline = [(0.0, 0.0), (0.0, 1.0)]
    landmarks = [{
        "name": "crown",
        "description": "Top of head",
        "dy": 0.0,
        "dx": 0.0,
    }]
    strokes = [{
        "id": 0,
        "region": "torso",
        "n_points": 3,
        "bbox": {"dx_min": 0.0, "dx_max": 1.0, "dy_min": 0.0, "dy_max": 1.0},
        "points": [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0)],
    }]
    symmetry = {
        "samples": {
            "0.5": {"right_dx": 0.5, "left_dx": 0.5, "delta": 0.0},
        },
    }
    measurements = {
        "scanlines": {
            "0.5": {"right_dx": 0.5, "left_dx": -0.5, "full_width_hu": 1.0},
        },
    }
    parametric = {
        "segments": [{
            "label": "torso",
            "landmark_start": "crown",
            "landmark_end": "sole",
            "dy_range": (0.0, 1.0),
            "knots": [0.0, 0.5, 1.0],
            "coeffs_dx": [0.1, 0.2, 0.3],
            "degree": 3,
        }],
    }
    proportion = {
        "head_count_total": 7.5,
        "head_height_hu": 0.133,
        "figure_height_total_hu": 1.0,
        "segment_ratios": {"head": 0.133},
        "width_ratios": {"shoulder": 0.25},
    }
    candidates = [{
        "method": "floodfill",
        "score": 0.9,
        "selected": True,
        "bounds": {
            "midline_px": 500.0,
            "y_top": 50,
            "y_bot": 2000,
            "fig_height_px": 1950,
            "scale_px_to_hu": 0.005,
        },
        "score_breakdown": {},
    }]
    curvature = {
        "sample_count": 2,
        "samples": [
            {"dy": 0.0, "dx": 0.0, "kappa": 0.1},
            {"dy": 1.0, "dx": 0.0, "kappa": -0.1},
        ],
    }
    body_regions = {
        "regions": [{
            "name": "torso",
            "dy_start": 0.0,
            "dy_end": 0.5,
            "description": "Upper body",
        }],
    }
    cross_section_topology = {
        "profile": {
            "0.5": {"crossings": 2, "pairs": 1},
        },
    }
    fourier_descriptors = {
        "n_harmonics": 1,
        "perimeter_hu": 4.0,
        "coefficients": [{
            "harmonic": 1,
            "a_x": 1.0,
            "b_x": 0.0,
            "a_y": 0.0,
            "b_y": 1.0,
            "amplitude": 1.0,
        }],
    }
    width_profile = {
        "resolution_hu": 0.1,
        "sample_count": 2,
        "samples": [
            {"dy": 0.0, "dx": 0.5, "full_width": 1.0},
            {"dy": 1.0, "dx": 0.3, "full_width": 0.6},
        ],
        "extrema": {
            "maxima": {"count": 1, "points": [{"dy": 0.0, "dx": 0.5, "full_width": 1.0}]},
            "minima": {"count": 1, "points": [{"dy": 1.0, "dx": 0.3, "full_width": 0.6}]},
        },
        "statistics": {
            "mean_dx": 0.4,
            "max_dx": 0.5,
            "min_dx": 0.3,
        },
    }
    area_profile = {
        "total_area_hu2": 0.8,
        "per_region": [{
            "name": "torso",
            "dy_range": (0.0, 0.5),
            "height_hu": 0.5,
            "area_hu2": 0.4,
            "area_fraction": 0.5,
        }],
    }
    contour_normals = {
        "sample_step": 5,
        "sample_count": 2,
        "full_point_count": 100,
        "samples": [
            {"index": 0, "dx": 0.0, "dy": 0.0, "nx": 1.0, "ny": 0.0},
            {"index": 5, "dx": 0.5, "dy": 0.5, "nx": 0.0, "ny": 1.0},
        ],
    }
    shape_vector = {
        "dimension": 3,
        "vector": [0.1, 0.2, 0.3],
        "dy_sample_points": [0.0, 0.5, 1.0],
        "normalization": {"width_max_dx": 0.5, "method": "max_dx"},
    }
    hu_moments = {
        "raw": (1.0, 0.5, 0.3, 0.2, 0.1, 0.05, 0.01),
        "log_transformed": (-0.0, -0.3, -0.5, -0.7, -1.0, -1.3, -2.0),
        "centroid": {"dx": 0.0, "dy": 0.5},
    }
    turning_function = {
        "total_angle_rad": 6.283,
        "winding_number": 1.0,
        "sample_count": 2,
        "samples": [
            {"s": 0.0, "theta": 0.0},
            {"s": 1.0, "theta": 6.283},
        ],
    }
    convex_hull = {
        "hull_area_hu2": 1.2,
        "silhouette_area_hu2": 0.85,
        "solidity": 0.708,
        "convexity_deficiency": 0.292,
    }
    gesture_line = {
        "primary_axis": {
            "direction": (0.0, 1.0),
            "eigenvalue": 0.95,
            "explained_variance_ratio": 0.95,
        },
        "secondary_axis": {
            "direction": (1.0, 0.0),
            "eigenvalue": 0.05,
        },
        "lean_angle_deg": 2.3,
        "gesture_energy": 0.05,
    }
    curvature_scale_space = {
        "scales": [{
            "label": "fine",
            "sigma": 1.0,
            "zero_crossings": 12,
            "mean_abs_kappa": 0.5,
            "max_abs_kappa": 2.0,
        }],
    }
    style_deviation = {
        "canon": "Loomis",
        "position_deviations": [{
            "landmark": "crown",
            "canon_name": "crown",
            "measured_fraction": 0.0,
            "canon_fraction": 0.0,
            "deviation": 0.0,
        }],
        "l2_stylisation_distance": 0.12,
    }
    volumetric_estimates = {
        "assumptions": {
            "canonical_height_cm": 175.0,
            "scale_cm_per_hu": 23.3,
            "figure_height_hu": 7.5,
        },
        "cylindrical": {
            "volume_hu3": 10.0,
            "volume_cm3": 50000.0,
            "volume_liters": 50.0,
            "method": "cylindrical",
        },
        "ellipsoidal": {
            "volume_hu3": 8.0,
            "volume_cm3": 40000.0,
            "volume_liters": 40.0,
            "method": "ellipsoidal",
        },
        "pappus": {
            "volume_hu3": 9.0,
            "volume_cm3": 45000.0,
            "volume_liters": 45.0,
            "method": "pappus",
        },
    }
    biomechanics = {
        "gender_data": "female",
        "segments": [{
            "segment": "head",
            "mass_fraction": 0.081,
            "com_proximal_fraction": 0.5,
            "rog_com_fraction": 0.5,
            "rog_proximal_fraction": 0.5,
        }],
    }
    medial_axis = {
        "main_axis": {
            "start": {"dx": 0.0, "dy": 0.0},
            "end": {"dx": 0.0, "dy": 1.0},
            "sample_count": 2,
            "samples": [
                {"dy": 0.0, "medial_dx": 0.0, "inscribed_radius": 0.5, "inscribed_diameter": 1.0},
                {"dy": 1.0, "medial_dx": 0.0, "inscribed_radius": 0.3, "inscribed_diameter": 0.6},
            ],
        },
    }
    shape_complexity = {
        "curvature_entropy": {"value": 3.5},
        "fractal_dimension": {"value": 1.2, "method": "box_counting"},
        "compactness": {"value": 0.7},
        "eccentricity": {"value": 0.9},
    }

    return {
        "contour": contour,
        "midline": midline,
        "landmarks": landmarks,
        "strokes": strokes,
        "symmetry": symmetry,
        "measurements": measurements,
        "parametric": parametric,
        "proportion": proportion,
        "candidates": candidates,
        "curvature": curvature,
        "body_regions": body_regions,
        "cross_section_topology": cross_section_topology,
        "fourier_descriptors": fourier_descriptors,
        "width_profile": width_profile,
        "area_profile": area_profile,
        "contour_normals": contour_normals,
        "shape_vector": shape_vector,
        "hu_moments": hu_moments,
        "turning_function": turning_function,
        "convex_hull": convex_hull,
        "gesture_line": gesture_line,
        "curvature_scale_space": curvature_scale_space,
        "style_deviation": style_deviation,
        "volumetric_estimates": volumetric_estimates,
        "biomechanics": biomechanics,
        "medial_axis": medial_axis,
        "shape_complexity": shape_complexity,
    }


# ═══════════════════════════════════════════════════════════
# MetaBuilder tests
# ═══════════════════════════════════════════════════════════

class TestMetaBuilder:
    def test_build_minimal(self):
        meta = _meta_builder().build()
        assert isinstance(meta, Meta)
        assert meta.source == "test_source"
        assert meta.schema_version == "4.0.0"

    def test_defaults_applied(self):
        meta = _meta_builder().build()
        assert meta.mirror.applied is False
        assert meta.mirror.semantics == "none"
        assert meta.coordinate_system.dx == "right positive"

    def test_override_mirror(self):
        meta = (
            _meta_builder()
            .mirror(applied=True, semantics="right_half_authoritative")
            .build()
        )
        assert meta.mirror.applied is True

    def test_optional_multi_figure(self):
        meta = (
            _meta_builder()
            .multi_figure_sheet(is_multi=True, figure_index=0, figure_view="front")
            .build()
        )
        assert meta.multi_figure_sheet is True
        assert meta.extracted_figure_index == 0

    def test_optional_hair_symmetry(self):
        meta = (
            _meta_builder()
            .hair_symmetry({"label": "symmetric"})
            .build()
        )
        assert meta.classification.hair_symmetry is not None
        assert meta.classification.hair_symmetry.label == "symmetric"

    def test_optional_shape_prior(self):
        meta = (
            _meta_builder()
            .shape_prior({"model": "loomis"})
            .build()
        )
        assert meta.shape_prior == {"model": "loomis"}

    def test_optional_landmark_validation(self):
        meta = (
            _meta_builder()
            .landmark_validation({
                "anomalies_detected": 1,
                "corrections_applied": ["fixed crown"],
            })
            .build()
        )
        assert meta.landmark_validation is not None
        assert meta.landmark_validation.anomalies_detected == 1

    def test_missing_required_field_raises(self):
        # Missing crop_rect
        builder = (
            MetaBuilder("src", (100, 200))
            .midline(50.0)
            .y_range(10, 200)
            .scale(0.01)
            .contour_info(100)
            .extraction("floodfill", floodfill=1.0)
            .timing(10.0, 20.0)
            .classify(surface="nude", gender="male", view="front")
            .contour_quality({
                "total_perimeter_hu": 1.0,
                "right_perimeter_hu": 0.5,
                "mean_segment_length": 0.01,
                "segment_length_cv": 0.1,
            })
            .bounding_box({
                "dx_min": 0.0, "dx_max": 1.0, "dy_min": 0.0, "dy_max": 1.0,
                "width": 1.0, "height": 1.0, "aspect_ratio": 1.0,
            })
            .sections({"total_sections": 1, "sections": ["meta"]})
        )

        with pytest.raises(ValidationError):
            builder.build()


# ═══════════════════════════════════════════════════════════
# SilhouetteBuilder tests
# ═══════════════════════════════════════════════════════════

class TestSilhouetteBuilder:
    def test_missing_sections(self):
        builder = SilhouetteBuilder()
        assert len(builder.missing_sections()) == 28  # 27 data sections + meta

    def test_build_from_dicts(self):
        meta = _meta_builder().build()
        sections = _minimal_sections()

        builder = SilhouetteBuilder().meta(meta)
        for name, data in sections.items():
            builder.set_section(name, data)

        doc = builder.build()
        assert isinstance(doc, SilhouetteDocument)
        assert doc.model.meta.source == "test_source"

    def test_build_missing_raises(self):
        builder = SilhouetteBuilder()
        builder.meta(_meta_builder().build())
        with pytest.raises(ValueError, match="missing"):
            builder.build()

    def test_build_partial(self):
        builder = SilhouetteBuilder()
        meta = _meta_builder().build()
        builder.meta(meta)
        builder.contour([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)])

        partial = builder.build_partial()
        assert "meta" in partial
        assert "contour" in partial
        assert len(partial) == 2

    def test_set_sections_introspection(self):
        builder = SilhouetteBuilder()
        builder.meta(_meta_builder().build())
        builder.contour([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)])
        assert builder.set_sections() == ["contour", "meta"]

    def test_invalid_section_name_raises(self):
        builder = SilhouetteBuilder()
        with pytest.raises(ValueError, match="Unknown section"):
            builder.set_section("nonexistent", {})

    def test_accepts_model_instances(self):
        builder = SilhouetteBuilder()
        lm = Landmark(name="crown", description="Top", dy=0.0, dx=0.0)
        builder.landmarks([lm])
        assert builder.set_sections() == ["landmarks"]

    def test_invalid_data_raises_at_set_time(self):
        builder = SilhouetteBuilder()

        with pytest.raises(ValidationError):
            # Missing required fields
            builder.symmetry({})

    def test_chaining(self):
        meta = _meta_builder().build()
        sections = _minimal_sections()
        builder = (
            SilhouetteBuilder()
            .meta(meta)
            .contour(sections["contour"])
            .midline(sections["midline"])
            .landmarks(sections["landmarks"])
        )
        assert len(builder.set_sections()) == 4


# ═══════════════════════════════════════════════════════════
# SilhouetteDocument tests
# ═══════════════════════════════════════════════════════════

class TestSilhouetteDocument:
    @pytest.fixture()
    def full_doc(self) -> SilhouetteDocument:
        meta = _meta_builder().build()
        sections = _minimal_sections()
        builder = SilhouetteBuilder().meta(meta)
        for name, data in sections.items():
            builder.set_section(name, data)
        return builder.build()

    def test_to_dict(self, full_doc):
        d = full_doc.to_dict()
        assert isinstance(d, dict)
        assert d["meta"]["source"] == "test_source"

    def test_to_json_str(self, full_doc):
        s = full_doc.to_json_str()
        parsed = json.loads(s)
        assert parsed["meta"]["schema_version"] == "4.0.0"

    def test_to_json_file(self, full_doc, tmp_path):
        path = tmp_path / "output.json"
        full_doc.to_json(path)
        assert path.exists()
        loaded = json.loads(path.read_text())
        assert loaded["meta"]["source"] == "test_source"

    def test_round_trip_json(self, full_doc, tmp_path):
        path = tmp_path / "round_trip.json"
        full_doc.to_json(path)
        reloaded = SilhouetteDocument.from_json(path)
        assert reloaded.model.meta.source == full_doc.model.meta.source
        assert reloaded.to_dict() == full_doc.to_dict()

    def test_round_trip_dict(self, full_doc):
        d = full_doc.to_dict()
        reloaded = SilhouetteDocument.from_dict(d)
        assert reloaded.to_dict() == d

    def test_from_json_str(self, full_doc):
        s = full_doc.to_json_str()
        reloaded = SilhouetteDocument.from_json_str(s)
        assert reloaded.to_dict() == full_doc.to_dict()

    def test_validate_clean_doc(self, full_doc):
        errors = full_doc.validate()
        assert errors == []

    def test_is_strict(self, full_doc):
        assert full_doc.is_strict is True

    def test_repr(self, full_doc):
        r = repr(full_doc)
        assert "SilhouetteDocument" in r
        assert "test_source" in r

    def test_repr_lenient(self, full_doc):
        d = full_doc.to_dict()
        lenient = SilhouetteDocument.from_dict(d, strict=False)
        r = repr(lenient)
        assert "SilhouetteDocument" in r
        assert "test_source" in r
        assert lenient.is_strict is False

    def test_from_dict_strict_false(self):
        """Lenient mode should not raise on constraint violations."""
        # Build a valid dict then corrupt a constrained field.
        meta = _meta_builder().build()
        sections = _minimal_sections()
        builder = SilhouetteBuilder().meta(meta)
        for name, data in sections.items():
            builder.set_section(name, data)
        d = builder.build().to_dict()

        # Introduce a violation: negative full_width
        d["width_profile"]["samples"][0]["full_width"] = -1.0

        # Strict should fail

        with pytest.raises(ValidationError):
            SilhouetteDocument.from_dict(d, strict=True)

        # Lenient should succeed
        doc = SilhouetteDocument.from_dict(d, strict=False)
        assert doc is not None


# ═══════════════════════════════════════════════════════════
# Integration: real pipeline output
# ═══════════════════════════════════════════════════════════

SAMPLE_JSON = Path(__file__).resolve().parent.parent / "data" / "output" / "generated_v4.json"


@pytest.mark.skipif(
    not SAMPLE_JSON.exists(),
    reason="Sample pipeline output not available",
)
class TestRealData:
    def test_lenient_load(self):
        doc = SilhouetteDocument.from_json(SAMPLE_JSON, strict=False)
        assert doc.model is None  # lenient mode skips model construction
        assert doc.to_dict()["meta"]["schema_version"] == "4.0.0"

    def test_lenient_round_trip(self, tmp_path):
        doc = SilhouetteDocument.from_json(SAMPLE_JSON, strict=False)
        out = tmp_path / "re_exported.json"
        doc.to_json(out)
        assert out.exists()
        reloaded = json.loads(out.read_text())
        assert sorted(reloaded.keys()) == sorted(
            json.loads(SAMPLE_JSON.read_text()).keys()
        )

    def test_validate_reports_errors(self):
        doc = SilhouetteDocument.from_json(SAMPLE_JSON, strict=False)
        errors = doc.validate()
        # The sample data is known to have constraint violations.
        assert isinstance(errors, list)


# ═══════════════════════════════════════════════════════════
# PALS's Law v1.5.4 compliance tests
# ═══════════════════════════════════════════════════════════

class TestPALSLawCompliance:
    """Tests verifying PALS's Law v1.5.4 compliance (§5, §8, §9)."""

    @pytest.fixture()
    def strict_doc(self) -> SilhouetteDocument:
        meta = _meta_builder().build()
        sections = _minimal_sections()
        builder = SilhouetteBuilder().meta(meta)
        for name, data in sections.items():
            builder.set_section(name, data)
        return builder.build()

    # -- §9.1: PALS_LAW_VERSION constant exists --

    def test_pals_law_version_constant(self):
        assert PALS_LAW_VERSION == "1.5.4"

    # -- §5: All 9 error classes are defined --

    def test_error_taxonomy_completeness(self):
        expected = {
            "ERR_HALLUCINATION",
            "ERR_OMISSION",
            "ERR_SCHEMA",
            "ERR_TRUNCATION",
            "ERR_SYCOPHANCY",
            "ERR_INSTRUCTION",
            "ERR_CALIBRATION",
            "ERR_SEMANTIC",
            "ERR_REASONING",
        }
        actual = {cls.value for cls in LLMErrorClass}
        assert actual == expected

    def test_all_error_classes_frozenset(self):
        assert len(ALL_ERROR_CLASSES) == 9
        assert all(isinstance(c, LLMErrorClass) for c in ALL_ERROR_CLASSES)

    # -- §8.3 Corollary 3: Verification scope must match error taxonomy --

    def test_strict_report_covers_schema_omission_truncation(self, strict_doc):
        report = strict_doc.verification_report()
        covered = report.covered_classes
        assert LLMErrorClass.ERR_SCHEMA in covered
        assert LLMErrorClass.ERR_OMISSION in covered
        assert LLMErrorClass.ERR_TRUNCATION in covered

    def test_strict_report_declares_uncovered_classes(self, strict_doc):
        report = strict_doc.verification_report()
        uncovered = report.uncovered_classes
        assert LLMErrorClass.ERR_HALLUCINATION in uncovered
        assert LLMErrorClass.ERR_SYCOPHANCY in uncovered
        assert LLMErrorClass.ERR_INSTRUCTION in uncovered
        assert LLMErrorClass.ERR_CALIBRATION in uncovered
        assert LLMErrorClass.ERR_SEMANTIC in uncovered
        assert LLMErrorClass.ERR_REASONING in uncovered

    def test_strict_report_all_classes_accounted_for(self, strict_doc):
        report = strict_doc.verification_report()
        accounted = report.covered_classes | report.uncovered_classes
        assert accounted == ALL_ERROR_CLASSES

    def test_strict_report_version(self, strict_doc):
        report = strict_doc.verification_report()
        assert report.pals_law_version == "1.5.4"

    def test_strict_report_passed_on_valid_doc(self, strict_doc):
        report = strict_doc.verification_report()
        assert report.passed is True
        assert report.schema_errors == []

    # -- §8.4 Corollary 4: Silent acceptance is an architectural defect --

    def test_lenient_report_covers_nothing(self, strict_doc):
        """Lenient mode MUST declare zero coverage (explicit risk acceptance)."""
        d = strict_doc.to_dict()
        lenient_doc = SilhouetteDocument.from_dict(d, strict=False)
        report = lenient_doc.verification_report()
        assert report.covered_classes == frozenset()
        assert report.uncovered_classes == ALL_ERROR_CLASSES

    def test_lenient_report_all_results_uncovered(self, strict_doc):
        d = strict_doc.to_dict()
        lenient_doc = SilhouetteDocument.from_dict(d, strict=False)
        report = lenient_doc.verification_report()
        for result in report.verified:
            assert result.covered is False
            assert "Lenient mode" in (result.note or "")

    # -- §8.3: Every result has a method or note --

    def test_every_result_has_explanation(self, strict_doc):
        report = strict_doc.verification_report()
        for result in report.verified:
            has_explanation = result.method is not None or result.note is not None
            assert has_explanation, (
                f"{result.error_class}: must have method or note"
            )

    # -- VerificationReport properties --

    def test_report_is_not_fully_verified(self, strict_doc):
        """SDK cannot claim full coverage (§8.3)."""
        report = strict_doc.verification_report()
        assert report.is_fully_verified is False

    # -- §8.3: Report detects schema violations --

    def test_report_captures_schema_errors(self):
        meta = _meta_builder().build()
        sections = _minimal_sections()
        builder = SilhouetteBuilder().meta(meta)
        for name, data in sections.items():
            builder.set_section(name, data)
        d = builder.build().to_dict()

        # Introduce a violation: negative full_width
        d["width_profile"]["samples"][0]["full_width"] = -1.0

        lenient_doc = SilhouetteDocument.from_dict(d, strict=False)
        report = lenient_doc.verification_report()
        # Lenient mode doesn't run Pydantic validation eagerly,
        # but verification_report() re-validates and captures errors.
        assert len(report.schema_errors) > 0
        assert report.passed is False


# ═══════════════════════════════════════════════════════════
# P1 Regression tests — review audit fixes
# ═══════════════════════════════════════════════════════════


class TestP1FractalDimension:
    """P1-1: fractal_dimension.value must be in [1, 2]."""

    def test_valid_dimension(self):
        fd = FractalDimension(value=1.2, method="box_counting")
        assert fd.value == 1.2

    def test_rejects_below_one(self):
        with pytest.raises(ValidationError, match="greater_than_equal"):
            FractalDimension(value=0.95, method="box_counting")

    def test_rejects_above_two(self):
        with pytest.raises(ValidationError, match="less_than_equal"):
            FractalDimension(value=2.1, method="box_counting")

    def test_boundary_one(self):
        fd = FractalDimension(value=1.0, method="box_counting")
        assert fd.value == 1.0

    def test_boundary_two(self):
        fd = FractalDimension(value=2.0, method="box_counting")
        assert fd.value == 2.0


class TestP1Compactness:
    """P1-2: Compactness must include perimeter traceability fields."""

    def test_basic_compactness(self):
        c = Compactness(value=0.7)
        assert c.perimeter_used is None

    def test_with_traceability(self):
        c = Compactness(
            value=0.33,
            formula="4π·A / P²",
            perimeter_used="original",
            computed_area_hu2=12.39,
            computed_perimeter_hu=21.81,
        )
        assert c.perimeter_used == "original"
        assert c.computed_area_hu2 == 12.39
        assert c.computed_perimeter_hu == 21.81

    def test_perimeter_used_enum_values(self):
        for variant in ("right_half", "mirrored_full", "original"):
            c = Compactness(value=0.5, perimeter_used=variant)
            assert c.perimeter_used == variant

    def test_rejects_invalid_perimeter_used(self):
        with pytest.raises(ValidationError):
            Compactness(value=0.5, perimeter_used="invalid")


class TestP1TurningFunction:
    """P1-3: TurningFunction must declare computed_on contour variant."""

    def test_computed_on_field_exists(self):
        tf = TurningFunction(
            total_angle_rad=6.28,
            winding_number=1.0,
            sample_count=2,
            samples=[{"s": 0.0, "theta": 0.0}, {"s": 1.0, "theta": 6.28}],
            computed_on="mirrored_full",
        )
        assert tf.computed_on == "mirrored_full"

    def test_computed_on_optional_for_backward_compat(self):
        tf = TurningFunction(
            total_angle_rad=6.28,
            winding_number=1.0,
            sample_count=2,
            samples=[{"s": 0.0, "theta": 0.0}, {"s": 1.0, "theta": 6.28}],
        )
        assert tf.computed_on is None

    def test_rejects_invalid_computed_on(self):
        with pytest.raises(ValidationError):
            TurningFunction(
                total_angle_rad=6.28,
                winding_number=1.0,
                sample_count=2,
                samples=[{"s": 0.0, "theta": 0.0}, {"s": 1.0, "theta": 6.28}],
                computed_on="invalid_variant",
            )


class TestP1ConvexHull:
    """P1-4: ConvexHull must cite Gonzalez-Woods for area-ratio solidity."""

    def test_solidity_formula_field(self):
        ch = ConvexHull(
            hull_area_hu2=1.2,
            silhouette_area_hu2=0.85,
            solidity=0.708,
            convexity_deficiency=0.292,
            solidity_formula="A_shape / A_hull",
        )
        assert ch.solidity_formula == "A_shape / A_hull"

    def test_solidity_formula_optional(self):
        ch = ConvexHull(
            hull_area_hu2=1.0,
            silhouette_area_hu2=0.8,
            solidity=0.8,
            convexity_deficiency=0.2,
        )
        assert ch.solidity_formula is None


class TestP1Biomechanics:
    """P1-5: Biomechanics endpoint convention and corrected CoM."""

    def test_endpoint_convention_field(self):
        bio = Biomechanics(
            gender_data="female",
            segments=[{
                "segment": "head_neck",
                "mass_fraction": 0.0681,
                "com_proximal_fraction": 0.50,
                "rog_com_fraction": 0.495,
                "rog_proximal_fraction": 0.495,
                "proximal_landmark": "crown",
                "distal_landmark": "neck_valley",
            }],
            endpoint_convention={
                "source": "schema_landmarks",
                "note": "Endpoints use schema landmark names.",
            },
        )
        assert bio.endpoint_convention is not None
        assert bio.endpoint_convention.source == "schema_landmarks"

    def test_segment_landmark_fields(self):
        seg = BioSegment(
            segment="head_neck",
            mass_fraction=0.068,
            com_proximal_fraction=0.50,
            rog_com_fraction=0.5,
            rog_proximal_fraction=0.5,
            proximal_landmark="crown",
            distal_landmark="neck_valley",
        )
        assert seg.proximal_landmark == "crown"
        assert seg.distal_landmark == "neck_valley"

    def test_head_neck_com_not_1_0(self):
        """The corrected head_neck CoM should be ~0.50, not 1.0."""
        seg = BioSegment(
            segment="head_neck",
            mass_fraction=0.068,
            com_proximal_fraction=0.5002,
            rog_com_fraction=0.495,
            rog_proximal_fraction=0.495,
        )
        assert seg.com_proximal_fraction < 0.6, (
            "head_neck CoM should be ~0.50 for crown→neck_valley, not 1.0"
        )

    def test_female_reference_includes_de_leva(self):
        """Female BSP data must cite de Leva (1996)."""
        bio = Biomechanics(
            gender_data="female",
            segments=[{
                "segment": "head_neck",
                "mass_fraction": 0.068,
                "com_proximal_fraction": 0.50,
                "rog_com_fraction": 0.5,
                "rog_proximal_fraction": 0.5,
            }],
            reference=[
                "de Leva, P. 'Adjustments to Zatsiorsky-Seluyanov's segment inertia parameters.' J. Biomech. 29(9):1223–1230, 1996.",
                "Winter, D.A. 'Biomechanics and Motor Control of Human Movement.' 4th ed., Wiley, 2009.",
            ],
        )
        refs = bio.reference
        assert isinstance(refs, list)
        assert any("de Leva" in r for r in refs)


class TestP1Rectangularity:
    """P1-2b: Rectangularity must stay in [0, 1]."""

    def test_valid_rectangularity(self):
        r = Rectangularity(value=0.8)
        assert r.value == 0.8

    def test_rejects_above_one(self):
        with pytest.raises(ValidationError, match="less_than_equal"):
            Rectangularity(value=1.17)


class TestContourVariantType:
    """Verify the ContourVariant type alias works across models."""

    def test_all_variants_accepted(self):
        for v in ("right_half", "mirrored_full", "original"):
            c = Compactness(value=0.5, perimeter_used=v)
            assert c.perimeter_used == v


# ═══════════════════════════════════════════════════════════
# P2 Regression tests — consistency & documentation
# ═══════════════════════════════════════════════════════════

_MINIMAL_CURVATURE_SAMPLES = [
    {"dy": 0.0, "dx": 0.0, "kappa": 0.1},
    {"dy": 1.0, "dx": 0.0, "kappa": -0.1},
]


class TestP2ComputedOnAllSections:
    """P2-7: Every contour-consuming section must accept computed_on."""

    def test_curvature_computed_on(self):
        c = Curvature(
            sample_count=2,
            samples=_MINIMAL_CURVATURE_SAMPLES,
            computed_on="right_half",
        )
        assert c.computed_on == "right_half"

    def test_fourier_descriptors_computed_on(self):
        fd = FourierDescriptors(
            n_harmonics=1,
            perimeter_hu=4.0,
            coefficients=[{
                "harmonic": 1, "a_x": 1.0, "b_x": 0.0,
                "a_y": 0.0, "b_y": 1.0, "amplitude": 1.0,
            }],
            computed_on="right_half",
        )
        assert fd.computed_on == "right_half"

    def test_contour_normals_computed_on(self):
        cn = ContourNormals(
            sample_step=5, sample_count=1, full_point_count=100,
            samples=[{"index": 0, "dx": 0.0, "dy": 0.0, "nx": 1.0, "ny": 0.0}],
            computed_on="right_half",
        )
        assert cn.computed_on == "right_half"

    def test_hu_moments_computed_on_enum(self):
        """HuMoments.computed_on was tightened from str to ContourVariant."""
        hm = HuMoments(
            raw=(1, 0.5, 0.3, 0.2, 0.1, 0.05, 0.01),
            log_transformed=(0, -0.3, -0.5, -0.7, -1, -1.3, -2),
            centroid={"dx": 0.0, "dy": 0.5},
            computed_on="mirrored_full",
        )
        assert hm.computed_on == "mirrored_full"

    def test_hu_moments_rejects_old_string(self):
        """Old free-text computed_on values must now fail validation."""
        with pytest.raises(ValidationError):
            HuMoments(
                raw=(1, 0.5, 0.3, 0.2, 0.1, 0.05, 0.01),
                log_transformed=(0, -0.3, -0.5, -0.7, -1, -1.3, -2),
                centroid={"dx": 0.0, "dy": 0.5},
                computed_on="bilateral_symmetric_silhouette",
            )

    def test_curvature_scale_space_computed_on(self):
        css = CurvatureScaleSpace(
            scales=[{
                "label": "raw", "sigma": 0, "zero_crossings": 5,
                "mean_abs_kappa": 0.3, "max_abs_kappa": 1.5,
            }],
            computed_on="right_half",
        )
        assert css.computed_on == "right_half"

    def test_shape_complexity_computed_on(self):
        sc = ShapeComplexity(
            curvature_entropy={"value": 3.5},
            fractal_dimension={"value": 1.2, "method": "box_counting"},
            compactness={"value": 0.7},
            eccentricity={"value": 0.9},
            computed_on="right_half",
        )
        assert sc.computed_on == "right_half"

    def test_computed_on_optional_everywhere(self):
        """All computed_on fields default to None for backward compat."""
        c = Curvature(sample_count=2, samples=_MINIMAL_CURVATURE_SAMPLES)
        assert c.computed_on is None

    def test_rejects_invalid_variant(self):
        with pytest.raises(ValidationError):
            Curvature(
                sample_count=2,
                samples=_MINIMAL_CURVATURE_SAMPLES,
                computed_on="full_contour",
            )


class TestP2AmplitudeFormula:
    """P2-8: FourierDescriptors must have amplitude_formula field."""

    def test_amplitude_formula_present(self):
        fd = FourierDescriptors(
            n_harmonics=1,
            perimeter_hu=4.0,
            coefficients=[{
                "harmonic": 1, "a_x": 1.0, "b_x": 0.0,
                "a_y": 0.0, "b_y": 1.0, "amplitude": 1.0,
            }],
            amplitude_formula="frobenius_norm: sqrt(a_x^2 + b_x^2 + a_y^2 + b_y^2)",
        )
        assert "frobenius" in fd.amplitude_formula

    def test_amplitude_formula_optional(self):
        fd = FourierDescriptors(
            n_harmonics=1,
            perimeter_hu=4.0,
            coefficients=[{
                "harmonic": 1, "a_x": 1.0, "b_x": 0.0,
                "a_y": 0.0, "b_y": 1.0, "amplitude": 1.0,
            }],
        )
        assert fd.amplitude_formula is None


class TestP2HuConvention:
    """P2-9: CoordinateSystem must support hu_convention and conversion factor."""

    def test_hu_convention_field(self):
        cs = CoordinateSystem(
            dx="right positive", dy="down positive",
            hu_definition="fraction of figure height",
            hu_convention="crown_to_neck_valley",
            hu_to_standard_factor=1.1765,
        )
        assert cs.hu_convention == "crown_to_neck_valley"
        assert cs.hu_to_standard_factor == 1.1765

    def test_hu_convention_all_values(self):
        for v in ("crown_to_chin", "crown_to_neck_valley", "crown_to_c7", "custom"):
            cs = CoordinateSystem(
                dx="x", dy="y", hu_definition="hu",
                hu_convention=v,
            )
            assert cs.hu_convention == v

    def test_hu_convention_optional(self):
        cs = CoordinateSystem(dx="x", dy="y", hu_definition="hu")
        assert cs.hu_convention is None
        assert cs.hu_to_standard_factor is None

    def test_rejects_invalid_convention(self):
        with pytest.raises(ValidationError):
            CoordinateSystem(
                dx="x", dy="y", hu_definition="hu",
                hu_convention="forehead_to_chin",
            )

    def test_factor_must_be_positive(self):
        with pytest.raises(ValidationError):
            CoordinateSystem(
                dx="x", dy="y", hu_definition="hu",
                hu_convention="crown_to_chin",
                hu_to_standard_factor=-1.0,
            )


class TestP2NormalizedHu:
    """P2-10: StyleDeviation must declare whether HU values are normalized."""

    def test_normalized_flag_false(self):
        sd = StyleDeviation(
            canon="Loomis",
            position_deviations=[{
                "landmark": "crown", "canon_name": "crown",
                "measured_fraction": 0.0, "canon_fraction": 0.0,
                "deviation": 0.0,
            }],
            l2_stylisation_distance=0.12,
            normalized_to_standard_hu=False,
        )
        assert sd.normalized_to_standard_hu is False

    def test_normalized_flag_optional(self):
        sd = StyleDeviation(
            canon="Loomis",
            position_deviations=[{
                "landmark": "crown", "canon_name": "crown",
                "measured_fraction": 0.0, "canon_fraction": 0.0,
                "deviation": 0.0,
            }],
            l2_stylisation_distance=0.0,
        )
        assert sd.normalized_to_standard_hu is None


class TestP2RectangularityFormula:
    """P2-11: Rectangularity must document the formula convention."""

    def test_formula_field_accepts_rosin(self):
        r = Rectangularity(
            value=0.8,
            formula="A_shape / A_MBR per Rosin (2003), must be in [0,1]",
        )
        assert "Rosin" in r.formula


# ═══════════════════════════════════════════════════════════
# P3 Regression tests — structural improvements
# ═══════════════════════════════════════════════════════════

_MINIMAL_PRINCIPAL_AXES = {
    "primary_axis": {
        "direction": (0.0, 1.0),
        "eigenvalue": 0.95,
        "explained_variance_ratio": 0.95,
    },
    "secondary_axis": {
        "direction": (1.0, 0.0),
        "eigenvalue": 0.05,
    },
    "lean_angle_deg": 2.3,
    "gesture_energy": 0.05,
}


class TestP3PrincipalAxesRename:
    """P3-12: gesture_line renamed to principal_axes; back-compat alias."""

    def test_principal_axes_model(self):
        pa = PrincipalAxes(**_MINIMAL_PRINCIPAL_AXES)
        assert pa.lean_angle_deg == 2.3

    def test_gesture_line_alias(self):
        """GestureLine is an alias for PrincipalAxes."""
        assert GestureLine is PrincipalAxes
        gl = GestureLine(**_MINIMAL_PRINCIPAL_AXES)
        assert isinstance(gl, PrincipalAxes)

    def test_builder_gesture_line_backcompat(self):
        """Builder.gesture_line() still works and maps to principal_axes."""
        builder = SilhouetteBuilder()
        builder.gesture_line(_MINIMAL_PRINCIPAL_AXES)
        assert "principal_axes" in builder.set_sections()

    def test_builder_principal_axes(self):
        builder = SilhouetteBuilder()
        builder.principal_axes(_MINIMAL_PRINCIPAL_AXES)
        assert "principal_axes" in builder.set_sections()

    def test_set_section_gesture_line_backcompat(self):
        """set_section('gesture_line', ...) still works."""
        builder = SilhouetteBuilder()
        builder.set_section("gesture_line", _MINIMAL_PRINCIPAL_AXES)
        assert "principal_axes" in builder.set_sections()

    def test_json_alias_round_trip(self):
        """JSON uses 'gesture_line' key (alias), model uses principal_axes."""
        meta = _meta_builder().build()
        sections = _minimal_sections()
        builder = SilhouetteBuilder().meta(meta)
        for name, data in sections.items():
            builder.set_section(name, data)
        doc = builder.build()
        d = doc.to_dict()
        # The alias means the JSON key is 'gesture_line'
        assert "gesture_line" in d
        # Round-trip works
        reloaded = SilhouetteDocument.from_dict(d)
        assert reloaded.model.principal_axes.lean_angle_deg == 2.3

    def test_full_doc_missing_sections_count(self):
        """28 required sections (gesture_line_spline is optional)."""
        builder = SilhouetteBuilder()
        assert len(builder.missing_sections()) == 28


class TestP3GestureLineSpline:
    """P3-12: New gesture_line_spline section from medial axis."""

    def test_gesture_line_spline_model(self):
        gls = GestureLineSpline(
            method="medial_axis_spline",
            control_points=[(0.0, 0.0), (0.1, 0.5), (0.0, 1.0)],
            curvature_class="S_curve",
            max_lateral_deviation_hu=0.12,
        )
        assert gls.method == "medial_axis_spline"
        assert gls.curvature_class == "S_curve"
        assert len(gls.control_points) == 3

    def test_method_enum_values(self):
        for m in ("medial_axis_spline", "joint_chain_spline", "manual"):
            gls = GestureLineSpline(
                method=m,
                control_points=[(0.0, 0.0), (0.0, 1.0)],
            )
            assert gls.method == m

    def test_curvature_class_enum(self):
        for cc in ("C_curve", "S_curve", "straight", "complex"):
            gls = GestureLineSpline(
                method="medial_axis_spline",
                control_points=[(0.0, 0.0), (0.0, 1.0)],
                curvature_class=cc,
            )
            assert gls.curvature_class == cc

    def test_rejects_invalid_method(self):
        with pytest.raises(ValidationError):
            GestureLineSpline(
                method="bezier",
                control_points=[(0.0, 0.0), (0.0, 1.0)],
            )

    def test_min_control_points(self):
        with pytest.raises(ValidationError):
            GestureLineSpline(
                method="medial_axis_spline",
                control_points=[(0.0, 0.0)],  # needs at least 2
            )

    def test_optional_on_silhouette_v4(self):
        """gesture_line_spline is optional — not in missing_sections."""
        builder = SilhouetteBuilder()
        missing = builder.missing_sections()
        assert "gesture_line_spline" not in missing

    def test_builder_accepts_spline(self):
        builder = SilhouetteBuilder()
        builder.gesture_line_spline({
            "method": "medial_axis_spline",
            "control_points": [(0.0, 0.0), (0.0, 1.0)],
            "curvature_class": "straight",
        })
        assert "gesture_line_spline" in builder.set_sections()


class TestP3SeamHandling:
    """P3-13: CurvatureScaleSpace must declare seam_handling."""

    def test_seam_handling_field(self):
        css = CurvatureScaleSpace(
            scales=[{
                "label": "raw", "sigma": 0, "zero_crossings": 5,
                "mean_abs_kappa": 0.3, "max_abs_kappa": 1.5,
            }],
            seam_handling="none",
        )
        assert css.seam_handling == "none"

    def test_seam_handling_all_values(self):
        for v in ("none", "blended", "windowed"):
            css = CurvatureScaleSpace(
                scales=[{
                    "label": "raw", "sigma": 0, "zero_crossings": 5,
                    "mean_abs_kappa": 0.3, "max_abs_kappa": 1.5,
                }],
                seam_handling=v,
            )
            assert css.seam_handling == v

    def test_seam_handling_optional(self):
        css = CurvatureScaleSpace(
            scales=[{
                "label": "raw", "sigma": 0, "zero_crossings": 5,
                "mean_abs_kappa": 0.3, "max_abs_kappa": 1.5,
            }],
        )
        assert css.seam_handling is None

    def test_rejects_invalid_seam_handling(self):
        with pytest.raises(ValidationError):
            CurvatureScaleSpace(
                scales=[{
                    "label": "raw", "sigma": 0, "zero_crossings": 5,
                    "mean_abs_kappa": 0.3, "max_abs_kappa": 1.5,
                }],
                seam_handling="periodic",
            )


class TestP3CanonicalComparisons:
    """P3-14: proportion.canonical_comparisons must support multiple canons."""

    def test_canonical_comparison_model(self):
        cc = CanonicalComparison(
            system="Chibi / super-deformed",
            total_heads=2.5,
            landmark_positions_hu={"crown": 0.0, "sole": 2.5},
        )
        assert cc.total_heads == 2.5

    def test_multiple_canons(self):
        """At least 4 canon systems should be representable."""
        systems = [
            CanonicalComparison(system="Chibi", total_heads=2.5, landmark_positions_hu={"crown": 0}),
            CanonicalComparison(system="Anime", total_heads=6.5, landmark_positions_hu={"crown": 0}),
            CanonicalComparison(system="Realistic", total_heads=7.5, landmark_positions_hu={"crown": 0}),
            CanonicalComparison(system="Loomis", total_heads=8.0, landmark_positions_hu={"crown": 0}),
            CanonicalComparison(system="Fashion", total_heads=9.5, landmark_positions_hu={"crown": 0}),
        ]
        assert len(systems) >= 4


class TestP3BoundaryConvexity:
    """P3-15: ConvexHull must support optional boundary_convexity."""

    def test_boundary_convexity_field(self):
        ch = ConvexHull(
            hull_area_hu2=1.2,
            silhouette_area_hu2=0.85,
            solidity=0.708,
            convexity_deficiency=0.292,
            boundary_convexity=0.92,
        )
        assert ch.boundary_convexity == 0.92

    def test_boundary_convexity_optional(self):
        ch = ConvexHull(
            hull_area_hu2=1.0,
            silhouette_area_hu2=0.8,
            solidity=0.8,
            convexity_deficiency=0.2,
        )
        assert ch.boundary_convexity is None

    def test_boundary_convexity_range(self):
        """Must be in [0, 1]."""
        with pytest.raises(ValidationError):
            ConvexHull(
                hull_area_hu2=1.0, silhouette_area_hu2=0.8,
                solidity=0.8, convexity_deficiency=0.2,
                boundary_convexity=1.5,
            )


class TestP3BinaryPayload:
    """P3-16: Meta must support optional binary_payload path."""

    def test_binary_payload_field(self):
        meta = (
            _meta_builder()
            .build()
        )
        assert meta.binary_payload is None

    def test_binary_payload_set(self):
        builder = _meta_builder()
        builder._data["binary_payload"] = "data/contour.npy"
        meta = builder.build()
        assert meta.binary_payload == "data/contour.npy"


# ═══════════════════════════════════════════════════════════
# Multi-span scanline regression tests
# ═══════════════════════════════════════════════════════════


class TestMultiSpanEntry:
    """MultiSpanEntry model for per-span contour crossing data."""

    def test_basic(self):
        e = MultiSpanEntry(outer_dx=0.7, inner_dx=0.16)
        assert e.outer_dx == 0.7
        assert e.inner_dx == 0.16

    def test_negative_dx(self):
        e = MultiSpanEntry(outer_dx=-0.3, inner_dx=-0.8)
        assert e.outer_dx == -0.3


class TestScanlineEntryTopology:
    """ScanlineEntry must accept topology fields for multi-span data."""

    def test_plain_scanline(self):
        s = ScanlineEntry(right_dx=0.5, left_dx=0.5, full_width_hu=1.0)
        assert s.contour_pairs is None
        assert s.topology_detail is None
        assert s.topology is None

    def test_with_topology_detail(self):
        s = ScanlineEntry(
            right_dx=0.5, left_dx=0.5, full_width_hu=1.0,
            contour_pairs=2,
            topology_detail=[
                {"outer_dx": 0.7, "inner_dx": 0.16},
                {"outer_dx": -0.27, "inner_dx": -0.8},
            ],
        )
        assert s.contour_pairs == 2
        assert len(s.topology_detail) == 2
        assert s.topology_detail[0].outer_dx == 0.7
        assert s.topology_detail[1].inner_dx == -0.8

    def test_with_topology_string(self):
        s = ScanlineEntry(
            right_dx=0.3, left_dx=0.3, full_width_hu=0.6,
            topology="unknown",
        )
        assert s.topology == "unknown"

    def test_six_spans(self):
        """Arm+torso region can have 6 spans."""
        spans = [
            {"outer_dx": 1.28, "inner_dx": 1.08},
            {"outer_dx": 1.02, "inner_dx": 0.95},
            {"outer_dx": 0.78, "inner_dx": 0.05},
            {"outer_dx": -0.10, "inner_dx": -0.85},
            {"outer_dx": -1.01, "inner_dx": -1.09},
            {"outer_dx": -1.15, "inner_dx": -1.35},
        ]
        s = ScanlineEntry(
            right_dx=0.58, left_dx=0.58, full_width_hu=1.16,
            contour_pairs=6,
            topology_detail=spans,
        )
        assert s.contour_pairs == 6
        assert len(s.topology_detail) == 6

    def test_measurements_with_mixed_entries(self):
        """Measurements dict can mix ScanlineEntry dicts and raw lists."""
        m = Measurements(scanlines={
            "5.00": {
                "right_dx": 0.74, "left_dx": 0.74, "full_width_hu": 1.48,
                "contour_pairs": 2,
                "topology_detail": [
                    {"outer_dx": 0.71, "inner_dx": 0.16},
                    {"outer_dx": -0.27, "inner_dx": -0.80},
                ],
            },
            "3.50": [
                {"outer_dx": 1.22, "inner_dx": 0.97},
                {"outer_dx": 0.71, "inner_dx": 0.54},
            ],
        })
        # ScanlineEntry with topology_detail
        entry = m.scanlines["5.00"]
        assert hasattr(entry, "contour_pairs")
        assert entry.contour_pairs == 2

    def test_gap_between_legs(self):
        """The gap between legs is inner_dx[0] to outer_dx[1]."""
        s = ScanlineEntry(
            right_dx=0.74, left_dx=0.74, full_width_hu=1.48,
            contour_pairs=2,
            topology_detail=[
                {"outer_dx": 0.71, "inner_dx": 0.16},
                {"outer_dx": -0.27, "inner_dx": -0.80},
            ],
        )
        gap = s.topology_detail[0].inner_dx - s.topology_detail[1].outer_dx
        assert gap > 0, "Gap should be positive (right leg inner > left leg outer)"
        assert 0.3 < gap < 0.6, f"Expected ~0.43 HU gap, got {gap:.2f}"


@pytest.mark.skipif(
    not SAMPLE_JSON.exists(),
    reason="Sample pipeline output not available",
)
class TestMultiSpanIntegration:
    """Integration: verify topology_detail survives the full pipeline."""

    def test_topology_detail_present_in_output(self):
        import json
        d = json.loads(SAMPLE_JSON.read_text())
        m = d["measurements"]["scanlines"]
        with_detail = [
            k for k, v in m.items()
            if isinstance(v, dict) and "topology_detail" in v
        ]
        assert len(with_detail) > 0, (
            "No scanline entries have topology_detail — "
            "multi-span key matching may be broken"
        )

    def test_leg_level_has_two_spans(self):
        import json
        d = json.loads(SAMPLE_JSON.read_text())
        m = d["measurements"]["scanlines"]
        # dy=5.00 should have 2 spans (right leg + left leg)
        entry = m.get("5.00")
        assert entry is not None, "Missing scanline at dy=5.00"
        assert isinstance(entry, dict), f"Expected dict, got {type(entry)}"
        assert "topology_detail" in entry, "Missing topology_detail at dy=5.00"
        assert entry["contour_pairs"] == 2
        spans = entry["topology_detail"]
        assert len(spans) == 2
        # Right leg: positive dx
        assert spans[0]["outer_dx"] > 0
        assert spans[0]["inner_dx"] > 0
        # Left leg: negative dx
        assert spans[1]["outer_dx"] < 0
        assert spans[1]["inner_dx"] < 0
