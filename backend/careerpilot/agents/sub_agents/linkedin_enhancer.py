"""LinkedIn enhancer sub-agent — conversational LinkedIn coach + low-level rewrite utilities."""
import json
from langchain_core.messages import HumanMessage
from careerpilot.utils.groq_client import groq_complete
from careerpilot.config import GROQ_MODEL
from careerpilot.orchestrator.state import State
from careerpilot.prompts.loader import load_prompt


async def run(state: State) -> dict:
    base = load_prompt("linkedin_enhancer.txt")

    linkedin_text = state.get("linkedin_text")
    talent_map = state.get("talent_map")

    snippets = []
    if linkedin_text:
        snippets.append(f"\nUSER'S CURRENT LINKEDIN PROFILE:\n{linkedin_text}")
    if talent_map:
        snippets.append(f"\nTALENT MAP (target roles + skills):\n{json.dumps(talent_map, indent=2)}")

    system = base + "".join(snippets)

    history = [
        {"role": "user" if isinstance(m, HumanMessage) else "assistant", "content": m.content}
        for m in state["messages"]
    ]
    resp = groq_complete(
        model=GROQ_MODEL,
        max_tokens=512,
        messages=[{"role": "system", "content": system}, *history],
    )
    return {"response": resp.choices[0].message.content, "sources": []}


async def improve_headline(current_headline: str, talent_map: dict) -> str:
    roles = ", ".join(talent_map.get("target_roles", [])[:3])
    skills = ", ".join(talent_map.get("top_skills", [])[:5])
    prompt = (
        f"Rewrite this LinkedIn headline to attract recruiters for {roles} roles. "
        f"Highlight: {skills}. Max 220 characters. No hashtags.\n\n"
        f"Current: {current_headline}\n\nImproved:"
    )
    resp = groq_complete(
        model=GROQ_MODEL,
        max_tokens=60,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()


async def improve_about(current_about: str, talent_map: dict) -> str:
    seniority = talent_map.get("seniority", "")
    industries = ", ".join(talent_map.get("industries", [])[:3])
    prompt = (
        f"Rewrite the LinkedIn About section for a {seniority} professional in {industries}. "
        "Lead with value proposition. Include a call-to-action. Under 300 words. "
        "First person. No clichés like 'passionate' or 'seasoned'.\n\n"
        f"Current:\n{current_about}\n\nImproved:"
    )
    resp = groq_complete(
        model=GROQ_MODEL,
        max_tokens=400,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()
