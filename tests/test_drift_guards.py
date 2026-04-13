"""Drift-risk regression tests.

These tests guard against silent desynchronisation between the source-of-truth
(lib/model.py) and its unguarded dependents: the frontend JSX renderers, the
hardcoded demo data snapshot, the formal specification document, the README,
the test fixtures, and the shared RIGHT_END constant.

Each test corresponds to a CRITICAL or HIGH finding from the drift-risk map.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from lib.model import SilhouetteV4

# ── paths ────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schema" / "silhouette_v4.schema.json"
SPEC_PATH = ROOT / "docs" / "SPEC-model.md"
FRONTEND_DIR = ROOT / "frontend"

LOADER_JSX = FRONTEND_DIR / "silhouette_loader.jsx"
ANALYSIS_JSX = FRONTEND_DIR / "v4_silhouette_analysis.jsx"
RENDER_JSX = FRONTEND_DIR / "silhouette_render.jsx"
PIPELINE_JSX = FRONTEND_DIR / "stick_to_mesh_pipeline.jsx"


# ── helpers ──────────────────────────────────────────────────────────────


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _resolve_ref(root: dict, ref_str: str) -> dict:
    """Resolve a JSON Schema ``$ref`` string like ``#/$defs/Foo``."""
    name = ref_str.rsplit("/", 1)[-1]
    return root.get("$defs", {}).get(name, {})


def _resolve_node(root: dict, node: dict) -> dict:
    """Follow ``$ref`` and ``anyOf`` wrappers to get the concrete schema node."""
    if "$ref" in node:
        node = _resolve_ref(root, node["$ref"])
    if "anyOf" in node:
        for option in node["anyOf"]:
            if "$ref" in option:
                return _resolve_ref(root, option["$ref"])
            if option.get("type") == "object":
                return option
            if "items" in option:
                return option
            if option.get("type") == "array":
                return option
    return node


def _schema_path_exists(root: dict, dotted_path: str) -> bool:
    """Return True if *dotted_path* (e.g. ``body_regions.regions.name``)
    resolves through the JSON Schema, traversing ``$ref``, ``items``, and
    ``anyOf`` as needed.
    """
    parts = dotted_path.split(".")
    node: dict = root

    for part in parts:
        node = _resolve_node(root, node)

        # Try direct property lookup.
        props = node.get("properties", {})
        if part in props:
            node = props[part]
            continue

        # Try array items → property.
        items = node.get("items", {})
        if items:
            items = _resolve_node(root, items)
            props = items.get("properties", {})
            if part in props:
                node = props[part]
                continue

        # Try anyOf array items (nullable arrays).
        if "anyOf" in node:
            found = False
            for option in node["anyOf"]:
                opt = _resolve_node(root, option)
                items = opt.get("items", {})
                if items:
                    items = _resolve_node(root, items)
                    if part in items.get("properties", {}):
                        node = items["properties"][part]
                        found = True
                        break
            if found:
                continue

        return False
    return True


# ═════════════════════════════════════════════════════════════════════════
# CRITICAL #1 / #4 — Frontend JSX field references must resolve in the
# JSON schema generated from lib/model.py.
#
# If a field is renamed or removed in model.py, `make schema` updates the
# JSON schema.  These tests catch any JSX file still referencing the old
# field name.
# ═════════════════════════════════════════════════════════════════════════

# Every dotted path that silhouette_loader.jsx ``normalize()`` reads from
# the raw v4 JSON document.  Paths are relative to the document root.
# Maintaining this list by hand is intentional: it forces an explicit
# decision when the frontend starts consuming a new field.

