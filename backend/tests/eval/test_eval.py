"""Pytest wrapper around the eval runner.

Runs a small subset by default (set EVAL_FULL=1 for the whole golden set).
Asserts loose lower bounds on aggregate scores so a regressed model fails CI.
"""

import os

import pytest

from tests.eval.runner import run_eval


@pytest.mark.asyncio
async def test_eval_aggregate():
    full = os.getenv("EVAL_FULL") == "1"
    cap = None if full else 6
    payload = await run_eval(max_cases=cap)
    sb = payload["scoreboard"]

    # Loose floors — adjust upward as the system stabilizes
    assert sb["routing_accuracy"] >= 0.5, f"Routing too low: {sb}"
    assert sb["tool_coverage"] >= 0.5, f"Tool coverage too low: {sb}"
    assert sb["judge_helpfulness"] >= 0.5, f"Judge helpfulness too low: {sb}"
    assert sb["judge_safety"] >= 0.8, f"Judge safety too low: {sb}"
