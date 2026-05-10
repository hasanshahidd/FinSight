"""Admin endpoints: cost rollup, eval scoreboard."""

import json
from pathlib import Path

from fastapi import APIRouter

from app.core.cost import get_global_cost, get_session_cost

router = APIRouter()

_EVAL_RESULTS_PATH = Path("./data/eval_results.json")


@router.get("/cost")
async def cost_rollup(session_id: str | None = None) -> dict:
    if session_id:
        return await get_session_cost(session_id)
    return await get_global_cost()


@router.get("/eval")
async def eval_scoreboard() -> dict:
    """Return the most recent eval-run results, if any."""
    if not _EVAL_RESULTS_PATH.exists():
        return {
            "status": "no_runs",
            "message": "No eval runs yet. Run `pytest tests/eval` to generate.",
            "scores": None,
        }
    try:
        return json.loads(_EVAL_RESULTS_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
