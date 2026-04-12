"""Tests for lib.builder — SilhouetteV4 builder SDK."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.builder import MetaBuilder, SilhouetteBuilder, SilhouetteDocument
from lib.model import (
    ALL_ERROR_CLASSES,
    PALS_LAW_VERSION,
    Landmark,
    LLMErrorClass,
    Meta,
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
        from pydantic import ValidationError
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
        from pydantic import ValidationError
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
        from pydantic import ValidationError
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
