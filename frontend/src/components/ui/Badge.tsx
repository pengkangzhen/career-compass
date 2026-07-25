import type { HTMLAttributes, ReactNode } from "react";

export type BadgeTone = "neutral" | "accent" | "ok" | "warn" | "muted";

type Props = HTMLAttributes<HTMLSpanElement> & {
  tone?: BadgeTone;
  // Smaller padding — used for inline annotations inside dense tables.
  size?: "sm" | "xs";
  children?: ReactNode;
};

const TONE_CLASS: Record<BadgeTone, string> = {
  neutral: "bg-[var(--color-border)] text-[var(--color-muted)]",
  accent: "bg-[var(--color-accent)]/15 text-[var(--color-accent)]",
  ok: "bg-[var(--color-ok)]/15 text-[var(--color-ok)]",
  warn: "bg-[var(--color-warn)]/15 text-[var(--color-warn)]",
  muted: "bg-[var(--color-border)]/60 text-[var(--color-muted)]",
};

const SIZE_CLASS = {
  sm: "px-2.5 py-1 text-xs",
  xs: "px-1.5 py-0.5 text-[10px]",
};

export function Badge({
  tone = "neutral",
  size = "sm",
  className = "",
  children,
  ...rest
}: Props) {
  const cls = [
    "inline-flex items-center rounded-lg font-medium",
    TONE_CLASS[tone],
    SIZE_CLASS[size],
    className,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <span className={cls} {...rest}>
      {children}
    </span>
  );
}

export function TagList({
  items,
  tone = "accent",
  muted,
}: {
  items: string[];
  tone?: BadgeTone;
  // Legacy alias kept for parity with the old ViewPanels TagList which had a
  // single `muted` boolean. New code should pass `tone` directly.
  muted?: boolean;
}) {
  const resolved = muted ? "muted" : tone;
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <Badge key={item} tone={resolved}>
          {item}
        </Badge>
      ))}
    </div>
  );
}
