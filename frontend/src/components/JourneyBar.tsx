import type { Journey, CoreStepId } from "../api/types";

/** 核心三步 — GUI 主导航 */
export const CORE_STEP_IDS: CoreStepId[] = ["know_self", "explore", "decide"];

type Props = {
  journey: Journey;
  activeStep: CoreStepId;
  onSelect: (step: CoreStepId) => void;
  canOpen: (step: CoreStepId) => { ok: boolean; reason?: string };
};

export function JourneyNav({ journey, activeStep, onSelect, canOpen }: Props) {
  const coreDone = journey.core_complete;
  const coreSteps = journey.steps.filter((s) => CORE_STEP_IDS.includes(s.id as CoreStepId));

  return (
    <div className="border-b border-[var(--color-border)] bg-[var(--color-surface)]/80 px-3 py-3 backdrop-blur md:px-4">
      <div className="flex items-center gap-1 overflow-x-auto md:gap-2">
        {coreSteps.map((step, i) => {
          const id = step.id as CoreStepId;
          const access = canOpen(id);
          const isActive = activeStep === id;
          const cls = [
            "flex min-w-[88px] flex-1 flex-col items-center gap-1 rounded-lg px-1 py-2 text-center transition-colors md:min-w-[100px]",
            step.done ? "text-[var(--color-ok)]" : "text-[var(--color-muted)]",
            isActive ? "bg-[var(--color-accent)]/15 ring-1 ring-[var(--color-accent)]/40" : "",
            !access.ok ? "opacity-45" : "hover:bg-white/5 cursor-pointer",
          ]
            .filter(Boolean)
            .join(" ");

          const numCls = [
            "flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold",
            step.done
              ? "bg-[var(--color-ok)]/20 text-[var(--color-ok)]"
              : "bg-[var(--color-border)] text-[var(--color-muted)]",
            isActive ? "!bg-[var(--color-accent)] !text-white" : "",
          ]
            .filter(Boolean)
            .join(" ");

          return (
            <button
              key={step.id}
              type="button"
              className={cls}
              title={!access.ok ? access.reason : step.subtitle}
              onClick={() => onSelect(id)}
            >
              <span className={numCls}>{i + 1}</span>
              <span className="whitespace-nowrap text-xs font-medium leading-tight">{step.title}</span>
            </button>
          );
        })}
        {coreDone && (
          <span className="ml-1 shrink-0 rounded-full bg-[var(--color-ok)]/15 px-2 py-1 text-[10px] font-semibold text-[var(--color-ok)] md:px-3 md:text-xs">
            ✓ 矩阵就绪
          </span>
        )}
      </div>
      <p
        className={`mt-2 px-1 text-xs ${coreDone ? "text-[var(--color-ok)]" : "text-[var(--color-muted)]"}`}
      >
        {journey.next_hint}
      </p>
    </div>
  );
}
