"""End-to-end agent response evaluator — calls the real LangGraph pipeline."""
import asyncio
from langchain_core.messages import HumanMessage

from careerpilot.orchestrator.graph import build_graph
from careerpilot.orchestrator.state import State
from careerpilot.eval.evaluators.similarity import score_response

_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def _make_state(input_text: str, phase: str = "intake", extra: dict | None = None) -> State:
    base: State = {
        "messages": [HumanMessage(content=input_text)],
        "user_id": "eval_user",
        "intent": "",
        "agent": "",
        "agent_display": "",
        "agent_events": [],
        "intake_complete": phase != "intake",
        "phase": phase,
        "days_since": None,
        "days_left": None,
        "mood_score": None,
        "energy_score": None,
        "open_tasks": None,
        "leetcode_level": None,
        "resume_text": None,
        "linkedin_text": None,
        "role": None,
        "tracking_summary": None,
        "tracking_skills": None,
        "talent_map": None,
        "response": "",
        "sources": [],
        "chips": [],
        "field_key": None,
    }
    if extra:
        base.update(extra)
    return base


async def run_case(case: dict) -> dict:
    """Run a single golden test case through the real agent pipeline."""
    raw_input = case["input"]
    phase = case.get("phase", "intake")

    if isinstance(raw_input, dict):
        # Structured checkin dict — always includes mood/energy so _has_progress_content fires correctly.
        wins = raw_input.get("wins", [])
        blockers = raw_input.get("blockers", [])
        parts = [
            f"Mood: {raw_input.get('mood_score', '?')}/10, Energy: {raw_input.get('energy_score', '?')}/10.",
        ]
        if wins:
            parts.append(f"Wins: {', '.join(wins)}.")
        if blockers:
            parts.append(f"Blockers: {', '.join(blockers)}.")
        input_text = " ".join(parts)
        extra = {
            "mood_score": raw_input.get("mood_score"),
            "energy_score": raw_input.get("energy_score"),
        }
    else:
        # Freeform string input — passed through verbatim so the agent's freeform branch is exercised.
        input_text = raw_input
        extra = {}

    state = _make_state(input_text, phase, extra)

    error = None
    for attempt in range(3):
        try:
            result = await _get_graph().ainvoke(state)
            response = result.get("response", "")
            intent = result.get("intent", "unknown")
            error = None
            break
        except Exception as e:
            error = str(e)
            if "429" in error and attempt < 2:
                import asyncio
                await asyncio.sleep(10 * (attempt + 1))
            else:
                response = ""
                intent = "error"
                break
    sim = score_response(
        response,
        must_contain=case.get("must_contain"),
        must_not_contain=case.get("must_not_contain"),
        must_contain_one_of=case.get("must_contain_one_of"),
    )

    expected_intent = case.get("expected_intent")
    routing_correct = (intent == expected_intent) if expected_intent else None

    return {
        "id": case.get("id", "?"),
        "input": input_text[:100],
        "response_snippet": response[:200] if response else "",
        "intent_routed": intent,
        "routing_correct": routing_correct,
        "similarity": sim,
        "error": error,
        "passed": sim["passed"] and (routing_correct is not False) and error is None,
    }


async def run_dataset(cases: list[dict]) -> dict:
    tasks = [run_case(c) for c in cases]
    results = await asyncio.gather(*tasks)
    results = list(results)

    passed = sum(1 for r in results if r["passed"])
    avg_sim = round(sum(r["similarity"]["avg_similarity"] for r in results) / len(results), 1) if results else 0.0

    return {
        "passed": passed,
        "total": len(results),
        "pass_rate": round(passed / len(results), 3) if results else 0.0,
        "avg_similarity": avg_sim,
        "results": results,
    }
