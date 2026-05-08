"""Unit tests for data_loader. SDK is mocked — no live Databricks calls."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.lib import data_loader


def _mock_client(rows, schema):
    client = MagicMock()
    response = MagicMock()
    response.status.state.value = "SUCCEEDED"
    response.result.data_array = rows
    cols = []
    for name in schema:
        c = MagicMock()
        c.name = name
        cols.append(c)
    response.manifest.schema.columns = cols
    client.statement_execution.execute_statement.return_value = response
    return client


def test_load_classified_returns_dataframe_with_expected_columns():
    rows = [
        ["fdp_prd_x.s.t1", "MAINLAND_TAGGED", "fdp_prd_x", "s", "t1", True, 1, 2,
         0, 0, 0, 0, 0, 0, 1.0, 0.5, 0.7],
    ]
    cols = [
        "node", "category", "catalog", "schema", "table_name", "is_seed",
        "n_upstream", "n_downstream",
        "sep_business_entity", "sep_location", "sep_employee",
        "sep_customer", "sep_material", "sep_sales_org",
        "mainland_in_ratio", "mainland_out_ratio", "bridge_score",
    ]
    client = _mock_client(rows, cols)
    df = data_loader.load_classified(client, warehouse_id="W", working_schema="s.m")
    assert list(df.columns) == cols
    assert len(df) == 1
    assert df.iloc[0]["category"] == "MAINLAND_TAGGED"


def test_load_pinchpoints_filters_to_co_mingled():
    rows = [["n1", "CO_MINGLED_UPSTREAM"], ["n2", "CO_MINGLED_DOWNSTREAM"]]
    client = _mock_client(rows, ["node", "category"])
    df = data_loader.load_pinchpoints(client, warehouse_id="W", working_schema="s.m")
    assert len(df) == 2
    sql = client.statement_execution.execute_statement.call_args.kwargs["statement"]
    assert "CO_MINGLED_UPSTREAM" in sql and "CO_MINGLED_DOWNSTREAM" in sql


def test_failed_statement_raises():
    client = MagicMock()
    response = MagicMock()
    response.status.state.value = "FAILED"
    response.status.error.message = "permission denied"
    client.statement_execution.execute_statement.return_value = response
    with pytest.raises(RuntimeError, match="permission denied"):
        data_loader.load_classified(client, warehouse_id="W", working_schema="s.m")
