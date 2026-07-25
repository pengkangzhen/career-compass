import type { HTMLAttributes, ReactNode } from "react";

type Props = HTMLAttributes<HTMLDivElement> & {
  // Subtle hover lift; off by default to keep lists calm.
  interactive?: boolean;
  // Padding scale — md is the default and matches the old `p-4`.
  pad?: "sm" | "md" | "lg";
  children?: ReactNode;
};

const PAD_CLASS = {
  sm: "p-3",
  md: "p-4",
  lg: "p-5 md:p-6",
};

export function Card({
  interactive = false,
  pad = "md",
  className = "",
  children,
  ...rest
}: Props) {
  const cls = [
    "rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)]",
    PAD_CLASS[pad],
    interactive
      ? "transition-colors hover:border-[var(--color-accent)]/40"
      : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}
