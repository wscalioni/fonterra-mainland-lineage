"""Nightly incremental refresh - watermark + MERGE.

Reads max(last_seen) from mainland_lineage_edges as the watermark, fetches
new lineage events from system.access.table_lineage, merges them into edges,
inserts any new nodes, and re-classifies the affected node set.

Full BFS hop structure is NOT recomputed here. New edges are tagged with
hop=NULL, direction='incremental' so they are visible to classification but
excluded from the per-hop BFS statistics. Run a full BFS reset monthly via
lib/lineage_walker.py.
"""
from __future__ import annotations

import argparse
import time
import uuid
from datetime import datetime, timezone

from databricks.sdk import WorkspaceClient


CLASSIFIED_COLUMNS = [
    "node", "is_seed", "first_seen_hop", "first_seen_dir",
    "n_upstream", "n_upstream_mainland", "n_downstream", "n_downstream_mainland",
    "mainland_in_ratio", "mainland_out_ratio", "bridge_score",
    "category",
    "sep_business_entity", "sep_location", "sep_employee",
    "sep_customer", "sep_material", "sep_sales_org",
    "catalog", "schema", "table_name",
]


def _state(resp):
    return resp.status.state.value if hasattr(resp.status.state, "value") else resp.status.state


def _exec(client, *, warehouse_id, statement, max_wait_s=900):
    resp = client.statement_execution.execute_statement(
        warehouse_id=warehouse_id, statement=statement, wait_timeout="50s",
    )
    deadline = time.time() + max_wait_s
    while _state(resp) in ("PENDING", "RUNNING") and time.time() < deadline:
        time.sleep(2)
        resp = client.statement_execution.get_statement(resp.statement_id)
    state = _state(resp)
    if state != "SUCCEEDED":
        msg = getattr(resp.status, "error", None)
        msg = msg.message if msg else f"state={state}"
        raise RuntimeError(f"SQL failed: {msg}")
    return resp


def read_watermark(client, *, warehouse_id, working_schema):
    sql = f"SELECT max(last_seen) AS watermark FROM {working_schema}.mainland_lineage_edges"
    resp = _exec(client, warehouse_id=warehouse_id, statement=sql)
    rows = resp.result.data_array or []
    if not rows or rows[0][0] is None:
        return "2000-01-01T00:00:00"
    return str(rows[0][0]).replace(" ", "T")


def build_merge_edges_sql(*, working_schema, watermark_iso):
    return f"""
        MERGE INTO {working_schema}.mainland_lineage_edges t
        USING (
          SELECT
            source_table_full_name AS src_full_name,
            target_table_full_name AS tgt_full_name,
            count(*) AS edge_count_inc,
            max(event_time) AS last_seen
          FROM system.access.table_lineage
          WHERE event_time > TIMESTAMP '{watermark_iso}'
            AND source_table_full_name IS NOT NULL
            AND target_table_full_name IS NOT NULL
            AND source_table_full_name != target_table_full_name
          GROUP BY source_table_full_name, target_table_full_name
        ) s
        ON t.src_full_name = s.src_full_name AND t.tgt_full_name = s.tgt_full_name
        WHEN MATCHED THEN UPDATE SET
          edge_count = t.edge_count + s.edge_count_inc,
          last_seen = greatest(t.last_seen, s.last_seen)
        WHEN NOT MATCHED THEN INSERT
          (src_full_name, tgt_full_name, edge_count, hop, direction, first_seen, last_seen)
          VALUES (s.src_full_name, s.tgt_full_name, s.edge_count_inc, NULL, 'incremental', s.last_seen, s.last_seen)
    """


def merge_new_edges(client, *, warehouse_id, working_schema, watermark_iso):
    _exec(client, warehouse_id=warehouse_id,
          statement=build_merge_edges_sql(working_schema=working_schema, watermark_iso=watermark_iso))
    count_sql = (
        f"SELECT count(*) FROM {working_schema}.mainland_lineage_edges "
        f"WHERE direction = 'incremental' AND last_seen > TIMESTAMP '{watermark_iso}'"
    )
    resp = _exec(client, warehouse_id=warehouse_id, statement=count_sql)
    return int(resp.result.data_array[0][0])


def insert_new_nodes(client, *, warehouse_id, working_schema, watermark_iso):
    sql = f"""
        INSERT INTO {working_schema}.mainland_lineage_nodes
        SELECT DISTINCT n AS full_name, -1 AS first_seen_hop, 'incremental' AS first_seen_dir, FALSE AS is_seed
        FROM (
          SELECT src_full_name AS n FROM {working_schema}.mainland_lineage_edges
          WHERE last_seen > TIMESTAMP '{watermark_iso}'
          UNION
          SELECT tgt_full_name AS n FROM {working_schema}.mainland_lineage_edges
          WHERE last_seen > TIMESTAMP '{watermark_iso}'
        )
        WHERE n NOT IN (SELECT full_name FROM {working_schema}.mainland_lineage_nodes)
    """
    _exec(client, warehouse_id=warehouse_id, statement=sql)
    count_sql = (
        f"SELECT count(*) FROM {working_schema}.mainland_lineage_nodes "
        f"WHERE first_seen_dir = 'incremental'"
    )
    resp = _exec(client, warehouse_id=warehouse_id, statement=count_sql)
    return int(resp.result.data_array[0][0])


