import type { ReactNode } from "react";

type Tone = "ok" | "warn" | "hint";

type Props = {
  tone: Tone;
  title?: ReactNode;
  children: ReactNode;
  // Override the default vertical margin (e.g. mb-4) — useful when stacking
  // inside a flex column.
  className?: string;
};

const TONE_CLASS: Record<Tone, string> = {
  ok: "border-[var(--color-ok)]/30 bg-[var(--color-ok)]/10 text-[var(--color-ok)]",
  warn: "border-[var(--color-warn)]/30 bg-[var(--color-warn)]/10",
  hint: "border-[var(--color-accent)]/30 bg-[var(--color-accent)]/10",
};

export function Alert({ tone, title, children, className = "mt-3" }: Props) {
  const cls = [
    "rounded-xl border p-3 text-sm",
    TONE_CLASS[tone],
    className,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={cls}>
      {title && <strong className="mb-1 block">{title}</strong>}
      {children}
    </div>
  );
}
