"""Provider adapters that normalize Anthropic, Groq and Gemini function calls."""
import json
from typing import Any, Literal, Protocol
import httpx
from anthropic import AsyncAnthropic
from groq import AsyncGroq

ProviderName = Literal["anthropic", "groq", "gemini"]


class ProviderClient(Protocol):
    """Provider-neutral boundary used by the agent loop."""
    async def create(self, *, model: str, max_tokens: int, system: str, tools: list[dict[str, Any]], messages: list[dict[str, Any]]) -> dict[str, Any]: ...


def _field(value: Any, name: str, default: Any = None) -> Any:
    return value.get(name, default) if isinstance(value, dict) else getattr(value, name, default)


class AnthropicProvider:
    """Claude Messages API adapter."""
    def __init__(self, api_key: str) -> None: self.client = AsyncAnthropic(api_key=api_key)

    async def create(self, **kwargs: Any) -> dict[str, Any]:
        response = await self.client.messages.create(**kwargs)
        content: list[dict[str, Any]] = []
        for block in response.content:
            if block.type == "text": content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use": content.append({"type": "tool_use", "id": block.id, "name": block.name, "input": block.input})
        return {"content": content}


class GroqProvider:
    """Groq's OpenAI-compatible chat-completions tool-call adapter."""
    def __init__(self, api_key: str) -> None: self.client = AsyncGroq(api_key=api_key)

    async def create(self, *, model: str, max_tokens: int, system: str, tools: list[dict[str, Any]], messages: list[dict[str, Any]]) -> dict[str, Any]:
        groq_messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
        for message in messages:
            content = message["content"]
            if message["role"] == "assistant":
                blocks = content if isinstance(content, list) else [{"type": "text", "text": content}]
                text = "".join(block.get("text", "") for block in blocks if block.get("type") == "text")
                calls = [{"id": block["id"], "type": "function", "function": {"name": block["name"], "arguments": json.dumps(block["input"])}} for block in blocks if block.get("type") == "tool_use"]
                groq_messages.append({"role": "assistant", "content": text or None, **({"tool_calls": calls} if calls else {})})
            elif isinstance(content, list):
                for result in content:
                    groq_messages.append({"role": "tool", "tool_call_id": result["tool_use_id"], "content": result["content"]})
            else:
                groq_messages.append({"role": "user", "content": content})
        groq_tools = [{"type": "function", "function": {"name": tool["name"], "description": tool["description"], "parameters": tool["input_schema"]}} for tool in tools]
        response = await self.client.chat.completions.create(model=model, max_tokens=max_tokens, messages=groq_messages, tools=groq_tools)
        message = response.choices[0].message
        content = ([{"type": "text", "text": message.content}] if message.content else [])
        for call in message.tool_calls or []:
            try: arguments = json.loads(call.function.arguments)
            except json.JSONDecodeError: arguments = {}
            content.append({"type": "tool_use", "id": call.id, "name": call.function.name, "input": arguments})
        return {"content": content}


class GeminiProvider:
    """Gemini REST adapter using function declarations and function-response parts."""
    def __init__(self, api_key: str) -> None: self.api_key = api_key

    async def create(self, *, model: str, max_tokens: int, system: str, tools: list[dict[str, Any]], messages: list[dict[str, Any]]) -> dict[str, Any]:
        contents: list[dict[str, Any]] = []
        for message in messages:
            content = message["content"]
            if message["role"] == "assistant":
                blocks = content if isinstance(content, list) else [{"type": "text", "text": content}]
                parts = ([{"text": block["text"]} for block in blocks if block.get("type") == "text"] + [{"functionCall": {"id": block["id"], "name": block["name"], "args": block["input"]}} for block in blocks if block.get("type") == "tool_use"])
                contents.append({"role": "model", "parts": parts})
            elif isinstance(content, list):
                function_results = [
                    {"functionResponse": {
                        "id": result["tool_use_id"],
                        "name": result["tool_name"],
                        "response": {"result": json.loads(result["content"])},
                    }}
                    for result in content
                ]
                contents.append({"role": "user", "parts": function_results})
            else:
                contents.append({"role": "user", "parts": [{"text": content}]})
        declarations = [{"name": tool["name"], "description": tool["description"], "parameters": tool["input_schema"]} for tool in tools]
        body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": contents, "tools": [{"functionDeclarations": declarations}], "generationConfig": {"maxOutputTokens": max_tokens}}
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, params={"key": self.api_key}, json=body)
            response.raise_for_status()
        parts = response.json()["candidates"][0]["content"].get("parts", [])
        content = []
        for index, part in enumerate(parts):
            if "text" in part: content.append({"type": "text", "text": part["text"]})
            if "functionCall" in part:
                call = part["functionCall"]
                content.append({"type": "tool_use", "id": call.get("id", f"gemini-{index}"), "name": call["name"], "input": call.get("args", {})})
        return {"content": content}


def build_provider(provider: ProviderName, api_key: str) -> ProviderClient:
    """Instantiate one provider without exposing API keys to persistence layers."""
    if provider == "anthropic": return AnthropicProvider(api_key)
    if provider == "groq": return GroqProvider(api_key)
    return GeminiProvider(api_key)
