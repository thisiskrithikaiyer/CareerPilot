"""Intake agent — collects role, offer_timeline, leetcode_level, proposes goal, then hands off."""
import json
from langchain_core.messages import HumanMessage
from crisiscoach.utils.groq_client import groq_complete
from crisiscoach.config import GROQ_MODEL
from crisiscoach.orchestrator.state import CrisisCoachState
from crisiscoach.orchestrator.state_prompt import state_to_prompt
from crisiscoach.prompts.loader import load_prompt

TECH_ROLES = {"SWE", "MLE", "Software Engineer", "ML Engineer", "AI Engineer", "Data Engineer"}

_FIELD_EXTRACT_PROMPT = """
Extract what intake fields have been confirmed so far from this conversation.
Return ONLY valid JSON. Use null if not yet collected.

{
  "role": "Software Engineer | ML Engineer | AI Engineer | Data Engineer | Other | null",
  "offer_timeline": "1_2_months | 3_months | 3_6_months | 6_plus | null",
  "leetcode_level": "fundamentals | building | standard | advanced | null",
  "goal_confirmed": true | false,
  "notes": "<user's notes text, or 'skip' if they skipped, or null if not yet asked>"
}

Role mapping — extract from ANY mention, not just chip selections:
- "software engineer", "SWE", "backend engineer", "frontend engineer", "fullstack", "web developer" → "Software Engineer"
- "machine learning engineer", "ML engineer", "MLE", "MLOps" → "ML Engineer"
- "AI engineer", "LLM engineer", "AI/ML", "GenAI" → "AI Engineer"
- "data engineer", "data pipeline", "DE" → "Data Engineer"
- "product manager", "PM", "senior PM", "TPM", "designer", "UX", "data scientist", "other" → "Other"
If the user mentions ANY of these in passing (e.g. "I was a software engineer"), extract it.

Leetcode level mapping:
- "Can't do Two Sum yet" → fundamentals
- "Two Sum is fine, easy/medium feels shaky" → building
- "Comfortable with mediums" → standard
- "Can do hards" → advanced

offer_timeline mapping — extract from ANY mention of timeframe:
- "ASAP", "within 2 months", "urgently", "as soon as possible", "1-2 months" → 1_2_months
- "~3 months", "3 months", "about 3 months" → 3_months
- "3-6 months", "3–6 months", "a few months" → 3_6_months
- "6+ months", "6 months", "no rush", "I have runway", "some runway", "not urgent" → 6_plus

goal_confirmed: Set to true ONLY when the user explicitly agrees to the proposed goal
(e.g. user says "Yes, let's go", "Sounds good", "Yes", "Let's do it"). False otherwise.

notes: Set to the user's free-text response when the agent asks "anything specific we should factor in?"
Set to "skip" if the user clicks Skip or says nothing extra. Keep null until the notes question is asked.

Conversation:
"""


def _sanitize_fields(raw: dict) -> dict:
    out = {}
    for k, v in raw.items():
        if v == "null" or v == "None":
            out[k] = None
        elif v == "true":
            out[k] = True
        elif v == "false":
            out[k] = False
        else:
            out[k] = v
    return out


def _extract_fields(history: list[dict]) -> dict:
    try:
        convo = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history[-14:])
        resp = groq_complete(
            model=GROQ_MODEL,
            max_tokens=256,
            temperature=0,
            messages=[{"role": "user", "content": _FIELD_EXTRACT_PROMPT + convo}],
        )
        return _sanitize_fields(json.loads(resp.choices[0].message.content.strip()))
    except Exception:
        return {}


def _core_fields_collected(fields: dict) -> bool:
    """Core questions answered: role and offer_timeline."""
    return bool(fields.get("role")) and bool(fields.get("offer_timeline"))


def _needs_leetcode(fields: dict) -> bool:
    role = fields.get("role", "")
    is_tech = role in TECH_ROLES or any(r.lower() in role.lower() for r in TECH_ROLES)
    return is_tech and not fields.get("leetcode_level")


def _get_intake_phase(fields: dict) -> str:
    if not _core_fields_collected(fields):
        return "collecting"
    if _needs_leetcode(fields):
        return "checking"
    if not fields.get("goal_confirmed"):
        return "proposing"
    if fields.get("notes") is None:
        return "notes"
    return "complete"


