"""Token + USD cost accounting per request and per session.

Reads `usage_metadata` from LangChain AI messages (gpt-4o-mini exposes it)
and converts to USD using a static price table. Aggregates in Redis so the
admin endpoint can roll up across sessions."""

from langchain_core.messages import AIMessage

from app.core.cache import cache_get, cache_set
from app.core.logging import get_logger
from app.core.metrics import LLM_COST_USD_TOTAL, LLM_TOKENS_TOTAL

logger = get_logger(__name__)


# Per-1k-token prices in USD (input, output). Update as needed.
MODEL_PRICES = {
    "gpt-4o-mini": (0.000150, 0.000600),
    "gpt-4o": (0.0025, 0.010),
    "gpt-4-turbo": (0.010, 0.030),
    "gpt-3.5-turbo": (0.0005, 0.0015),
}


def _price_for(model: str) -> tuple[float, float]:
    if model in MODEL_PRICES:
        return MODEL_PRICES[model]
    for prefix, prices in MODEL_PRICES.items():
        if model.startswith(prefix):
            return prices
    return (0.0, 0.0)


def estimate_cost(messages: list, model: str) -> dict:
    """Walk a message list, sum input/output tokens, return cost breakdown."""
    in_tok = out_tok = 0
    for m in messages:
        if not isinstance(m, AIMessage):
            continue
        usage = getattr(m, "usage_metadata", None) or {}
        in_tok += int(usage.get("input_tokens", 0))
        out_tok += int(usage.get("output_tokens", 0))

    p_in, p_out = _price_for(model)
    cost = (in_tok / 1000.0) * p_in + (out_tok / 1000.0) * p_out

    LLM_TOKENS_TOTAL.labels(model=model, kind="input").inc(in_tok)
    LLM_TOKENS_TOTAL.labels(model=model, kind="output").inc(out_tok)
    LLM_COST_USD_TOTAL.labels(model=model).inc(cost)

    return {
        "model": model,
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "total_tokens": in_tok + out_tok,
        "estimated_cost_usd": round(cost, 6),
    }


# ---------------------------------------------------------------------------
# Per-session aggregation in Redis
# ---------------------------------------------------------------------------


_SESSION_KEY = "finsight:cost:session:{session_id}"
_GLOBAL_KEY = "finsight:cost:global"


async def record_session_cost(session_id: str, cost: dict) -> None:
    skey = _SESSION_KEY.format(session_id=session_id)
    cur = (await cache_get(skey)) or {"input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0, "calls": 0}
    cur["input_tokens"] += cost["input_tokens"]
    cur["output_tokens"] += cost["output_tokens"]
    cur["estimated_cost_usd"] = round(cur["estimated_cost_usd"] + cost["estimated_cost_usd"], 6)
    cur["calls"] += 1
    cur["model"] = cost["model"]
    await cache_set(skey, cur, ttl=86400)

    g = (await cache_get(_GLOBAL_KEY)) or {"input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0, "calls": 0}
    g["input_tokens"] += cost["input_tokens"]
    g["output_tokens"] += cost["output_tokens"]
    g["estimated_cost_usd"] = round(g["estimated_cost_usd"] + cost["estimated_cost_usd"], 6)
    g["calls"] += 1
    await cache_set(_GLOBAL_KEY, g, ttl=86400 * 7)


async def get_global_cost() -> dict:
    return (await cache_get(_GLOBAL_KEY)) or {
        "input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0, "calls": 0,
    }


async def get_session_cost(session_id: str) -> dict:
    return (await cache_get(_SESSION_KEY.format(session_id=session_id))) or {
        "input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0, "calls": 0,
    }
