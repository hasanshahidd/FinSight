"""Chat / agent request & response schemas."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str
    session_id: str = Field(default="default")
    user_id: str = Field(default="user_1")


class ToolCallTrace(BaseModel):
    """A single tool invocation captured during agent execution - surfaced to the UI."""
    name: str
    args: dict[str, Any]
    result_preview: str
    duration_ms: int | None = None


class ChatResponse(BaseModel):
    message: str
    session_id: str
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    structured_data: dict[str, Any] | None = None  # charts/tables for the UI to render


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: str