LOADER_FIELD_PATHS: list[str] = [
    # meta
    "meta.classification",
    "meta.schema_version",
    "meta.mirror",
    # contour / strokes / landmarks (top-level)  # noqa: ERA001
    "contour",
    "strokes",
    "landmarks",
    # landmarks item fields
    "landmarks.name",
    "landmarks.description",
    "landmarks.dy",
    "landmarks.dx",
    # strokes item fields
    "strokes.points",
    "strokes.region",
    # proportion
    "proportion.head_count_total",
    "proportion.segment_ratios",
    "proportion.width_ratios",
    "proportion.composite_ratios",
    "proportion.canonical_comparisons",
    # body_regions
    "body_regions.regions",
    "body_regions.regions.name",
    "body_regions.regions.dy_start",
    "body_regions.regions.dy_end",
    # area_profile
    "area_profile.per_region",
    "area_profile.per_region.name",
    "area_profile.per_region.height_hu",
    "area_profile.per_region.area_hu2",
    "area_profile.per_region.area_fraction",
    "area_profile.per_region.mean_full_width_hu",
    # width_profile
    "width_profile.samples",
    "width_profile.samples.dy",
    "width_profile.samples.full_width",
    # style_deviation
    "style_deviation.canon",
    "style_deviation.figure_head_count",
    "style_deviation.canon_head_count",
    "style_deviation.l2_stylisation_distance",
    "style_deviation.position_deviations",
    "style_deviation.position_deviations.landmark",
    "style_deviation.position_deviations.measured_fraction",
    "style_deviation.position_deviations.canon_fraction",
    "style_deviation.position_deviations.deviation",
    "style_deviation.width_deviations",
    "style_deviation.width_deviations.feature",
    "style_deviation.width_deviations.measured",
    "style_deviation.width_deviations.canon",
    "style_deviation.width_deviations.deviation",
    # shape_complexity
    "shape_complexity",
    # gesture_line (alias of principal_axes)
    "gesture_line.lean_angle_deg",
    "gesture_line.lean_interpretation",
    "gesture_line.contrapposto_score",
    "gesture_line.contrapposto_interpretation",
    "gesture_line.gesture_energy",
    "gesture_line.centroid",
    # volumetric_estimates
    "volumetric_estimates.cylindrical",
    "volumetric_estimates.ellipsoidal",
    "volumetric_estimates.pappus",
    # convex_hull
    "convex_hull.solidity",
    "convex_hull.hull_area_hu2",
    "convex_hull.silhouette_area_hu2",
    "convex_hull.negative_space_area_hu2",
    # biomechanics
    "biomechanics.canonical_height_cm",
    "biomechanics.scale_cm_per_hu",
    "biomechanics.whole_body_com",
    # medial_axis
    "medial_axis.main_axis.samples",
    "medial_axis.main_axis.samples.dy",
    "medial_axis.main_axis.samples.inscribed_radius",
    # measurements
    "measurements.scanlines",
]


@pytest.mark.parametrize("path", LOADER_FIELD_PATHS)
def test_loader_field_path_exists_in_schema(path: str) -> None:
    """silhouette_loader.jsx field references must resolve in the schema."""
    schema = _load_schema()
    assert _schema_path_exists(schema, path), (
        f"Field path '{path}' used by silhouette_loader.jsx "
        f"does not resolve in {SCHEMA_PATH.name}. "
        f"Was a field renamed or removed in lib/model.py?"
    )


def test_loader_jsx_raw_field_access_covered() -> None:
    """Every ``raw.<section>`` access in normalize() must appear in the
    declared LOADER_FIELD_PATHS list.

    This catches newly added ``raw.xxx`` references in the JSX that were
    not registered in the contract list.
    """
    source = LOADER_JSX.read_text(encoding="utf-8")
    # Extract the normalize() function body (ends at the next top-level function).
    match = re.search(r"function normalize\(raw\)\s*\{", source)
    assert match, "normalize() function not found in silhouette_loader.jsx"
    start = match.start()
    # Find closing brace at same indentation level.
    brace_depth = 0
    end = start
    for i, ch in enumerate(source[start:], start=start):
        if ch == "{":
            brace_depth += 1
        elif ch == "}":
            brace_depth -= 1
            if brace_depth == 0:
                end = i + 1
                break
    body = source[start:end]

    # Find raw.XXXX references (first two segments: raw.section.field).
    raw_accesses = set(re.findall(r"raw\.([a-z_]+(?:\.[a-z_]+)?)", body))

    # Build the set of first-two-segment prefixes from our declared paths.
    declared_prefixes: set[str] = set()
    for p in LOADER_FIELD_PATHS:
        parts = p.split(".")
        declared_prefixes.add(parts[0])
        if len(parts) >= 2:  # noqa: PLR2004
            declared_prefixes.add(f"{parts[0]}.{parts[1]}")

    missing = raw_accesses - declared_prefixes
    assert not missing, (
        f"New raw.* field accesses found in normalize() that are not "
        f"declared in LOADER_FIELD_PATHS: {sorted(missing)}. "
        f"Add the paths to the contract list."
    )


# ═════════════════════════════════════════════════════════════════════════
# CRITICAL #2 — Hardcoded snapshot in v4_silhouette_analysis.jsx
#
# The ``const D = {{...}}`` object is a frozen demo dataset.  These tests
# assert its top-level section keys and nested structure match what the
# current schema expects, so that a schema change surfaces as a test
# failure rather than silently producing a stale demo.
# ═════════════════════════════════════════════════════════════════════════

# Mapping from abbreviated keys in const D to the schema section names.
# This is the normalization contract: silhouette_loader.jsx normalize()
# produces objects with these abbreviated keys from the full schema names.
_ABBREVIATED_TO_SCHEMA: dict[str, str] = {
    "c": "contour",
    "l": "landmarks",
    "wp": "width_profile",
    "ar": "area_profile",
    "sd": "style_deviation",
    "sc": "shape_complexity",
    "gl": "gesture_line",
    "pr": "proportion",
    "vol": "volumetric_estimates",
    "hull": "convex_hull",
    "br": "body_regions",
    "bio": "biomechanics",
    "med": "medial_axis",
}


