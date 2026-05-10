"""Custom Prometheus metrics for FinSight.

These complement the default HTTP metrics exposed by
`prometheus-fastapi-instrumentator`."""

from prometheus_client import Counter, Histogram

CHAT_REQUESTS_TOTAL = Counter(
    "finsight_chat_requests_total",
    "Total chat requests received",
    ["transport", "route", "status"],
)

CHAT_DURATION_SECONDS = Histogram(
    "finsight_chat_duration_seconds",
    "Chat request end-to-end latency",
    ["route"],
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 60),
)

TOOL_INVOCATIONS_TOTAL = Counter(
    "finsight_tool_invocations_total",
    "Tool invocations by name",
    ["tool", "status"],
)

LLM_TOKENS_TOTAL = Counter(
    "finsight_llm_tokens_total",
    "Tokens consumed by LLM calls",
    ["model", "kind"],  # kind ∈ {input, output}
)

LLM_COST_USD_TOTAL = Counter(
    "finsight_llm_cost_usd_total",
    "Approximate LLM cost in USD",
    ["model"],
)

RAG_RETRIEVAL_DURATION_SECONDS = Histogram(
    "finsight_rag_retrieval_duration_seconds",
    "Hybrid retrieval latency",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2),
)

CACHE_EVENTS_TOTAL = Counter(
    "finsight_cache_events_total",
    "Cache hits and misses",
    ["layer", "kind"],
)
