"""Common factory for specialist ReAct subgraphs."""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

from app.agent.prompts import load_prompt
from app.config import settings


def build_specialist(name: str, llm: BaseChatModel, tools: list, user_id: str, persona_desc: str = ""):
    """Compile a ReAct agent for a specialist with its prompt + tool subset."""
    prompt = load_prompt(name, user_id=user_id, persona_desc=persona_desc)
    return create_react_agent(
        llm,
        tools=tools,
        state_modifier=SystemMessage(content=prompt),
    )
