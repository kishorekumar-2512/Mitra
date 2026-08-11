"""Mermaid diagram generation tool."""
import re
from typing import Any, Literal
from pydantic import BaseModel, Field
from app.tools.base import tool_error


class GenerateFlowchartInput(BaseModel):
    """Build an ER diagram from schema or a process/decision chart from ordered steps."""
    diagram_type: Literal["er", "process", "decision"]
    context: dict[str, Any]


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", name)


async def generate_flowchart(payload: GenerateFlowchartInput) -> dict[str, Any]:
    """Return syntactically valid Mermaid ER or flowchart text from structured context."""
    try:
        if payload.diagram_type == "er":
            tables = payload.context.get("tables", [])
            if not tables:
                return tool_error("ER diagrams require a schema context with tables.", True)
            lines = ["erDiagram"]
            for table in tables:
                lines.append(f"  {_safe(table['name'])} {{")
                for column in table.get("columns", []):
                    key = " PK" if column.get("primary_key") else ""
                    lines.append(f"    {str(column.get('type', 'string')).replace(' ', '_')} {_safe(column['name'])}{key}")
                lines.append("  }")
            for table in tables:
                for fk in table.get("foreign_keys", []):
                    lines.append(f"  {_safe(fk['references_table'])} ||--o{{ {_safe(table['name'])} : \"{_safe(fk['column'])}\"")
            return {"mermaid": "\n".join(lines)}
        steps = payload.context.get("steps", [])
        if not isinstance(steps, list) or not steps:
            return tool_error("Process and decision diagrams require context.steps.", True)
        lines = ["flowchart TD"]
        for index, step in enumerate(steps):
            label = str(step).replace('"', "'")
            node = f"S{index}"
            shape = f"{{{label}}}" if payload.diagram_type == "decision" and index < len(steps)-1 else f"[{label}]"
            lines.append(f"  {node}{shape}")
            if index:
                lines.append(f"  S{index-1} --> {node}")
        return {"mermaid": "\n".join(lines)}
    except (KeyError, TypeError) as exc:
        return tool_error(f"Invalid diagram context: {exc}", True)