def _extract_const_d() -> dict:
    """Parse the ``const D = {...};`` JSON object from the JSX source."""
    source = ANALYSIS_JSX.read_text(encoding="utf-8")
    match = re.search(r"const\s+D\s*=\s*(\{.+?\});", source, re.DOTALL)
    assert match, "const D = {...}; not found in v4_silhouette_analysis.jsx"
    raw = match.group(1)
    # Keys are quoted strings, but numbers use bare decimals (.007 instead
    # of 0.007) which is valid JS but not valid JSON.  Prefix with 0.
    raw = re.sub(r"(?<![0-9])\.(\d)", r"0.\1", raw)
    return json.loads(raw)


def test_snapshot_has_all_expected_section_keys() -> None:
    """const D must contain every abbreviated section key."""
    d = _extract_const_d()
    missing = set(_ABBREVIATED_TO_SCHEMA.keys()) - set(d.keys())
    assert not missing, (
        f"const D is missing section keys: {missing}. "
        f"Update the snapshot when the schema changes."
    )


def test_snapshot_has_no_unknown_section_keys() -> None:
    """const D must not contain keys outside the known abbreviation set."""
    d = _extract_const_d()
    unknown = set(d.keys()) - set(_ABBREVIATED_TO_SCHEMA.keys())
    assert not unknown, (
        f"const D contains unexpected keys: {unknown}. "
        f"Register them in _ABBREVIATED_TO_SCHEMA if intentional."
    )


def test_snapshot_sections_map_to_valid_schema_sections() -> None:
    """Every abbreviated key must map to a real schema section."""
    schema = _load_schema()
    schema_sections = set(schema.get("properties", {}).keys())
    for abbrev, section in _ABBREVIATED_TO_SCHEMA.items():
        assert section in schema_sections, (
            f"Abbreviated key '{abbrev}' maps to '{section}' which is "
            f"not a top-level property in the JSON schema. "
            f"Was the section renamed or removed?"
        )


def test_snapshot_landmark_fields_match_schema() -> None:
    """Landmark entries in const D must use field names from the schema."""
    schema = _load_schema()
    landmark_ref = schema["properties"]["landmarks"]["items"]
    landmark_schema = _resolve_ref(schema, landmark_ref["$ref"])
    schema_fields = set(landmark_schema["properties"].keys())

    d = _extract_const_d()
    # Abbreviated landmark keys: n→name, d→description, dy→dy, dx→dx.
    abbrev_to_full = {"n": "name", "d": "description", "dy": "dy", "dx": "dx"}
    sample = d["l"][0]
    for abbrev_key in sample:
        full_key = abbrev_to_full.get(abbrev_key, abbrev_key)
        assert full_key in schema_fields, (
            f"Landmark abbreviated key '{abbrev_key}' (→ '{full_key}') "
            f"not found in Landmark schema fields: {schema_fields}"
        )


def test_snapshot_contour_is_nonempty_point_array() -> None:
    """const D.c must be a non-empty array of [dx, dy] pairs."""
    d = _extract_const_d()
    assert isinstance(d["c"], list)
    assert len(d["c"]) > 0
    for pt in d["c"][:5]:
        assert isinstance(pt, list)  # noqa: S101
        assert len(pt) == 2  # noqa: PLR2004, S101


def test_snapshot_abbreviation_map_covers_all_required_sections() -> None:
    """Every required SilhouetteV4 section that normalize() exposes must
    have an abbreviation entry.

    If a new required section is added to the model, this test fails —
    forcing a conscious decision about whether the demo snapshot and the
    abbreviation map need updating.
    """
    # Sections that normalize() currently exposes (the ones that appear
    # in the rendering pipeline).  Not every schema section needs to be
    # in the demo — but any section the renderer touches must be mapped.
    rendered_sections = set(_ABBREVIATED_TO_SCHEMA.values())
    schema = _load_schema()
    all_sections = set(schema.get("properties", {}).keys())

    # Sections intentionally excluded from the demo renderer.
    excluded_from_demo = {
        "meta",
        "contour",  # handled as "c" already
        "midline",
        "strokes",
        "symmetry",
        "measurements",
        "parametric",
        "candidates",
        "curvature",
        "cross_section_topology",
        "fourier_descriptors",
        "contour_normals",
        "shape_vector",
        "hu_moments",
        "turning_function",
        "curvature_scale_space",
        "gesture_line_spline",
    }
    expected = all_sections - excluded_from_demo - {"contour"}
    # "contour" is mapped as "c"
    expected.add("contour")

    missing = (expected & all_sections) - rendered_sections - excluded_from_demo
    assert not missing, (
        f"Schema sections {missing} are not covered by either the "
        f"abbreviation map or the exclusion list. Add them to "
        f"_ABBREVIATED_TO_SCHEMA or excluded_from_demo."
    )


