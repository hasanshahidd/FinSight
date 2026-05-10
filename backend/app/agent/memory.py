"""Summary-buffer compaction: when message history exceeds threshold, replace
the oldest N messages with a single SystemMessage summary."""

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import settings

MAX_MESSAGES_BEFORE_COMPACT = 40
KEEP_RECENT = 16


_summary_llm = None


def _llm():
    global _summary_llm
    if _summary_llm is None:
        _summary_llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=0.0,
            api_key=settings.openai_api_key,
            timeout=30,
        )
    return _summary_llm


async def maybe_compact(messages: list[AnyMessage]) -> list[AnyMessage]:
    """If `messages` exceeds threshold, summarize the oldest portion."""
    if len(messages) <= MAX_MESSAGES_BEFORE_COMPACT:
        return messages

    older = messages[:-KEEP_RECENT]
    recent = messages[-KEEP_RECENT:]

    convo_text = []
    for m in older:
        if isinstance(m, HumanMessage):
            convo_text.append(f"User: {m.content}")
        elif isinstance(m, AIMessage):
            convo_text.append(f"Assistant: {m.content}")
    convo = "\n".join(convo_text)[:6000]

    prompt = (
        "Summarize the following finance-assistant conversation in <= 200 words. "
        "Preserve: dollar amounts the user has been told, recurring topics, the "
        "user's stated goals or preferences, anything labelled 'remember this'. "
        "Drop pleasantries.\n\nCONVERSATION:\n" + convo
    )
    summary_msg = await _llm().ainvoke([SystemMessage(content=prompt)])
    summary_text = summary_msg.content if isinstance(summary_msg.content, str) else str(summary_msg.content)

    digest = SystemMessage(
        content=(
            "Earlier in this conversation:\n"
            f"{summary_text}\n\n"
            "(history before this point has been summarized for context length; "
            "the user's most recent messages follow.)"
        )
    )
    return [digest, *recent]
