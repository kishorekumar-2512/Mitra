"""Chart-spec generation tool."""
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator
from app.tools.base import tool_error


class GenerateChartInput(BaseModel):
    """Input data and field mapping for an inline Recharts visualization."""
    chart_type: Literal["bar", "line", "pie", "scatter"]
    data: list[dict[str, Any]] = Field(min_length=1)
    x_field: str
    y_field: str
    title: str = Field(min_length=1, max_length=160)


async def generate_chart(payload: GenerateChartInput) -> dict[str, Any]:
    """Validate chart fields and return a frontend-ready Recharts JSON specification."""
    try:
        available = set().union(*(row.keys() for row in payload.data))
        missing = [field for field in (payload.x_field, payload.y_field) if field not in available]
        if missing:
            return tool_error(f"Chart field(s) not present in data: {', '.join(missing)}", True)
        return {"type": payload.chart_type, "title": payload.title, "data": payload.data, "x_field": payload.x_field, "y_field": payload.y_field}
    except Exception as exc:
        return tool_error(f"Could not generate chart: {exc}", False)
