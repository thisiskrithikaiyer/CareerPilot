"""File-based Q&A store for finance and legal domains.

Each JSON file is a list of {"q": "...", "a": "..."} pairs — edit them directly.
"""
import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "data"

_FILES: dict[str, Path] = {
    "finance": _DATA_DIR / "finance_qa.json",
    "legal": _DATA_DIR / "legal_qa.json",
}


def load_qa(domain: str) -> list[dict[str, str]]:
    """Return all Q&A pairs for a domain."""
    path = _FILES.get(domain)
    if path is None or not path.exists():
        return []
    return json.loads(path.read_text())


def search_qa(domain: str, keyword: str) -> list[dict[str, str]]:
    """Return Q&A pairs whose question or answer contains the keyword (case-insensitive)."""
    kw = keyword.lower()
    return [
        qa for qa in load_qa(domain)
        if kw in qa["q"].lower() or kw in qa["a"].lower()
    ]


def all_questions(domain: str) -> list[str]:
    """Return just the question strings — useful for building interview-style prompts."""
    return [qa["q"] for qa in load_qa(domain)]
