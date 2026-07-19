export type JourneyStep = {
  id: string;
  title: string;
  subtitle: string;
  engine: string;
  optional?: boolean;
  done: boolean;
  current: boolean;
};

export type Journey = {
  current: string;
  current_title: string;
  engine_stage: string;
  next_hint: string;
  know_self_complete: boolean;
  explore_complete: boolean;
  core_complete: boolean;
  steps: JourneyStep[];
};

export type CoreStepId = "know_self" | "explore" | "decide";

export type ChatMessage = { role: "user" | "assistant"; content: string };

export type ProfilePreview = {
  name: string | null;
  current_role: string | null;
  education: string[];
  core_skills: string[];
  values: string[];
  evidence_count: number;
};

export type IntakeProgress = {
  percent: number;
  checks: { label: string; done: boolean }[];
};

export type ChatState = {
  messages: ChatMessage[];
  llm: { provider: string; model: string; configured: boolean };
  intake_complete: boolean;
  validation: { errors: string[]; warnings: string[] };
  profile_preview: ProfilePreview;
  progress: IntakeProgress;
  gap_hints: string[];
  journey: Journey;
};

export type ProfileView = {
  empty: boolean;
  message?: string;
  title?: string;
  validation?: { errors: string[]; warnings: string[] };
  education?: {
    level: string;
    school: string;
    school_tier?: string;
    major: string;
    department?: string;
    time: string;
    notes: string;
  }[];
  core_skills?: string[];
  adjacent_skills?: string[];
  evidence?: { claim: string; proof: string }[];
  constraints?: { age?: number; risk_appetite: string; notes?: string };
  narrative_md?: string | null;
};

export type TrendsView = {
  empty: boolean;
  message?: string;
  signals: {
    domain: string;
    label: string;
    items: {
      topic: string;
      finding: string;
      confidence: string;
      retrieved_on: string;
      source: string;
      source_url?: string;
    }[];
  }[];
  sectors: {
    name: string;
    why_hot?: string;
    value_is_in?: string;
    trap?: string;
  }[];
};

export type SavedJobItem = {
  id?: string;
  company: string;
  role: string;
  location: string;
  source?: string;
  saved_on: string;
  status: string;
  linked_direction?: string;
  notes?: string;
  description?: string;
  description_preview?: string;
  match?: {
    summary: string;
    linked_direction?: string;
    barriers: string[];
  };
};

export type JobsView = {
  empty: boolean;
  message?: string;
  hint?: string;
  count?: number;
  jobs: SavedJobItem[];
};

export type JobsAddPayload = {
  company: string;
  role: string;
  description: string;
  location?: string;
  source?: string;
  linked_direction?: string;
  notes?: string;
};

export type JobsAddResponse = {
  ok: boolean;
  job?: SavedJobItem;
  error?: string;
};

export type JobsUpdatePayload = {
  company?: string;
  role?: string;
  description?: string;
  location?: string;
  source?: string;
  linked_direction?: string;
  notes?: string;
  status?: SavedJobStatus;
};

export type SavedJobStatus =
  | "interested"
  | "researching"
  | "ready"
  | "applied"
  | "archived";

export type JobsUpdateResponse = {
  ok: boolean;
  job?: SavedJobItem;
  error?: string;
};

export type JobsRemoveResponse = {
  ok: boolean;
  removed?: string;
  error?: string;
};

export type MatrixView = {
  empty: boolean;
  message?: string;
  hint?: string;
  format?: "markdown" | "yaml_summary";
  content?: string;
  has_markdown?: boolean;
  unified_theme?: string;
  shared_assets?: string[];
  primary?: MatrixRow[];
  hidden_directions?: string[];
  order_overrides?: string[];
  notes?: Record<string, string>;
};

export type MatrixRow = Record<string, string | number>;

export type MatrixFeedbackAction = {
  action: "remove" | "reorder" | "reset" | "note";
  direction?: string;
  timestamp: string;
  details?: Record<string, unknown>;
};

export type MatrixFeedbackResponse = {
  actions: MatrixFeedbackAction[];
};

export type ExecutionView = {
  empty: boolean;
  message?: string;
  hint?: string;
  format?: "markdown";
  content?: string;
};

export type TrackView = {
  empty: boolean;
  message?: string;
  hint?: string;
  funnel: {
    total: number;
    by_status: Record<string, number>;
    response_rate: number;
    interview_rate: number;
    offer_rate: number;
    ghosted_count: number;
    rejected_count: number;
  };
  applications: {
    id: string;
    company: string;
    role: string;
    tier: string;
    direction: string;
    status: string;
    applied_on: string;
    feedback: string;
    notes: string;
  }[];
};

export type AppData = {
  data_dir: string;
  intake_complete: boolean;
  journey: Journey;
  views: {
    profile: ProfileView;
    trends: TrendsView;
    jobs: JobsView;
    matrix: MatrixView;
    execution: ExecutionView;
    track: TrackView;
  };
  spa: boolean;
};

export type CommandResult = {
  ok: boolean;
  code: number;
  output: string;
};

export type User = {
  id: string;
  email: string;
  is_active: boolean;
};

export type AuthTokens = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
};

export type LoginPayload = {
  email: string;
  password: string;
};

export type RegisterPayload = {
  email: string;
  password: string;
};

