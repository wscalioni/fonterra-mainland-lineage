"""Server-side BFS lineage walker over system.access.table_lineage.

State lives in Delta tables (no Python batching of frontier IDs). Each hop
issues two SQL statements per direction: insert new edges, insert new nodes.

Why not a single recursive CTE: we want hop-level visibility for the report
and the ability to stop early when the frontier collapses.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass


WAREHOUSE_ID = "406253829ca12fd5"
PROFILE = "FONTERRA"
WORKING_SCHEMA = "aw_internal_adpcoe.mainland_lineage_analysis"


def run_sql(statement: str, wait: str = "50s") -> dict:
    payload = {"warehouse_id": WAREHOUSE_ID, "statement": statement, "wait_timeout": wait}
    r = subprocess.run(
        ["databricks", "-p", PROFILE, "api", "post",
         "/api/2.0/sql/statements", "--json", json.dumps(payload)],
        capture_output=True, text=True, timeout=300,
    )
    if r.returncode != 0:
        raise RuntimeError(f"databricks CLI failed: {r.stderr[:500]}")
    d = json.loads(r.stdout)
    state = d.get("status", {}).get("state")
    if state != "SUCCEEDED":
        err = d.get("status", {}).get("error", {}).get("message", "")
        raise RuntimeError(f"SQL state {state}: {err[:500]}")
    return d


def fetch_rows(d: dict) -> list[list]:
    return d.get("result", {}).get("data_array", []) or []


def scalar(d: dict) -> int:
    rows = fetch_rows(d)
    return int(rows[0][0]) if rows and rows[0] and rows[0][0] is not None else 0


@dataclass
class HopStat:
    hop: int
    direction: str
    new_edges: int
    new_nodes: int
    cumulative_visited: int


def init_state() -> None:
    """Create / reset edges + nodes Delta tables, prime nodes from seed."""
    run_sql(f"""
        CREATE OR REPLACE TABLE {WORKING_SCHEMA}.mainland_lineage_edges (
          src_full_name STRING,
          tgt_full_name STRING,
          edge_count    BIGINT,
          hop           INT,
          direction     STRING,
          first_seen    TIMESTAMP,
          last_seen     TIMESTAMP
        ) USING DELTA
        COMMENT 'BFS lineage walk edges, 90d window. hop=BFS depth (1..N), direction=down|up.'
    """)
    run_sql(f"""
        CREATE OR REPLACE TABLE {WORKING_SCHEMA}.mainland_lineage_nodes (
          full_name      STRING,
          first_seen_hop INT,
          first_seen_dir STRING,
          is_seed        BOOLEAN
        ) USING DELTA
        COMMENT 'Distinct nodes reached in the BFS walk.'
    """)
    run_sql(f"""
        INSERT INTO {WORKING_SCHEMA}.mainland_lineage_nodes
        SELECT DISTINCT full_name, 0 AS first_seen_hop, 'seed' AS first_seen_dir, TRUE AS is_seed
        FROM {WORKING_SCHEMA}.mainland_lineage_seed
    """)


def walk_one_hop(direction: str, hop: int, days: int = 90) -> tuple[int, int, int]:
    """One BFS hop. Frontier = nodes whose first_seen_hop == hop-1 *for this direction*
    (or seed at hop=1). Returns (new_edges, new_nodes, cumulative_visited).
    """
    assert direction in ("down", "up")
    match_col = "source_table_full_name" if direction == "down" else "target_table_full_name"
    other_col = "target_table_full_name" if direction == "down" else "source_table_full_name"

    # Frontier: rows in the nodes table whose hop = hop-1 AND direction matches
    # (or is_seed=TRUE for hop 1).
    frontier_predicate = (
        "(is_seed = TRUE)" if hop == 1
        else f"(first_seen_hop = {hop - 1} AND first_seen_dir = '{direction}')"
    )

    # Insert new edges. Edges are deduped per (src, tgt) within the hop.
    run_sql(f"""
        INSERT INTO {WORKING_SCHEMA}.mainland_lineage_edges
        WITH frontier AS (
          SELECT full_name FROM {WORKING_SCHEMA}.mainland_lineage_nodes
          WHERE {frontier_predicate}
        )
        SELECT
          l.source_table_full_name,
          l.target_table_full_name,
          COUNT(*)         AS edge_count,
          {hop}            AS hop,
          '{direction}'    AS direction,
          MIN(l.event_time) AS first_seen,
          MAX(l.event_time) AS last_seen
        FROM system.access.table_lineage l
        JOIN frontier f ON l.{match_col} = f.full_name
        WHERE l.event_time > current_date() - INTERVAL {days} DAYS
          AND l.source_table_full_name IS NOT NULL
          AND l.target_table_full_name IS NOT NULL
          AND l.source_table_full_name <> l.target_table_full_name
        GROUP BY 1, 2
    """)

    # Count edges added in this hop.
    new_edges = scalar(run_sql(f"""
        SELECT COUNT(*) FROM {WORKING_SCHEMA}.mainland_lineage_edges
        WHERE hop = {hop} AND direction = '{direction}'
    """))

    # Insert new nodes: for 'down' the new nodes are tgt_full_name; for 'up'
    # they are src_full_name. Anti-join against existing nodes table.
    new_node_col = "tgt_full_name" if direction == "down" else "src_full_name"
    run_sql(f"""
        INSERT INTO {WORKING_SCHEMA}.mainland_lineage_nodes
        SELECT DISTINCT
          e.{new_node_col} AS full_name,
          {hop}            AS first_seen_hop,
          '{direction}'    AS first_seen_dir,
          FALSE            AS is_seed
        FROM {WORKING_SCHEMA}.mainland_lineage_edges e
        LEFT ANTI JOIN {WORKING_SCHEMA}.mainland_lineage_nodes n
          ON e.{new_node_col} = n.full_name
        WHERE e.hop = {hop} AND e.direction = '{direction}'
    """)

    # Count new nodes added.
    new_nodes = scalar(run_sql(f"""
        SELECT COUNT(*) FROM {WORKING_SCHEMA}.mainland_lineage_nodes
        WHERE first_seen_hop = {hop} AND first_seen_dir = '{direction}'
    """))

    cumulative = scalar(run_sql(f"SELECT COUNT(*) FROM {WORKING_SCHEMA}.mainland_lineage_nodes"))
    return new_edges, new_nodes, cumulative


def walk(max_hops: int = 5, days: int = 90) -> list[HopStat]:
    init_state()
    seed_size = scalar(run_sql(f"SELECT COUNT(*) FROM {WORKING_SCHEMA}.mainland_lineage_nodes"))
    print(f"Seed size: {seed_size}")

    stats: list[HopStat] = []
    for direction in ("down", "up"):
        for hop in range(1, max_hops + 1):
            ne, nn, cv = walk_one_hop(direction, hop, days=days)
            stats.append(HopStat(hop, direction, ne, nn, cv))
            print(f"  {direction} hop {hop}: +{ne:>6} edges, +{nn:>5} nodes, visited={cv}")
            if nn == 0:
                break
    return stats


if __name__ == "__main__":
    import sys
    max_hops = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 90
    stats = walk(max_hops=max_hops, days=days)
    print("\nFinal hop stats:")
    for s in stats:
        print(f"  hop {s.hop} {s.direction:>4}  +{s.new_edges:>7} edges  +{s.new_nodes:>6} nodes  visited={s.cumulative_visited}")
