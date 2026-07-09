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

export type JobsView = {
  empty: boolean;
  message?: string;
  hint?: string;
  count?: number;
  jobs: {
    company: string;
    role: string;
    location: string;
    saved_on: string;
    status: string;
    notes?: string;
    match?: {
      summary: string;
      linked_direction?: string;
      barriers: string[];
    };
  }[];
};

export type MatrixView = {
  empty: boolean;
  message?: string;
  hint?: string;
  format?: "markdown" | "yaml_summary";
  content?: string;
  unified_theme?: string;
  shared_assets?: string[];
  primary?: Record<string, string | number>[];
  side?: Record<string, string | number>[];
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

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : "{}",
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  loadAll: () => fetch("/api/load_all").then((r) => r.json()) as Promise<AppData>,
  chatState: () => fetch("/api/chat_state").then((r) => r.json()) as Promise<ChatState>,
  chatSend: (message: string) =>
    post<ChatState & { reply: string; files_updated?: string[]; just_completed?: boolean }>(
      "/api/chat_send",
      { message },
    ),
  chatReset: () => post<{ ok: boolean }>("/api/chat_reset"),
  runCommand: (cmd: string) => post<CommandResult>("/api/run_command", { cmd }),
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
