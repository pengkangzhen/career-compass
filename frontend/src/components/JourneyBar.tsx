import type { Journey, CoreStepId } from "../api/types";

/** 核心三步 — GUI 主导航 */
export const CORE_STEP_IDS: CoreStepId[] = ["know_self", "explore", "decide"];

type Props = {
  journey: Journey;
  activeStep: CoreStepId;
  onSelect: (step: CoreStepId) => void;
  canOpen: (step: CoreStepId) => { ok: boolean; hint?: string };
};

export function JourneyNav({ journey, activeStep, onSelect, canOpen }: Props) {
  const coreSteps = journey.steps.filter((s) =>
    CORE_STEP_IDS.includes(s.id as CoreStepId),
  );

  return (
    <nav
      aria-label="主导航"
      className="border-b border-[var(--color-border)] bg-[var(--color-surface)]/80 px-3 py-3 backdrop-blur md:px-6"
    >
      <ol className="flex items-center gap-1 overflow-x-auto md:gap-2">
        {coreSteps.map((step, i) => {
          const id = step.id as CoreStepId;
          const access = canOpen(id);
          const isActive = activeStep === id;
          const isLast = i === coreSteps.length - 1;
          const cls = [
            "group relative flex min-w-[88px] flex-1 items-center gap-2 rounded-lg px-2 py-1.5 text-left transition-colors md:min-w-[120px] cursor-pointer hover:bg-white/5",
            isActive ? "bg-[var(--color-accent)]/10" : "",
          ]
            .filter(Boolean)
            .join(" ");

          const numCls = [
            "flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full text-xs font-semibold transition-colors",
            step.done
              ? "bg-[var(--color-ok)]/20 text-[var(--color-ok)]"
              : isActive
                ? "!bg-[var(--color-accent)] !text-white"
                : "bg-[var(--color-border)] text-[var(--color-muted)]",
          ]
            .filter(Boolean)
            .join(" ");

          return (
            <li key={step.id} className="flex flex-1 items-center gap-1 md:gap-2">
              <button
                type="button"
                className={cls}
                title={access.hint ?? step.subtitle}
                onClick={() => onSelect(id)}
              >
                <span className={numCls}>{step.done ? "✓" : i + 1}</span>
                <span className="min-w-0">
                  <span
                    className={`block whitespace-nowrap text-xs font-medium leading-tight ${
                      step.done
                        ? "text-[var(--color-ok)]"
                        : isActive
                          ? "text-[var(--color-text)]"
                          : "text-[var(--color-muted)]"
                    }`}
                  >
                    {step.title}
                  </span>
                </span>
              </button>
              {/* Connector line — hidden on the last step and on narrow viewports. */}
              {!isLast && (
                <span
                  aria-hidden="true"
                  className="hidden h-px flex-shrink-0 flex-1 bg-gradient-to-r from-[var(--color-border)] to-transparent md:block"
                />
              )}
            </li>
          );
        })}
      </ol>
      <p
        className={`mt-2 px-1 text-xs ${
          journey.core_complete
            ? "text-[var(--color-ok)]"
            : "text-[var(--color-muted)]"
        }`}
      >
        {journey.next_hint}
      </p>
    </nav>
  );
}
