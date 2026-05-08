"""Fuzzy similarity scoring for agent response evaluation."""
from rapidfuzz import fuzz


_FUZZY_THRESHOLD = 72  # token_set_ratio score (0-100) to count as "contained"


def fuzzy_contains(text: str, phrase: str, threshold: int = _FUZZY_THRESHOLD) -> tuple[bool, float]:
    """Return (matched, score) using sliding window over the text."""
    text_lower = text.lower()
    phrase_lower = phrase.lower()

    # Exact match fast path
    if phrase_lower in text_lower:
        return True, 100.0

    # Slide a window of similar length across the text
    words = text_lower.split()
    phrase_words = phrase_lower.split()
    window = len(phrase_words)

    best = 0.0
    for i in range(max(1, len(words) - window + 1)):
        chunk = " ".join(words[i : i + window + 1])
        score = fuzz.token_set_ratio(phrase_lower, chunk)
        if score > best:
            best = score
        if best >= threshold:
            break

    # Also try full-text token_set_ratio for short phrases
    full_score = fuzz.token_set_ratio(phrase_lower, text_lower)
    best = max(best, full_score)

    return best >= threshold, round(best, 1)


def score_response(
    response: str,
    must_contain: list[str] | None = None,
    must_not_contain: list[str] | None = None,
    must_contain_one_of: list[str] | None = None,
) -> dict:
    """
    Returns a scored eval result with per-keyword fuzzy similarity scores.
    Overall score is 0.0–1.0.
    """
    must_contain = must_contain or []
    must_not_contain = must_not_contain or []
    must_contain_one_of = must_contain_one_of or []

    keyword_scores: list[dict] = []
    all_required_pass = True

    for phrase in must_contain:
        matched, sim = fuzzy_contains(response, phrase)
        keyword_scores.append({"phrase": phrase, "type": "must_contain", "similarity": sim, "passed": matched})
        if not matched:
            all_required_pass = False

    for phrase in must_not_contain:
        # Exact substring match only — fuzzy is too aggressive for exclusion checks
        exact = phrase.lower() in response.lower()
        keyword_scores.append({"phrase": phrase, "type": "must_not_contain", "similarity": 100.0 if exact else 0.0, "passed": not exact})
        if exact:
            all_required_pass = False

    one_of_pass = True
    if must_contain_one_of:
        one_of_results = []
        any_matched = False
        for phrase in must_contain_one_of:
            matched, sim = fuzzy_contains(response, phrase)
            one_of_results.append({"phrase": phrase, "similarity": sim, "matched": matched})
            if matched:
                any_matched = True
        keyword_scores.append({
            "phrase": f"one_of({must_contain_one_of})",
            "type": "must_contain_one_of",
            "candidates": one_of_results,
            "passed": any_matched,
        })
        if not any_matched:
            one_of_pass = False

    passed = all_required_pass and one_of_pass

    # Collect similarity scores — must_not_contain excluded (0/100 presence flag, not a quality score)
    all_sims: list[float] = []
    for k in keyword_scores:
        if k.get("type") == "must_not_contain":
            continue
        if "similarity" in k:
            all_sims.append(k["similarity"])
        elif "candidates" in k:
            best = max((c["similarity"] for c in k["candidates"]), default=0.0)
            all_sims.append(best)

    avg_sim = round(sum(all_sims) / len(all_sims), 1) if all_sims else 100.0

    return {
        "passed": passed,
        "avg_similarity": avg_sim,
        "keyword_scores": keyword_scores,
    }
