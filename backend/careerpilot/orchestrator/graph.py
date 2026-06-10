"""LangGraph graph definition for CrisisCoach."""
import importlib
from langgraph.graph import StateGraph, END

from careerpilot.orchestrator.state import State
from careerpilot.orchestrator.orchestrator import orchestrator_node, AGENT_MAP


def _make_agent_node(module_path: str):
    """Dynamically import and wrap an agent's `run` coroutine as a LangGraph node."""
    async def node(state: State) -> dict:
        mod = importlib.import_module(module_path)
        return await mod.run(state)
    node.__name__ = module_path.split(".")[-1]
    return node


def _route_after_orchestrator(state: State) -> str:
    return state.get("intent", "chat")


def build_graph() -> StateGraph:
    graph = StateGraph(State)

    graph.add_node("orchestrator", orchestrator_node)

    for intent, module_path in AGENT_MAP.items():
        graph.add_node(intent, _make_agent_node(module_path))

    graph.set_entry_point("orchestrator")

    graph.add_conditional_edges(
        "orchestrator",
        _route_after_orchestrator,
        {intent: intent for intent in AGENT_MAP},
    )

    for intent in AGENT_MAP:
        graph.add_edge(intent, END)

    return graph.compile()
