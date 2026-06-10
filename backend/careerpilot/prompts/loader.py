"""Utility to load agent prompts with the shared system personality prepended."""
import os

_PROMPTS_DIR = os.path.dirname(__file__)


def _read(filename: str) -> str:
    with open(os.path.join(_PROMPTS_DIR, filename)) as f:
        return f.read()


def load_prompt(agent_prompt_file: str) -> str:
    """Return system.txt + agent-specific prompt, separated by a divider."""
    system = _read("system.txt")
    agent = _read(agent_prompt_file)
    return f"{system}\n\n---\n\n{agent}"
