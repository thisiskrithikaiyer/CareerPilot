"""Evaluates whether the supervisor routes messages to the correct agent."""
from crisiscoach.orchestrator.supervisor import decide
from crisiscoach.orchestrator.state import CrisisCoachState
from langchain_core.messages import HumanMessage


def _make_eval_state(text: str, phase: str = "active") -> CrisisCoachState:
    return {
        "messages": [HumanMessage(content=text)],
        "user_id": "eval",
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


def score_routing(test_cases: list[dict]) -> dict:
    """
    test_cases: [{"input": "...", "expected_intent": "...", "phase": "active"}]
    Returns accuracy metrics and per-case results.
    """
    correct = 0
    results = []
    for case in test_cases:
        input_text = case["input"] if isinstance(case["input"], str) else str(case["input"])
        phase = case.get("phase", "active")
        state = _make_eval_state(input_text, phase)
        predicted, reason = decide(state)
        expected = case["expected_intent"]
        is_correct = predicted == expected
        correct += int(is_correct)
        results.append({
            "id": case.get("id", "?"),
            "input": input_text[:80],
            "expected": expected,
            "predicted": predicted,
            "reason": reason,
            "correct": is_correct,
        })

    accuracy = correct / len(test_cases) if test_cases else 0
    return {
        "accuracy": round(accuracy, 3),
        "correct": correct,
        "total": len(test_cases),
        "results": results,
    }
