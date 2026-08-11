import pytest
from pydantic import ValidationError
from app.tools.execute_query import ExecuteQueryInput, execute_query
from app.tools.generate_chart import GenerateChartInput


@pytest.mark.asyncio
async def test_execute_query_rejects_non_select(adapter):
    result = await execute_query(adapter, ExecuteQueryInput(sql="DELETE FROM sales"))
    assert result["error"] is True
    assert "SELECT" in result["message"]


def test_generate_chart_rejects_invalid_chart_type():
    with pytest.raises(ValidationError):
        GenerateChartInput(chart_type="histogram", data=[{"name": "A", "value": 1}], x_field="name", y_field="value", title="Invalid")
