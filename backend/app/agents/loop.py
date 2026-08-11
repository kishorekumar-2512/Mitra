"""Small, testable hand-rolled multi-provider tool loop."""
import json
import logging
from collections.abc import AsyncIterator
from typing import Any
from app.agents.providers import ProviderClient
from app.agents.system_prompt import SYSTEM_PROMPT
from app.core.memory import SessionMemory
from app.tools.registry import ToolDefinition, anthropic_tools

logger = logging.getLogger(__name__)


class InsightForgeAgent:
    """Coordinates one provider and five flat tools while emitting UI-friendly SSE payloads."""
    def __init__(self, client: ProviderClient, registry: dict[str, ToolDefinition], memory: SessionMemory, model: str, provider: str = "LLM") -> None:
        self.client, self.registry, self.memory, self.model = client, registry, memory, model
        self.provider = provider

    async def run(self, session_id: str, message: str) -> AsyncIterator[dict[str, Any]]:
        state = await self.memory.get(session_id)
        messages: list[dict[str, Any]] = state["history"][-12:] + [{"role": "user", "content": message}]
        retries = 0
        for _ in range(8):
            try:
                response = await self.client.create(
                    model=self.model, max_tokens=1024, system=SYSTEM_PROMPT,
                    tools=anthropic_tools(self.registry), messages=messages,
                )
            except Exception as exc:
                logger.warning("%s provider request failed: %s", self.provider, exc)
                yield {"event": "error", "data": {"message": self._provider_error(exc)}}
                return
            content = self._content(response)
            tool_blocks = [block for block in content if self._kind(block) == "tool_use"]
            text_blocks = [self._text(block) for block in content if self._kind(block) == "text" and self._text(block)]
            for token in text_blocks:
                yield {"event": "token", "data": {"text": token}}
            if not tool_blocks:
                messages.append({"role": "assistant", "content": content})
                state["history"] = messages[-12:]
                state["query_history"].append({"question": message, "summary": "".join(text_blocks)[:500]})
                state["query_history"] = state["query_history"][-20:]
                await self.memory.save(session_id, state)
                yield {"event": "done", "data": {"session_id": session_id}}
                return
            messages.append({"role": "assistant", "content": content})
            results: list[dict[str, Any]] = []
            retry_needed = False
            for block in tool_blocks:
                name, tool_id, tool_input = self._name(block), self._id(block), self._input(block)
                yield {"event": "tool_call", "data": {"name": name, "input": tool_input}}
                tool = self.registry.get(name)
                if tool is None:
                    result = {"error": True, "message": f"Unknown tool {name}", "recoverable": False}
                else:
                    try:
                        result = await tool.handler(tool.input_model.model_validate(tool_input))
                    except Exception as exc:
                        result = {"error": True, "message": f"Invalid input for {name}: {exc}", "recoverable": True}
                if result.get("error") and result.get("recoverable"):
                    retry_needed = True
                if name == "execute_query" and not result.get("error"):
                    state["last_result"] = result
                    yield {"event": "sql", "data": {"sql": result.get("sql", tool_input.get("sql", ""))}}
                if name == "generate_chart" and not result.get("error"):
                    yield {"event": "chart", "data": result}
                if name == "generate_flowchart" and not result.get("error"):
                    yield {"event": "diagram", "data": result}
                yield {"event": "tool_result", "data": {"name": name, "result": result}}
                results.append({"type": "tool_result", "tool_use_id": tool_id, "tool_name": name, "content": json.dumps(result, default=str), "is_error": bool(result.get("error"))})
            messages.append({"role": "user", "content": results})
            if retry_needed:
                if retries >= 1:
                    yield {"event": "error", "data": {"message": "A tool could not complete after one correction attempt."}}
                    return
                retries += 1
        yield {"event": "error", "data": {"message": "Agent exceeded its tool-call limit."}}

    @staticmethod
    def _field(value: Any, name: str, default: Any = None) -> Any:
        """Read from Anthropic SDK objects or light-weight dict mocks without eager defaults."""
        return value.get(name, default) if isinstance(value, dict) else getattr(value, name, default)

    @classmethod
    def _content(cls, response: Any) -> list[Any]: return list(cls._field(response, "content", []))
    @classmethod
    def _kind(cls, block: Any) -> str: return cls._field(block, "type")
    @classmethod
    def _text(cls, block: Any) -> str: return cls._field(block, "text", "")
    @classmethod
    def _name(cls, block: Any) -> str: return cls._field(block, "name")
    @classmethod
    def _id(cls, block: Any) -> str: return cls._field(block, "id")
    @classmethod
    def _input(cls, block: Any) -> dict[str, Any]: return cls._field(block, "input", {})

    def _provider_error(self, error: Exception) -> str:
        """Convert upstream errors into actionable messages without exposing request IDs."""
        detail = str(error).lower()
        name = self.provider.title()
        if "401" in detail or "authentication" in detail or "invalid api key" in detail or "invalid x-api-key" in detail:
            return f"{name} rejected this API key. Select the matching provider and paste a valid key, or update the corresponding server environment variable."
        if "429" in detail or "rate limit" in detail or "quota" in detail:
            return f"{name} is rate-limiting this request or the account has no remaining quota. Try again shortly or select another provider."
        if "403" in detail or "permission" in detail or "forbidden" in detail:
            return f"This {name} key does not have permission to use the selected model. Check its project/model permissions or select another model."
        if "400" in detail or "invalid request" in detail or "bad request" in detail:
            return f"{name} rejected the request format. Try the provider’s suggested model; the server terminal contains the detailed provider response."
        if "404" in detail or "not found" in detail or "model" in detail:
            return f"The selected {name} model is unavailable for this key. Choose a model available in that provider account."
        return f"{name} could not complete the request. Check the provider key, model name, and server terminal for details."
