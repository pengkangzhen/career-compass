import type { ButtonHTMLAttributes, ReactNode } from "react";

// Design tokens — kept in JS so variant logic lives next to the component.
// The CSS variables (--color-*, etc.) are defined in src/index.css @theme.
export type ButtonVariant =
  | "primary"
  | "secondary"
  | "ghost"
  | "danger"
  | "subtle";
export type ButtonSize = "sm" | "md";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  // When set, renders the button at full width (used by auth forms).
  block?: boolean;
  // Optional leading icon node — rendered before the label, sized to match.
  leading?: ReactNode;
};

const VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary:
    "bg-[var(--color-accent)] text-white hover:opacity-90 disabled:opacity-50",
  secondary:
    "border border-[var(--color-border)] bg-transparent text-[var(--color-text)] hover:border-[var(--color-accent)] hover:text-[var(--color-accent)] disabled:opacity-50",
  ghost:
    "text-[var(--color-muted)] hover:text-[var(--color-text)] disabled:opacity-50",
  danger:
    "border border-[var(--color-border)] text-[var(--color-muted)] hover:border-[var(--color-warn)] hover:text-[var(--color-warn)] disabled:opacity-50",
  subtle:
    "bg-[var(--color-accent)]/10 text-[var(--color-accent)] hover:bg-[var(--color-accent)]/18 disabled:opacity-50",
};

const SIZE_CLASS: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-4 py-2.5 text-sm",
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  block = false,
  leading,
  className = "",
  children,
  disabled,
  ...rest
}: Props) {
  const cls = [
    "inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-colors",
    "active:scale-[0.98]",
    VARIANT_CLASS[variant],
    SIZE_CLASS[size],
    block ? "w-full" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <button
      type="button"
      // Loading implies disabled: prevent clicks while a request is in flight
      // even if the caller forgot to pass `disabled`.
      disabled={disabled || loading}
      className={cls}
      {...rest}
    >
      {leading}
      {children}
    </button>
  );
}
