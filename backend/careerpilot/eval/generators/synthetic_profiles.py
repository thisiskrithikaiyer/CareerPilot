"""
Generate diverse synthetic job-seeker crisis profiles using Groq for eval data augmentation.

Usage:
    python -m careerpilot.eval.generators.synthetic_profiles --n 50
    python -m careerpilot.eval.generators.synthetic_profiles --n 50 --output synthetic_golden
"""
import json
import argparse
from collections import Counter
from pathlib import Path

from careerpilot.utils.groq_client import groq_complete
from careerpilot.config import GROQ_MODEL

DATASETS_DIR = Path(__file__).parent.parent / "datasets"

_BATCH_SIZE = 10  # Generate in batches to stay under token limits

_SYSTEM = (
    "You are a dataset engineer building evaluation cases for an AI career coach. "
    "You generate realistic, diverse synthetic user messages. "
    "You always respond with valid JSON only — no markdown, no explanation."
)

_PROFILE_SCHEMA = """{
  "id": "syn_NNN",
  "phase": "intake" | "active",
  "input": "<user message — 1-3 sentences, first person, natural>",
  "expected_intent": "intake" | "checkin" | "accountability" | "goal_planner" | "mental_health",
  "expected_tone": "<tone descriptor>",
  "must_contain_one_of": ["<keyword1>", "<keyword2>"],
  "must_not_contain": ["<toxic phrase>"],
  "profile_meta": {
    "role": "<job role>",
    "emotional_state": "<state>",
    "financial_situation": "<situation>",
    "experience_level": "junior|mid|senior|staff"
  }
}"""

_DIVERSITY_SPEC = """Vary ACROSS these dimensions:
Roles: Software Engineer, Product Manager, Data Scientist, ML Engineer, UX Designer, DevOps Engineer,
  Frontend Engineer, Backend Engineer, Engineering Manager, Staff Engineer, AI Engineer,
  Data Engineer, QA Engineer, Security Engineer, Solutions Architect, TPM, Product Designer
Emotional states: anxious/spiraling, burned out, cautiously optimistic, deeply depressed,
  frustrated/stuck, quietly determined, overwhelmed, paralyzed by self-doubt, angry,
  grief after sudden layoff, pragmatic/methodical, panicking about finances
Financial: 1 month runway, 2-3 months, 4-6 months, 6+ months, no runway, partner income covers
Experience: junior (0-3 yrs), mid (3-8 yrs), senior (8+), staff/principal"""

_ROUTING_RULES = """Routing rules:
- phase=intake → expected_intent MUST be "intake"
- phase=active → use checkin / accountability / goal_planner / mental_health
- mental_health: user expresses hopelessness, wanting to die, can't function, crisis signals
- checkin: user reporting daily progress, mood, wins, blockers
- accountability: user hasn't done tasks, avoidance, slippage, making excuses
- goal_planner: user wants to change strategy, targets, approach
- Include varied message lengths: some terse (3-6 words), some verbose (40-60 words)"""


def _generate_batch(batch_num: int, size: int, start_id: int, intent_hint: str) -> list[dict]:
    prompt = (
        f"Generate exactly {size} synthetic crisis coaching evaluation cases as a JSON array.\n\n"
        f"{_DIVERSITY_SPEC}\n\n"
        f"{_ROUTING_RULES}\n\n"
        f"This batch should emphasize: {intent_hint}\n\n"
        f"Each item schema:\n{_PROFILE_SCHEMA}\n\n"
        f"Start IDs at syn_{start_id:03d}. "
        f"Output ONLY the JSON array."
    )

    resp = groq_complete(
        model=GROQ_MODEL,
        max_tokens=4000,
        temperature=0.85,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )

    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def generate_profiles(n: int = 50) -> list[dict]:
    """Generate n diverse profiles across intent types using batched Groq calls."""
    batches = [
        (min(_BATCH_SIZE, n - i * _BATCH_SIZE), i * _BATCH_SIZE + 1)
        for i in range((n + _BATCH_SIZE - 1) // _BATCH_SIZE)
        if i * _BATCH_SIZE < n
    ]

    # Vary what each batch emphasizes so we get balanced coverage
    hints = [
        "intake cases (phase=intake) across diverse roles and emotional states",
        "active phase: mix of checkin and accountability, including terse inputs",
        "mental_health crisis signals mixed with near-crisis (anxious/burned out) active cases",
        "goal_planner and ambiguous cases where routing isn't obvious",
        "emotional escalation mid-session, topic switches, very short inputs",
    ]

    all_profiles: list[dict] = []
    for idx, (size, start_id) in enumerate(batches):
        hint = hints[idx % len(hints)]
        print(f"  Batch {idx + 1}/{len(batches)}: generating {size} cases ({hint[:50]}…)")
        try:
            batch = _generate_batch(idx, size, start_id, hint)
            all_profiles.extend(batch)
        except Exception as e:
            print(f"  ⚠ Batch {idx + 1} failed: {e}")

    # Re-number IDs sequentially
    for i, p in enumerate(all_profiles, 1):
        p["id"] = f"syn_{i:03d}"

    return all_profiles


def save_profiles(profiles: list[dict], output_name: str = "synthetic_golden") -> Path:
    DATASETS_DIR.mkdir(exist_ok=True)
    out_path = DATASETS_DIR / f"{output_name}.json"
    with open(out_path, "w") as f:
        json.dump(profiles, f, indent=2)
    return out_path


def print_summary(profiles: list[dict]) -> None:
    intents = Counter(p.get("expected_intent", "?") for p in profiles)
    phases = Counter(p.get("phase", "?") for p in profiles)
    roles = Counter(p.get("profile_meta", {}).get("role", "?") for p in profiles)
    print(f"\n  Total profiles: {len(profiles)}")
    print(f"  Intent distribution: {dict(intents)}")
    print(f"  Phase distribution:  {dict(phases)}")
    print(f"  Top roles: {dict(roles.most_common(5))}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic eval profiles via Groq")
    parser.add_argument("--n", type=int, default=50, help="Number of profiles to generate")
    parser.add_argument("--output", default="synthetic_golden", help="Output dataset name")
    args = parser.parse_args()

    print(f"Generating {args.n} synthetic profiles using Groq…")
    profiles = generate_profiles(args.n)
    path = save_profiles(profiles, args.output)
    print(f"\nSaved {len(profiles)} profiles → {path}")
    print_summary(profiles)
