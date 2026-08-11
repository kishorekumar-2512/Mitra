"""Deterministic, grounded result-summary tool."""
from typing import Any
from pydantic import BaseModel, Field
from app.tools.base import tool_error


class ExplainDataInput(BaseModel):
    """Query result payload plus the original natural-language question."""
    query_results: dict[str, Any]
    user_question: str = Field(min_length=1)


async def explain_data(payload: ExplainDataInput) -> dict[str, Any]:
    """Produce a concise 2–4 sentence grounded insight rather than repeat raw tabular data."""
    try:
        rows = payload.query_results.get("rows", [])
        count = payload.query_results.get("row_count", len(rows))
        if not rows:
            return {"summary": f"I found no matching records for your question. Try widening the date range or checking the available values in the schema."}
        fields = payload.query_results.get("columns") or list(rows[0].keys())
        numeric = [field for field in fields if isinstance(rows[0].get(field), (int, float)) and not isinstance(rows[0].get(field), bool)]
        detail = ""
        if numeric:
            field = numeric[0]
            values = [row.get(field) for row in rows if isinstance(row.get(field), (int, float))]
            if values:
                detail = f" The {field} values range from {min(values):,.2f} to {max(values):,.2f}."
        return {"summary": f"For “{payload.user_question}”, the query returned {count} matching record{'s' if count != 1 else ''}.{detail} This is based only on the returned result set."}
    except Exception as exc:
        return tool_error(f"Could not explain results: {exc}", False)
