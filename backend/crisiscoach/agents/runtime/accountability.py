from langchain_core.messages import HumanMessage
"""Accountability agent — reviews task progress and adjusts the plan."""
from crisiscoach.utils.groq_client import groq_complete
from crisiscoach.config import GROQ_MODEL
from crisiscoach.orchestrator.state import CrisisCoachState
from crisiscoach.prompts.loader import load_prompt


async def run(state: CrisisCoachState) -> dict:
    last_msg = next(
        (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None
    )
    content = last_msg.content if last_msg else ""

    base = load_prompt("accountability.txt")
    open_tasks = state.get("open_tasks")
    task_context = f"\nUser has {open_tasks} open tasks from their current plan." if open_tasks else ""
    system = base + task_context

    history = [
        {"role": "user" if isinstance(m, HumanMessage) else "assistant", "content": m.content}
        for m in state["messages"]
    ]
    resp = groq_complete(
        model=GROQ_MODEL,
        max_tokens=512,
        messages=[{"role": "system", "content": system}, *history],
    )
    return {"response": resp.choices[0].message.content, "sources": []}