# ═════════════════════════════════════════════════════════════════════════
# CRITICAL #3 — SPEC-model.md must document every model field
#
# The formal specification is hand-maintained.  These tests assert that
# every field in the Pydantic model hierarchy appears somewhere in the
# spec.  This catches the most common drift: a new field added to
# model.py that the spec never mentions.
# ═════════════════════════════════════════════════════════════════════════


def _collect_section_model_classes(model: type) -> dict[str, type]:
    """Return a mapping of field-name → annotation-type for every
    top-level SilhouetteV4 field whose annotation is a Pydantic model.
    """
    result: dict[str, type] = {}
    for name, fi in model.model_fields.items():
        ann = fi.annotation
        # Unwrap Optional (X | None → X).
        origin = getattr(ann, "__origin__", None)
        if origin is not None:
            for arg in getattr(ann, "__args__", ()):
                if isinstance(arg, type) and hasattr(arg, "model_fields"):
                    result[name] = arg
                    break
                # Handle list[ModelType] generics.  # noqa: ERA001
                inner_origin = getattr(arg, "__origin__", None)
                if inner_origin is not None:
                    for inner_arg in getattr(arg, "__args__", ()):
                        if isinstance(inner_arg, type) and hasattr(inner_arg, "model_fields"):
                            result[name] = inner_arg
                            break
        elif isinstance(ann, type) and hasattr(ann, "model_fields"):
            result[name] = ann
    return result


def test_spec_documents_all_silhouette_v4_fields() -> None:
    """Every top-level SilhouetteV4 field name (or its alias) and every
    direct field of the section model classes must appear in
    SPEC-model.md as a backtick-quoted identifier.

    This catches new fields added to model.py that the spec never
    mentions, without requiring every deeply nested leaf field to be
    individually documented.
    """
    spec_text = SPEC_PATH.read_text(encoding="utf-8")

    # 1. All top-level field names / aliases.
    missing: list[str] = []
    for name, fi in SilhouetteV4.model_fields.items():
        candidates = [name]
        if fi.alias:
            candidates.append(fi.alias)
        if not any(f"`{c}`" in spec_text for c in candidates):
            missing.append(name)

    # 2. Direct fields of each section model class.
    section_models = _collect_section_model_classes(SilhouetteV4)
    for section_name, model_cls in section_models.items():
        for field_name in model_cls.model_fields:
            pattern = rf"`{re.escape(field_name)}`"
            if not re.search(pattern, spec_text):
                missing.append(f"{section_name}.{field_name}")

    assert not missing, (
        f"{len(missing)} model field(s) not documented in SPEC-model.md: "
        f"{missing}. Update the spec when adding or renaming fields."
    )


def test_spec_section_count_matches_model() -> None:
    """The §8.1 table in SPEC-model.md must list the same number of
    required sections as SilhouetteV4 has required fields.
    """
    required_count = sum(
        1 for fi in SilhouetteV4.model_fields.values() if fi.is_required()
    )
    spec_text = SPEC_PATH.read_text(encoding="utf-8")

    # Count numbered rows in the §8.1 table: lines matching "| <digit> |".
    table_rows = re.findall(r"^\|\s*\d+\s*\|", spec_text, re.MULTILINE)
    assert len(table_rows) == required_count, (
        f"SPEC-model.md §8.1 table has {len(table_rows)} numbered rows, "
        f"but SilhouetteV4 has {required_count} required fields. "
        f"Update the spec table."
    )


def test_spec_documents_all_top_level_field_names() -> None:
    """Every top-level SilhouetteV4 field (by name or alias) must appear
    as a backtick-quoted identifier in the §8.1 table.
    """
    spec_text = SPEC_PATH.read_text(encoding="utf-8")
    # Extract the §8.1 table region.
    match = re.search(
        r"###\s+8\.1\.\s+.+?\n(.*?)(?=\n###|\Z)", spec_text, re.DOTALL
    )
    assert match, "§8.1 section not found in SPEC-model.md"
    table_text = match.group(1)

    missing: list[str] = []
    for field_name, field_info in SilhouetteV4.model_fields.items():
        # Check both the Python name and the alias.
        names_to_check = [field_name]
        if field_info.alias:
            names_to_check.append(field_info.alias)

        found = any(f"`{n}`" in table_text for n in names_to_check)
        if not found:
            missing.append(field_name)

    assert not missing, (
        f"Top-level fields not found in §8.1 table: {missing}. "
        f"Update the spec."
    )


# ═════════════════════════════════════════════════════════════════════════
# Schema generation sanity — ensures `make schema` output stays current
# ═════════════════════════════════════════════════════════════════════════


