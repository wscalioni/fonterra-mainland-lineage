"""Tests for SQL composition in the nightly refresh script."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Make repo root importable so `from jobs import nightly_refresh` works
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from jobs import nightly_refresh as nr


def _ok_client():
    c = MagicMock()
    r = MagicMock()
    r.status.state.value = "SUCCEEDED"
    r.result.data_array = [["2026-05-07 12:00:00"]]
    col = MagicMock()
    col.name = "watermark"
    r.manifest.schema.columns = [col]
    c.statement_execution.execute_statement.return_value = r
    return c


def test_read_watermark_uses_max_last_seen():
    c = _ok_client()
    nr.read_watermark(c, warehouse_id="W", working_schema="s.m")
    sql = c.statement_execution.execute_statement.call_args.kwargs["statement"]
    assert "max(last_seen)" in sql.lower()
    assert "s.m.mainland_lineage_edges" in sql


def test_merge_new_edges_query_uses_correct_schema():
    sql = nr.build_merge_edges_sql(working_schema="s.m", watermark_iso="2026-05-07T00:00:00")
    assert "MERGE INTO s.m.mainland_lineage_edges" in sql
    assert "system.access.table_lineage" in sql
    assert "event_time > TIMESTAMP '2026-05-07T00:00:00'" in sql
    assert "WHEN NOT MATCHED THEN INSERT" in sql


def test_classify_affected_filters_by_node_column():
    sql = nr.build_classify_affected_sql(
        working_schema="s.m",
        affected_csv="'a.b.c','d.e.f'",
    )
    # NOTE: filter is on `node` (matches mainland_lineage_classified column name).
    assert "WHERE node IN ('a.b.c','d.e.f')" in sql
    assert "MERGE INTO s.m.mainland_lineage_classified" in sql
    # Explicit column list, not UPDATE SET * / INSERT *
    assert "category" in sql and "sep_business_entity" in sql


def test_run_logs_to_refresh_control(monkeypatch):
    c = _ok_client()
    monkeypatch.setattr(nr, "read_watermark", lambda *a, **k: "2026-05-07T00:00:00")
    monkeypatch.setattr(nr, "merge_new_edges", lambda *a, **k: 5)
    monkeypatch.setattr(nr, "insert_new_nodes", lambda *a, **k: 2)
    monkeypatch.setattr(nr, "classify_affected", lambda *a, **k: 7)
    nr.run(c, warehouse_id="W", working_schema="s.m")
    statements = [
        call.kwargs["statement"]
        for call in c.statement_execution.execute_statement.call_args_list
    ]
    assert any("refresh_control" in s and "INSERT" in s.upper() for s in statements)
