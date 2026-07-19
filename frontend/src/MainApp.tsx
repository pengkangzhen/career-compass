import { useCallback, useEffect, useState } from "react";
import {
  api,
  canOpenStep,
  JOURNEY_STEPS,
  STEP_TOOLBAR,
  stepTitle,
  type AppData,
  type CoreStepId,
} from "./api/types";
import { ChatPanel, resetChat } from "./components/ChatPanel";
import { JourneyNav } from "./components/JourneyBar";
import {
  JobsViewPanel,
  MatrixViewPanel,
  ProfileViewPanel,
  TrendsViewPanel,
} from "./components/ViewPanels";
import { UserMenu } from "./auth/UserMenu";

export function MainApp() {
  const [data, setData] = useState<AppData | null>(null);
  const [step, setStep] = useState<CoreStepId>("know_self");
  const [subView, setSubView] = useState("chat");
  const [toast, setToast] = useState("");
  const [chatKey, setChatKey] = useState(0);
  const [loadError, setLoadError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const d = await api.loadAll();
      setData(d);
      setLoadError(null);
      return d;
    } catch (err) {
      // SaaS 迁移期：/api/load_all 在新后端尚未实现 (M2 范围)
      // 旧桌面 server 已停用，登录后这里会 404 —— 别让组件白屏。
      const msg =
        err instanceof Error ? err.message : "未知错误";
      setLoadError(
        `数据层加载失败：${msg}。SaaS 化迁移中 (M2 里程碑会实现此接口)。`,
      );
      throw err;
    }
  }, []);

  const refreshView = useCallback(async () => {
    try {
      await refresh();
    } catch {
      // 错误已写入 loadError 状态，refreshView 不能再向上抛
    }
  }, [refresh]);

  useEffect(() => {
    refresh().catch(() => {
      // 已写入 loadError；不能再向上抛，否则会白屏
    });
  }, [refresh]);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(""), 4000);
  };

  const selectStep = (id: CoreStepId) => {
    if (!data) return;
    const access = canOpenStep(data.journey, id);
    if (!access.ok) {
      showToast(access.reason ?? "暂不可进入");
      return;
    }
    setStep(id);
    const meta = JOURNEY_STEPS.find((s) => s.id === id);
    if (meta?.sub?.length) setSubView(meta.sub[0].id);
  };

  const runCmd = async (cmd: string) => {
    if (cmd === "refresh") {
      await refresh();
      setChatKey((k) => k + 1);
      return;
    }
    if (cmd === "chat-reset") {
      await resetChat(async () => {
        await refresh();
      });
      setChatKey((k) => k + 1);
      showToast("对话已重置");
      return;
    }
    const res = await api.runCommand(cmd);
    const msg = res.output?.trim() || `career-compass ${cmd} (exit ${res.code})`;
    showToast(res.code === 0 ? msg.split("\n").pop() || msg : msg);
    await refresh();
    if (cmd === "validate") {
      setStep("know_self");
      setSubView("profile");
    }
    if (cmd === "render-opportunities") setStep("decide");
    if (cmd === "job-analyze") {
      setStep("explore");
      setSubView("jobs");
    }
  };

  if (loadError && !data) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
        <p className="text-lg font-semibold text-[var(--color-warn)]">
          数据层暂未就绪
        </p>
        <p className="max-w-md text-sm text-[var(--color-muted)]">
          {loadError}
        </p>
        <p className="max-w-md text-xs text-[var(--color-muted)]">
          登录 / 注册功能已跑通 (M1)。岗位、矩阵、画像等数据接口在
          M2/M3 里程碑会迁移到数据库。当前如果你想体验完整功能，
          可以用单机桌面模式启动：<code>uv run career-compass-app --web --port 8765</code>
        </p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex h-full items-center justify-center text-[var(--color-muted)]">
        加载北斗星…
      </div>
    );
  }

  const stepMeta = JOURNEY_STEPS.find((s) => s.id === step);
  const currentStepTitle = stepTitle(data.journey.steps, step);

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center gap-3 border-b border-[var(--color-border)] bg-[var(--color-surface)]/90 px-5 py-3 backdrop-blur">
        <span className="text-lg font-bold tracking-tight">
          北斗星
          <span className="ml-2 text-sm font-normal text-[var(--color-accent-2)]">Beidou</span>
        </span>
        <p className="hidden text-xs text-[var(--color-muted)] sm:block">{currentStepTitle}</p>
        <p className="ml-auto hidden max-w-[30%] truncate font-mono text-[10px] text-[var(--color-muted)] sm:block">
          {data.data_dir}
        </p>
        <div className="ml-auto sm:ml-2">
          <UserMenu />
        </div>
      </header>

      <JourneyNav
        journey={data.journey}
        activeStep={step}
        onSelect={selectStep}
        canOpen={(id) => canOpenStep(data.journey, id)}
      />

      {stepMeta?.sub && (
        <div className="flex gap-1 border-b border-[var(--color-border)] bg-[var(--color-surface)]/50 px-4 py-2">
          {stepMeta.sub.map((sub) => (
            <button
              key={sub.id}
              type="button"
              onClick={() => setSubView(sub.id)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
                subView === sub.id
                  ? "bg-[var(--color-accent)]/20 text-[var(--color-accent)]"
                  : "text-[var(--color-muted)] hover:text-[var(--color-text)]"
              }`}
            >
              {sub.label}
            </button>
          ))}
        </div>
      )}

      <div className="flex gap-2 border-b border-[var(--color-border)] bg-[var(--color-surface)]/60 px-4 py-2">
        {(STEP_TOOLBAR[step] ?? []).map((item) => (
          <button
            key={item.cmd}
            type="button"
            onClick={() => runCmd(item.cmd)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
              item.secondary
                ? "border border-[var(--color-border)] bg-transparent text-[var(--color-text)]"
                : "bg-[var(--color-accent)] text-white"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      <main className="min-h-0 flex-1 overflow-auto p-4 md:p-6">
        <div className="mx-auto max-w-6xl rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/60 p-4 md:p-6 backdrop-blur-sm">
          {step === "know_self" && subView === "chat" && (
            <ChatPanel
              key={chatKey}
              onRefresh={refresh}
              onIntakeComplete={() => setSubView("profile")}
            />
          )}
          {step === "know_self" && subView === "profile" && (
            <ProfileViewPanel data={data.views.profile} />
          )}
          {step === "explore" && subView === "trends" && (
            <TrendsViewPanel data={data.views.trends} />
          )}
          {step === "explore" && subView === "jobs" && (
            <JobsViewPanel data={data.views.jobs} onRefresh={refreshView} />
          )}
          {step === "decide" && (
            <MatrixViewPanel data={data.views.matrix} onRefresh={refreshView} />
          )}
        </div>
      </main>

      {toast && (
        <div className="fixed bottom-4 right-4 max-w-sm rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-2)] px-4 py-3 text-sm shadow-xl">
          {toast}
        </div>
      )}
    </div>
  );
}
