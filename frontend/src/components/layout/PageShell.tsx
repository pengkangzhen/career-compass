import type { ReactNode } from "react";

export type PageAction = {
  // Stable key for React reconciliation.
  key: string;
  // Visible button label.
  label: ReactNode;
  onClick: () => void;
  // "primary" highlights the main action; others use secondary styling.
  variant?: "primary" | "secondary";
  disabled?: boolean;
  loading?: boolean;
};

type Props = {
  // Page heading — e.g. "对话" or "岗位收藏".
  title: ReactNode;
  // Optional context above the title — typically "认识自己 ›" breadcrumb.
  eyebrow?: ReactNode;
  // Optional one-line description rendered under the title.
  subtitle?: ReactNode;
  // Right-aligned action buttons. Empty array → actions column hidden.
  actions?: PageAction[];
  // Optional inline content rendered on the same row as actions (e.g. segmented control).
  leading?: ReactNode;
  children?: ReactNode;
};

export function PageShell({
  title,
  eyebrow,
  subtitle,
  actions,
  leading,
  children,
}: Props) {
  const hasActions = actions && actions.length > 0;
  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Page header — single row with title left, actions right */}
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--color-border)] px-4 py-3 md:px-6">
        <div className="min-w-0">
          {eyebrow && (
            <p className="mb-0.5 text-[11px] uppercase tracking-wider text-[var(--color-muted)]">
              {eyebrow}
            </p>
          )}
          <h2 className="text-lg font-semibold leading-tight">{title}</h2>
          {subtitle && (
            <p className="mt-1 text-xs text-[var(--color-muted)]">{subtitle}</p>
          )}
        </div>
        {(leading || hasActions) && (
          <div className="flex flex-shrink-0 flex-wrap items-center gap-2">
            {leading}
            {hasActions &&
              actions!.map((a) => (
                <button
                  key={a.key}
                  type="button"
                  disabled={a.disabled || a.loading}
                  onClick={a.onClick}
                  className={
                    a.variant === "primary"
                      ? "rounded-lg bg-[var(--color-accent)] px-3 py-1.5 text-xs font-medium text-white shadow-[var(--shadow-card)] transition hover:bg-[var(--color-accent-soft)] active:scale-[0.98] disabled:opacity-50"
                      : "rounded-lg border border-[var(--color-border)] bg-transparent px-3 py-1.5 text-xs font-medium text-[var(--color-text)] transition hover:border-[var(--color-accent)] hover:text-[var(--color-accent)] active:scale-[0.98] disabled:opacity-50"
                  }
                >
                  {a.loading ? "…" : a.label}
                </button>
              ))}
          </div>
        )}
      </div>

      {/* Page body */}
      <div className="min-h-0 flex-1 overflow-auto p-4 md:p-6">{children}</div>
    </div>
  );
}

// Compact segmented control — used to switch between sub-views (e.g. 对话/完整画像)
// without taking a whole chrome row. Renders inline inside PageShell.leading.
export function SegmentedControl<T extends string>({
  value,
  options,
  onChange,
  ariaLabel,
}: {
  value: T;
  options: { value: T; label: ReactNode }[];
  onChange: (v: T) => void;
  ariaLabel?: string;
}) {
  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className="inline-flex rounded-lg border border-[var(--color-border)] bg-black/15 p-0.5"
    >
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(opt.value)}
            className={
              "rounded-md px-3 py-1 text-xs font-medium transition " +
              (active
                ? "bg-[var(--color-accent)]/20 text-[var(--color-accent)]"
                : "text-[var(--color-muted)] hover:text-[var(--color-text)]")
            }
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
