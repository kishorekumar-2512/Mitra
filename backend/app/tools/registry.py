"""One typed registry: the sole mapping from Claude tool names to implementations."""
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Type
from pydantic import BaseModel
from app.db.adapter import DatabaseAdapter
from app.tools.execute_query import ExecuteQueryInput, execute_query
from app.tools.explain_data import ExplainDataInput, explain_data
from app.tools.generate_chart import GenerateChartInput, generate_chart
from app.tools.generate_flowchart import GenerateFlowchartInput, generate_flowchart
from app.tools.get_schema import GetSchemaInput, get_schema

Handler = Callable[[BaseModel], Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_model: Type[BaseModel]
    handler: Handler

    def anthropic_schema(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "input_schema": self.input_model.model_json_schema()}


def build_tool_registry(adapter: DatabaseAdapter) -> dict[str, ToolDefinition]:
    """Create all five native Claude tools using closures over the DB adapter."""
    return {
        "get_schema": ToolDefinition("get_schema", "Inspect database tables, columns and foreign keys before querying.", GetSchemaInput, lambda p: get_schema(adapter, p)),
        "execute_query": ToolDefinition("execute_query", "Run one read-only SELECT query. Never use writes.", ExecuteQueryInput, lambda p: execute_query(adapter, p)),
        "generate_chart": ToolDefinition("generate_chart", "Create a Recharts-ready chart specification from result rows.", GenerateChartInput, generate_chart),
        "generate_flowchart": ToolDefinition("generate_flowchart", "Create a Mermaid ER, process, or decision diagram.", GenerateFlowchartInput, generate_flowchart),
        "explain_data": ToolDefinition("explain_data", "Summarize query results in concise plain language.", ExplainDataInput, explain_data),
    }


def anthropic_tools(registry: dict[str, ToolDefinition]) -> list[dict[str, Any]]:
    return [tool.anthropic_schema() for tool in registry.values()]
