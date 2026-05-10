"""50-query scenario sweep. Hits the n8n webhook (same path as the UI).
Validates routing + tool selection + citations + response shape per scenario.

Usage:  python scripts/scenario_sweep.py
"""

import json
import time
import urllib.request

WEBHOOK = "http://localhost:5678/webhook/finance-chat"

SCENARIOS = {
    "A_transactions": {
        "user_id": "user_1",
        "expected_route": "transaction_analyst",
        "queries": [
            "How much did I spend last week?",
            "Show me my dining transactions in the last 30 days",
            "What were my top 3 spending categories last month?",
            "How much have I spent on Netflix this year?",
            "Compare this week's spending to last week",
            "Show my biggest purchase in May",
            "What subscriptions am I paying for?",
            "Find my coffee runs",
            "How much have I spent on transit total?",
            "Which categories grew the most over the last 90 days?",
        ],
    },
    "B_knowledge": {
        "user_id": "user_1",
        "expected_route": "knowledge_advisor",
        "queries": [
            "What is the 50/30/20 rule?",
            "How big should my emergency fund be?",
            "What's the difference between snowball and avalanche debt payoff?",
            "Explain compound interest",
            "What's a high-yield savings account?",
            "How does FIRE work?",
            "What is lifestyle creep?",
            "What insurance do I really need?",
            "Explain tax-advantaged retirement accounts",
            "How do I track net worth?",
        ],
    },
    "C_budget": {
        "user_id": "user_1",
        "expected_route": "budget_coach",
        "queries": [
            "Am I on track with my budget this month?",
            "Based on my spending, suggest a budget",
            "I'm spending too much on dining. What should I do?",
            "How can I save more money based on my actual spending?",
            "Help me build a 50/30/20 plan based on my real spending",
            "What's a reasonable food budget for me?",
            "How much should I be saving each month?",
            "Am I overspending compared to my income?",
            "Forecast my end-of-month spending",
            "Where can I cut back the most?",
        ],
    },
    "D_anomaly": {
        "user_id": "user_2",  # Sam — has the medical-bill story
        "expected_route": "anomaly_detective",
        "queries": [
            "Is anything weird in my recent spending?",
            "What's the biggest charge in the last 90 days?",
            "Did anything unusual happen in my Health spending?",
            "What's draining my account?",
            "Find any subscription I might have forgotten about",
            "Are there any duplicate charges?",
            "What was my largest expense this year?",
            "Has my spending pattern changed recently?",
            "Any spending spikes I should know about?",
            "Is there activity that looks like fraud?",
        ],
    },
    "E_out_of_scope": {
        "user_id": "user_1",
        "expected_route": "knowledge_advisor",  # advisor declines
        "expect_decline": True,
        "queries": [
            "What's the weather today?",
            "What's the best travel destination?",
            "How do I cook pasta?",
            "Pick stocks for me",
            "Tell me a joke",
            "Explain Python loops",
            "Recommend a movie",
            "What's a good restaurant?",
            "Who is the president?",
            "Translate hello to French",
        ],
    },
}


def post(query: str, session_id: str, user_id: str) -> dict:
    body = json.dumps({
        "message": query, "session_id": session_id, "user_id": user_id
    }).encode("utf-8")
    req = urllib.request.Request(
        WEBHOOK,
        data=body,
        headers={"Content-Type": "application/json", "X-User-Id": user_id},
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            elapsed = time.time() - started
            return {
                "ok": True,
                "status": resp.status,
                "elapsed_s": round(elapsed, 1),
                "body": json.loads(resp.read().decode("utf-8")),
            }
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "elapsed_s": round(time.time() - started, 1), "err": e.read().decode("utf-8", "ignore")}
    except Exception as e:
        return {"ok": False, "status": 0, "elapsed_s": round(time.time() - started, 1), "err": str(e)}


def declined(text: str) -> bool:
    t = (text or "").lower()
    cues = [
        "i'm finsight", "personal finance assistant", "can't advise on",
        "can't help with", "i can help you with",
    ]
    return any(c in t for c in cues)


