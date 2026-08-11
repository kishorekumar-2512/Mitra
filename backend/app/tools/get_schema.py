"""Database schema inspection tool."""
from typing import Any
from pydantic import BaseModel
from app.db.adapter import DatabaseAdapter
from app.tools.base import tool_error


class GetSchemaInput(BaseModel):
    """get_schema needs no arguments."""
    pass


async def get_schema(adapter: DatabaseAdapter, _: GetSchemaInput | None = None) -> dict[str, Any]:
    """Inspect tables, columns and foreign keys. Outputs a serializable schema object."""
    try:
        return await adapter.get_schema()
    except Exception as exc:
        return tool_error(f"Could not inspect the database schema: {exc}", False)
