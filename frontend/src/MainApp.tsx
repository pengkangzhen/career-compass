import { useCallback, useState } from "react";
import {
  canOpenStep,
  JOURNEY_STEPS,
  stepTitle,
  type AppData,
  type CoreStepId,
} from "./api/types";
import { ChatPanel, ProfileView } from "./features/know_self";
import { JourneyNav } from "./components/JourneyBar";
import { JobsView, TrendsView } from "./features/explore";
import { MatrixView } from "./features/decide";
import { PageShell, SegmentedControl, type PageAction } from "./components/layout/PageShell";
import { UserMenu } from "./auth/UserMenu";
import { useAppData } from "./stores/useAppData";
import { useToast } from "./stores/useToast";

// Sub-view keys per step. The union is open (string) because individual views
// define their own keys; this just documents the well-known ones.
type SubView = string;

const STEP_EYEBROW: Record<CoreStepId, string> = {
  know_self: "认识自己",
  explore: "探索世界",
  decide: "决策",
};

const STEP_SUB_OPTIONS: Partial<
  Record<CoreStepId, { value: SubView; label: string }[]>
> = {
  know_self: [
    { value: "chat", label: "对话" },
    { value: "profile", label: "完整画像" },
  ],
  explore: [
    { value: "trends", label: "行业信号" },
    { value: "jobs", label: "岗位收藏" },
  ],
};

export function MainApp() {
  const [step, setStep] = useState<CoreStepId>("know_self");
  const [subView, setSubView] = useState<SubView>("chat");
  const [chatKey, setChatKey] = useState(0);
  const { toast, show } = useToast();

  // Route run-command outcomes back into the local step state.
  const onData = useCallback((_d: AppData) => {
    // No-op: kept for future derivation; current step is purely user-driven.
  }, []);

  const { data, loadError, busy, refresh, refreshView, runCmd } = useAppData({
    onData,
    onError: show,
    onRefreshed: () => setChatKey((k) => k + 1),
  });

  const selectStep = useCallback(
    (id: CoreStepId) => {
      if (!data) return;
      const access = canOpenStep(data.journey, id);
      const leavingKnowSelf = step === "know_self" && id !== "know_self";
      setStep(id);
      const meta = JOURNEY_STEPS.find((s) => s.id === id);
      if (meta?.sub?.length) setSubView(meta.sub[0].id);
      if (leavingKnowSelf && access.hint) show(access.hint);
    },
    [data, step, show],
  );

  const handleCmd = useCallback(
    async (cmd: string) => {
      const result = await runCmd(cmd);
      if (!result) return;
      show(result.toast);
      if (result.route) {
        setStep(result.route.step);
        if (result.route.sub) setSubView(result.route.sub);
      }
    },
    [runCmd, show],
  );

  if (loadError && !data) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
        <p className="text-lg font-semibold text-[var(--color-warn)]">
          数据层暂未就绪
        </p>
        <p className="max-w-md text-sm text-[var(--color-muted)]">{loadError}</p>
        <p className="max-w-md text-xs text-[var(--color-muted)]">
          登录 / 注册功能已跑通 (M1)。岗位、矩阵、画像等数据接口在
          M2/M3 里程碑会迁移到数据库。当前如果你想体验完整功能，
          可以用单机桌面模式启动：
          <code className="ml-1">uv run career-compass-app --web --port 8765</code>
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

  const currentStepTitle = stepTitle(data.journey.steps, step);
  const subOptions = STEP_SUB_OPTIONS[step];

  // Build the per-view PageShell configuration.
  const shell = buildShell({
    step,
    subView,
    currentStepTitle,
    busy,
    onCmd: handleCmd,
    onSubChange: setSubView,
    subOptions,
  });

  return (
    <div className="flex h-full flex-col">
      {/* Row 1 — app header (logo + current step + user menu) */}
      <header className="flex items-center gap-3 border-b border-[var(--color-border)] bg-[var(--color-surface)]/90 px-5 py-3 backdrop-blur">
        <span className="text-lg font-bold tracking-tight">
          北斗星
          <span className="ml-2 text-sm font-normal text-[var(--color-accent-2)]">
            Beidou
          </span>
        </span>
        <p className="hidden text-xs text-[var(--color-muted)] sm:block">
          {currentStepTitle}
        </p>
        <p className="ml-auto hidden max-w-[30%] truncate font-mono text-[10px] text-[var(--color-muted)] sm:block">
          {data.data_dir}
        </p>
        <div className="ml-auto sm:ml-2">
          <UserMenu />
        </div>
      </header>

      {/* Row 2 — three-step journey navigation */}
      <JourneyNav
        journey={data.journey}
        activeStep={step}
        onSelect={selectStep}
        canOpen={(id) => canOpenStep(data.journey, id)}
      />

      {/* Soft warning when exploring/deciding before know_self is done */}
      {step !== "know_self" && !data.journey.know_self_complete && (
        <div className="border-b border-[var(--color-warn)]/30 bg-[var(--color-warn)]/10 px-4 py-2 text-xs text-[var(--color-warn)] md:px-6">
          「认识自己」尚未完成，当前探索/决策可能不够准。
          <button
            type="button"
            className="ml-2 underline hover:no-underline"
            onClick={() => {
              setStep("know_self");
              setSubView("chat");
            }}
          >
            回去补全
          </button>
        </div>
      )}

      {/* Page body — title + actions in one row, content below */}
      <div className="min-h-0 flex-1">
        <PageShell
          title={shell.title}
          eyebrow={shell.eyebrow}
          subtitle={shell.subtitle}
          actions={shell.actions}
          leading={shell.leading}
        >
          <div className="mx-auto max-w-6xl">
            {step === "know_self" && subView === "chat" && (
              <ChatPanel
                key={chatKey}
                onRefresh={refresh}
                onIntakeComplete={() => setSubView("profile")}
              />
            )}
            {step === "know_self" && subView === "profile" && (
              <ProfileView data={data.views.profile} />
            )}
            {step === "explore" && subView === "trends" && (
              <TrendsView data={data.views.trends} />
            )}
            {step === "explore" && subView === "jobs" && (
              <JobsView data={data.views.jobs} onRefresh={refreshView} />
            )}
            {step === "decide" && (
              <MatrixView data={data.views.matrix} onRefresh={refreshView} />
            )}
          </div>
        </PageShell>
      </div>

      {toast && (
        <div className="fixed bottom-4 right-4 max-w-sm rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-2)] px-4 py-3 text-sm shadow-xl">
          {toast}
        </div>
      )}
    </div>
  );
}

