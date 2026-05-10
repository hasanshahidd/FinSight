"""System prompts for the FinSight multi-agent graph.

Each prompt lives in its own .md file to keep them version-controllable and
human-readable. `load_prompt(name)` reads, formats, and returns the text."""

from datetime import datetime, timezone
from pathlib import Path

_DIR = Path(__file__).parent


def _format_context(name: str, user_id: str, persona_desc: str = "") -> str:
    today = datetime.now(timezone.utc).date().isoformat()
    return (
        f"---\n"
        f"You are operating in the FinSight multi-agent system.\n"
        f"Active user_id: {user_id}\n"
        f"Persona context: {persona_desc or '(none)'}\n"
        f"Today is: {today}\n"
        f"When you call tools, ALWAYS pass user_id=\"{user_id}\".\n"
        f"---\n\n"
    )


def load_prompt(name: str, user_id: str = "user_1", persona_desc: str = "") -> str:
    """Load a prompt by short name (e.g. 'supervisor', 'budget_coach')."""
    path = _DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"prompt not found: {name}")
    body = path.read_text(encoding="utf-8")
    return _format_context(name, user_id, persona_desc) + body
