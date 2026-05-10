"""Supervisor: classifies the user's question and picks one specialist."""

from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.agent.prompts import load_prompt
from app.config import settings


class RouteDecision(BaseModel):
    specialist: Literal[
        "transaction_analyst",
        "knowledge_advisor",
        "budget_coach",
        "anomaly_detective",
    ] = Field(description="Which specialist will best answer the user's last message")
    rationale: str = Field(description="One short sentence (<=20 words) on why")


def _supervisor_llm():
    return ChatOpenAI(
        model=settings.llm_model,
        temperature=0.0,
        api_key=settings.openai_api_key,
        timeout=30,
    ).with_structured_output(RouteDecision)


async def route(messages: list, user_id: str = "user_1", persona_desc: str = "") -> RouteDecision:
    """Run the supervisor on the conversation and return its routing decision."""
    last_user = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)),
        None,
    )
    if last_user is None:
        return RouteDecision(specialist="transaction_analyst", rationale="default - no human message")

    prompt = load_prompt("supervisor", user_id=user_id, persona_desc=persona_desc)
    decision = await _supervisor_llm().ainvoke([
        SystemMessage(content=prompt),
        HumanMessage(content=last_user.content if isinstance(last_user.content, str) else str(last_user.content)),
    ])
    return decision
