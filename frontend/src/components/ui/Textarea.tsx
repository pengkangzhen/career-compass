import type { TextareaHTMLAttributes, ReactNode } from "react";

type Props = Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "size"> & {
  label?: ReactNode;
  error?: string;
  hint?: ReactNode;
  // Right-aligned accessory shown next to the label (e.g. character count).
  labelAccessory?: ReactNode;
};

export function Textarea({
  label,
  error,
  hint,
  labelAccessory,
  className = "",
  id,
  ...rest
}: Props) {
  const fieldCls = [
    "w-full rounded-md border bg-[var(--color-surface)] px-3 py-2 text-sm outline-none transition",
    "focus:border-[var(--color-accent)] disabled:opacity-60",
    error ? "border-[var(--color-warn)]" : "border-[var(--color-border)]",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <label className="block" htmlFor={id}>
      {(label || labelAccessory) && (
        <span className="mb-1 flex items-center justify-between gap-2 text-xs font-medium text-[var(--color-muted)]">
          <span>{label}</span>
          {labelAccessory}
        </span>
      )}
      <textarea id={id} className={fieldCls} {...rest} />
      {error ? (
        <span className="mt-1 block text-xs text-[var(--color-warn)]">{error}</span>
      ) : hint ? (
        <span className="mt-1 block text-xs text-[var(--color-muted)]">{hint}</span>
      ) : null}
    </label>
  );
}
