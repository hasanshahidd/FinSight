"""Multi-agent supergraph: supervisor → conditional → specialist → END.

The graph is per-user (instances are cached). The supervisor's routing
decision is a model call (no hardcoded if/else). Specialists are LangGraph
ReAct agents with focused tool subsets. Memory is per-thread via
MemorySaver (process-local; demo-grade).
"""

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.agent.memory import maybe_compact
from app.agent.specialists import (
    anomaly_detective,
    budget_coach,
    knowledge_advisor,
    transaction_analyst,
)
from app.agent.supervisor import RouteDecision, route as supervisor_route
from app.config import settings


SpecialistId = Literal[
    "transaction_analyst",
    "knowledge_advisor",
    "budget_coach",
    "anomaly_detective",
]


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    user_id: str
    persona_desc: str
    route: SpecialistId | None
    rationale: str | None


def _llm():
    return ChatOpenAI(
        model=settings.llm_model,
        temperature=0.2,
        api_key=settings.openai_api_key,
        timeout=60,
    )


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


async def supervisor_node(state: AgentState) -> dict:
    decision: RouteDecision = await supervisor_route(
        state["messages"], user_id=state.get("user_id", "user_1"),
        persona_desc=state.get("persona_desc", ""),
    )
    return {"route": decision.specialist, "rationale": decision.rationale}


def _make_specialist_node(builder):
    async def node(state: AgentState) -> dict:
        compacted = await maybe_compact(state["messages"])
        agent = builder(_llm(), state.get("user_id", "user_1"), state.get("persona_desc", ""))
        result = await agent.ainvoke({"messages": compacted})
        return {"messages": result["messages"]}
    return node


def _route_decider(state: AgentState) -> str:
    return state.get("route") or "transaction_analyst"


# ---------------------------------------------------------------------------
# Compile
# ---------------------------------------------------------------------------


_graph = None


def get_graph():
    """Compile (once) and return the multi-agent graph."""
    global _graph
    if _graph is not None:
        return _graph

    builder = StateGraph(AgentState)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("transaction_analyst", _make_specialist_node(transaction_analyst.build))
    builder.add_node("knowledge_advisor", _make_specialist_node(knowledge_advisor.build))
    builder.add_node("budget_coach", _make_specialist_node(budget_coach.build))
    builder.add_node("anomaly_detective", _make_specialist_node(anomaly_detective.build))

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        _route_decider,
        {
            "transaction_analyst": "transaction_analyst",
            "knowledge_advisor": "knowledge_advisor",
            "budget_coach": "budget_coach",
            "anomaly_detective": "anomaly_detective",
        },
    )
    builder.add_edge("transaction_analyst", END)
    builder.add_edge("knowledge_advisor", END)
    builder.add_edge("budget_coach", END)
    builder.add_edge("anomaly_detective", END)

    _graph = builder.compile(checkpointer=MemorySaver())
    return _graph