def test_schema_file_matches_model() -> None:
    """The committed JSON schema must match what model.py would generate.

    This catches forgotten ``make schema`` runs.
    """
    on_disk = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    generated = SilhouetteV4.model_json_schema(by_alias=True)

    # Ignore the $comment field (build metadata).
    on_disk.pop("$comment", None)
    generated.pop("$comment", None)

    assert on_disk == generated, (
        "schema/silhouette_v4.schema.json is out of date with lib/model.py. "
        "Run `make schema` to regenerate."
    )


# ═════════════════════════════════════════════════════════════════════════
# HIGH #4 — silhouette_render.jsx and stick_to_mesh_pipeline.jsx
#
# These renderers embed hardcoded DATA objects whose field structure must
# stay aligned with the schema.  The abbreviated keys map back to v4
# schema sections, similar to the CRITICAL #2 snapshot tests.
# ═════════════════════════════════════════════════════════════════════════

# silhouette_render.jsx DATA keys and their schema mappings.
# DATA has: c (contour), s (strokes), l (landmarks), p (proportions), m (meta classification).
_RENDER_ABBREVIATED_TO_SCHEMA: dict[str, str] = {
    "c": "contour",
    "s": "strokes",
    "l": "landmarks",
    "p": "proportion",
}

# Within DATA.l[*], abbreviated keys map to Landmark schema fields.
_RENDER_LANDMARK_ABBREV: dict[str, str] = {
    "n": "name",
    "d": "description",
    "dy": "dy",
    "dx": "dx",
}

# Within DATA.s[*], abbreviated keys map to Stroke schema fields.
_RENDER_STROKE_ABBREV: dict[str, str] = {
    "r": "region",
    "p": "points",
}

# Within DATA.p, abbreviated keys map to Proportion schema fields.
_RENDER_PROPORTION_ABBREV: dict[str, str] = {
    "hc": "head_count_total",
    "sr": "segment_ratios",
    "wr": "width_ratios",
}


def _extract_render_data() -> dict:
    """Parse the ``const DATA = {...};`` JSON from silhouette_render.jsx."""
    source = RENDER_JSX.read_text(encoding="utf-8")
    match = re.search(r"const\s+DATA\s*=\s*(\{.+?\});", source, re.DOTALL)
    assert match, "const DATA = {...}; not found in silhouette_render.jsx"
    raw = match.group(1)
    raw = re.sub(r"(?<![0-9])\.(\d)", r"0.\1", raw)
    return json.loads(raw)


def test_render_data_section_keys_map_to_schema() -> None:
    """silhouette_render.jsx DATA keys must map to valid schema sections."""
    schema = _load_schema()
    schema_sections = set(schema.get("properties", {}).keys())
    for abbrev, section in _RENDER_ABBREVIATED_TO_SCHEMA.items():
        assert section in schema_sections, (
            f"Render DATA key '{abbrev}' maps to '{section}' which is "
            f"not in the JSON schema."
        )


def test_render_data_landmark_fields_match_schema() -> None:
    """Landmark entries in silhouette_render.jsx DATA.l must use valid fields."""
    schema = _load_schema()
    landmark_ref = schema["properties"]["landmarks"]["items"]
    landmark_schema = _resolve_ref(schema, landmark_ref["$ref"])
    schema_fields = set(landmark_schema["properties"].keys())

    d = _extract_render_data()
    sample = d["l"][0]
    for abbrev_key in sample:
        full_key = _RENDER_LANDMARK_ABBREV.get(abbrev_key, abbrev_key)
        assert full_key in schema_fields, (
            f"Render landmark key '{abbrev_key}' (→ '{full_key}') "
            f"not in Landmark schema: {schema_fields}"
        )


def test_render_data_proportion_fields_match_schema() -> None:
    """Proportion fields in silhouette_render.jsx DATA.p must be valid."""
    schema = _load_schema()
    prop_ref = schema["properties"]["proportion"]
    prop_schema = _resolve_ref(schema, prop_ref["$ref"])
    schema_fields = set(prop_schema["properties"].keys())

    d = _extract_render_data()
    for abbrev_key in d["p"]:
        full_key = _RENDER_PROPORTION_ABBREV.get(abbrev_key, abbrev_key)
        assert full_key in schema_fields, (
            f"Render proportion key '{abbrev_key}' (→ '{full_key}') "
            f"not in Proportion schema: {schema_fields}"
        )


def test_render_data_contour_is_valid() -> None:
    """silhouette_render.jsx DATA.c must be a non-empty [dx,dy] array."""
    d = _extract_render_data()
    assert isinstance(d["c"], list)
    assert len(d["c"]) >= 3  # noqa: PLR2004
    for pt in d["c"][:5]:
        assert isinstance(pt, list)  # noqa: S101
        assert len(pt) == 2  # noqa: PLR2004, S101


# stick_to_mesh_pipeline.jsx: landmark entries use field names from the
# Landmark schema and must stay synchronised.  The DATA arrays (dy,
# widths, prior_ratios, final_ratios, rewards) are pipeline-specific.

