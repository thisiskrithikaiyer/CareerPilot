export interface Message {
  role: "user" | "assistant";
  content: string;
}

export interface AgentEvent {
  agent: string;
  display_name: string;
  reason: string;
  timestamp: string;
}

export interface ChatResponse {
  reply: string;
  chips: string[];
  intent: string;
  agent: string;
  sources?: string[];
  agent_events?: AgentEvent[];
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "cc_token";
const TOKEN_VERSION_KEY = "cc_token_v";
const TOKEN_VERSION = "2"; // bump this whenever auth system changes

// --- Token helpers ---
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  // If token is from a previous auth system, discard it
  if (localStorage.getItem(TOKEN_VERSION_KEY) !== TOKEN_VERSION) {
    localStorage.removeItem(TOKEN_KEY);
    return null;
  }
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(TOKEN_VERSION_KEY, TOKEN_VERSION);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(TOKEN_VERSION_KEY);
}

// --- Session date (for "advance day" testing) ---
const SESSION_DATE_KEY = "cc_session_date";

export function getSessionDate(): string {
  if (typeof window === "undefined") return new Date().toISOString().slice(0, 10);
  return localStorage.getItem(SESSION_DATE_KEY) ?? new Date().toISOString().slice(0, 10);
}

export function setSessionDate(date: string) {
  localStorage.setItem(SESSION_DATE_KEY, date);
}

export function advanceSessionDate(): string {
  const current = getSessionDate();
  const d = new Date(current + "T00:00:00");
  d.setDate(d.getDate() + 1);
  const next = d.toISOString().slice(0, 10);
  setSessionDate(next);
  return next;
}

// --- Auth ---
export async function login(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Login failed: ${res.status}`);
  }

  return res.json();
}

export async function register(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Registration failed: ${res.status}`);
  }

  return res.json();
}

// --- Profile ---
export async function saveResume(text: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/profile/resume`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken()}`,
    },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Failed to save resume: ${res.status}`);
  }
}

export async function saveLinkedIn(text: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/profile/linkedin`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken()}`,
    },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Failed to save LinkedIn: ${res.status}`);
  }
}

export interface GoalPlan {
  id: string;
  date: string;
  created_at: string;
  goal_committed_at: string | null;
  next_revision_date: string | null;
  goal_stratergy: {
    mode: string;
    reasoning: string | null;
    resume_score: number | null;
    linkedin_score: number | null;
    role_targets: { stretch: string | null; realistic: string | null; safety: string | null };
    daily_targets: { applications: number; networking_messages: number; linkedin_connects: number; leetcode_problems: number };
    weekly_milestones: { week: string; goal: string }[];
    leetcode_tier: string;
    technical_focus: string;
    suggested_info: string | null;
    current_daily_plan?: {
      date: string;
      job_apps: number;
      networking: number;
      leetcode_problems: number;
      leetcode_topic: string;
      leetcode_suggested: string[];
      behavioral_focus: string;
      system_design: number;
      coach_note: string;
    };
  };
  revision_analytics: unknown;
}

export async function fetchGoalPlan(): Promise<GoalPlan | null> {
  const token = getToken();
  const res = await fetch(`${API_BASE}/api/goal-plan/recent`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) return null;
  return res.json();
}

export async function commitPlan(): Promise<{ plan_id: string; committed_at: string } | null> {
  const token = getToken();
  const res = await fetch(`${API_BASE}/api/goal-plan/commit`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) return null;
  return res.json();
}

export interface ScheduleBlock {
  time: string;
  tasks: string[];
}

export interface TodayPlan {
  plan_id: string;
  date: string;
  coach_note: string;
  priority_mode: string;
  schedule: {
    morning: ScheduleBlock;
    midday: ScheduleBlock;
    evening: ScheduleBlock;
  };
  job_apps: number;
  leetcode_problems: number;
  leetcode_topic: string;
  [key: string]: unknown;
}

export async function fetchTodayPlan(date?: string): Promise<TodayPlan | null> {
  const token = getToken();
  const url = date ? `${API_BASE}/api/plan/today?target_date=${date}` : `${API_BASE}/api/plan/today`;
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) return null;
  return res.json();
}

export async function generatePlan(): Promise<TodayPlan | null> {
  const token = getToken();
  const res = await fetch(`${API_BASE}/api/plan/generate`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) return null;
  return res.json();
}

