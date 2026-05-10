"""TransactionAnalyst — ReAct subgraph."""

from langchain_core.language_models import BaseChatModel

from app.agent.specialists.base import build_specialist
from app.agent.tools import TRANSACTION_ANALYST_TOOLS


def build(llm: BaseChatModel, user_id: str, persona_desc: str = ""):
    return build_specialist(
        "transaction_analyst", llm, TRANSACTION_ANALYST_TOOLS, user_id, persona_desc
    )