// ---- Per-view shell configuration ------------------------------------------

type ShellConfig = {
  title: string;
  eyebrow: string;
  subtitle?: string;
  actions?: PageAction[];
  leading?: React.ReactNode;
};

function buildShell(args: {
  step: CoreStepId;
  subView: SubView;
  currentStepTitle: string;
  busy: boolean;
  onCmd: (cmd: string) => void;
  onSubChange: (v: SubView) => void;
  subOptions?: { value: SubView; label: string }[];
}): ShellConfig {
  const { step, subView, busy, onCmd, onSubChange, subOptions } = args;
  const eyebrow = STEP_EYEBROW[step];

  // Segmented control for steps with multiple sub-views.
  const leading =
    subOptions && subOptions.length > 0 ? (
      <SegmentedControl
        value={subView}
        options={subOptions}
        onChange={onSubChange}
        ariaLabel="子视图切换"
      />
    ) : undefined;

  // Per-view actions + titles.
  if (step === "know_self") {
    if (subView === "chat") {
      return {
        title: "对话",
        eyebrow,
        subtitle: "聊聊你的背景、困惑或目标，北斗星会逐步构建画像。",
        leading,
        actions: [
          { key: "reset", label: "重置对话", onClick: () => onCmd("chat-reset") },
          {
            key: "refresh",
            label: "刷新",
            onClick: () => onCmd("refresh"),
          },
        ],
      };
    }
    return {
      title: "完整画像",
      eyebrow,
      subtitle: "校验通过即可解锁「探索世界」与「决策」。",
      leading,
      actions: [
        {
          key: "validate",
          label: "校验画像",
          variant: "primary",
          onClick: () => onCmd("validate"),
        },
        { key: "refresh", label: "刷新", onClick: () => onCmd("refresh") },
      ],
    };
  }
  if (step === "explore") {
    if (subView === "trends") {
      return {
        title: "行业信号",
        eyebrow,
        subtitle: "外部趋势扫描结果，按领域分组。",
        leading,
        actions: [{ key: "refresh", label: "刷新", onClick: () => onCmd("refresh") }],
      };
    }
    return {
      title: "岗位收藏",
      eyebrow,
      subtitle: "保存心仪 JD，可与机会矩阵方向关联。",
      leading,
      actions: [
        {
          key: "analyze",
          label: "分析收藏",
          variant: "primary",
          onClick: () => onCmd("job-analyze"),
        },
        { key: "refresh", label: "刷新", onClick: () => onCmd("refresh") },
      ],
    };
  }
  // decide
  return {
    title: "机会矩阵",
    eyebrow,
    subtitle: "多维度并列展示候选方向 — 你来挑，北斗星不替你选。",
    actions: [
      {
        key: "render",
        label: busy ? "生成中…" : "生成矩阵",
        variant: "primary",
        disabled: busy,
        onClick: () => onCmd("render-opportunities"),
      },
      { key: "refresh", label: "刷新", onClick: () => onCmd("refresh") },
    ],
  };
}
