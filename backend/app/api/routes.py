"""HTTP and SSE routes."""
import json
import re
from typing import Any
import httpx
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Literal
from app.agents.providers import ProviderCandidate, ProviderName
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


def configured_key(value: str) -> bool:
    """Do not advertise copied example values as usable credentials."""
    normalized = value.strip()
    return bool(normalized) and "your_" not in normalized.lower() and "api_key_here" not in normalized.lower()


@router.post("/voice/transcribe")
async def transcribe_voice(audio: UploadFile = File(...)) -> dict[str, str]:
    """Minimal isolated proxy for browser-recorded dictation; it never reaches the chat agent."""
    settings = get_settings()
    if not configured_key(settings.groq_api_key):
        raise HTTPException(status_code=503, detail="Voice transcription needs the existing GROQ_API_KEY.")
    if not (audio.content_type or "").startswith("audio/"):
        raise HTTPException(status_code=415, detail="Please upload a supported audio recording.")
    content = await audio.read()
    await audio.close()
    if not content:
        raise HTTPException(status_code=400, detail="No audio was received.")
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Voice recordings must be 20 MB or smaller.")

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                files={"file": (audio.filename or "mitra-dictation.webm", content, audio.content_type or "audio/webm")},
                data={
                    "model": settings.voice_transcription_model,
                    "language": "en",
                    "prompt": "Transcribe database analytics questions accurately, including SQL terms, table names, and punctuation.",
                },
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Voice transcription is temporarily unavailable.") from exc

    text = response.json().get("text", "")
    return {"text": text.strip() if isinstance(text, str) else ""}


@router.get("/health")
async def health(request: Request) -> dict[str, str]:
    return {"status": "ok", "service": "mitra"}


@router.get("/schema")
async def schema(request: Request) -> dict[str, Any]:
    return await request.app.state.database.get_schema()


@router.get("/providers")
async def providers() -> dict[str, Any]:
    """Return configured AI providers and defaults."""
    settings = get_settings()
    configured_keys = {
        "anthropic": settings.anthropic_api_key.strip(),
        "groq": settings.groq_api_key.strip(),
        "gemini": settings.gemini_api_key.strip()
    }
    configured_models = {
        "anthropic": settings.claude_model,
        "groq": settings.groq_model,
        "gemini": settings.gemini_model
    }
    available = [p for p, k in configured_keys.items() if configured_key(k)]
    default_p = "groq" if "groq" in available else ("gemini" if "gemini" in available else ("anthropic" if "anthropic" in available else "groq"))
    return {
        "default_provider": default_p,
        "available": available,
        "models": configured_models
    }


@router.post("/chat")
async def chat(payload: ChatRequest, request: Request) -> StreamingResponse:
    settings = get_settings()
    configured_keys = {
        "anthropic": settings.anthropic_api_key.strip(),
        "groq": settings.groq_api_key.strip(),
        "gemini": settings.gemini_api_key.strip()
    }
    configured_models = {
        "anthropic": settings.claude_model,
        "groq": settings.groq_model,
        "gemini": settings.gemini_model
    }
    
    user_key = (payload.api_key or "").strip()
    target_provider = payload.provider
    api_key = user_key or configured_keys.get(target_provider, "")
    
    # Auto-fallback to any provider that HAS an active key if the selected one is missing
    if not configured_key(api_key):
        for p in ["groq", "gemini", "anthropic"]:
            if configured_key(configured_keys.get(p, "")):
                target_provider = p
                api_key = configured_keys[p]
                break

    requested_model = payload.model.strip() if payload.model else ""
    # If a missing selected provider was replaced above, use the replacement's model.
    model_to_use = requested_model if requested_model and target_provider == payload.provider else configured_models.get(target_provider, "")
    candidates: list[ProviderCandidate] = []
    if configured_key(api_key):
        candidates.append(ProviderCandidate(name=target_provider, api_key=api_key, model=model_to_use))
    # A failed provider should not make the chat fail when another configured one works.
    for provider in ("groq", "gemini", "anthropic"):
        if provider != target_provider and configured_key(configured_keys.get(provider, "")):
            candidates.append(ProviderCandidate(name=provider, api_key=configured_keys[provider], model=configured_models[provider]))
    
    state = await request.app.state.memory.get(payload.session_id)
    if state.get("provider") not in (None, target_provider):
        state["history"] = []
        await request.app.state.memory.save(payload.session_id, state)
    state["provider"] = target_provider
    await request.app.state.memory.save(payload.session_id, state)
    agent = request.app.state.agent_factory(candidates)
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


