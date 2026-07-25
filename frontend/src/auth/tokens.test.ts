import { describe, expect, it, beforeEach } from "vitest";
import { clearTokens, loadTokens, saveTokens } from "../auth/tokens";

describe("auth/tokens localStorage round-trip", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("returns null when nothing is stored", () => {
    expect(loadTokens()).toBeNull();
  });

  it("round-trips access + refresh tokens", () => {
    saveTokens({
      access_token: "acc-123",
      refresh_token: "ref-456",
      token_type: "bearer",
    });
    const loaded = loadTokens();
    expect(loaded).not.toBeNull();
    expect(loaded!.access_token).toBe("acc-123");
    expect(loaded!.refresh_token).toBe("ref-456");
    expect(loaded!.token_type).toBe("bearer");
  });

  it("clearTokens wipes both keys", () => {
    saveTokens({
      access_token: "acc-123",
      refresh_token: "ref-456",
      token_type: "bearer",
    });
    clearTokens();
    expect(loadTokens()).toBeNull();
    expect(window.localStorage.getItem("beidou.access_token")).toBeNull();
    expect(window.localStorage.getItem("beidou.refresh_token")).toBeNull();
  });

  it("returns null if only one of two tokens is present (corrupt state)", () => {
    window.localStorage.setItem("beidou.access_token", "acc-only");
    expect(loadTokens()).toBeNull();
  });
});
