import { loadTokens, saveTokens, clearTokens } from "../auth/tokens";

// API base URL — empty in dev (Vite proxy forwards /api/* to localhost:8000),
// set to the Render backend URL in prod (e.g. https://beidou-api.onrender.com).
const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "";

export function apiUrl(path: string): string {
  // path always starts with "/api/..."
  if (API_BASE) return API_BASE + path;
  return path;
}

type FetchInit = RequestInit & {
  headers?: Record<string, string>;
};

async function attachAuthHeader(init: FetchInit): Promise<FetchInit> {
  const tokens = loadTokens();
  if (!tokens) return init;
  const headers: Record<string, string> = { ...(init.headers ?? {}) };
  headers.Authorization = `Bearer ${tokens.access_token}`;
  return { ...init, headers };
}

// Calls /api/auth/refresh directly with a bare fetch — deliberately bypassing
// api/client so the auth refresh path doesn't form a module cycle with it.
// The refresh token IS the credential here, so no Authorization header needed.
async function refreshAccessToken(refreshToken: string): Promise<boolean> {
  try {
    const res = await fetch(apiUrl("/api/auth/refresh"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) {
      clearTokens();
      return false;
    }
    const data = (await res.json()) as { access_token: string };
    const existing = loadTokens();
    if (!existing) return false;
    saveTokens({
      access_token: data.access_token,
      refresh_token: existing.refresh_token,
      token_type: "bearer",
    });
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

export async function fetchWithAuth(
  url: string,
  init: FetchInit = {},
): Promise<Response> {
  const authedInit = await attachAuthHeader(init);
  const res = await fetch(url, authedInit);
  if (res.status !== 401) return res;

  const tokens = loadTokens();
  if (!tokens) return res;

  const refreshed = await refreshAccessToken(tokens.refresh_token);
  if (!refreshed) return res;

  const retriedInit = await attachAuthHeader(init);
  return fetch(url, retriedInit);
}

export const authenticatedFetch = fetchWithAuth;

export async function readErrorPayload(res: Response): Promise<{
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
