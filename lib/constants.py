"""Shared constants used across the SDK and the enrichment pipeline."""

from __future__ import annotations

# Contour boundary index: indices 0..RIGHT_END-1 are the right half,
# indices RIGHT_END..1199 are the left half.  Used by both the parser
# (lib/parser.py) and the enrichment pipeline (scripts/generate_v4.py).
RIGHT_END: int = 727