def _extract_pipeline_data() -> dict:
    """Parse the ``const DATA = {...};`` JSON from stick_to_mesh_pipeline.jsx."""
    source = PIPELINE_JSX.read_text(encoding="utf-8")
    match = re.search(r"const\s+DATA\s*=\s*(\{.+?\});", source, re.DOTALL)
    assert match, "const DATA = {...}; not found in stick_to_mesh_pipeline.jsx"
    raw = match.group(1)
    raw = re.sub(r"(?<![0-9])\.(\d)", r"0.\1", raw)
    return json.loads(raw)


def test_pipeline_data_landmark_fields_match_schema() -> None:
    """Landmark entries in stick_to_mesh_pipeline.jsx must use valid field names."""
    schema = _load_schema()
    landmark_ref = schema["properties"]["landmarks"]["items"]
    landmark_schema = _resolve_ref(schema, landmark_ref["$ref"])
    schema_fields = set(landmark_schema["properties"].keys())

    d = _extract_pipeline_data()
    sample = d["landmarks"][0]
    for key in sample:
        assert key in schema_fields, (
            f"Pipeline landmark key '{key}' not in Landmark schema: {schema_fields}"
        )


def test_pipeline_data_has_expected_structure() -> None:
    """stick_to_mesh_pipeline.jsx DATA must have all expected arrays."""
    d = _extract_pipeline_data()
    expected_keys = {"dy", "widths", "prior_ratios", "final_ratios", "rewards", "landmarks"}
    assert set(d.keys()) == expected_keys, (
        f"Pipeline DATA keys {set(d.keys())} != expected {expected_keys}"
    )
    # All parallel arrays must be the same length.
    n = len(d["dy"])
    assert len(d["widths"]) == n
    assert len(d["prior_ratios"]) == n
    assert len(d["final_ratios"]) == n


# ═════════════════════════════════════════════════════════════════════════
# HIGH #5 — README.md section table and API signatures
#
# The README documents 28 sections and shows MetaBuilder/SilhouetteDocument
# API examples.  These tests catch silent drift when sections are added/
# removed or builder methods are renamed.
# ═════════════════════════════════════════════════════════════════════════

README_PATH = ROOT / "README.md"


def test_readme_section_count_matches_model() -> None:
    """The README section table must list exactly as many sections as
    SilhouetteV4 has required fields.
    """
    readme = README_PATH.read_text(encoding="utf-8")
    required_count = sum(
        1 for fi in SilhouetteV4.model_fields.values() if fi.is_required()
    )

    # Count rows in the section table (lines matching "| `section_name` |").
    table_rows = re.findall(r"^\|\s*`[a-z_]+`\s*\|", readme, re.MULTILINE)
    assert len(table_rows) == required_count, (
        f"README section table has {len(table_rows)} rows, "
        f"but SilhouetteV4 has {required_count} required fields. "
        f"Update the README table."
    )


def test_readme_section_names_match_model() -> None:
    """Every section name in the README table must correspond to a
    SilhouetteV4 field (by name or alias).
    """
    readme = README_PATH.read_text(encoding="utf-8")
    # Extract section names from the table.
    readme_sections = set(re.findall(r"^\|\s*`([a-z_]+)`\s*\|", readme, re.MULTILINE))

    # Build the set of valid names (field names + aliases).
    valid_names: set[str] = set()
    for name, fi in SilhouetteV4.model_fields.items():
        valid_names.add(name)
        if fi.alias:
            valid_names.add(fi.alias)

    unknown = readme_sections - valid_names
    assert not unknown, (
        f"README section table contains names not in the model: {unknown}"
    )

    # Check the reverse: every required field must appear.
    required_names: set[str] = set()
    for name, fi in SilhouetteV4.model_fields.items():
        if fi.is_required():
            required_names.add(fi.alias if fi.alias else name)

    missing = required_names - readme_sections
    assert not missing, (
        f"README section table is missing required fields: {missing}"
    )


def test_readme_builder_methods_exist() -> None:
    """MetaBuilder method names referenced in README examples must exist
    on the actual MetaBuilder class.
    """
    from lib.builder import MetaBuilder

    readme = README_PATH.read_text(encoding="utf-8")
    # Extract .method_name( calls chained on MetaBuilder in the code block.
    methods_in_readme = set(re.findall(r"\.([a-z_]+)\(", readme))
    # Filter to methods that appear in the MetaBuilder chain (lines 49-63).
    meta_methods = {
        "crop_rect", "midline", "y_range", "scale", "contour_info",
        "extraction", "timing", "classify", "contour_quality",
        "bounding_box", "sections", "build",
    }
    for method in meta_methods:
        if method in methods_in_readme:
            assert hasattr(MetaBuilder, method), (
                f"README references MetaBuilder.{method}() but the method "
                f"does not exist."
            )


