"""Shared tool types."""
from typing import Any, Awaitable, Callable
from pydantic import BaseModel

ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


def tool_error(message: str, recoverable: bool = True) -> dict[str, Any]:
    """Return the uniform non-throwing tool failure contract."""
    return {"error": True, "message": message, "recoverable": recoverable}


class EmptyInput(BaseModel):
    """Schema for a tool that takes no inputs."""
    pass
