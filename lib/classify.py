"""Phase 3 helpers — pull the classified nodes table down to a local CSV.

The classification SQL (queries/03_classify_nodes.sql) materialises a Delta
table; this script reads it back in chunks and writes outputs/classified_nodes.csv
along with summary stats.
"""
from __future__ import annotations

import csv
import json
import pathlib
import subprocess


WAREHOUSE_ID = "406253829ca12fd5"
PROFILE = "FONTERRA"
TABLE = "aw_internal_adpcoe.mainland_lineage_analysis.mainland_lineage_classified"


def run_sql_paged(statement: str, page: int = 5000) -> tuple[list[str], list[list]]:
    """Run a SELECT and stream rows back. Returns (column_names, rows)."""
    payload = {
        "warehouse_id": WAREHOUSE_ID,
        "statement": statement,
        "wait_timeout": "50s",
        "format": "JSON_ARRAY",
        "disposition": "INLINE",
    }
    r = subprocess.run(
        ["databricks", "-p", PROFILE, "api", "post",
         "/api/2.0/sql/statements", "--json", json.dumps(payload)],
        capture_output=True, text=True, timeout=180,
    )
    d = json.loads(r.stdout)
    if d.get("status", {}).get("state") != "SUCCEEDED":
        raise RuntimeError(d.get("status", {}).get("error", {}).get("message", "")[:500])
    cols = [c["name"] for c in d.get("manifest", {}).get("schema", {}).get("columns", [])]
    rows = d.get("result", {}).get("data_array", []) or []
    # Single page is fine for ~4k rows.
    return cols, rows


def dump_classified(out_path: pathlib.Path) -> int:
    cols, rows = run_sql_paged(f"SELECT * FROM {TABLE} ORDER BY node")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    return len(rows)


def dump_edges(out_path: pathlib.Path) -> int:
    cols, rows = run_sql_paged(
        "SELECT src_full_name, tgt_full_name, edge_count, hop, direction "
        "FROM aw_internal_adpcoe.mainland_lineage_analysis.mainland_lineage_edges "
        "ORDER BY src_full_name, tgt_full_name"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    n = dump_classified(pathlib.Path("outputs/classified_nodes.csv"))
    print(f"classified_nodes.csv: {n} rows")
    n = dump_edges(pathlib.Path("outputs/edges.csv"))
    print(f"edges.csv: {n} rows")
