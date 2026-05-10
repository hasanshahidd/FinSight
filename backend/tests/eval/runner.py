"""Eval runner: walk golden.jsonl, invoke the agent, score, persist results."""

import asyncio
import json
import time
from pathlib import Path

from langchain_core.messages import HumanMessage

from app.agent.graph import get_graph
from app.db.personas import get_persona
from tests.eval.judge import (
    judge_response,
    must_not_violations,
    text_check_facts,
)

_GOLDEN = Path(__file__).parent / "golden.jsonl"
_RESULTS = Path("./data/eval_results.json")


def _load_golden() -> list[dict]:
    cases = []
    for line in _GOLDEN.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            cases.append(json.loads(line))
    return cases


async def _run_one(case: dict) -> dict:
    persona = get_persona(case["user_id"])
    persona_desc = persona.description if persona else ""
    graph = get_graph()
    config = {"configurable": {"thread_id": f"eval:{case['id']}"}}

    started = time.time()
    state = await graph.ainvoke(
        {
            "messages": [HumanMessage(content=case["query"])],
            "user_id": case["user_id"],
            "persona_desc": persona_desc,
            "route": None,
            "rationale": None,
        },
        config=config,
    )
    duration_ms = int((time.time() - started) * 1000)

    final_text = ""
    tools_called: list[str] = []
    for m in state["messages"]:
        if hasattr(m, "tool_calls") and m.tool_calls:
            for tc in m.tool_calls:
                tools_called.append(tc["name"])
        if hasattr(m, "content") and m.content and m.__class__.__name__ == "AIMessage":
            text = m.content if isinstance(m.content, str) else str(m.content)
            if text.strip():
                final_text = text

    actual_route = state.get("route") or "unknown"

    # Routing accuracy
    expected_route = case.get("expected_route")
    if expected_route is None:
        routing_ok = 1.0  # no expectation - pass
    else:
        routing_ok = 1.0 if actual_route == expected_route else 0.0

    # Tool coverage
    expected_tools = set(case.get("expected_tools_subset") or [])
    actual_tools = set(tools_called)
    if not expected_tools:
        tool_coverage = 1.0
    else:
        hit = len(expected_tools & actual_tools)
        tool_coverage = hit / len(expected_tools)

    # Heuristic fact matching
    matched, total = text_check_facts(final_text, case.get("must_contain_facts") or [])
    fact_heuristic = (matched / total) if total else 1.0

    # Forbidden phrases
    bad = must_not_violations(final_text, case.get("must_not_contain") or [])
    safety_heuristic = 1.0 if bad == 0 else 0.0

    # LLM judge
    try:
        judge = await judge_response(case["query"], final_text, case)
        judge_dict = judge.model_dump()
    except Exception as exc:
        judge_dict = {"factual_grounding": 0.5, "helpfulness": 0.5, "safety": 1.0, "rationale": f"judge_error: {exc}"}

    return {
        "id": case["id"],
        "query": case["query"],
        "user_id": case["user_id"],
        "expected_route": expected_route,
        "actual_route": actual_route,
        "rationale": state.get("rationale", ""),
        "tools_called": tools_called,
        "expected_tools": list(expected_tools),
        "duration_ms": duration_ms,
        "scores": {
            "routing_accuracy": routing_ok,
            "tool_coverage": round(tool_coverage, 3),
            "factual_heuristic": round(fact_heuristic, 3),
            "safety_heuristic": round(safety_heuristic, 3),
            "judge_factual_grounding": judge_dict["factual_grounding"],
            "judge_helpfulness": judge_dict["helpfulness"],
            "judge_safety": judge_dict["safety"],
        },
        "judge_rationale": judge_dict.get("rationale", ""),
        "response_excerpt": final_text[:240],
    }


async def run_eval(max_cases: int | None = None) -> dict:
    cases = _load_golden()
    if max_cases:
        cases = cases[:max_cases]

    results = []
    for case in cases:
        try:
            results.append(await _run_one(case))
        except Exception as exc:
            results.append({"id": case["id"], "error": str(exc), "scores": {}})

    # Aggregate
    axes = ["routing_accuracy", "tool_coverage", "factual_heuristic", "safety_heuristic",
            "judge_factual_grounding", "judge_helpfulness", "judge_safety"]
    rolled: dict[str, float] = {}
    for axis in axes:
        vals = [r["scores"].get(axis, 0) for r in results if "scores" in r and r["scores"]]
        rolled[axis] = round(sum(vals) / len(vals), 3) if vals else 0.0

    payload = {
        "ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_cases": len(results),
        "passed": sum(1 for r in results if r.get("scores", {}).get("routing_accuracy", 0) >= 0.5),
        "scoreboard": rolled,
        "results": results,
    }

    _RESULTS.parent.mkdir(parents=True, exist_ok=True)
    _RESULTS.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    payload = asyncio.run(run_eval())
    print(f"Ran {payload['total_cases']} cases.")
    for k, v in payload["scoreboard"].items():
        print(f"  {k:>30s}: {v:.3f}")


if __name__ == "__main__":
    main()
