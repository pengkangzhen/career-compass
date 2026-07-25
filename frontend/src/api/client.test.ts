import { describe, expect, it, vi, beforeEach } from "vitest";
import { api, ApiError } from "./client";
import { saveTokens } from "../auth/tokens";

type FetchSpy = ReturnType<typeof vi.fn<typeof fetch>>;
function mockFetchSequence(responses: Response[]): FetchSpy {
  const spy = vi.fn(async (..._args: Parameters<typeof fetch>) =>
    responses.shift() ?? new Response("{}", { status: 599 }),
  ) as FetchSpy;
  vi.stubGlobal("fetch", spy);
  return spy;
}

describe("api client error mapping", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.unstubAllGlobals();
  });

  it("getJson surfaces server {code, detail} as ApiError with code+detail", async () => {
    saveTokens({ access_token: "ACC", refresh_token: "REF", token_type: "bearer" });
    mockFetchSequence([
      new Response(JSON.stringify({ code: "EMAIL_ALREADY_REGISTERED", detail: { field: "email" } }), {
        status: 409,
        headers: { "Content-Type": "application/json" },
      }),
    ]);
    await expect(api.health()).rejects.toMatchObject({
      status: 409,
      code: "EMAIL_ALREADY_REGISTERED",
    });
  });

  it("getJson surfaces server {message} as ApiError.message when no code", async () => {
    saveTokens({ access_token: "ACC", refresh_token: "REF", token_type: "bearer" });
    mockFetchSequence([
      new Response(JSON.stringify({ message: "boom" }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }),
    ]);
    await expect(api.health()).rejects.toSatisfy((err: unknown) => {
      return err instanceof ApiError && err.status === 500 && err.message === "boom";
    });
  });

  it("getJson falls back to 'HTTP <status>' when body is not JSON", async () => {
    saveTokens({ access_token: "ACC", refresh_token: "REF", token_type: "bearer" });
    mockFetchSequence([
      new Response("Internal Server Error", { status: 500 }),
    ]);
    await expect(api.health()).rejects.toSatisfy((err: unknown) => {
      return err instanceof ApiError && err.status === 500 && err.message === "HTTP 500";
    });
  });

  it("post throws a plain Error on non-2xx (does not wrap as ApiError)", async () => {
    saveTokens({ access_token: "ACC", refresh_token: "REF", token_type: "bearer" });
    mockFetchSequence([new Response("{}", { status: 422 })]);
    await expect(api.chatReset()).rejects.toThrow("HTTP 422");
    await expect(api.chatReset()).rejects.not.toBeInstanceOf(ApiError);
  });
});

describe("api client URL composition", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts to /api/<endpoint> path (proxy in dev)", async () => {
    saveTokens({ access_token: "ACC", refresh_token: "REF", token_type: "bearer" });
    const spy = mockFetchSequence([
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    ]);
    await api.chatReset();
    expect(spy.mock.calls[0]![0]).toBe("/api/chat_reset");
  });
});
