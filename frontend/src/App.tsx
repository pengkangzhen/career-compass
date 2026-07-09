import { useCallback, useEffect, useState } from "react";
import {
  api,
  canOpenStep,
  CORE_STEP_IDS,
  JOURNEY_STEPS,
  STEP_TOOLBAR,
  stepTitle,
  type AppData,
  type CoreStepId,
} from "./api/types";
import { ChatPanel, resetChat } from "./components/ChatPanel";
import { JourneyNav } from "./components/JourneyBar";
import { OptionalCliPanel } from "./components/OptionalCliPanel";
import {
  JobsViewPanel,
  MatrixViewPanel,
  ProfileViewPanel,
  TrendsViewPanel,
} from "./components/ViewPanels";

export default function App() {
  const [data, setData] = useState<AppData | null>(null);
  const [step, setStep] = useState<CoreStepId>("know_self");
  const [subView, setSubView] = useState("chat");
  const [toast, setToast] = useState("");
  const [chatKey, setChatKey] = useState(0);
  const [cliExpanded, setCliExpanded] = useState(false);

  const refresh = useCallback(async () => {
    const d = await api.loadAll();
    setData(d);
    return d;
  }, []);

  useEffect(() => {
    refresh().then((d) => {
      const current = d.journey.current as CoreStepId;
      setStep(CORE_STEP_IDS.includes(current) ? current : "decide");
      if (d.intake_complete) setSubView("profile");
      if (d.journey.core_complete) setCliExpanded(true);
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
        <p className="ml-auto max-w-[40%] truncate font-mono text-[10px] text-[var(--color-muted)]">
          {data.data_dir}
        </p>
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
        <div className="mx-auto h-full max-w-6xl rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/60 p-4 md:p-6 backdrop-blur-sm">
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
            <JobsViewPanel data={data.views.jobs} />
          )}
          {step === "decide" && <MatrixViewPanel data={data.views.matrix} />}
        </div>
      </main>

      {data.journey.core_complete && (
        <OptionalCliPanel expanded={cliExpanded} onToggle={() => setCliExpanded((v) => !v)} />
      )}

      {toast && (
        <div className="fixed bottom-4 right-4 max-w-sm rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-2)] px-4 py-3 text-sm shadow-xl">
          {toast}
        </div>
      )}
    </div>
  );
}
