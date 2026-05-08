"""Status write-back helpers — pinchpoint_status, workspace_identities."""
from __future__ import annotations

from databricks.sdk import WorkspaceClient


VALID_STATUSES = {"Pending", "UC Tagged", "Row Filter Applied", "Attested", "Cleared"}


def _q(s: str) -> str:
    return s.replace("'", "''")


def _exec(client, *, warehouse_id, statement):
    resp = client.statement_execution.execute_statement(
        warehouse_id=warehouse_id, statement=statement, wait_timeout="50s",
    )
    state = resp.status.state.value if hasattr(resp.status.state, "value") else resp.status.state
    if state != "SUCCEEDED":
        msg = getattr(resp.status, "error", None)
        msg = msg.message if msg else f"state={state}"
        raise RuntimeError(f"SQL failed: {msg}")


def set_pinchpoint_status(client, *, warehouse_id, working_schema,
                           node, status, notes, updated_by):
    if status not in VALID_STATUSES:
        raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")
    statement = f"""
        MERGE INTO {working_schema}.pinchpoint_status t
        USING (SELECT '{_q(node)}' AS node) s
          ON t.node = s.node
        WHEN MATCHED THEN UPDATE SET
          status = '{_q(status)}',
          notes = '{_q(notes)}',
          updated_by = '{_q(updated_by)}',
          updated_at = current_timestamp()
        WHEN NOT MATCHED THEN INSERT
          (node, status, notes, updated_by, updated_at)
          VALUES ('{_q(node)}', '{_q(status)}', '{_q(notes)}',
                  '{_q(updated_by)}', current_timestamp())
    """
    _exec(client, warehouse_id=warehouse_id, statement=statement)


def set_workspace_identity(client, *, warehouse_id, working_schema,
                            workspace_id, display_name, notes, updated_by):
    statement = f"""
        MERGE INTO {working_schema}.workspace_identities t
        USING (SELECT '{_q(workspace_id)}' AS workspace_id) s
          ON t.workspace_id = s.workspace_id
        WHEN MATCHED THEN UPDATE SET
          display_name = '{_q(display_name)}',
          notes = '{_q(notes)}',
          updated_by = '{_q(updated_by)}',
          updated_at = current_timestamp()
        WHEN NOT MATCHED THEN INSERT
          (workspace_id, display_name, notes, updated_by, updated_at)
          VALUES ('{_q(workspace_id)}', '{_q(display_name)}', '{_q(notes)}',
                  '{_q(updated_by)}', current_timestamp())
    """
    _exec(client, warehouse_id=warehouse_id, statement=statement)
