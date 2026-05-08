from unittest.mock import MagicMock
import pytest
from lib import status_writer


def _ok_client():
    c = MagicMock()
    r = MagicMock()
    r.status.state.value = "SUCCEEDED"
    c.statement_execution.execute_statement.return_value = r
    return c


def test_set_pinchpoint_status_uses_merge_and_quotes_inputs():
    c = _ok_client()
    status_writer.set_pinchpoint_status(
        c, warehouse_id="W", working_schema="s.m",
        node="cat.sch.tbl", status="UC Tagged", notes="needs review",
        updated_by="mike@fonterra.com",
    )
    sql = c.statement_execution.execute_statement.call_args.kwargs["statement"]
    assert "MERGE INTO s.m.pinchpoint_status" in sql
    assert "'cat.sch.tbl'" in sql
    assert "'UC Tagged'" in sql
    assert "'mike@fonterra.com'" in sql


def test_set_pinchpoint_status_rejects_unknown_status():
    c = _ok_client()
    with pytest.raises(ValueError, match="status must be one of"):
        status_writer.set_pinchpoint_status(
            c, warehouse_id="W", working_schema="s.m",
            node="x", status="LOL", notes="", updated_by="m@f.com",
        )


def test_set_pinchpoint_status_escapes_single_quotes_in_notes():
    c = _ok_client()
    status_writer.set_pinchpoint_status(
        c, warehouse_id="W", working_schema="s.m",
        node="x", status="Pending", notes="mike's note",
        updated_by="m@f.com",
    )
    sql = c.statement_execution.execute_statement.call_args.kwargs["statement"]
    assert "mike''s note" in sql