def test_readme_document_api_methods_exist() -> None:
    """SilhouetteDocument methods referenced in README must exist."""
    from lib.builder import SilhouetteDocument

    assert hasattr(SilhouetteDocument, "from_json"), (
        "README references SilhouetteDocument.from_json but method is missing."
    )


# ═════════════════════════════════════════════════════════════════════════
# HIGH #6 — Test fixture field coverage
#
# _minimal_sections() in test_builder.py returns hand-written dicts that
# must cover all SilhouetteV4 section fields.  If a new section is added
# to the model, this test fails.
# ═════════════════════════════════════════════════════════════════════════


def test_fixture_covers_all_sections() -> None:
    """_minimal_sections() must return a key for every SilhouetteV4 section
    (excluding ``meta`` which uses a separate builder, and the optional
    ``gesture_line_spline``).
    """
    # Import the fixture function from the test module.
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "test_builder", ROOT / "tests" / "test_builder.py",
    )
    assert spec is not None  # noqa: S101
    assert spec.loader is not None  # noqa: S101
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    sections = mod._minimal_sections()

    # Every required field except meta must be present.
    expected: set[str] = set()
    for name, fi in SilhouetteV4.model_fields.items():
        if name == "meta":
            continue
        if not fi.is_required():
            continue
        # Use alias if present (gesture_line for principal_axes).
        key = fi.alias if fi.alias else name
        expected.add(key)

    fixture_keys = set(sections.keys())
    missing = expected - fixture_keys
    assert not missing, (
        f"_minimal_sections() is missing keys for required fields: {missing}. "
        f"Add fixture data for new model sections."
    )

    extra = fixture_keys - expected
    assert not extra, (
        f"_minimal_sections() has keys not matching any required field: {extra}. "
        f"Was a section renamed or removed?"
    )


# ═════════════════════════════════════════════════════════════════════════
# HIGH #7 — RIGHT_END constant must be defined in one place
#
# Previously duplicated between scripts/generate_v4.py and lib/parser.py.
# Now extracted to lib/constants.py.  These tests ensure both consumers
# import the shared value and that it stays consistent.
# ═════════════════════════════════════════════════════════════════════════


def test_right_end_shared_constant_is_consistent() -> None:
    """lib/constants.py RIGHT_END must be importable and equal to 727."""
    from lib.constants import RIGHT_END

    assert RIGHT_END == 727, (  # noqa: PLR2004
        f"lib/constants.RIGHT_END changed to {RIGHT_END}. "
        f"Verify that both parser.py and generate_v4.py handle this correctly."
    )


def test_parser_uses_shared_right_end() -> None:
    """lib/parser.py must import RIGHT_END from lib.constants, not define
    its own literal.
    """
    source = (ROOT / "lib" / "parser.py").read_text(encoding="utf-8")
    assert "from lib.constants import" in source, (
        "lib/parser.py does not import from lib.constants. "
        "It should use the shared RIGHT_END constant."
    )
    # Must NOT have a standalone _RIGHT_END = <number> assignment.
    standalone = re.search(r"^_RIGHT_END\s*=\s*\d+", source, re.MULTILINE)
    assert standalone is None, (
        "lib/parser.py still has a hardcoded _RIGHT_END = <number> assignment. "
        "Remove it and use the import from lib.constants."
    )


def test_generate_v4_uses_shared_right_end() -> None:
    """scripts/generate_v4.py must import RIGHT_END from lib.constants,
    not define its own literal.
    """
    source = (ROOT / "scripts" / "generate_v4.py").read_text(encoding="utf-8")
    assert "from lib.constants import" in source, (
        "scripts/generate_v4.py does not import from lib.constants. "
        "It should use the shared RIGHT_END constant."
    )
    # Must NOT have a standalone RIGHT_END = <number> assignment.
    standalone = re.search(r"^RIGHT_END\s*=\s*\d+", source, re.MULTILINE)
    assert standalone is None, (
        "scripts/generate_v4.py still has a hardcoded RIGHT_END = <number>. "
        "Remove it and use the import from lib.constants."
    )


# ═════════════════════════════════════════════════════════════════════════
# MODERATE #8 — Schema codegen freshness
#
# The JSON schema is generated from model.py via `make schema`.  The
# `test_schema_file_matches_model` test (above, in the CRITICAL section)
# already catches a stale schema.  These additional tests verify that the
# Makefile wiring is correct so the guard is enforceable at build time.
# ═════════════════════════════════════════════════════════════════════════

MAKEFILE_PATH = ROOT / "Makefile"


def test_makefile_has_check_schema_target() -> None:
    """The Makefile must have a ``check-schema`` target that validates the
    committed schema against the model without regenerating it.
    """
    makefile = MAKEFILE_PATH.read_text(encoding="utf-8")
    assert "check-schema" in makefile, (
        "Makefile is missing the check-schema target. "
        "Add a target that asserts schema freshness."
    )


