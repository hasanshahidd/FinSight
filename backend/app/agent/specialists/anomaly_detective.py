"""AnomalyDetective - ReAct subgraph."""

from langchain_core.language_models import BaseChatModel

from app.agent.specialists.base import build_specialist
from app.agent.tools import ANOMALY_DETECTIVE_TOOLS


def build(llm: BaseChatModel, user_id: str, persona_desc: str = ""):
    return build_specialist(
        "anomaly_detective", llm, ANOMALY_DETECTIVE_TOOLS, user_id, persona_desc
    )
