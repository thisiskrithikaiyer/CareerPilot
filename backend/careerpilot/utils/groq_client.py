"""Shared Groq client with key rotation and exponential backoff on rate limits."""
import time
from openai import OpenAI, RateLimitError
from careerpilot.config import GROQ_API_KEY, GROQ_API_KEY_2, GROQ_MODEL

_GROQ_BASE = "https://api.groq.com/openai/v1"

_keys = [k for k in [GROQ_API_KEY, GROQ_API_KEY_2] if k]
_clients = [OpenAI(api_key=k, base_url=_GROQ_BASE) for k in _keys]
_idx = 0  # points to the current active key


def groq_complete(**kwargs) -> object:
    """
    Drop-in for client.chat.completions.create.
    On 429: immediately rotates to the next key.
    After all keys exhausted in a round: backs off (2s, 5s, 15s) before trying again.
    Raises after 4 full rounds with no success.
    """
    global _idx
    kwargs.setdefault("model", GROQ_MODEL)

    n = len(_clients)
    backoffs = [0, 2, 5, 15]  # wait before each round (0 = first try is instant)

    for round_num, delay in enumerate(backoffs):
        if delay:
            time.sleep(delay)
        for _ in range(n):
            try:
                return _clients[_idx % n].chat.completions.create(**kwargs)
            except RateLimitError:
                _idx = (_idx + 1) % n  # rotate to next key

    raise RateLimitError(
        message="All Groq API keys are rate-limited after 4 rounds.",
        response=None,  # type: ignore[arg-type]
        body=None,
    )
