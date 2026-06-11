# CrisisCoach AI — API & Workers Reference

Backend reference for frontend development. FastAPI app defined in [careerpilot/main.py](careerpilot/main.py).

- **Base URL (local):** `http://localhost:8000`
- **All endpoints are prefixed with `/api`** except `GET /health`.
- **Auth:** JWT bearer token from `/api/auth/login` or `/api/auth/register`. Send on every request:
  ```
  Authorization: Bearer <access_token>
  ```
  The user id is taken from the token (`sub` claim). If no token is sent, most endpoints fall back to an empty/anonymous user and will return empty data or 401.
- **Errors:** failures return `{"detail": "<message>"}` with status 401 (auth), 404 (not found), or 500 (server error).
- **Dates:** ISO format — dates are `YYYY-MM-DD`, timestamps are ISO 8601 UTC.

---

## Table of Contents

1. [Auth](#1-auth)
2. [Chat (agent conversation)](#2-chat-agent-conversation)
3. [Intake (onboarding)](#3-intake-onboarding)
4. [Daily Check-in](#4-daily-check-in)
5. [Daily Plan](#5-daily-plan)
6. [Goal Plan](#6-goal-plan)
7. [Daily Activity Log](#7-daily-activity-log)
8. [Interviews](#8-interviews)
9. [Profile (resume / LinkedIn)](#9-profile-resume--linkedin)
10. [Dashboard (single fetch)](#10-dashboard-single-fetch)
11. [Health](#11-health)
12. [Chat Agents (routing)](#12-chat-agents-routing)
13. [Background Workers & Agents](#13-background-workers--agents)

---

## 1. Auth

Source: [careerpilot/api/routes/auth.py](careerpilot/api/routes/auth.py)

### POST `/api/auth/register`

Creates a Supabase user (email auto-confirmed) and returns a JWT.

**Request**
```json
{ "email": "jane@example.com", "password": "hunter2!" }
```

**Response `200`**
```json
{ "access_token": "eyJhbGciOiJIUzI1NiIs...", "token_type": "bearer" }
```

Errors: `400` with `detail` if the email is taken or Supabase rejects the signup.

### POST `/api/auth/login`

Authenticates against Supabase and returns a local JWT. Unconfirmed emails are force-confirmed and retried automatically.

**Request**
```json
{ "email": "jane@example.com", "password": "hunter2!" }
```

**Response `200`** — same shape as register.

Errors: `401` with `detail` on bad credentials.

---

## 2. Chat (agent conversation)

Source: [careerpilot/api/routes/chat.py](careerpilot/api/routes/chat.py)

The chat endpoints run the LangGraph orchestrator: a supervisor classifies intent, routes to one of the agents (see [§12](#12-chat-agents-routing)), and returns the agent's reply. Messages are encrypted and persisted automatically.

### POST `/api/chat` (non-streaming)

**Request**
```json
{
  "messages": [
    { "role": "user", "content": "I bombed my Google phone screen yesterday" }
  ]
}
```
Send the full conversation history each call (`role` is `"user"` or `"assistant"`). `user_id` is optional and only used when no JWT is present.

**Response `200`**
```json
{
  "reply": "That stings — let's break down what happened so it doesn't repeat...",
  "chips": ["Log this interview", "What went wrong?", "Practice similar questions"],
  "intent": "accountability",
  "agent": "Accountability Coach",
  "sources": ["interview_db: phone_screen_recovery"],
  "agent_events": [
    {
      "agent": "accountability",
      "display_name": "Accountability Coach",
      "reason": "User reporting interview outcome",
      "timestamp": "2026-06-11T18:21:04.123Z"
    }
  ]
}
```

- `chips` — quick-reply suggestions to render as tappable buttons.
- `agent` — friendly display name for the responding agent badge.
- `sources` — retrieval citations (may be empty).

### POST `/api/chat/stream` (SSE — preferred for the UI)

Same request body as `/api/chat`. Returns `text/event-stream`. Each event is a `data: <json>` line. Event types:

**1. `agent_event`** — emitted as soon as routing is decided (show "Accountability Coach is thinking…"):
```json
{
  "type": "agent_event",
  "agent": "accountability",
  "display_name": "Accountability Coach",
  "reason": "User reporting interview outcome",
  "timestamp": "2026-06-11T18:21:04.123Z"
}
```

**2. `done`** — the final reply:
```json
{
  "type": "done",
  "reply": "That stings — let's break down what happened...",
  "chips": ["Log this interview", "Practice similar questions"],
  "intent": "accountability",
  "agent": "Accountability Coach",
  "sources": [],
  "phase": "active",
  "refresh_plan": false
}
```
- `refresh_plan: true` means the agent changed the plan — re-fetch `GET /api/plan/today`.
- `phase` — current user phase (`intake` | `goal_setup` | `active`); use it to drive UI flow transitions.

**3. `error`**:
```json
{ "type": "error", "message": "..." }
```

### GET `/api/chat/history?limit=10`

Last N message pairs for the authenticated user, oldest-first (max `limit` = 50; each exchange counts as 2 rows).

**Response `200`**
```json
[
  { "role": "user", "content": "I bombed my phone screen", "intent": "accountability", "created_at": "2026-06-10T17:00:01Z" },
  { "role": "assistant", "content": "That stings — let's break it down...", "intent": "accountability", "created_at": "2026-06-10T17:00:04Z" }
]
```

---

## 3. Intake (onboarding)

Source: [careerpilot/api/routes/intake.py](careerpilot/api/routes/intake.py)

### POST `/api/intake/stream` (SSE)

Conversational onboarding driven by the Intake agent. Send the conversation so far plus any already-collected fields; the agent decides the next question.

**Request**
```json
{
  "messages": [
    { "role": "assistant", "content": "What kind of engineer are you?" },
    { "role": "user", "content": "ML Engineer" }
  ],
  "collected_fields": { "role": "MLE" }
}
```

**Events** — first an `agent_event` (`display_name: "Intake Specialist"`), then one `step`:
```json
{
  "type": "step",
  "reply": "Nice — ML roles it is. What's your timeline to land an offer?",
  "field_key": "offer_timeline",
  "question": "What's your timeline to land an offer?",
  "options": [
    { "value": "1_2_months", "label": "ASAP — within 2 months" },
    { "value": "3_months", "label": "~3 months" },
    { "value": "3_6_months", "label": "3–6 months" },
    { "value": "6_plus", "label": "6+ months, no rush" }
  ],
  "intake_complete": false,
  "chips": []
}
```
- When `options` is non-empty, render them as structured choices and submit the `value` back as the next user message / collected field.
- `chips` is only populated when there are no structured `options` (free-form confirmation steps).
- `field_key` is one of: `role`, `offer_timeline`, `leetcode_level` (their option sets are fixed — see source).
- `intake_complete: true` → call `POST /api/intake` to persist, then move to goal setup.

### POST `/api/intake`

Persist the final collected intake fields. Sets `intake_complete = true` and `phase = "goal_setup"`.

**Request**
```json
{
  "role": "MLE",
  "offer_timeline": "3_months",
  "leetcode_level": "shaky_mediums",
  "resume_text": "JANE DOE\nML Engineer, 4 yrs...",
  "notes": "Recently laid off, 6 months runway"
}
```
`leetcode_level`, `resume_text`, `notes` are optional.

**Response `200`**
```json
{ "success": true }
```

### GET `/api/intake/status`

**Response `200`**
```json
{ "intake_complete": true, "phase": "goal_setup" }
```
Phases: `intake` → `goal_setup` → `active`.

---

## 4. Daily Check-in

Source: [careerpilot/api/routes/checkin.py](careerpilot/api/routes/checkin.py)

### POST `/api/checkin`

Saves a mood/energy check-in, returns an LLM coach response, and kicks off tomorrow's plan build in the background.

**Request**
```json
{
  "mood_score": 6,
  "energy_score": 4,
  "wins": ["Finished 3 leetcode mediums", "Got a recruiter reply"],
  "blockers": ["Anxious about Friday's onsite"],
  "notes": "Slept badly"
}
```
`mood_score` / `energy_score`: integers 1–10 (1 = exhausted, 10 = energized). `wins`, `blockers`, `notes` optional.

**Response `200`**
```json
{
  "id": "9f1c2a44-...",
  "created_at": "2026-06-11T22:10:00.000Z",
  "mood_score": 6,
  "energy_score": 4,
  "coach_response": "Three mediums on bad sleep is real progress. For Friday's onsite, let's channel that anxiety into one mock tomorrow morning..."
}
```

### GET `/api/checkin/history?limit=7`

**Response `200`** — newest first, raw check-in rows:
```json
[
  {
    "id": "9f1c2a44-...",
    "user_id": "uuid",
    "mood_score": 6,
    "energy_score": 4,
    "wins": ["Finished 3 leetcode mediums"],
    "blockers": ["Anxious about Friday's onsite"],
    "notes": "Slept badly",
    "created_at": "2026-06-11T22:10:00.000Z"
  }
]
```

---

## 5. Daily Plan

Source: [careerpilot/api/routes/plan.py](careerpilot/api/routes/plan.py)

Plans are built by the Daily Plan Builder pipeline (see [§13](#13-background-workers--agents)): signals → carryover → prioritizer → schedule blocks.

### GET `/api/plan/today?target_date=2026-06-11`

`target_date` optional (defaults to today). `404` if no plan exists for that date — call `POST /api/plan/generate` to create one.

**Response `200`**
```json
{
  "plan_id": "5e7d...",
  "date": "2026-06-11",
  "coach_note": "Interview Thursday — today is drill day. One topic, deep.",
  "priority_mode": "interview_prep",
  "schedule": {
    "morning": {
      "time": "Morning (9am–12pm)",
      "tasks": [
        "Leetcode: dynamic programming (60min) — Solve: House Robber II, Coin Change",
        "System design deep dive (60min) — Topic: rate limiting"
      ]
    },
    "midday": {
      "time": "Midday (1pm–4pm)",
      "tasks": [
        "Behavioral prep (45min) — Practice: conflict with teammate",
        "Job applications (45min) — Send 3 targeted applications"
      ]
    },
    "evening": {
      "time": "Evening (6pm–8pm)",
      "tasks": [
        "Behavioral question practice (30min) — Topic: conflict with teammate",
        "Review applications sent today (15min) — Note any follow-ups needed",
        "Log today's activity (10min) — Update daily tracker"
      ]
    }
  },
  "leetcode_topic": "dynamic programming",
  "system_design_concept": "rate limiting",
  "task_status": { "morning-0": true, "morning-1": false }
}
```
Notes:
- `priority_mode` values include `standard`, `interview_prep`, `fix_resume`, `no_interview_14d`, `recovery` — use it for a banner/theme.
- Extra keys from `plan_json` (targets, signals, etc.) are spread into the top level; treat unknown keys as optional.
- Schedule task keys for completion tracking are `"<block>-<index>"`, e.g. `morning-0`, `midday-1`.

### POST `/api/plan/generate`

Builds a plan immediately (synchronous — takes a few seconds).

**Request** (body optional)
```json
{ "target_date": "2026-06-12" }
```

**Response `200`** — same shape as `GET /api/plan/today`.

### PATCH `/api/plan/task-status`

Persist a schedule task checkbox. The next-day planner reads this for carryover.

**Request**
```json
{ "task_key": "morning-0", "completed": true, "date": "2026-06-11" }
```
`date` optional (defaults to today).

**Response `200`**
```json
{ "ok": true, "task_status": { "morning-0": true } }
```

### PATCH `/api/plan/task/{task_id}`

Legacy: toggles a row in `plan_tasks` (used by dashboard `today_plan.tasks`).

**Request** `{ "completed": true }` → **Response** `{ "ok": true }`

---

## 6. Goal Plan

Source: [careerpilot/api/routes/goal_plan.py](careerpilot/api/routes/goal_plan.py)

The goal plan itself is created conversationally by the Goal Strategist agent via chat during `goal_setup` phase. These endpoints read/commit it.

### GET `/api/goal-plan/recent`

**Response `200`**
```json
{
  "id": "7ab3...",
  "date": "2026-06-09",
  "goal_stratergy": {
    "role_targets": ["ML Engineer", "AI Engineer"],
    "milestones": [
      { "week": 1, "focus": "Resume rewrite + 15 applications" },
      { "week": 2, "focus": "DP + graph drills, 2 mock interviews" }
    ],
    "daily_targets": { "applications": 5, "networking": 3, "leetcode": 2 }
  },
  "revision_analytics": null,
  "goal_committed_at": "2026-06-09",
  "next_revision_date": "2026-06-19",
  "created_at": "2026-06-09T15:02:11Z"
}
```
Note the field is spelled `goal_stratergy` (sic) in the DB — its inner JSON shape is produced by the LLM and may vary; render defensively. `404` if no plan exists yet.

### POST `/api/goal-plan/commit`

No body. Marks the latest goal plan committed, moves user phase to `active`, sets `next_revision_date` (+10 days), and fires target recalibration in the background.

**Response `200`**
```json
{ "plan_id": "7ab3...", "committed_at": "2026-06-11" }
```
`404` if there is no goal plan to commit.

---

## 7. Daily Activity Log

Source: [careerpilot/api/routes/daily_log.py](careerpilot/api/routes/daily_log.py)

### POST `/api/daily-log`

Upserts today's activity (one row per user per day). All counters default to 0 — send only what changed or the whole form.

**Request**
```json
{
  "date": "2026-06-11",
  "dsa_problems": 3,
  "other_prep": "Read DDIA ch. 5",
  "system_design_topic": "rate limiting",
  "applications_sent": 5,
  "networking_sent": 3,
  "coffee_chat": 1,
  "called_for_calls": 0,
  "oa_pending": 1,
  "recruiter_screens": 1,
  "technical_rounds": 0,
  "final_rounds": 0,
  "mocks_done": 1,
  "notes": "Good momentum today"
}
```

**Response `200`**
```json
{ "ok": true, "date": "2026-06-11" }
```

### GET `/api/daily-log?days=90`

Last N days of logs, **oldest-first** (chart-ready).

**Response `200`**
```json
[
  {
    "user_id": "uuid",
    "date": "2026-06-10",
    "dsa_problems": 2,
    "applications_sent": 4,
    "networking_sent": 2,
    "recruiter_screens": 0,
    "technical_rounds": 1,
    "mocks_done": 0,
    "notes": "",
    "apps_done": 4,
    "leetcode_done": 2
  }
]
```
(Legacy fields `apps_done`, `networking_done`, `leetcode_done`, etc. are mirrored for backward compat — prefer the new names.)

---

## 8. Interviews

Source: [careerpilot/api/routes/interviews.py](careerpilot/api/routes/interviews.py)

Enums:
- `stage`: `phone_screen` | `technical` | `system_design` | `behavioral` | `onsite` | `final`
- `how_contacted`: `linkedin` | `referral` | `job_board` | `cold_apply` | `recruiter` | `other`
- `status`: `pass` | `fail` | `pending`

### POST `/api/interviews` → `201`

Logging an interview also triggers a background skill-map re-score.

**Request**
```json
{
  "company": "Stripe",
  "role": "ML Engineer",
  "stage": "technical",
  "date": "2026-06-13",
  "how_contacted": "referral",
  "topics": ["dynamic programming", "system design"],
  "questions_asked": ["Design a fraud-detection pipeline"],
  "what_went_wrong": null,
  "notes": "Recruiter said 2 rounds",
  "status": "pending"
}
```
Only `company`, `stage`, `date` are required.

**Response `201`** — the saved row:
```json
{
  "id": "c2d4...",
  "user_id": "uuid",
  "company": "Stripe",
  "role": "ML Engineer",
  "stage": "technical",
  "date": "2026-06-13",
  "how_contacted": "referral",
  "topics": ["dynamic programming", "system design"],
  "questions_asked": ["Design a fraud-detection pipeline"],
  "what_went_wrong": null,
  "notes": "Recruiter said 2 rounds",
  "status": "pending",
  "created_at": "2026-06-11T20:00:00Z"
}
```

### PATCH `/api/interviews/{interview_id}`

Update outcome afterwards (flip `pending` → `pass`/`fail`, add post-mortem). Any subset of: `status`, `what_went_wrong`, `notes`, `topics`, `questions_asked`.

**Request**
```json
{ "status": "fail", "what_went_wrong": "Froze on the DP follow-up" }
```

**Response `200`** `{ "ok": true }`

### GET `/api/interviews?limit=20`

All interviews, newest date first. **Response `200`** — array of rows in the shape above.

---

## 9. Profile (resume / LinkedIn)

Source: [careerpilot/api/routes/profile.py](careerpilot/api/routes/profile.py)

Both endpoints save the raw text and trigger the background Talent Mapper to (re)score the skill map.

### POST `/api/profile/resume`
```json
{ "text": "JANE DOE\nML Engineer...\nEXPERIENCE..." }
```
**Response `200`** `{ "status": "ok" }`

### POST `/api/profile/linkedin`
```json
{ "text": "About: ML engineer with 4 years..." }
```
**Response `200`** `{ "status": "ok" }`

---

## 10. Dashboard (single fetch)

Source: [careerpilot/api/routes/dashboard.py](careerpilot/api/routes/dashboard.py)

### GET `/api/dashboard`

One call returns everything the dashboard page needs.

**Response `200`**
```json
{
  "upcoming_interviews": [ { "...": "interview rows, date >= today, soonest first" } ],
  "past_interviews":     [ { "...": "last 20 past interview rows, newest first" } ],
  "today_log":           { "...": "today's daily_log row" },
  "recent_logs":         [ { "...": "last 30 days of daily_log, oldest first" } ],
  "recent_checkins":     [ { "...": "last 14 check-ins, newest first" } ],
  "today_plan": {
    "plan_id": "5e7d...",
    "date": "2026-06-11",
    "coach_note": "...",
    "priority_mode": "interview_prep",
    "schedule": { "morning": {}, "midday": {}, "evening": {} },
    "tasks": [
      { "id": "t1", "title": "Send 5 applications", "category": "job_search", "priority": 1, "completed": false }
    ]
  },
  "active_goal":  { "...": "full latest goal_plan row (see §6)" },
  "skill_map": {
    "dynamic_programming": { "score": 0.45, "evidence": ["failed Stripe technical"] },
    "system_design":       { "score": 0.7 }
  },
  "tracking_skills": ["python", "pytorch", "sql"],
  "snapshot": {
    "days_since": 24,
    "days_left": 56,
    "phase": "active",
    "open_tasks": 4,
    "role": "MLE",
    "leetcode_level": "shaky_mediums",
    "intake_complete": true,
    "mood_score": 6,
    "energy_score": 4,
    "last_checkin_at": "2026-06-11T22:10:00Z"
  }
}
```
Nullable: `today_log`, `today_plan`, `active_goal`, `skill_map`, `tracking_skills`, and every `snapshot` field can be `null` for a new user — render empty states. `days_since` counts from search start; `days_left` is derived from `runway_weeks`.

---

## 11. Health

### GET `/health` (no `/api` prefix, no auth)
```json
{ "status": "ok" }
```

---

## 12. Chat Agents (routing)

Source: [careerpilot/orchestrator/orchestrator.py](careerpilot/orchestrator/orchestrator.py)

Every `/api/chat` message is classified by the supervisor into an `intent`, which maps to an agent. The frontend sees the `intent` string and friendly `agent` display name in responses:

| Intent | Agent module | Display name | Handles |
|---|---|---|---|
| `intake` | runtime/intake | Intake Coach | Onboarding Q&A |
| `goal_planner` | runtime/goal_planner | Goal Strategist | Building/revising the goal plan |
| `checkin` | runtime/daily_tracker | Daily Tracker | Mood/energy/progress check-ins |
| `plan`, `accountability` | runtime/accountability | Accountability Coach | Plan questions, slipping targets, interview outcomes |
| `mental_health`, `chat` | runtime/mental_health_check | Wellness Coach | Stress, burnout, default fallback |
| `resume` | sub_agents/resume_helper | Resume Coach | Resume review/rewrites |
| `linkedin` | sub_agents/linkedin_enhancer | LinkedIn Coach | Profile improvement |
| `mock_prep` | sub_agents/mock_prep | Mock Prep | Mock interview practice |
| `patterns` | sub_agents/pattern_tracker | Pattern Tracker | Trends across interviews/logs |

UI hints: show `agent_event.display_name` + `reason` as a "routing" indicator while streaming; the `intent` is also stored on each history row.

---

## 13. Background Workers & Agents

These run server-side — the frontend never calls them directly, but their output appears in plans, dashboards, and skill maps. Useful for understanding when data changes.

### Workers ([careerpilot/workers/](careerpilot/workers/))

| Worker | Trigger | What it does |
|---|---|---|
| `scheduler.py` | APScheduler cron | Sun 6 AM: target recalibration (active users) · Sun 9 AM: finance/runway check · Mon 7 AM: weekly interview prep plan |
| `health_worker.py` | Nightly run | For all active users: aggregates daily signals + runs PauseAgent burnout check |
| `plan_worker.py` | Redis `plan_queue` consumer | Dequeues `{ "user_id": ... }` jobs and runs the Daily Plan Builder |

### Background agents ([careerpilot/agents/background/](careerpilot/agents/background/))

| Agent | Triggered by | Effect visible to frontend |
|---|---|---|
| `daily_check.py` (Daily Plan Builder) | Check-in submit, `/api/plan/generate`, plan_worker | New row readable via `GET /api/plan/today` (signals → carryover → prioritizer → schedule) |
| `signal_analyzer.py` | Inside plan build | `priority_mode` + diagnosis embedded in plan |
| `carryover.py` | Inside plan build | Unfinished tasks roll into the next plan |
| `plan_prioritizer.py` | Inside plan build | Picks `priority_mode` and adjusts daily targets (pure logic, no LLM) |
| `schedule_builder.py` | Inside plan build | The `schedule.morning/midday/evening` blocks + `coach_note` |
| `talent_mapper.py` | Resume/LinkedIn upload, interview logged/updated | Updates `skill_map` on dashboard |
| `target_recalibrator.py` | Goal commit, weekly cron | Updates `daily_targets` from deadline + funnel math |
| `interview_prep.py` | Weekly cron (Mon) | Weekly prep plan from target roles + stage history |
| `finance_check_agent.py` | Weekly cron (Sun) | Recalculates `runway_weeks` → affects `snapshot.days_left` |
| `pause_agent.py` | Nightly health_worker | Burnout flag → `recovery` priority mode in next plan |
| `job_strategy.py` | Weekly | Market data refresh + pipeline recommendations |
| `role_curriculum.py` | Inside plan build | Maps role → leetcode/system-design topic sequence |
| `severance_agent.py` | Onboarding | Parses severance package, tracks declining balance |
| `fact_checker.py` | Document ingestion | Pre-embeds source chunks for citation retrieval |

### Practical refresh rules for the frontend

- After `POST /api/checkin` → tomorrow's plan rebuilds in the background (no need to poll).
- After `POST /api/goal-plan/commit` → call `POST /api/plan/generate` yourself (the commit fires recalibration only).
- After logging/updating an interview or uploading resume/LinkedIn → `skill_map` refreshes within seconds; re-fetch `/api/dashboard` lazily.
- On a `done` SSE chat event with `refresh_plan: true` → re-fetch `GET /api/plan/today`.
