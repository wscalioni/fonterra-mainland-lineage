"""Category colours for the Mainland Lineage app.

KEEP IN SYNC with the canonical CATEGORY_COLOUR dict in lib/visualize.py
(repo root). The pipeline runs from repo root and uses lib/visualize.py;
the app runs from the app/ subtree and uses this file. Databricks Apps only
bundles source_code_path (./app), so we cannot import the canonical dict at
runtime — duplication is the pragmatic answer.

If you change a colour here, change it in lib/visualize.py too.
"""
from __future__ import annotations

CATEGORY_COLOUR = {
    "MAINLAND_TAGGED":        "#4CAF50",
    "MAINLAND_INTERIOR":      "#2E7D32",
    "MAINLAND_SOURCE":        "#1976D2",
    "MAINLAND_SINK":          "#0288D1",
    "CO_MINGLED_UPSTREAM":    "#E65100",
    "CO_MINGLED_DOWNSTREAM":  "#D32F2F",
    "RETAINED_OR_INDIRECT":   "#9E9E9E",
    "UNCLASSIFIED":           "#BDBDBD",
}

__all__ = ["CATEGORY_COLOUR"]
