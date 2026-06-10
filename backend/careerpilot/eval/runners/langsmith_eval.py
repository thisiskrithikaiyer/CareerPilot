"""Push eval results to LangSmith for tracking over time."""
import os
from careerpilot.config import LANGCHAIN_API_KEY, LANGCHAIN_PROJECT


def push_results(results: dict, run_name: str = "careerpilot_eval") -> None:
    if not LANGCHAIN_API_KEY:
        print("LANGCHAIN_API_KEY not set — skipping LangSmith push")
        return

    try:
        from langsmith import Client
        client = Client(api_key=LANGCHAIN_API_KEY)

        routing = results.get("routing", {})
        client.create_run(
            name=run_name,
            project_name=LANGCHAIN_PROJECT,
            run_type="chain",
            inputs={"eval_type": "routing"},
            outputs={
                "accuracy": routing.get("accuracy"),
                "correct": routing.get("correct"),
                "total": routing.get("total"),
            },
        )
        print(f"LangSmith: pushed eval results to project '{LANGCHAIN_PROJECT}'")
    except Exception as e:
        print(f"LangSmith push failed: {e}")


if __name__ == "__main__":
    import asyncio
    from careerpilot.eval.runners.run_evals import run_all

    results = asyncio.run(run_all())
    push_results(results)
