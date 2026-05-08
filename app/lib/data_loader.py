"""Delta table read helpers for the Mainland Lineage app."""
from __future__ import annotations

import pandas as pd
from databricks.sdk import WorkspaceClient


def _execute(client: WorkspaceClient, *, warehouse_id: str, statement: str) -> pd.DataFrame:
    resp = client.statement_execution.execute_statement(
        warehouse_id=warehouse_id, statement=statement, wait_timeout="50s",
    )
    state = resp.status.state.value if hasattr(resp.status.state, "value") else resp.status.state
    if state != "SUCCEEDED":
        msg = getattr(resp.status, "error", None)
        msg = msg.message if msg else f"state={state}"
        raise RuntimeError(f"SQL failed: {msg}")
    rows = resp.result.data_array or []
    cols = [c.name for c in resp.manifest.schema.columns]
    return pd.DataFrame(rows, columns=cols)


def load_classified(client, *, warehouse_id, working_schema):
    return _execute(client, warehouse_id=warehouse_id,
                    statement=f"SELECT * FROM {working_schema}.mainland_lineage_classified")


def load_pinchpoints(client, *, warehouse_id, working_schema):
    return _execute(client, warehouse_id=warehouse_id, statement=(
        f"SELECT * FROM {working_schema}.mainland_lineage_classified "
        f"WHERE category IN ('CO_MINGLED_UPSTREAM', 'CO_MINGLED_DOWNSTREAM')"
    ))


def load_edges(client, *, warehouse_id, working_schema):
    return _execute(client, warehouse_id=warehouse_id,
                    statement=f"SELECT * FROM {working_schema}.mainland_lineage_edges")


def load_pinchpoint_status(client, *, warehouse_id, working_schema):
    return _execute(client, warehouse_id=warehouse_id,
                    statement=f"SELECT * FROM {working_schema}.pinchpoint_status")


def load_workspace_identities(client, *, warehouse_id, working_schema):
    return _execute(client, warehouse_id=warehouse_id,
                    statement=f"SELECT * FROM {working_schema}.workspace_identities")


def load_refresh_control(client, *, warehouse_id, working_schema):
    return _execute(client, warehouse_id=warehouse_id, statement=(
        f"SELECT * FROM {working_schema}.refresh_control "
        f"ORDER BY run_completed DESC LIMIT 50"
    ))


def load_neighbourhood(client, *, warehouse_id, working_schema, node, hops=2):
    if hops < 1 or hops > 5:
        raise ValueError("hops must be in [1, 5]")
    safe = node.replace("'", "''")
    statement = f"""
        WITH RECURSIVE walk (n, hop) AS (
          SELECT '{safe}' AS n, 0 AS hop
          UNION ALL
          SELECT CASE WHEN e.src_full_name = w.n THEN e.tgt_full_name
                      ELSE e.src_full_name END AS n,
                 w.hop + 1 AS hop
          FROM walk w
          JOIN {working_schema}.mainland_lineage_edges e
            ON (e.src_full_name = w.n OR e.tgt_full_name = w.n)
          WHERE w.hop < {hops}
        )
        SELECT DISTINCT e.src_full_name, e.tgt_full_name, e.edge_count
        FROM {working_schema}.mainland_lineage_edges e
        WHERE e.src_full_name IN (SELECT n FROM walk)
           OR e.tgt_full_name IN (SELECT n FROM walk)
    """
    return _execute(client, warehouse_id=warehouse_id, statement=statement)
