import { describe, expect, it, vi, beforeEach } from "vitest";
import { fetchWithAuth, apiUrl } from "./fetch";
import { saveTokens, clearTokens } from "../auth/tokens";

// Typed fetch stub: same signature as global fetch, so calls[n][1] is a
// RequestInit (not undefined). The spy shifts through `responses` in order.
type FetchSpy = ReturnType<typeof vi.fn<typeof fetch>>;
function mockFetchSequence(responses: Response[]): FetchSpy {
  const spy = vi.fn(async (..._args: Parameters<typeof fetch>) =>
    responses.shift() ?? new Response("{}", { status: 599 }),
  ) as FetchSpy;
  vi.stubGlobal("fetch", spy);
  return spy;
}

function jsonRes(body: unknown, init?: ResponseInit): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

describe("apiUrl", () => {
  it("returns the path as-is when VITE_API_BASE unset", () => {
    // In test env VITE_API_BASE is undefined → falls back to "".
    expect(apiUrl("/api/health")).toBe("/api/health");
  });
});

describe("fetchWithAuth", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.unstubAllGlobals();
  });

  it("passes through when no tokens are stored (no Authorization header)", async () => {
    const spy = mockFetchSequence([jsonRes({ ok: true })]);
    const res = await fetchWithAuth("/api/foo");
    expect(res.status).toBe(200);
    expect(spy).toHaveBeenCalledTimes(1);
    const init = spy.mock.calls[0]![1] as RequestInit;
    const headers = (init.headers as Record<string, string> | undefined) ?? {};
    expect(headers.Authorization).toBeUndefined();
  });

  it("attaches Bearer token from storage", async () => {
    saveTokens({ access_token: "ACC", refresh_token: "REF", token_type: "bearer" });
    const spy = mockFetchSequence([jsonRes({ ok: true })]);
    await fetchWithAuth("/api/foo");
    const init = spy.mock.calls[0]![1] as RequestInit;
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer ACC");
  });

  it("retries with refreshed token after a 401", async () => {
    saveTokens({ access_token: "OLD", refresh_token: "REF", token_type: "bearer" });
    const spy = mockFetchSequence([
      new Response("{}", { status: 401 }),
      jsonRes({ access_token: "NEW" }), // refresh response
      jsonRes({ ok: true }),            // retried original
    ]);
    const res = await fetchWithAuth("/api/foo");
    expect(res.status).toBe(200);
    expect(spy).toHaveBeenCalledTimes(3);

    // After refresh, storage should hold the new access token.
    const init3 = spy.mock.calls[2]![1] as RequestInit;
    expect((init3.headers as Record<string, string>).Authorization).toBe("Bearer NEW");

    // Storage should now reflect the rotated access token.
    expect(window.localStorage.getItem("beidou.access_token")).toBe("NEW");
  });

  it("clears tokens and returns 401 if refresh itself fails", async () => {
    saveTokens({ access_token: "OLD", refresh_token: "REF", token_type: "bearer" });
    const spy = mockFetchSequence([
      new Response("{}", { status: 401 }),
      new Response("{}", { status: 401 }), // refresh fails
    ]);
    const res = await fetchWithAuth("/api/foo");
    expect(res.status).toBe(401);
    expect(spy).toHaveBeenCalledTimes(2);
    // Refresh failure clears tokens so the app can route back to /login.
    expect(window.localStorage.getItem("beidou.access_token")).toBeNull();
  });

  it("does not attempt refresh when no tokens are stored", async () => {
    clearTokens();
    const spy = mockFetchSequence([new Response("{}", { status: 401 })]);
    const res = await fetchWithAuth("/api/foo");
    expect(res.status).toBe(401);
    expect(spy).toHaveBeenCalledTimes(1);
  });
});
