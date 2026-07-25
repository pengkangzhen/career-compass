import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { resetChat } from "../features/know_self/ChatPanel";
import type { AppData, CoreStepId } from "../api/types";

export type RunCommandResult = {
  // Toast message summarising the outcome (already user-friendly).
  toast: string;
  // Optional navigation hint — caller can route to a specific step after run.
  route?: { step: CoreStepId; sub?: string };
};

type Options = {
  // Called after every successful refresh with the latest data, so callers
  // can sync derived state (current step, completion flags, etc.).
  onData?: (d: AppData) => void;
  // Toast shower — if provided, errors get surfaced here instead of throwing.
  onError?: (msg: string) => void;
  // Called after a refresh tick completes (e.g. to bump a chat remount key).
  onRefreshed?: () => void;
};

// Single source of truth for the loaded AppData + the side-effecting commands
// that mutate it (run CLI command, reset chat, manual refresh). Pulled out of
// MainApp so the component stops being a grab-bag of useState + useCallback.
export function useAppData(opts: Options = {}) {
  const { onData, onError, onRefreshed } = opts;
  const [data, setData] = useState<AppData | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const d = await api.loadAll();
      setData(d);
      setLoadError(null);
      onData?.(d);
      return d;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "未知错误";
      setLoadError(
        `数据层加载失败：${msg}。SaaS 化迁移中 (M2 里程碑会实现此接口)。`,
      );
      onError?.(`数据加载失败：${msg}`);
      throw err;
    }
  }, [onData, onError]);

  // Soft refresh: same as refresh but never rethrows — used by panels that
  // don't want a render-time error to crash them.
  const refreshView = useCallback(async () => {
    try {
      await refresh();
      onRefreshed?.();
    } catch {
      // swallow — refresh() already wrote to loadError
    }
  }, [refresh, onRefreshed]);

  // Initial load on mount.
  const [booted, setBooted] = useState(false);
  useEffect(() => {
    if (booted) return;
    setBooted(true);
    refresh().catch(() => {
      // already in loadError state
    });
  }, [booted, refresh]);

  const runCmd = useCallback(
    async (cmd: string): Promise<RunCommandResult | null> => {
      if (cmd === "refresh") {
        await refreshView();
        return { toast: "已刷新" };
      }
      if (cmd === "chat-reset") {
        await resetChat(async () => {
          await refresh();
        });
        onRefreshed?.();
        return { toast: "对话已重置" };
      }
      setBusy(true);
      try {
        const res = await api.runCommand(cmd);
        const outMsg = res.output?.trim() || `career-compass ${cmd} (exit ${res.code})`;
        const toast =
          res.code === 0 ? outMsg.split("\n").pop() || outMsg : outMsg;
        await refresh();
        const route: RunCommandResult["route"] = cmd === "validate"
          ? { step: "know_self", sub: "profile" }
          : cmd === "render-opportunities"
            ? { step: "decide" }
            : cmd === "job-analyze"
              ? { step: "explore", sub: "jobs" }
              : undefined;
        return { toast, route };
      } catch (err) {
        const msg = err instanceof Error ? err.message : "命令执行失败";
        onError?.(msg);
        return { toast: msg };
      } finally {
        setBusy(false);
      }
    },
    [refresh, refreshView, onError, onRefreshed],
  );

  return { data, loadError, busy, refresh, refreshView, runCmd };
}
