import pytest
from app.agents.loop import InsightForgeAgent
from app.agents.providers import GroqProvider
from app.core.memory import SessionMemory
from app.tools.registry import build_tool_registry


class Block:
    def __init__(self, **kwargs): self.__dict__.update(kwargs)


class MockClaude:
    def __init__(self): self.calls = 0
    async def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return Block(content=[Block(type="tool_use", id="tool_1", name="execute_query", input={"sql": "SELECT name, category FROM products"})])
        return Block(content=[Block(type="text", text="I found the available products and their categories.")])


class RejectingProvider:
    async def create(self, **kwargs):
        raise RuntimeError("Error code: 401 - invalid x-api-key")


class EmptyResultProvider:
    async def create(self, **kwargs):
        return Block(content=[Block(type="tool_use", id="tool_empty", name="execute_query", input={"sql": "SELECT * FROM sales WHERE 1 = 0"})])


class InvalidSqlProvider:
    def __init__(self): self.calls = 0

    async def create(self, **kwargs):
        self.calls += 1
        return Block(content=[Block(type="tool_use", id="tool_invalid", name="execute_query", input={"sql": "SELECT * FROM sales WHERE date = '2040-01-01'"})])


class CapturingCompletions:
    def __init__(self): self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return Block(choices=[Block(message=Block(content="Done.", tool_calls=[]))])


class CapturingGroqClient:
    def __init__(self): self.chat = Block(completions=CapturingCompletions())


@pytest.mark.asyncio
async def test_end_to_end_agent_tool_turn(adapter):
    agent = InsightForgeAgent(MockClaude(), build_tool_registry(adapter), SessionMemory(), "test")
    events = [event async for event in agent.run("demo", "List products")]
    assert any(event["event"] == "tool_result" for event in events)
    assert any(event["event"] == "token" for event in events)
    assert events[-1]["event"] == "done"


@pytest.mark.asyncio
async def test_agent_returns_actionable_provider_auth_error(adapter):
    agent = InsightForgeAgent(RejectingProvider(), build_tool_registry(adapter), SessionMemory(), "test", "groq")
    events = [event async for event in agent.run("demo", "List products")]
    assert events[-1]["event"] == "done"
    assert events[0]["event"] == "token"
    assert "will not guess or invent" in events[0]["data"]["text"]


@pytest.mark.asyncio
async def test_agent_uses_safe_offline_chart_when_provider_is_unavailable(adapter):
    agent = InsightForgeAgent(RejectingProvider(), build_tool_registry(adapter), SessionMemory(), "test", "groq")
    events = [event async for event in agent.run("demo", "Show monthly revenue trend for 2025 as a line chart")]
    chart = next(event["data"] for event in events if event["event"] == "chart")
    assert chart["type"] == "line"
    assert chart["x_field"] == "month"
    assert events[-1]["event"] == "done"


@pytest.mark.asyncio
async def test_agent_answers_informal_questions_without_a_provider(adapter):
    agent = InsightForgeAgent(RejectingProvider(), build_tool_registry(adapter), SessionMemory(), "test", "groq")
    events = [event async for event in agent.run("demo", "How was your day?")]
    assert events[0]["event"] == "token"
    assert "do not experience days" in events[0]["data"]["text"]
    assert not any(event["event"] == "tool_call" for event in events)


@pytest.mark.asyncio
async def test_agent_explains_zero_row_results_without_chart(adapter):
    agent = InsightForgeAgent(EmptyResultProvider(), build_tool_registry(adapter), SessionMemory(), "test", "groq")
    events = [event async for event in agent.run("demo", "Show average revenue by category")]
    text = next(event["data"]["text"] for event in events if event["event"] == "token")
    assert "no matching records" in text
    assert any(event["event"] == "table" and event["data"]["row_count"] == 0 for event in events)
    assert not any(event["event"] == "chart" for event in events)
    assert any(event["event"] == "suggestions" for event in events)


@pytest.mark.asyncio
async def test_agent_answers_greetings_without_querying_the_database(adapter):
    agent = InsightForgeAgent(RejectingProvider(), build_tool_registry(adapter), SessionMemory(), "test", "groq")
    events = [event async for event in agent.run("demo", "Hi")]
    assert events == [
        {"event": "token", "data": {"text": "Hello! I’m Mitra, your database analytics assistant. Ask me about sales, customers, products, orders, employees, or request a chart."}},
        {"event": "done", "data": {"session_id": "demo"}},
    ]


@pytest.mark.asyncio
async def test_agent_does_not_broaden_a_failed_sql_query(adapter):
    provider = InvalidSqlProvider()
    agent = InsightForgeAgent(provider, build_tool_registry(adapter), SessionMemory(), "test", "groq")
    events = [event async for event in agent.run("demo", "Show average revenue by category")]
    text = next(event["data"]["text"] for event in events if event["event"] == "token")
    assert "could not find" in text.lower()
    assert provider.calls == 1
    assert not any(event["event"] == "table" for event in events)


@pytest.mark.asyncio
async def test_agent_explains_unsupported_database_entities_without_querying(adapter):
    agent = InsightForgeAgent(RejectingProvider(), build_tool_registry(adapter), SessionMemory(), "test", "groq")
    events = [event async for event in agent.run("demo", "Which suppliers have the most late shipments?")]
    assert "does not include supplier" in events[0]["data"]["text"]
    assert not any(event["event"] == "tool_call" for event in events)


@pytest.mark.asyncio
async def test_agent_explains_unavailable_year_before_calling_provider(adapter):
    provider = RejectingProvider()
    agent = InsightForgeAgent(provider, build_tool_registry(adapter), SessionMemory(), "test", "groq")
    events = [event async for event in agent.run("demo", "Show sales for the year 2040")]
    assert "no sales data for 2040" in events[0]["data"]["text"].lower()
    assert not any(event["event"] == "tool_call" for event in events)


@pytest.mark.asyncio
async def test_groq_adapter_preserves_tool_name_in_follow_up_messages():
    provider = GroqProvider("test-key")
    client = CapturingGroqClient()
    provider.client = client
    await provider.create(
        model="test-model",
        max_tokens=10,
        system="test",
        tools=[],
        messages=[
            {"role": "assistant", "content": [{"type": "tool_use", "id": "call_1", "name": "execute_query", "input": {"sql": "SELECT 1"}}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "call_1", "tool_name": "execute_query", "content": "{}"}]},
        ],
    )
    tool_message = client.chat.completions.kwargs["messages"][-1]
    assert tool_message["role"] == "tool"
    assert tool_message["name"] == "execute_query"


def test_offline_result_summary_uses_actual_extremes():
    summary = InsightForgeAgent._offline_result_summary(
        "Revenue by category",
        [{"category": "Books", "revenue": 10}, {"category": "Toys", "revenue": 30}],
        "category",
        "revenue",
    )
    assert "30.00 for Toys" in summary
    assert "10.00 for Books" in summary