@router.get("/tables/{table_name}/rows")
async def table_rows(table_name: str, request: Request, limit: int = 50) -> dict[str, Any]:
    """Return a small, read-only preview after checking the requested table exists."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table_name):
        return {"error": "Invalid table name"}
    schema = await request.app.state.database.get_schema()
    names = {table["name"] for table in schema.get("tables", [])}
    if table_name not in names:
        return {"error": "Table not found"}
    safe_limit = max(1, min(limit, 100))
    columns, rows = await request.app.state.database.fetch_all(f"SELECT * FROM {table_name} LIMIT {safe_limit}")
    return {"columns": columns, "rows": rows, "row_count": len(rows)}


@router.get("/analytics")
async def analytics(request: Request) -> dict[str, Any]:
    """Curated, data-backed visual library shown on the analytics dashboard."""
    definitions = [
        ("Monthly revenue in 2025", "line", "month", "revenue", "SELECT strftime('%Y-%m', sale_date) AS month, ROUND(SUM(revenue), 2) AS revenue FROM sales WHERE strftime('%Y', sale_date) = '2025' GROUP BY month ORDER BY month"),
        ("Revenue by category", "bar", "category", "revenue", "SELECT c.name AS category, ROUND(SUM(s.revenue), 2) AS revenue FROM sales s JOIN products p ON p.id=s.product_id JOIN categories c ON c.id=p.category_id GROUP BY c.name ORDER BY revenue DESC"),
        ("Sales quantity by category", "bar", "category", "quantity", "SELECT c.name AS category, SUM(s.quantity) AS quantity FROM sales s JOIN products p ON p.id=s.product_id JOIN categories c ON c.id=p.category_id GROUP BY c.name ORDER BY quantity DESC"),
        ("Revenue distribution by category", "pie", "category", "revenue", "SELECT c.name AS category, ROUND(SUM(s.revenue), 2) AS revenue FROM sales s JOIN products p ON p.id=s.product_id JOIN categories c ON c.id=p.category_id GROUP BY c.name ORDER BY revenue DESC"),
        ("Top products by revenue", "bar", "product", "revenue", "SELECT p.name AS product, ROUND(SUM(s.revenue), 2) AS revenue FROM sales s JOIN products p ON p.id=s.product_id GROUP BY p.name ORDER BY revenue DESC LIMIT 10"),
        ("Products with lowest stock", "bar", "product", "stock", "SELECT name AS product, stock_quantity AS stock FROM products ORDER BY stock_quantity ASC LIMIT 10"),
        ("Average rating by category", "bar", "category", "rating", "SELECT c.name AS category, ROUND(AVG(p.rating), 2) AS rating FROM products p JOIN categories c ON c.id=p.category_id GROUP BY c.name ORDER BY rating DESC"),
        ("Customer tier distribution", "pie", "tier", "customers", "SELECT tier, COUNT(*) AS customers FROM customers GROUP BY tier ORDER BY customers DESC"),
        ("Customers by city", "bar", "city", "customers", "SELECT city, COUNT(*) AS customers FROM customers GROUP BY city ORDER BY customers DESC"),
        ("Orders by status", "pie", "status", "orders", "SELECT status, COUNT(*) AS orders FROM orders GROUP BY status ORDER BY orders DESC"),
        ("Orders by payment method", "bar", "payment_method", "orders", "SELECT payment_method, COUNT(*) AS orders FROM orders GROUP BY payment_method ORDER BY orders DESC"),
        ("Average order value by customer tier", "bar", "tier", "average_order_value", "SELECT c.tier, ROUND(AVG(o.total_amount), 2) AS average_order_value FROM orders o JOIN customers c ON c.id=o.customer_id GROUP BY c.tier ORDER BY average_order_value DESC"),
        ("Employee count by department", "bar", "department", "employees", "SELECT department, COUNT(*) AS employees FROM employees GROUP BY department ORDER BY employees DESC"),
        ("Average salary by department", "bar", "department", "average_salary", "SELECT department, ROUND(AVG(salary), 2) AS average_salary FROM employees GROUP BY department ORDER BY average_salary DESC"),
    ]
    charts = []
    for title, chart_type, x_field, y_field, sql in definitions:
        _, rows = await request.app.state.database.fetch_all(sql)
        charts.append({"title": title, "type": chart_type, "x_field": x_field, "y_field": y_field, "data": rows})
    return {"charts": charts}
