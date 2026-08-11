"""HTTP and SSE routes."""
import json
from typing import Any
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Literal
from app.agents.providers import ProviderName
from app.core.config import get_settings

router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=4000)
    provider: ProviderName = "anthropic"
    api_key: str | None = Field(default=None, min_length=10, max_length=500)
    model: str | None = Field(default=None, min_length=2, max_length=160)


def sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@router.get("/health")
async def health(request: Request) -> dict[str, str]:
    return {"status": "ok", "service": "mitra"}


@router.get("/schema")
async def schema(request: Request) -> dict[str, Any]:
    return await request.app.state.database.get_schema()


@router.post("/chat")
async def chat(payload: ChatRequest, request: Request) -> StreamingResponse:
    settings = get_settings()
    configured_keys = {"anthropic": settings.anthropic_api_key, "groq": settings.groq_api_key, "gemini": settings.gemini_api_key}
    configured_models = {"anthropic": settings.claude_model, "groq": settings.groq_model, "gemini": settings.gemini_model}
    api_key = payload.api_key or configured_keys[payload.provider]
    if not api_key:
        async def missing_key():
            yield sse("error", {"message": f"Add a {payload.provider.title()} API key in Settings or configure it on the server."})
        return StreamingResponse(missing_key(), media_type="text/event-stream")
    state = await request.app.state.memory.get(payload.session_id)
    if state.get("provider") not in (None, payload.provider):
        state["history"] = []
        await request.app.state.memory.save(payload.session_id, state)
    state["provider"] = payload.provider
    await request.app.state.memory.save(payload.session_id, state)
    agent = request.app.state.agent_factory(payload.provider, api_key, payload.model or configured_models[payload.provider])
    async def event_stream():
        try:
            async for item in agent.run(payload.session_id, payload.message):
                yield sse(item["event"], item["data"])
        except Exception as exc:
            yield sse("error", {"message": f"Unexpected agent error: {exc}"})
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, request: Request) -> dict[str, Any]:
    return await request.app.state.memory.get(session_id)


class PinRequest(BaseModel):
    chart: dict[str, Any]


@router.post("/sessions/{session_id}/pins")
async def pin_chart(session_id: str, payload: PinRequest, request: Request) -> dict[str, Any]:
    state = await request.app.state.memory.get(session_id)
    state["pinned"].append(payload.chart)
    await request.app.state.memory.save(session_id, state)
    return {"pinned": state["pinned"]}


@router.put("/sessions/{session_id}/pins")
async def reorder_pins(session_id: str, charts: list[dict[str, Any]], request: Request) -> dict[str, Any]:
    state = await request.app.state.memory.get(session_id)
    state["pinned"] = charts
    await request.app.state.memory.save(session_id, state)
    return {"pinned": charts}


@router.get("/suggestions")
async def suggestions() -> dict[str, Any]:
    """Return categorized example queries for the UI."""
    return {
        "categories": [
            {
                "emoji": "📊",
                "label": "Sales & Revenue",
                "queries": [
                    "Show monthly revenue trend for 2025 as a line chart",
                    "Which product category generates the most revenue?",
                    "Compare Q1 vs Q2 sales performance",
                    "What are the top 5 best-selling products by quantity?",
                    "Show revenue distribution by category as a pie chart"
                ]
            },
            {
                "emoji": "👥",
                "label": "Customer Analytics",
                "queries": [
                    "Who are the top 5 customers by total spending?",
                    "Show customer distribution by tier as a pie chart",
                    "Which cities have the most customers?",
                    "Show the customer growth trend by join date",
                    "What is the average order value by customer tier?"
                ]
            },
            {
                "emoji": "📦",
                "label": "Product Insights",
                "queries": [
                    "Which products have the highest profit margin?",
                    "Show average product rating by category as a bar chart",
                    "Which products are running low on stock?",
                    "Correlate product ratings with sales volume",
                    "List the most reviewed products"
                ]
            },
            {
                "emoji": "🛒",
                "label": "Order Analysis",
                "queries": [
                    "What is the order fulfillment rate by status?",
                    "Show order volume by payment method",
                    "Which month had the highest number of orders?",
                    "What is the average order size (items per order)?",
                    "Show cancelled orders trend over time"
                ]
            },
            {
                "emoji": "🏢",
                "label": "Employee & Organization",
                "queries": [
                    "Show average salary by department as a bar chart",
                    "Who are the managers and their direct reports?",
                    "What is the salary distribution across the company?",
                    "Show employee count by department",
                    "Who was hired most recently?"
                ]
            },
            {
                "emoji": "🔗",
                "label": "Relationships & Diagrams",
                "queries": [
                    "Draw the complete ER diagram for this database",
                    "Show the order processing workflow as a flowchart",
                    "Create a decision tree for customer tier classification"
                ]
            }
        ]
    }


@router.get("/stats")
async def stats(request: Request) -> dict[str, Any]:
    """Return row counts per table for the database explorer."""
    db = request.app.state.database
    columns, rows = await db.fetch_all(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    counts = {}
    for row in rows:
        table_name = row["name"]
        _, count_rows = await db.fetch_all(f"SELECT COUNT(*) as cnt FROM {table_name}")
        counts[table_name] = count_rows[0]["cnt"] if count_rows else 0
    return {"tables": counts}