def build_classify_affected_sql(*, working_schema, affected_csv):
    """Re-classify a subset by filtering v_classify_node_logic on `node`.

    affected_csv must be a quoted, comma-separated list of node names,
    e.g. "'a.b.c','d.e.f'".
    """
    cols = ", ".join(CLASSIFIED_COLUMNS)
    set_cols = ",\n          ".join(f"{c} = s.{c}" for c in CLASSIFIED_COLUMNS if c != "node")
    return f"""
        MERGE INTO {working_schema}.mainland_lineage_classified t
        USING (
          SELECT {cols}
          FROM {working_schema}.v_classify_node_logic
          WHERE node IN ({affected_csv})
        ) s
        ON t.node = s.node
        WHEN MATCHED THEN UPDATE SET
          {set_cols}
        WHEN NOT MATCHED THEN INSERT ({cols})
          VALUES ({", ".join(f"s.{c}" for c in CLASSIFIED_COLUMNS)})
    """


def classify_affected(client, *, warehouse_id, working_schema, watermark_iso):
    affected_sql = f"""
        SELECT DISTINCT full_name FROM (
          SELECT src_full_name AS full_name FROM {working_schema}.mainland_lineage_edges
          WHERE last_seen > TIMESTAMP '{watermark_iso}'
          UNION
          SELECT tgt_full_name AS full_name FROM {working_schema}.mainland_lineage_edges
          WHERE last_seen > TIMESTAMP '{watermark_iso}'
        )
    """
    resp = _exec(client, warehouse_id=warehouse_id, statement=affected_sql)
    rows = resp.result.data_array or []
    if not rows:
        return 0
    affected = [r[0] for r in rows]
    quoted = ",".join("'" + n.replace("'", "''") + "'" for n in affected)
    sql = build_classify_affected_sql(working_schema=working_schema, affected_csv=quoted)
    _exec(client, warehouse_id=warehouse_id, statement=sql)
    return len(affected)


def log_run(client, *, warehouse_id, working_schema, run_id, watermark_iso,
            new_edges, new_nodes, affected, started, completed, status):
    safe_status = status.replace("'", "''")
    sql = f"""
        INSERT INTO {working_schema}.refresh_control
          (run_id, run_type, watermark_ts, new_edges, new_nodes, affected_nodes,
           run_started, run_completed, status)
        VALUES
          ('{run_id}', 'incremental', TIMESTAMP '{watermark_iso}',
           {new_edges}, {new_nodes}, {affected},
           TIMESTAMP '{started}', TIMESTAMP '{completed}', '{safe_status}')
    """
    _exec(client, warehouse_id=warehouse_id, statement=sql)


def run(client, *, warehouse_id, working_schema):
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    run_id = str(uuid.uuid4())
    try:
        watermark = read_watermark(client, warehouse_id=warehouse_id, working_schema=working_schema)
        new_edges = merge_new_edges(client, warehouse_id=warehouse_id,
                                    working_schema=working_schema, watermark_iso=watermark)
        new_nodes = insert_new_nodes(client, warehouse_id=warehouse_id,
                                      working_schema=working_schema, watermark_iso=watermark)
        affected = classify_affected(client, warehouse_id=warehouse_id,
                                      working_schema=working_schema, watermark_iso=watermark)
        completed = datetime.now(timezone.utc).isoformat(timespec="seconds")
        log_run(client, warehouse_id=warehouse_id, working_schema=working_schema,
                run_id=run_id, watermark_iso=watermark, new_edges=new_edges,
                new_nodes=new_nodes, affected=affected,
                started=started, completed=completed, status="SUCCEEDED")
    except Exception as e:
        completed = datetime.now(timezone.utc).isoformat(timespec="seconds")
        log_run(client, warehouse_id=warehouse_id, working_schema=working_schema,
                run_id=run_id, watermark_iso="2000-01-01T00:00:00", new_edges=0,
                new_nodes=0, affected=0,
                started=started, completed=completed, status=f"FAILED: {e}")
        raise


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--warehouse-id", required=True)
    p.add_argument("--working-schema", required=True)
    args = p.parse_args()
    run(WorkspaceClient(), warehouse_id=args.warehouse_id, working_schema=args.working_schema)
