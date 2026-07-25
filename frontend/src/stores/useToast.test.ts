import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useToast } from "./useToast";

describe("useToast", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("starts with null toast", () => {
    const { result } = renderHook(() => useToast());
    expect(result.current.toast).toBeNull();
  });

  it("shows toast immediately on show()", () => {
    const { result } = renderHook(() => useToast());
    act(() => result.current.show("hello"));
    expect(result.current.toast).toBe("hello");
  });

  it("auto-dismisses after duration", () => {
    const { result } = renderHook(() => useToast(1000));
    act(() => result.current.show("hi"));
    expect(result.current.toast).toBe("hi");
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(result.current.toast).toBeNull();
  });

  it("dismiss() clears immediately", () => {
    const { result } = renderHook(() => useToast());
    act(() => result.current.show("hi"));
    act(() => result.current.dismiss());
    expect(result.current.toast).toBeNull();
  });

  it("second show() before first expires resets the timer", () => {
    const { result } = renderHook(() => useToast(1000));
    act(() => result.current.show("first"));
    act(() => vi.advanceTimersByTime(500));
    act(() => result.current.show("second"));
    // 600ms after the FIRST show (100ms after second) — first timer was cleared.
    act(() => vi.advanceTimersByTime(600));
    expect(result.current.toast).toBe("second");
    // 400ms more — total 1000ms after second show.
    act(() => vi.advanceTimersByTime(400));
    expect(result.current.toast).toBeNull();
  });
});
