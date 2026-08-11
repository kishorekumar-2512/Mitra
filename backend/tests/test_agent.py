import pytest
from app.agents.loop import InsightForgeAgent
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
    assert events == [{"event": "error", "data": {"message": "Groq rejected this API key. Select the matching provider and paste a valid key, or update the corresponding server environment variable."}}]
