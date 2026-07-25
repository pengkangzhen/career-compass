import { apiUrl, fetchWithAuth, readErrorPayload } from "./fetch";
import type {
  AppData,
  AuthTokens,
  ChatState,
  CommandResult,
  HealthResponse,
  JobsAddPayload,
  JobsAddResponse,
  JobsRemoveResponse,
  JobsUpdatePayload,
  JobsUpdateResponse,
  LoginPayload,
  MatrixFeedbackAction,
  MatrixFeedbackResponse,
  RegisterPayload,
  User,
} from "./types";

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

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetchWithAuth(apiUrl(path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : "{}",
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

async function postForm<T>(path: string, body: FormData): Promise<T> {
  // 注意：不要手动设 Content-Type —— 浏览器会自动加 multipart boundary
  const res = await fetchWithAuth(apiUrl(path), {
    method: "POST",
    body,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetchWithAuth(apiUrl(path));
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
  const res = await fetch(apiUrl(path), {
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
  const res = await fetch(apiUrl(path), { headers });
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
  uploadResume: (file: File) => {
    const form = new FormData();
    form.append("file", file, file.name);
    return postForm<ChatState & { reply: string; files_updated?: string[]; just_completed?: boolean }>(
      "/api/resume/upload",
      form,
    );
  },
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

// Legacy re-exports kept for the few places still importing `api` or
// `ApiError` from "../api/types" — new code should import from "./api/client".

export type {
  AppData,
  AuthTokens,
  ChatMessage,
  ChatState,
  CommandResult,
  CoreStepId,
  ExecutionView,
  HealthResponse,
  IntakeProgress,
  Journey,
  JourneyStep,
  JobsAddPayload,
  JobsAddResponse,
  JobsRemoveResponse,
  JobsUpdatePayload,
  JobsUpdateResponse,
  JobsView,
  MatrixFeedbackAction,
  MatrixFeedbackResponse,
  MatrixRow,
  MatrixView,
  ProfilePreview,
  ProfileView,
  RegisterPayload,
  LoginPayload,
  SavedJobItem,
  SavedJobStatus,
  TrackView,
  TrendsView,
  User,
} from "./types";
