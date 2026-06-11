# Career Pilot

An AI coach that helps you reach your absolute best when crisis hits and logic takes a backseat. Layoffs hit hard — it feels personal. The internet has all the advice you need, but when you're in crisis mode you're not mentally in a state to find it, read it, or act on it. That preparation gap is what separates people who break through from people who stay stuck. Not effort. Not talent. Preparation.

Carrier Pilot is an AI coach that customizes your preparation backed by data and your own existing potential — so when logic takes a backseat, you still move forward.

Built with **Next.js + FastAPI + Groq (Llama 3.3 70B)**, powered by a multi-agent system that meets you where you are emotionally and turns overwhelm into action.

## Multi-Agent Architecture

Carrier Pilot uses an orchestrated multi-agent system where each agent has a focused responsibility.

| Agent | Role |
|-------|------|
| **Orchestrator** | Routes every message to the right agent based on user phase and context |
| **Intake Agent** | Onboards new users — collects situation, emotional state, skills, and goals |
| **Planner Agent** | Builds a structured action plan; dispatches tasks to specialized agents |
| **DailyTracker Agent** | Handles daily check-ins — extracts and **persists** progress (apps, DSA, networking, mood), closes plan tasks on command ("close the leetcode task"), and triggers next-day prep |
| **Accountability Agent** | Monitors plan health; triggers replanning if progress stalls |
| **Resume Helper** | Tailors resume to target roles and highlights transferable skills |
| **LinkedIn Enhancer** | Optimizes LinkedIn profile for recruiter visibility |
| **Mock Prep Agent** | Runs targeted mock interviews based on role and skill gaps |
| **Pattern Tracker** | Surfaces recurring blockers and behavioral patterns across check-ins |

### Shared Infrastructure

All agents read and write to a shared layer:

- **PostgreSQL** — persistent user profiles, plans, check-ins, and interviews
- **pgvector** — semantic memory for surfacing relevant past context
- **ChromaDB** — vector search over job strategy, DSA patterns, and company intel

### Proactive Planning Loop

The coach preps the next day's tasks from what was *actually* completed, not what was planned:

1. Every check-in (chat or form) is extracted into structured progress and written to `daily_log` / `checkins`.
2. Plan tasks can be closed from chat ("mark the system design task done") or via checkbox — both persist to the plan's `task_status`.
3. Each saved check-in proactively rebuilds **tomorrow's** plan: unfinished work carries over to the morning block, application shortfalls fold into tomorrow's target (capped), and curriculum topics only advance when there's evidence they were completed.

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
cp .env.example .env   # add ANTHROPIC_API_KEY and DATABASE_URL
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
