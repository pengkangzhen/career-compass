type Props = { expanded: boolean; onToggle: () => void };

export function OptionalCliPanel({ expanded, onToggle }: Props) {
  return (
    <div className="border-t border-[var(--color-border)] bg-[var(--color-surface)]/50 px-4 py-3">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between text-left text-xs font-medium text-[var(--color-muted)] hover:text-[var(--color-text)]"
      >
        <span>投递阶段（可选 · CLI）</span>
        <span>{expanded ? "收起" : "展开"}</span>
      </button>
      {expanded && (
        <div className="mt-3 space-y-2 rounded-xl border border-[var(--color-border)] bg-black/15 p-4 text-xs text-[var(--color-muted)]">
          <p>
            北斗星<strong className="text-[var(--color-text)]">核心交付是机会矩阵</strong>
            。开始投递后的执行包、漏斗追踪、矩阵修订属于可选延伸，请用 CLI：
          </p>
          <pre className="overflow-x-auto rounded-lg bg-black/25 p-3 font-mono text-[11px] leading-relaxed text-[var(--color-text)]">
{`uv run career-compass render-execution   # L3 行动手册
uv run career-compass track add "公司" "岗位"
uv run career-compass track funnel
uv run career-compass replan --write       # L4 修订矩阵`}
          </pre>
          <p>详见 <code className="text-[var(--color-accent)]">docs/phase-3.md</code></p>
        </div>
      )}
    </div>
  );
}
