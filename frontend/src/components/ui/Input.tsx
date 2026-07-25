import type { InputHTMLAttributes, ReactNode } from "react";

type CommonProps = {
  label?: ReactNode;
  // Helper or error text rendered under the field.
  error?: string;
  hint?: ReactNode;
  // Wrapping label element semantics: clicking label focuses input.
};

type InputProps = CommonProps &
  Omit<InputHTMLAttributes<HTMLInputElement>, "size"> & {
    // Reserved for future size variants (sm/md); currently passthrough.
    inputSize?: "sm" | "md";
  };

export function Input({
  label,
  error,
  hint,
  inputSize = "md",
  className = "",
  id,
  ...rest
}: InputProps) {
  const fieldCls = [
    "w-full rounded-md border bg-[var(--color-surface)] px-3 py-2 text-sm outline-none transition",
    "focus:border-[var(--color-accent)] disabled:opacity-60",
    error
      ? "border-[var(--color-warn)]"
      : "border-[var(--color-border)]",
    inputSize === "sm" ? "py-1.5 text-xs" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <label className="block" htmlFor={id}>
      {label && (
        <span className="mb-1 block text-xs font-medium text-[var(--color-muted)]">
          {label}
        </span>
      )}
      <input id={id} className={fieldCls} {...rest} />
      {error ? (
        <span className="mt-1 block text-xs text-[var(--color-warn)]">{error}</span>
      ) : hint ? (
        <span className="mt-1 block text-xs text-[var(--color-muted)]">{hint}</span>
      ) : null}
    </label>
  );
}
