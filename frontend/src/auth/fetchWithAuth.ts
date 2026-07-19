import { api } from "../api/types";
import { clearTokens, loadTokens, saveTokens } from "./tokens";

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

async function attemptRefresh(refreshToken: string): Promise<boolean> {
  try {
    const res = await api.authRefresh(refreshToken);
    const existing = loadTokens();
    if (!existing) return false;
    saveTokens({
      access_token: res.access_token,
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

  const refreshed = await attemptRefresh(tokens.refresh_token);
  if (!refreshed) return res;

  const retriedInit = await attachAuthHeader(init);
  return fetch(url, retriedInit);
}

export const authenticatedFetch = fetchWithAuth;
