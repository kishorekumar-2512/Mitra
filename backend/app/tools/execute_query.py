"""Read-only SQL execution tool."""
from typing import Any
from pydantic import BaseModel, Field
from app.core.sql_guardrails import MAX_ROWS, guard_read_only_sql
from app.db.adapter import DatabaseAdapter
from app.tools.base import tool_error


class ExecuteQueryInput(BaseModel):
    """Input for a read-only SQL query."""
    sql: str = Field(min_length=1, description="A single SELECT statement")


async def execute_query(adapter: DatabaseAdapter, payload: ExecuteQueryInput) -> dict[str, Any]:
    """Run a guarded SELECT query. Outputs columns, up to 500 rows, count and truncation state."""
    try:
        guarded = guard_read_only_sql(payload.sql)
        columns, rows = await adapter.fetch_all(guarded.sql)
        truncated = len(rows) > MAX_ROWS
        rows = rows[:MAX_ROWS]
        return {"columns": columns, "rows": rows, "row_count": len(rows), "truncated": truncated, "sql": guarded.sql}
    except ValueError as exc:
        return tool_error(str(exc), True)
    except Exception as exc:
        return tool_error(f"Query could not be executed: {exc}", True)
