// Pure type definitions and navigation constants.
// No imports of fetch / api client — keeps the dependency graph acyclic.

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

export function stepTitle(steps: JourneyStep[], id: CoreStepId): string {
  return steps.find((s) => s.id === id)?.title ?? id;
}

/** 步骤可随时进入；画像未完成时仅返回软提示，不再硬拦。 */
export function canOpenStep(
  journey: Journey,
  step: CoreStepId,
): { ok: boolean; hint?: string } {
  if (step === "know_self") return { ok: true };
  if (!journey.know_self_complete) {
    return {
      ok: true,
      hint: "「认识自己」尚未完成，探索结果可能不够准，可随时回来补全",
    };
  }
  return { ok: true };
}
