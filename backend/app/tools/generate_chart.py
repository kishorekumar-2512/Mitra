"""Chart-spec generation tool."""
from typing import Any, Literal
from pydantic import BaseModel, Field
from app.tools.base import tool_error


class GenerateChartInput(BaseModel):
    """Trusted query data plus model-selected field mapping for an inline chart."""
    chart_type: Literal["bar", "line", "pie", "scatter"]
    data: list[dict[str, Any]] = Field(default_factory=list, description="Provided by the application from the most recent query; do not supply this argument.")
    x_field: str
    y_field: str
    title: str = Field(default="Chart", max_length=160)


async def generate_chart(payload: GenerateChartInput) -> dict[str, Any]:
    """Validate chart fields and return a frontend-ready Recharts JSON specification."""
    try:
        if not payload.data:
            return tool_error("Cannot generate chart: data is empty. Run execute_query first to get non-empty query results before calling generate_chart.", True)
        available = set().union(*(row.keys() for row in payload.data))
        missing = [field for field in (payload.x_field, payload.y_field) if field not in available]
        if missing:
            return tool_error(f"Chart field(s) not present in data: {', '.join(missing)}", True)
        return {"type": payload.chart_type, "title": payload.title, "data": payload.data, "x_field": payload.x_field, "y_field": payload.y_field}
    except Exception as exc:
        return tool_error(f"Could not generate chart: {exc}", False)
