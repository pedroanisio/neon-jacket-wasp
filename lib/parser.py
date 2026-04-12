"""
Parser for v2 silhouette extraction archives.

Transforms a v2 extraction ZIP (JSON + PNG) into a validated
``SilhouetteV4`` document by preprocessing the v2 format and
running the ``generate_v4.py`` enrichment pipeline.

Usage::

    from lib.parser import parse_zip

    doc = parse_zip("data/input/056663ee830a4717ae470b1a9cd6c46e.zip")
    print(doc.model.meta.schema_version)
    doc.to_json("output_v4.json")
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from lib.builder import SilhouetteDocument

__all__ = ["parse_v2_json", "parse_zip"]

_REPO_ROOT = Path(__file__).resolve().parent.parent
_GENERATE_SCRIPT = _REPO_ROOT / "scripts" / "generate_v4.py"

# ──────────────────────────────────────────────────────────
# Right-side contour boundary (matches generate_v4.py)
# ──────────────────────────────────────────────────────────

_RIGHT_END = 727

# ──────────────────────────────────────────────────────────
# Landmark descriptions for v2 → v4 upgrade
# ──────────────────────────────────────────────────────────

_LANDMARK_DESCRIPTIONS: dict[str, str] = {
    "crown": "Top of the head (minimum dy on right-side contour)",
    "head_peak": "Widest point of the head",
    "neck_valley": "Narrowest point at the neck",
    "shoulder_peak": "Widest point at shoulder level",
    "waist_valley": "Narrowest point of the waist",
    "hip_peak": "Widest point at hip level",
    "knee_valley": "Narrowest point at knee level",
    "ankle_valley": "Narrowest point at ankle level",
    "sole": "Bottom of the foot (maximum dy on right-side contour)",
}

# ──────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────


def parse_zip(
    zip_path: str | Path,
    *,
    strict: bool = False,
) -> SilhouetteDocument:
    """Parse a v2 extraction ZIP into a validated v4 document.

    The ZIP must contain a ``.json`` file (v2 extraction) and
    optionally a ``.png`` source image.

    Parameters
    ----------
    zip_path
        Path to the v2 extraction ZIP file.
    strict
        If ``True``, enforce all Pydantic constraints.  If ``False``
        (default), load in lenient mode (tolerates minor floating-point
        artifacts like negative widths from interpolation).

    Returns
    -------
    SilhouetteDocument
    """
    zip_path = Path(zip_path)
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp)

        json_files = list(Path(tmp).glob("*.json"))
        if not json_files:
            msg = f"No JSON file found in {zip_path}"
            raise FileNotFoundError(msg)

        return parse_v2_json(json_files[0], strict=strict)


def parse_v2_json(
    v2_path: str | Path,
    *,
    strict: bool = False,
) -> SilhouetteDocument:
    """Parse a v2 extraction JSON into a validated v4 document.

    Preprocesses the v2 format, runs the ``generate_v4.py`` enrichment
    pipeline, and validates the output through the Pydantic model.

    Parameters
    ----------
    v2_path
        Path to the v2 JSON file.
    strict
        See :func:`parse_zip`.

    Returns
    -------
    SilhouetteDocument
    """
    v2_path = Path(v2_path)
    raw = json.loads(v2_path.read_text(encoding="utf-8"))
    preprocessed = _preprocess_v2(raw)

    return _run_pipeline(preprocessed, strict=strict)


# ──────────────────────────────────────────────────────────
# V2 → intermediate preprocessing
# ──────────────────────────────────────────────────────────


def _preprocess_v2(data: dict[str, Any]) -> dict[str, Any]:
    """Convert v2 extraction dict to the format generate_v4.py expects."""
    # Deep copy to avoid mutating the caller's data.
    data = json.loads(json.dumps(data))

    _add_crown_sole(data)
    _add_landmark_descriptions(data)
    _strip_v2_landmark_fields(data)
    _restructure_strokes(data)
    _restructure_measurements(data)
    _restructure_symmetry(data)
    _restructure_parametric(data)
    _restructure_meta(data)
    _restructure_proportion(data)

    return data


def _add_crown_sole(data: dict[str, Any]) -> None:
    """Derive crown and sole landmarks from right-side contour extrema."""
    contour = data["contour"]
    right_pts = contour[:_RIGHT_END]

    names = {lm["name"] for lm in data["landmarks"]}

    if "crown" not in names:
        crown_idx = min(range(len(right_pts)), key=lambda i: right_pts[i][1])
        data["landmarks"].insert(
            0,
            {
                "name": "crown",
                "dy": round(right_pts[crown_idx][1], 4),
                "dx": round(right_pts[crown_idx][0], 4),
            },
        )

    if "sole" not in names:
        sole_idx = max(range(len(right_pts)), key=lambda i: right_pts[i][1])
        data["landmarks"].append(
            {
                "name": "sole",
                "dy": round(right_pts[sole_idx][1], 4),
                "dx": round(right_pts[sole_idx][0], 4),
            }
        )


def _add_landmark_descriptions(data: dict[str, Any]) -> None:
    """Add ``description`` field to landmarks missing it."""
    for lm in data["landmarks"]:
        if "description" not in lm:
            lm["description"] = _LANDMARK_DESCRIPTIONS.get(
                lm["name"],
                f"Landmark: {lm['name'].replace('_', ' ')}",
            )


# Fields present in v2 landmarks but forbidden by the v4 schema
# (additionalProperties: false).
_V2_LANDMARK_EXTRA_FIELDS = {"index", "band_constrained"}


def _strip_v2_landmark_fields(data: dict[str, Any]) -> None:
    """Remove v2-only fields that the v4 schema forbids."""
    for lm in data["landmarks"]:
        for field in _V2_LANDMARK_EXTRA_FIELDS:
            lm.pop(field, None)


def _restructure_strokes(data: dict[str, Any]) -> None:
    """Convert bare point arrays to structured stroke objects."""
    new_strokes: list[dict[str, Any]] = []
    for i, stroke in enumerate(data["strokes"]):
        if isinstance(stroke, list) and stroke and isinstance(stroke[0], list):
            pts = stroke
            dx_vals = [p[0] for p in pts]
            dy_vals = [p[1] for p in pts]
            new_strokes.append(
                {
                    "id": i,
                    "region": "unknown",
                    "n_points": len(pts),
                    "bbox": {
                        "dx_min": round(min(dx_vals), 4),
                        "dx_max": round(max(dx_vals), 4),
                        "dy_min": round(min(dy_vals), 4),
                        "dy_max": round(max(dy_vals), 4),
                    },
                    "points": pts,
                }
            )
        else:
            new_strokes.append(stroke)
    data["strokes"] = new_strokes


def _restructure_measurements(data: dict[str, Any]) -> None:
    """Wrap flat measurements dict in ``{scanlines: ...}``."""
    meas = data["measurements"]
    if "scanlines" not in meas:
        data["measurements"] = {"scanlines": meas}


def _restructure_symmetry(data: dict[str, Any]) -> None:
    """Wrap flat symmetry dict in ``{samples: ...}``."""
    sym = data["symmetry"]
    if "samples" not in sym:
        data["symmetry"] = {"samples": sym}


# v2 parametric fields not in the v4 schema (additionalProperties: false).
_V2_PARAMETRIC_TOP_EXTRA = {
    "max_error",
    "mean_error",
    "n_original_points",
    "n_parameters",
    "compression_ratio",
}


def _restructure_parametric(data: dict[str, Any]) -> None:
    """Add ``dy_range`` and strip v2-only fields from parametric."""
    param = data["parametric"]
    lm_dict = {lm["name"]: lm for lm in data["landmarks"]}

    for seg in param["segments"]:
        if "dy_range" not in seg:
            start = lm_dict.get(seg["landmark_start"])
            end = lm_dict.get(seg["landmark_end"])
            if start and end:
                seg["dy_range"] = [start["dy"], end["dy"]]
            elif "coeffs_dy" in seg:
                seg["dy_range"] = [seg["coeffs_dy"][0], seg["coeffs_dy"][-1]]
        # coeffs_dy is a v2 field (v4 uses only coeffs_dx with dy as param)
        seg.pop("coeffs_dy", None)

    # Strip top-level v2 extras
    for field in _V2_PARAMETRIC_TOP_EXTRA:
        param.pop(field, None)


def _restructure_meta(data: dict[str, Any]) -> None:
    """Convert v2 flat meta fields to v4 structured objects."""
    meta = data["meta"]

    # mirror: bool → {applied, semantics}
    if isinstance(meta.get("mirror"), bool):
        applied = meta.pop("mirror")
        meta["mirror"] = {
            "applied": applied,
            "semantics": "right side mirrored to left" if applied else "none",
        }

    # Flat score_* → scores object
    if "scores" not in meta:
        meta["scores"] = {
            "scanline": meta.pop("score_scanline", 0.0),
            "floodfill": meta.pop("score_floodfill", 0.0),
            "direct": meta.pop("score_direct", 0.0),
            "margin": meta.pop("score_margin", 0.0),
        }

    # Flat timing → timing object
    if "timing" not in meta:
        meta["timing"] = {
            "algo_elapsed_ms": meta.pop("algo_elapsed_ms", 0.0),
            "total_elapsed_ms": meta.pop("total_elapsed_ms", 0.0),
        }

    # coordinate_system (required by v4)
    if "coordinate_system" not in meta:
        meta["coordinate_system"] = {
            "dx": "horizontal distance from midline, right positive",
            "dy": "vertical position, 0=crown, increasing downward",
            "hu_definition": "head-units: 1 HU = crown-to-sole / head_count",
        }

    # Strip v2-only fields from classification sub-objects that
    # the v4 schema forbids (additionalProperties: false).
    cls = meta.get("classification", {})

    hair = cls.get("hair_symmetry")
    if isinstance(hair, dict) and "delta_hu" in hair:
        # v2 uses delta_hu; v4 schema uses raw_delta_hu
        hair.setdefault("raw_delta_hu", hair.pop("delta_hu"))

    annotations = cls.get("annotations")
    if isinstance(annotations, dict):
        label = annotations.get("label", "")
        if label not in {"single_figure", "multi_figure"}:
            annotations["label"] = "single_figure"


def _restructure_proportion(data: dict[str, Any]) -> None:
    """Rename v2 proportion fields to v4 schema names."""
    prop = data["proportion"]
    lm_dict = {lm["name"]: lm for lm in data["landmarks"]}

    # head_count → head_count_total
    if "head_count" in prop and "head_count_total" not in prop:
        prop["head_count_total"] = prop.pop("head_count")

    crown_dy = lm_dict["crown"]["dy"]
    sole_dy = lm_dict["sole"]["dy"]
    fig_height = sole_dy - crown_dy

    if "figure_height_total_hu" not in prop:
        prop["figure_height_total_hu"] = round(fig_height, 4)

    if "head_height_hu" not in prop and prop.get("head_count_total", 0) > 0:
        prop["head_height_hu"] = round(fig_height / prop["head_count_total"], 4)

    # standardized_vector is not in v4 schema
    prop.pop("standardized_vector", None)


# ──────────────────────────────────────────────────────────
# Pipeline execution
# ──────────────────────────────────────────────────────────


def _run_pipeline(
    data: dict[str, Any],
    *,
    strict: bool = False,
) -> SilhouetteDocument:
    """Write preprocessed data, run generate_v4.py, return document."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        v2_path = tmp_dir / "input.json"
        v4_path = tmp_dir / "output.json"

        v2_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        env = {**os.environ, "PYTHONPATH": str(_REPO_ROOT)}
        result = subprocess.run(  # noqa: S603
            [sys.executable, str(_GENERATE_SCRIPT), str(v2_path), str(v4_path)],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )

        if result.returncode != 0:
            msg = f"generate_v4.py failed (exit {result.returncode}):\n{result.stderr.strip()}"
            raise RuntimeError(msg)

        return SilhouetteDocument.from_json(v4_path, strict=strict)