def _persist_intake_fields(user_id: str, fields: dict) -> None:
    updates: dict = {}

    if fields.get("role"):
        updates["role"] = fields["role"]

    if fields.get("offer_timeline"):
        updates["offer_timeline"] = fields["offer_timeline"]

    if fields.get("leetcode_level"):
        updates["leetcode_level"] = fields["leetcode_level"]

    if not updates:
        return

    try:
        from crisiscoach.db.supabase import get_client
        get_client().table("users").update(updates).eq("id", user_id).execute()
        print(f"[INTAKE] Saved to DB: {list(updates.keys())}")
    except Exception as e:
        print(f"[INTAKE] DB save failed: {e}")


_JSON_SCHEMA = """

IMPORTANT: Respond with ONLY valid JSON — no markdown, no extra text:
{
  "reply": "<your conversational message to the user>",
  "field_key": "<field currently being collected: role | offer_timeline | leetcode_level | notes | null>",
  "intake_phase": "<collecting | checking | proposing | notes | complete>",
  "intake_complete": <true ONLY after the notes phase is done>,
  "chips": []
}

STRICT RULES — these override everything:
- NEVER ask a question not in the phase sequence.
- NEVER repeat a question whose answer is already confirmed (listed in context above).
- Once a field is answered, move IMMEDIATELY to the next. One short acknowledgment, then next question.
- The chips array MUST contain the exact options listed below for the current phase.

PHASE RULES — follow strictly, one phase at a time:

Phase "collecting": Ask in exact sequence (one per message):
  1. role          → chips: ["Software Engineer", "ML Engineer", "AI Engineer", "Data Engineer", "Other"]
  2. offer_timeline → chips: ["ASAP — within 2 months", "~3 months", "3–6 months", "6+ months, no rush"]
  Set field_key to the field being asked.

Phase "checking": Role is SWE/MLE/AI Engineer/Data Engineer and leetcode unknown → ask:
  "Quick gut check — where are you on LeetCode?"
  chips: ["Can't do Two Sum yet", "Two Sum is fine, easy/medium feels shaky", "Comfortable with mediums", "Can do hards"]
  field_key="leetcode_level". Non-tech roles → skip to "proposing".

Phase "proposing": Propose ONE specific 60-day goal (role + company type + timeline).
  Example: "Land 2 AI Engineer offers in 3 months — targeting Series B to mid-size AI companies."
  chips: ["Yes, let's go", "Adjust the goal", "I need more time than that"]
  intake_complete=false, field_key=null.

Phase "notes": Goal is confirmed. Ask for any additional considerations:
  "One last thing — anything specific we should factor in? Visa status, relocation, companies to avoid or target?"
  chips: ["Skip — that's all"]
  field_key="notes". intake_complete=false.
  The user may type a free-text answer OR click Skip. Either way, accept and close.

Phase "complete": Notes collected (or skipped). Set intake_complete=true.
  Acknowledge their notes briefly (or skip smoothly if they said nothing).
  Say: "Paste your resume in the dashboard when you get a chance — I'll use it to make the plan specific to you."
  Close: "Let's get to work — your next role is closer than you think."
"""


