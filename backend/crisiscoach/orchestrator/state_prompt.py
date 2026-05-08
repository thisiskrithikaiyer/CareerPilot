"""Converts CrisisCoachState into a reusable prompt context block.

Every agent and the supervisor calls `state_to_prompt(state)` instead of
building its own snippet — single source of truth for what context the LLM sees.
"""
from crisiscoach.orchestrator.state import CrisisCoachState

# Ordered list of (state_key, display_label, formatter)
_FIELDS: list[tuple[str, str, callable]] = [
    ("phase",          "Phase",                   str),
    ("days_since",     "Days into search",         str),
    ("days_left",      "Days left to offer",       str),
    ("mood_score",     "Last mood",                lambda v: f"{v}/10"),
    ("energy_score",   "Last energy",              lambda v: f"{v}/10"),
    ("open_tasks",     "Open plan tasks",          str),
    ("intake_complete","Intake complete",          str),
    ("tracking_skills","Skills",                   lambda v: ", ".join(f"{k}: {val}" for k, val in v.items()) if v else None),
]


def state_to_prompt(state: CrisisCoachState) -> str:
    """Return a formatted context block from state, skipping None/empty values."""
    lines = []
    for key, label, fmt in _FIELDS:
        val = state.get(key)
        if val is None:
            continue
        formatted = fmt(val)
        if formatted:
            lines.append(f"{label}: {formatted}")
    return "\n".join(lines)