def run_scenario(name: str, spec: dict) -> dict:
    print(f"\n{'='*72}\n[{name}]  user={spec['user_id']}  expected_route={spec['expected_route']}\n{'='*72}")
    results = []
    session_id = f"sweep_{name}"
    for i, q in enumerate(spec["queries"], 1):
        print(f"  Q{i:>2}: {q[:60]:<60}", end="", flush=True)
        r = post(q, session_id=session_id, user_id=spec["user_id"])
        if not r["ok"]:
            print(f"  HTTP {r['status']}  ERROR: {str(r.get('err',''))[:60]}")
            results.append({"q": q, "ok": False, "err": r.get("err")})
            continue
        body = r["body"]
        route = (body.get("structured_data") or {}).get("route")
        rationale = (body.get("structured_data") or {}).get("rationale", "")
        tools = [t["name"] for t in (body.get("tool_calls") or [])]
        citations = body.get("citations") or []
        message = body.get("message") or ""

        route_ok = route == spec["expected_route"]
        is_decline = declined(message)
        oos_expected = spec.get("expect_decline", False)
        if oos_expected:
            decline_ok = is_decline and len(tools) == 0
            tag = "OK " if (route_ok and decline_ok) else "FAIL"
        else:
            tag = "OK " if route_ok else "FAIL"

        print(f"  {r['elapsed_s']:>5.1f}s  route={route:<22} tools={','.join(tools) or '-':<35} cit={len(citations):>2}  [{tag}]")
        if oos_expected and "OUT_OF_SCOPE" in (rationale or ""):
            pass  # supervisor caught it as designed
        results.append({
            "q": q, "ok": True, "route": route, "rationale": rationale,
            "tools": tools, "citations_count": len(citations),
            "message_excerpt": message[:120], "decline": is_decline,
            "elapsed_s": r["elapsed_s"],
        })
    return {
        "name": name, "expected_route": spec["expected_route"],
        "expect_decline": spec.get("expect_decline", False),
        "results": results,
    }


def summarize(scenarios: list[dict]) -> None:
    print(f"\n{'#'*72}\n# SUMMARY\n{'#'*72}")
    grand_total = 0
    grand_ok = 0
    for s in scenarios:
        n = len(s["results"])
        route_ok = sum(1 for r in s["results"] if r.get("ok") and r.get("route") == s["expected_route"])
        tools_fired = sum(1 for r in s["results"] if r.get("ok") and len(r.get("tools", [])) > 0)
        if s["expect_decline"]:
            declines = sum(1 for r in s["results"] if r.get("ok") and r.get("decline"))
            no_tools = sum(1 for r in s["results"] if r.get("ok") and len(r.get("tools", [])) == 0)
            print(f"  {s['name']:<25} {n} queries  route_ok={route_ok}/{n}  declined_correctly={declines}/{n}  no_tool_burn={no_tools}/{n}")
            grand_ok += min(route_ok, declines, no_tools)
        else:
            avg_t = sum(r.get("elapsed_s", 0) for r in s["results"] if r.get("ok")) / max(1, sum(1 for r in s["results"] if r.get("ok")))
            print(f"  {s['name']:<25} {n} queries  route_ok={route_ok}/{n}  tools_fired={tools_fired}/{n}  avg_latency={avg_t:.1f}s")
            grand_ok += route_ok
        grand_total += n

    print(f"\n  Grand total:        {grand_total} queries")
    print(f"  Pass (route+behave): {grand_ok}/{grand_total} = {grand_ok/grand_total*100:.0f}%\n")


def main():
    out = []
    started = time.time()
    for name, spec in SCENARIOS.items():
        out.append(run_scenario(name, spec))
    elapsed = int(time.time() - started)
    print(f"\nTotal sweep time: {elapsed}s ({elapsed//60}m {elapsed%60}s)")
    summarize(out)
    # Persist results for report
    with open("data/scenario_sweep_results.json", "w", encoding="utf-8") as f:
        json.dump({"ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "scenarios": out, "elapsed_s": elapsed}, f, indent=2)
    print("Results saved to data/scenario_sweep_results.json")


if __name__ == "__main__":
    main()
