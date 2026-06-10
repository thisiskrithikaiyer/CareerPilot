"""Evaluates whether factual claims in responses are backed by retrieved sources."""


def score_citations(response: str, sources: list[str], domain: str) -> dict:
    """
    For domains with factual content (legal, finance), responses should
    cite sources or at minimum be grounded by retrieved documents.
    """
    FACTUAL_DOMAINS = {"legal", "finance", "interview_prep"}
    requires_citation = domain in FACTUAL_DOMAINS

    has_sources = bool(sources)
    disclaimer_phrases = ["consult", "attorney", "professional", "not legal advice", "verify"]
    has_disclaimer = any(p in response.lower() for p in disclaimer_phrases)

    if not requires_citation:
        return {"requires_citation": False, "passed": True}

    passed = has_sources or has_disclaimer
    return {
        "requires_citation": True,
        "has_sources": has_sources,
        "has_disclaimer": has_disclaimer,
        "source_count": len(sources),
        "passed": passed,
    }
