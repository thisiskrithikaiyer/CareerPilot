"""Evaluates whether agent responses use the right tone — direct but not harsh."""
import json
from crisiscoach.utils.groq_client import groq_complete
from crisiscoach.config import GROQ_MODEL

BANNED_PHRASES = [
    "don't worry", "everything will be fine", "you've got this",
    "stay positive", "keep your head up", "proud of you",
    "amazing", "incredible", "fantastic",
]


def check_banned_phrases(text: str) -> list[str]:
    text_lower = text.lower()
    return [p for p in BANNED_PHRASES if p in text_lower]


def score_tone(response: str, expected_tone: str) -> dict:
    found_banned = check_banned_phrases(response)

    prompt = (
        f"Rate this coaching response for tone. Expected tone: {expected_tone}.\n\n"
        f"Response: {response}\n\n"
        'Output JSON: {"tone_match": 0-10, "is_direct": true/false, '
        '"is_empathetic": true/false, "is_harsh": true/false, "notes": "..."}'
    )
    resp = groq_complete(
        model=GROQ_MODEL,
        max_tokens=200,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    scores = json.loads(resp.choices[0].message.content)
    scores["banned_phrases_found"] = found_banned
    scores["passed"] = (
        scores.get("tone_match", 0) >= 7
        and not scores.get("is_harsh", False)
        and not found_banned
    )
    return scores
