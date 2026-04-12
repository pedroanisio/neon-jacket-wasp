# Neon Jacket Wasp

Silhouette analysis SDK: v4 JSON schema, Pydantic models, fluent builder, and v2-to-v4 enrichment pipeline.

## Architecture

```
lib/model.py          ← AUTHORITATIVE source for all types
lib/builder.py        ← Fluent builder + SilhouetteDocument I/O
lib/parser.py         ← v2 ZIP → validated v4 document

schema/               ← GENERATED from lib/model.py (do not edit by hand)
  silhouette_v4.schema.json

scripts/
  generate_v4.py      ← 29-phase v2 → v4 enrichment pipeline

data/
  input/              ← v2 extraction ZIPs
  output/             ← generated v4 JSON documents
```

**`lib/model.py` is the single source of truth.** The JSON schema is derived
from it. Do not edit `schema/silhouette_v4.schema.json` by hand — regenerate
it with `make schema`.

## Quick start

```python
from lib.parser import parse_zip

# v2 ZIP → validated v4 document
doc = parse_zip("data/input/056663ee830a4717ae470b1a9cd6c46e.zip")
doc.to_json("output.json")

# Access typed fields
print(doc.model.meta.schema_version)        # "4.0.0"
print(len(doc.model.landmarks))             # 19
print(doc.model.proportion.head_count_total) # 10.492
```

```python
from lib.builder import SilhouetteBuilder, MetaBuilder

# Build from scratch
builder = SilhouetteBuilder()
builder.meta(MetaBuilder("source.png", (1024, 2048))
    .crop_rect(0, 0, 1024, 2048)
    .midline(512.0)
    .y_range(10, 1990)
    .scale(0.005)
    .contour_info(1200, 50)
    .extraction(method="floodfill", scanline=0.9, floodfill=0.95, direct=0.85, margin=0.05)
    .timing(algo_ms=200.0, total_ms=300.0)
    .classify(surface="nude", gender="female", view="front")
    .contour_quality({"total_perimeter_hu": 20.0, "right_perimeter_hu": 10.0,
                      "mean_segment_length": 0.02, "segment_length_cv": 0.1})
    .bounding_box({"dx_min": -1.5, "dx_max": 1.5, "dy_min": 0.0, "dy_max": 8.0,
                   "width": 3.0, "height": 8.0, "aspect_ratio": 0.375})
    .sections({"total_sections": 28, "sections": ["meta", "contour", "..."]})
    .build()
)
builder.contour(contour_points)
builder.landmarks(landmark_list)
# ... set remaining sections
doc = builder.build()
```

```python
from lib.builder import SilhouetteDocument

# Load existing v4 JSON
doc = SilhouetteDocument.from_json("existing_v4.json", strict=False)
print(doc.validate())  # list of constraint violations (if any)
```

## Make targets

```
make schema      Regenerate JSON schema from lib/model.py
make lint        ruff check lib/
make format      ruff format lib/
make typecheck   mypy lib/
make check       lint + typecheck
```

## Schema (v4.0)

28 required sections covering contour geometry, anatomical landmarks,
proportions, curvature, shape descriptors, biomechanics, volumetric
estimates, and complexity metrics. All spatial values use head-unit (HU)
coordinates.

| Section | Description |
|---|---|
| `meta` | Processing metadata, classification, quality metrics |
| `contour` | 1200-point closed contour in HU |
| `landmarks` | ~19 anatomical feature points |
| `midline` | Vertical centerline |
| `strokes` | Interior detail lines with semantic classification |
| `symmetry` | Bilateral symmetry measurements |
| `measurements` | Dense scanlines at 0.05 HU step |
| `parametric` | B-spline fits between landmarks |
| `proportion` | Head count, segment/width ratios, canon comparisons |
| `candidates` | Alternative extraction results with scores |
| `curvature` | Discrete kappa with extrema and inflections |
| `body_regions` | 9 anatomical zones |
| `cross_section_topology` | Contour crossing counts |
| `fourier_descriptors` | Elliptic Fourier coefficients |
| `width_profile` | 1D width signal with extrema |
| `area_profile` | Area decomposition by region |
| `contour_normals` | Subsampled unit normals |
| `shape_vector` | 21-dim ML feature vector |
| `hu_moments` | 7 rotation/scale/translation-invariant moments |
| `turning_function` | Cumulative tangent angle |
| `convex_hull` | Solidity, concavity decomposition |
| `gesture_line` | PCA action line, lean, contrapposto |
| `curvature_scale_space` | Multi-scale CSS features |
| `style_deviation` | Per-landmark deviation from Loomis canon |
| `volumetric_estimates` | Cylindrical/ellipsoidal/Pappus volume |
| `biomechanics` | Dempster/Winter segment parameters |
| `medial_axis` | Topological skeleton with inscribed radius |
| `shape_complexity` | Entropy, fractal dimension, compactness |

## Tooling

- **Python** 3.12+
- **pydantic** 2.x — model definitions, validation, JSON schema generation
- **ruff** — linting (strict) + formatting
- **mypy** — strict type checking with pydantic plugin
- **numpy/scipy** — enrichment pipeline math
