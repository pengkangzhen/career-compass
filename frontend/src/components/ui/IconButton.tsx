import type { ButtonHTMLAttributes, ReactNode } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  // Visual style — most icon buttons use ghost/danger semantics.
  tone?: "ghost" | "accent" | "danger" | "ok";
  // Tooltip text — also used as aria-label fallback.
  title: string;
  // The icon glyph. Typically an emoji or small SVG, sized via CSS.
  children: ReactNode;
};

const TONE_CLASS = {
  ghost:
    "border border-[var(--color-border)] text-[var(--color-muted)] hover:text-[var(--color-text)]",
  accent:
    "border border-[var(--color-border)] text-[var(--color-muted)] hover:border-[var(--color-accent)] hover:text-[var(--color-accent)]",
  danger:
    "border border-[var(--color-border)] text-[var(--color-muted)] hover:border-[var(--color-warn)] hover:text-[var(--color-warn)]",
  ok:
    "border border-[var(--color-border)] text-[var(--color-muted)] hover:border-[var(--color-ok)] hover:text-[var(--color-ok)]",
};

export function IconButton({
  tone = "accent",
  title,
  children,
  className = "",
  ...rest
}: Props) {
  const cls = [
    "inline-flex items-center justify-center rounded-md px-2 py-0.5 text-xs transition-colors",
    "disabled:opacity-50 disabled:cursor-not-allowed",
    TONE_CLASS[tone],
    className,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <button type="button" title={title} aria-label={title} className={cls} {...rest}>
      {children}
    </button>
  );
}