def _build_system(state: CrisisCoachState, fields: dict) -> str:
    base = load_prompt("intake.txt")
    snippets = []

    phase = _get_intake_phase(fields)
    snippets.append(f"\nCURRENT INTAKE PHASE: {phase}")

    if fields.get("role"):
        snippets.append(f"Role confirmed: {fields['role']}")
    if fields.get("offer_timeline"):
        snippets.append(f"Offer timeline confirmed: {fields['offer_timeline']}")
    if fields.get("leetcode_level"):
        snippets.append(f"Leetcode level confirmed: {fields['leetcode_level']}")

    snippets.append(state_to_prompt(state))

    if phase == "collecting":
        missing = []
        if not fields.get("role"):
            missing.append("role")
        if not fields.get("offer_timeline"):
            missing.append("offer_timeline")
        snippets.append(f"\nSTILL COLLECTING (ask next in sequence): {', '.join(missing)}")
        snippets.append("One field per message. Chips only. Do not advance to goal proposal yet.")

    elif phase == "checking":
        snippets.append("\nCore fields collected. Ask about leetcode level before proposing goal.")
        snippets.append("Set intake_phase='checking', field_key='leetcode_level'.")

    elif phase == "proposing":
        snippets.append("\nAll required info collected. NOW propose a specific goal.")
        snippets.append("Tailor it to their role and offer timeline.")
        snippets.append("Chips: [\"Yes, let's go\", \"Adjust the goal\", \"I need more time than that\"]")
        snippets.append("Set intake_phase='proposing', intake_complete=false, field_key=null.")

    elif phase == "notes":
        snippets.append("\nGoal confirmed. Ask for additional considerations (visa, relocation, target companies, etc.).")
        snippets.append("Set intake_phase='notes', intake_complete=false, field_key='notes'.")
        snippets.append("chips: [\"Skip — that's all\"]")
        snippets.append("Accept any free-text answer OR a Skip. Do not probe further.")

    elif phase == "complete":
        notes_val = fields.get("notes", "")
        if notes_val and notes_val != "skip":
            snippets.append(f"\nNotes received: \"{notes_val}\". Acknowledge briefly, then close intake.")
        else:
            snippets.append("\nUser skipped notes. Close intake smoothly.")
        snippets.append("Set intake_phase='complete', intake_complete=true, field_key=null.")
        snippets.append("Include resume paste prompt and closing line.")

    return base + ("\n\nUser context:\n" + "\n".join(snippets) if snippets else "") + _JSON_SCHEMA


_GOAL_CONFIRM_PHRASES = {"yes, let's go", "sounds good", "let's do it", "yes", "sure", "let's go"}


def _check_goal_confirmed(history: list[dict]) -> bool:
    for msg in reversed(history):
        if msg["role"] == "user":
            return msg["content"].strip().lower() in _GOAL_CONFIRM_PHRASES
    return False


async def run(state: CrisisCoachState) -> dict:
    history = [
        {"role": "user" if isinstance(m, HumanMessage) else "assistant", "content": m.content}
        for m in state["messages"]
    ]

    frontend_fields = state.get("collected_fields") or {}
    if frontend_fields:
        fields = dict(frontend_fields)
        if not fields.get("goal_confirmed"):
            fields["goal_confirmed"] = _check_goal_confirmed(history)
    else:
        fields = _extract_fields(history)

    phase = _get_intake_phase(fields)
    user_id = state.get("user_id")

    if user_id:
        _persist_intake_fields(user_id, fields)

    system = _build_system(state, fields)
    resp = groq_complete(
        model=GROQ_MODEL,
        max_tokens=256,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": system}, *history],
    )
    try:
        structured = json.loads(resp.choices[0].message.content)
    except Exception:
        structured = {"reply": resp.choices[0].message.content, "field_key": None, "intake_phase": phase, "intake_complete": False, "chips": []}

    reply = structured.get("reply") or ""
    field_key = structured.get("field_key")
    chips = structured.get("chips") or []

    if phase == "proposing" and not chips:
        chips = ["Yes, let's go", "Adjust the goal", "I need more time than that"]
    if phase == "notes" and not chips:
        chips = ["Skip — that's all"]

    notes_done = fields.get("notes") is not None
    goal_confirmed = bool(fields.get("goal_confirmed"))
    intake_done = (goal_confirmed and notes_done) or bool(structured.get("intake_complete", False))
    new_phase = "goal_setup" if intake_done else "intake"

    print(f"[INTAKE] phase={phase} goal_confirmed={goal_confirmed} intake_done={intake_done}")

    if intake_done and user_id:
        try:
            from crisiscoach.db.supabase import get_client
            get_client().table("users").update({
                "intake_complete": True,
                "phase": "goal_setup",
            }).eq("id", user_id).execute()
        except Exception:
            pass

    update: dict = {
        "response": reply,
        "sources": [],
        "chips": chips,
        "field_key": field_key,
        "intake_complete": intake_done,
        "phase": new_phase,
        "days_since": state.get("days_since"),
        "days_left": state.get("days_left"),
        "tracking_skills": state.get("tracking_skills") or None,
    }
    if fields.get("leetcode_level"):
        update["leetcode_level"] = fields["leetcode_level"]
    if fields.get("role"):
        update["role"] = fields["role"]
    return update
