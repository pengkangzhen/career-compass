import type { ReactNode } from "react";

type Tone = "default" | "warn";

type Props = {
  message: ReactNode;
  // Optional hint rendered below in smaller monospaced text (e.g. CLI command).
  hint?: ReactNode;
  // Optional action rendered below — typically a Button or link.
  action?: ReactNode;
  // Visual tone — warn tints the icon amber (e.g. "data layer not ready").
  tone?: Tone;
  className?: string;
};

export function Empty({
  message,
  hint,
  action,
  tone = "default",
  className = "py-12",
}: Props) {
  const stroke =
    tone === "warn" ? "var(--color-warn)" : "var(--color-muted)";
  return (
    <div className={`flex flex-col items-center text-center ${className}`}>
      <svg
        width="56"
        height="56"
        viewBox="0 0 56 56"
        fill="none"
        aria-hidden="true"
        className="mb-3 opacity-70"
      >
        <circle
          cx="28"
          cy="28"
          r="22"
          stroke={stroke}
          strokeWidth="1.5"
          strokeDasharray="3 4"
        />
        <path
          d="M28 18v12M28 36v.5"
          stroke={stroke}
          strokeWidth="1.5"
          strokeLinecap="round"
        />
      </svg>
      <p className="text-[var(--color-muted)]">{message}</p>
      {hint && (
        <p className="mt-2 font-mono text-xs text-[var(--color-muted)]">{hint}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