export async function generatePlanForDate(targetDate: string): Promise<TodayPlan | null> {
  const token = getToken();
  const res = await fetch(`${API_BASE}/api/plan/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ target_date: targetDate }),
  });
  if (!res.ok) return null;
  return res.json();
}

// --- Intake ---
export interface IntakeFields {
  role: string;
  offer_timeline: string;
  leetcode_level: string;
  resume_text?: string;
  notes?: string;
}

export async function submitIntake(fields: IntakeFields): Promise<void> {
  const token = getToken();
  const res = await fetch(`${API_BASE}/api/intake`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(fields),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Intake failed: ${res.status}`);
  }
}

export async function getIntakeStatus(): Promise<{ intake_complete: boolean; phase: string }> {
  const token = getToken();
  const res = await fetch(`${API_BASE}/api/intake/status`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) return { intake_complete: false, phase: "intake" };
  return res.json();
}

export interface IntakeOption {
  value: string;
  label: string;
}

export interface IntakeStepEvent {
  type: "step";
  reply: string;
  field_key: string | null;
  question: string;
  options: IntakeOption[];
  intake_complete: boolean;
  chips: string[];
}

export type IntakeStreamEvent =
  | { type: "agent_event"; agent: string; display_name: string; reason: string; timestamp: string }
  | IntakeStepEvent
  | { type: "error"; message: string };

export async function streamIntake(
  messages: Message[],
  collectedFields: Partial<IntakeFields>,
  onEvent: (event: IntakeStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const token = getToken();
  const res = await fetch(`${API_BASE}/api/intake/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ messages, collected_fields: collectedFields }),
    signal,
  });
  handleUnauthorized(res);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Intake stream failed: ${res.status}`);
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6).trim();
        if (data) {
          try { onEvent(JSON.parse(data)); } catch { /* ignore malformed */ }
        }
      }
    }
  }
}

export class AuthError extends Error {}

function handleUnauthorized(res: Response) {
  if (res.status === 401) {
    clearToken();
    throw new AuthError("Session expired. Please sign in again.");
  }
}

export interface StreamEvent {
  type: "agent_event" | "done" | "error";
  // agent_event
  agent?: string;
  display_name?: string;
  reason?: string;
  timestamp?: string;
  // done
  reply?: string;
  chips?: string[];
  intent?: string;
  sources?: string[];
  phase?: string;
  // error
  message?: string;
}

export async function streamChat(
  messages: Message[],
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const token = getToken();
  const res = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ messages }),
    signal,
  });

  handleUnauthorized(res);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Request failed: ${res.status}`);
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6).trim();
        if (data) {
          try { onEvent(JSON.parse(data)); } catch { /* ignore malformed */ }
        }
      }
    }
  }
}

// --- Daily Log ---
export interface DailyLogData {
  date?: string;
  dsa_problems?: number;
  other_prep?: string;
  system_design_topic?: string;
  applications_sent?: number;
  networking_sent?: number;
  coffee_chat?: number;
  called_for_calls?: number;
  oa_pending?: number;
  recruiter_screens?: number;
  technical_rounds?: number;
  final_rounds?: number;
  mocks_done?: number;
  notes?: string;
}

export interface DailyLogEntry extends DailyLogData {
  id?: string;
  user_id?: string;
  created_at?: string;
}

export async function submitDailyLog(data: DailyLogData): Promise<void> {
  const token = getToken();
  const res = await fetch(`${API_BASE}/api/daily-log`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Failed to save daily log: ${res.status}`);
  }
}

export async function fetchDailyLogs(days = 90): Promise<DailyLogEntry[]> {
  const token = getToken();
  const res = await fetch(`${API_BASE}/api/daily-log?days=${days}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) return [];
  return res.json();
}

// --- Chat ---
export async function fetchChatHistory(limit = 10): Promise<Message[]> {
  const token = getToken();
  const res = await fetch(`${API_BASE}/api/chat/history?limit=${limit}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) return [];
  const rows: { role: string; content: string }[] = await res.json();
  return rows.map((r) => ({ role: r.role as "user" | "assistant", content: r.content }));
}

export async function sendMessage(messages: Message[]): Promise<ChatResponse> {
  const token = getToken();
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ messages }),
  });

  handleUnauthorized(res);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Request failed: ${res.status}`);
  }

  return res.json();
}
