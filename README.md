# Career Pilot

An AI career coach powered by an agentic system that plans your day, tirelessly, so you can focus on succeeding. The internet has all the advice you need — but advice isn't a plan. What separates people who land their next role from people who stay stuck isn't effort or talent. It's preparation: knowing exactly what to do today, doing it, and building tomorrow on what you actually finished.

That's what the agents do, every single day, without being asked. They study your target role, your skill gaps, and your real progress, then build a day customized to you — which problems to drill, which roles to apply for, when to rest. Log a check-in and they're already re-planning tomorrow around what you completed. Fall behind and they carry the work forward and recalibrate. You never start a day wondering what to do; the system has already decided, and it decided based on *you*.

Built with **Next.js + FastAPI + Groq (Llama 3.3 70B)** — a multi-agent system that meets you where you are and turns an overwhelming search into a concrete daily plan.

## Multi-Agent Architecture

Career Pilot uses an orchestrated multi-agent system where each agent has a focused responsibility.

| Agent | Role |
|-------|------|
| **Orchestrator** | Reads every message and hands it to the right specialist — phase-aware, context-aware, with distress signals overriding everything else |
| **Intake Agent** | Learns who *you* are — situation, skills, goals, and target role — so every downstream agent plans for you, not a template |
| **Planner Agent** | Turns your goal into a strategy: daily targets, a role-specific prep curriculum, and weekly milestones |
| **DailyTracker Agent** | Listens to your check-ins and **persists** every win — apps sent, DSA solved, networking, mood — closes plan tasks on command ("close the leetcode task"), then immediately kicks off tomorrow's prep |
| **Accountability Agent** | Watches planned vs. actual and steps in the moment you drift — missed days, low motivation, stalled pipeline |
| **Resume Helper** | Tailors your resume to target roles and surfaces transferable skills you'd undersell |
| **LinkedIn Enhancer** | Sharpens your profile for recruiter visibility and positioning |
| **Mock Prep Agent** | Drills you with mock interviews aimed at *your* role and *your* weak spots |
| **Pattern Tracker** | Studies your check-in history to surface the recurring blockers you can't see from inside |

### Shared Infrastructure

All agents read and write to a shared layer:

- **PostgreSQL** — persistent user profiles, plans, check-ins, and interviews
- **pgvector** — semantic memory for surfacing relevant past context
- **ChromaDB** — vector search over job strategy, DSA patterns, and company intel

### Proactive Planning Loop

This is the core of the product: the agents plan tomorrow from what you *actually* completed, not what was on paper — and they do it the moment you report in, without being asked.

1. **You talk, the system writes.** Every check-in (chat or form) is extracted into structured progress and persisted to `daily_log` / `checkins` — "sent 3 apps and solved 2 leetcode problems" becomes data the planner acts on.
2. **Done means done.** Close tasks from chat ("mark the system design task done") or via checkbox — both persist to the plan's `task_status`, and the agents treat them as ground truth.
3. **Tomorrow is already prepped.** Each saved check-in triggers a rebuild of tomorrow's plan: unfinished work carries over to the morning block, application shortfalls fold into tomorrow's target (capped, so one rough day never snowballs), and prep topics only advance when there's evidence you completed them. Crush today and the curriculum moves forward; struggle, and the system meets you where you are.

Every guarantee in this loop is enforced by the hard evals below.

## Eval Results

Evals run against golden datasets across routing, agent response quality, LLM-as-judge rubrics, and consistency.

<!-- EVAL_METRICS_START -->
| Eval | Score |
|------|-------|
| Check-in extraction (hard) | **100%** (8/8) |
| Task close matching (hard) | **100%** (8/8) |
| Next-day plan carryover (hard) | **100%** (7/7) |
| Routing accuracy | **100%** (11/11) |
| Intake agent pass rate | **60%** (3/5) |
| Check-in agent pass rate | **100%** (5/5) |
| Accountability agent pass rate | **100%** (3/3) |
| LLM judge pass rate | **80%** |
|   — helpfulness | **5.6/10** |
|   — emotional appropriateness | **6.4/10** |
|   — actionability | **4.0/10** |
|   — safety | **9.2/10** |
|   — tone consistency | **6.0/10** |

_Last updated: Jun 10 2026, 15:22_
<!-- EVAL_METRICS_END -->

Evaluators check: keyword presence/absence, LLM-as-judge rubric scores (helpfulness, emotional appropriateness, actionability, safety, tone), routing correctness, and response consistency across repeated runs. Reports saved to `backend/careerpilot/eval/reports/`.

**Hard evals** are exact-match product guarantees (no similarity scoring): check-in messages must extract to the exact structured counts, "close task X" must resolve to the exact plan task, and next-day carryover math (topic advancement, shortfall folding, routine-task exclusion) must be exact. Run them alone with `python3 -m careerpilot.eval.runners.run_evals --hard-only`.

> Run `python3 -m careerpilot.eval.runners.update_readme` from `backend/` to refresh these numbers.

## Project Structure

```
careerpilot-ai/
├── frontend/                  # Next.js 14 (App Router, TypeScript, Tailwind)
│   └── src/
│       ├── app/               # Pages and layouts
│       ├── components/        # Chat UI components
│       └── lib/               # API client
└── backend/                   # FastAPI Python app
    └── careerpilot/
        ├── main.py            # FastAPI entry point
        ├── orchestrator/      # Orchestrator + state machine
        ├── agents/
        │   ├── runtime/       # Intake, planner, check-in, accountability
        │   ├── background/    # Async agents (job strategy, interview prep, etc.)
        │   └── sub_agents/    # Resume, LinkedIn, mock prep, pattern tracker
        ├── api/routes/        # REST endpoints
        ├── db/                # PostgreSQL schemas + pgvector store
        ├── ingestion/         # Vector DB seeders
        └── eval/              # Golden datasets, evaluators, and reports
```

## Quick Start

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your Groq API key (GROK_API_KEY) + Supabase URL/keys
uvicorn careerpilot.main:app --reload
```

### Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Run Evals

```bash
cd backend
python -m careerpilot.eval.runners.run_evals
```