export type HealthResponse = {
  ok: boolean;
  db: "up" | "down";
};

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : "{}",
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  status: number;
  code?: string;
  detail?: unknown;
  constructor(status: number, message: string, code?: string, detail?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

async function readErrorPayload(res: Response): Promise<{
  code?: string;
  message?: string;
  detail?: unknown;
}> {
  try {
    const data = (await res.json()) as {
      code?: string;
      error?: string;
      message?: string;
      detail?: unknown;
    };
    if (typeof data.code === "string") return { code: data.code, detail: data.detail };
    if (typeof data.error === "string") return { message: data.error, detail: data.detail };
    if (typeof data.message === "string") return { message: data.message, detail: data.detail };
    if (typeof data.detail === "string") return { message: data.detail, detail: data.detail };
    return { detail: data.detail };
  } catch {
    return {};
  }
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    const info = await readErrorPayload(res);
    throw new ApiError(
      res.status,
      info.message ?? `HTTP ${res.status}`,
      info.code,
      info.detail,
    );
  }
  return res.json() as Promise<T>;
}

async function authPost<T>(
  path: string,
  body?: unknown,
  tokens?: { accessToken?: string },
): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (tokens?.accessToken) headers.Authorization = `Bearer ${tokens.accessToken}`;
  const res = await fetch(path, {
    method: "POST",
    headers,
    body: body ? JSON.stringify(body) : "{}",
  });
  if (!res.ok) {
    const info = await readErrorPayload(res);
    throw new ApiError(
      res.status,
      info.message ?? `HTTP ${res.status}`,
      info.code,
      info.detail,
    );
  }
  return res.json() as Promise<T>;
}

async function authGet<T>(
  path: string,
  tokens?: { accessToken?: string },
): Promise<T> {
  const headers: Record<string, string> = {};
  if (tokens?.accessToken) headers.Authorization = `Bearer ${tokens.accessToken}`;
  const res = await fetch(path, { headers });
  if (!res.ok) {
    const info = await readErrorPayload(res);
    throw new ApiError(
      res.status,
      info.message ?? `HTTP ${res.status}`,
      info.code,
      info.detail,
    );
  }
  return res.json() as Promise<T>;
}

export const api = {
  loadAll: () => getJson<AppData>("/api/load_all"),
  chatState: () => getJson<ChatState>("/api/chat_state"),
  chatSend: (message: string) =>
    post<ChatState & { reply: string; files_updated?: string[]; just_completed?: boolean }>(
      "/api/chat_send",
      { message },
    ),
  chatReset: () => post<{ ok: boolean }>("/api/chat_reset"),
  runCommand: (cmd: string) => post<CommandResult>("/api/run_command", { cmd }),
  matrixFeedback: () => getJson<MatrixFeedbackResponse>("/api/matrix_feedback"),
  matrixFeedbackAdd: (
    action: MatrixFeedbackAction["action"],
    direction?: string,
    details?: Record<string, unknown>,
  ) =>
    post<{ ok: boolean; action?: MatrixFeedbackAction; error?: string }>(
      "/api/matrix_feedback/add",
      { action, direction, details },
    ),
  jobsAdd: (payload: JobsAddPayload) =>
    post<JobsAddResponse>("/api/jobs/add", payload),
  jobsUpdate: (id: string, payload: JobsUpdatePayload) =>
    post<JobsUpdateResponse>("/api/jobs/update", { id, ...payload }),
  jobsRemove: (id: string) =>
    post<JobsRemoveResponse>("/api/jobs/remove", { id }),
  authRegister: (payload: RegisterPayload) =>
    authPost<{ id: string; email: string }>("/api/auth/register", payload),
  authLogin: (payload: LoginPayload) =>
    authPost<AuthTokens>("/api/auth/login", payload),
  authRefresh: (refreshToken: string) =>
    authPost<{ access_token: string; token_type: "bearer" }>("/api/auth/refresh", {
      refresh_token: refreshToken,
    }),
  authLogout: (tokens?: { accessToken?: string }) =>
    authPost<{ ok: boolean }>("/api/auth/logout", undefined, tokens),
  authMe: (tokens?: { accessToken?: string }) =>
    authGet<User>("/api/auth/me", tokens),
  health: () => authGet<HealthResponse>("/api/health"),
};

/** 核心三步 — GUI 主导航 */
export const CORE_STEP_IDS: CoreStepId[] = ["know_self", "explore", "decide"];

export const JOURNEY_STEPS: {
  id: CoreStepId;
  sub?: { id: string; label: string }[];
}[] = [
  {
    id: "know_self",
    sub: [
      { id: "chat", label: "对话" },
      { id: "profile", label: "完整画像" },
    ],
  },
  {
    id: "explore",
    sub: [
      { id: "trends", label: "行业信号" },
      { id: "jobs", label: "岗位收藏" },
    ],
  },
  { id: "decide" },
];

export const STEP_TOOLBAR: Record<
  CoreStepId,
  { label: string; cmd: string; secondary?: boolean }[]
> = {
  know_self: [
    { label: "重置对话", cmd: "chat-reset" },
    { label: "校验画像", cmd: "validate", secondary: true },
    { label: "刷新", cmd: "refresh", secondary: true },
  ],
  explore: [
    { label: "分析收藏", cmd: "job-analyze" },
    { label: "刷新", cmd: "refresh", secondary: true },
  ],
  decide: [
    { label: "生成矩阵", cmd: "render-opportunities" },
    { label: "刷新", cmd: "refresh", secondary: true },
  ],
};

export function stepTitle(steps: JourneyStep[], id: CoreStepId): string {
  return steps.find((s) => s.id === id)?.title ?? id;
}

export function canOpenStep(journey: Journey, step: CoreStepId): { ok: boolean; reason?: string } {
  if (step === "know_self") return { ok: true };
  if (!journey.know_self_complete) {
    return { ok: false, reason: "请先完成「认识自己」" };
  }
  return { ok: true };
}
