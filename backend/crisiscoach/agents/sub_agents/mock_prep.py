"""Mock prep sub-agent — generates interview questions and scores answers."""
import json
from crisiscoach.utils.groq_client import groq_complete
from crisiscoach.config import GROQ_MODEL


async def generate_questions(role: str, interview_stage: str, n: int = 5) -> list[dict]:
    prompt = (
        f"Generate {n} realistic interview questions for a {role} {interview_stage} interview. "
        "Mix behavioral, technical, and situational. "
        'Output JSON array: [{"question": "...", "type": "behavioral|technical|situational", "difficulty": 1-3}]'
    )
    resp = groq_complete(
        model=GROQ_MODEL,
        max_tokens=512,
        temperature=0.5,
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(resp.choices[0].message.content)


async def score_answer(question: str, answer: str, role: str) -> dict:
    """Score a mock interview answer on clarity, specificity, and relevance."""
    prompt = (
        f"Role: {role}\nQuestion: {question}\nAnswer: {answer}\n\n"
        "Score this answer for a recruiter. Output JSON only: "
        '{"score": <1-10>, "strengths": [...], "gaps": [...], "improved_version": "..."}. '
        "Be direct and specific."
    )
    resp = groq_complete(
        model=GROQ_MODEL,
        max_tokens=512,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(resp.choices[0].message.content)