def test_makefile_check_runs_check_schema() -> None:
    """``make check`` must depend on ``check-schema`` so that schema
    freshness is verified alongside lint and typecheck.
    """
    makefile = MAKEFILE_PATH.read_text(encoding="utf-8")
    # Find the line defining the `check` target and assert check-schema
    # is in its dependency list.
    match = re.search(r"^check\s*:(.*)", makefile, re.MULTILINE)
    assert match, "Makefile has no `check` target."
    deps = match.group(1)
    assert "check-schema" in deps, (
        "`make check` does not depend on `check-schema`. "
        "Add check-schema to the check target's prerequisites."
    )


# ═════════════════════════════════════════════════════════════════════════
# MODERATE #9 — Port configuration must be consistent across Docker files
#
# The app port was previously hardcoded as 3000 in three independent
# files.  It is now centralised in .env (APP_PORT) and referenced via
# variable substitution.  These tests assert that none of the three
# consumers still embed a bare hardcoded port literal.
# ═════════════════════════════════════════════════════════════════════════

ENV_PATH = ROOT / ".env"
DOCKERFILE_PATH = ROOT / "packages" / "silhouette-2d" / "Dockerfile"
COMPOSE_PATH = ROOT / "docker-compose.yml"
PKG_JSON_PATH = ROOT / "packages" / "silhouette-2d" / "package.json"


def test_env_file_defines_app_port() -> None:
    """.env must define APP_PORT."""
    env_text = ENV_PATH.read_text(encoding="utf-8")
    match = re.search(r"^APP_PORT\s*=\s*(\d+)", env_text, re.MULTILINE)
    assert match, ".env does not define APP_PORT."
    port = int(match.group(1))
    assert port > 0, "APP_PORT must be a positive integer."


def test_dockerfile_uses_app_port_variable() -> None:
    """Dockerfile must reference APP_PORT, not a hardcoded port literal
    in EXPOSE and CMD.
    """
    source = DOCKERFILE_PATH.read_text(encoding="utf-8")
    # EXPOSE must use the variable.
    assert re.search(r"EXPOSE\s+\$\{?APP_PORT", source), (
        "Dockerfile EXPOSE still uses a hardcoded port. "
        "Use ${APP_PORT} instead."
    )
    # CMD / serve must reference the variable.
    assert "APP_PORT" in source.split("CMD")[1] if "CMD" in source else False, (
        "Dockerfile CMD still uses a hardcoded port for serve. "
        "Use ${APP_PORT} instead."
    )


def test_docker_compose_uses_app_port_variable() -> None:
    """docker-compose.yml port mapping must use ${APP_PORT}, not a literal."""
    source = COMPOSE_PATH.read_text(encoding="utf-8")
    assert "APP_PORT" in source, (
        "docker-compose.yml does not reference APP_PORT. "
        "Use ${APP_PORT:-3000} in the ports mapping."
    )
    # Must NOT have a bare "3000:3000" literal.
    assert '"3000:3000"' not in source, (
        'docker-compose.yml still has a hardcoded "3000:3000" port mapping. '
        "Use the APP_PORT variable."
    )


def test_package_json_uses_app_port_variable() -> None:
    """package.json serve scripts must reference $APP_PORT, not a literal."""
    source = PKG_JSON_PATH.read_text(encoding="utf-8")
    # The dev and serve scripts must reference APP_PORT.
    assert "APP_PORT" in source, (
        "package.json scripts do not reference APP_PORT. "
        "Use ${APP_PORT:-3000} in the serve commands."
    )


def test_port_values_are_consistent() -> None:
    """The default port across all configuration files must agree with .env."""
    env_text = ENV_PATH.read_text(encoding="utf-8")
    match = re.search(r"^APP_PORT\s*=\s*(\d+)", env_text, re.MULTILINE)
    assert match
    env_port = match.group(1)

    # docker-compose.yml defaults must use the same port.
    compose = COMPOSE_PATH.read_text(encoding="utf-8")
    compose_defaults = re.findall(r"APP_PORT:-(\d+)", compose)
    for default in compose_defaults:
        assert default == env_port, (
            f"docker-compose.yml default port {default} != .env port {env_port}"
        )

    # package.json defaults must use the same port.
    pkg = PKG_JSON_PATH.read_text(encoding="utf-8")
    pkg_defaults = re.findall(r"APP_PORT:-(\d+)", pkg)
    for default in pkg_defaults:
        assert default == env_port, (
            f"package.json default port {default} != .env port {env_port}"
        )

    # Dockerfile ARG default must use the same port.
    dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")
    arg_defaults = re.findall(r"ARG\s+APP_PORT\s*=\s*(\d+)", dockerfile)
    for default in arg_defaults:
        assert default == env_port, (
            f"Dockerfile ARG APP_PORT default {default} != .env port {env_port}"
        )
