"""Resume helper sub-agent — conversational resume coach + low-level rewrite utilities."""
from langchain_core.messages import HumanMessage
from careerpilot.utils.groq_client import groq_complete
from careerpilot.config import GROQ_MODEL
from careerpilot.orchestrator.state import State
from careerpilot.prompts.loader import load_prompt


async def run(state: State) -> dict:
    last_msg = next(
        (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None
    )

    base = load_prompt("resume_helper.txt")
    resume_text = state.get("resume_text")
    resume_section = f"\n\nUSER'S CURRENT RESUME:\n{resume_text}" if resume_text else ""
    system = base + resume_section

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


async def improve_bullet(bullet: str, job_description: str = "") -> str:
    """Rewrite a single resume bullet to be impact-focused and ATS-friendly."""
    jd_context = f"\nTarget JD context: {job_description[:500]}" if job_description else ""
    prompt = (
        f"Rewrite this resume bullet to be more impact-focused (quantify if possible), "
        f"ATS-friendly, and under 20 words.{jd_context}\n\nOriginal: {bullet}\n\nImproved:"
    )
    resp = groq_complete(
        model=GROQ_MODEL,
        max_tokens=80,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()


async def tailor_resume_summary(summary: str, job_description: str) -> str:
    """Rewrite the professional summary to match a specific job description."""
    prompt = (
        "Rewrite the professional summary below to align with the job description. "
        "Keep it under 60 words. First person. No buzzwords.\n\n"
        f"Job description: {job_description[:1000]}\n\nCurrent summary: {summary}\n\nTailored:"
    )
    resp = groq_complete(
        model=GROQ_MODEL,
        max_tokens=150,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()
