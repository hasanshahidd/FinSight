"""KnowledgeAdvisor — ReAct subgraph."""

from langchain_core.language_models import BaseChatModel

from app.agent.specialists.base import build_specialist
from app.agent.tools import KNOWLEDGE_ADVISOR_TOOLS


def build(llm: BaseChatModel, user_id: str, persona_desc: str = ""):
    return build_specialist(
        "knowledge_advisor", llm, KNOWLEDGE_ADVISOR_TOOLS, user_id, persona_desc
    )
