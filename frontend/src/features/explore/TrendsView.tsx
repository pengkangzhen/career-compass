import type { TrendsView } from "../../api/types";
import { Empty, Section } from "../../components/ui";

export function TrendsView({ data }: { data: TrendsView }) {
  if (data.empty) return <Empty message={data.message ?? "暂无趋势"} />;

  return (
    <div className="space-y-8">
      {data.signals.map((group) => (
        <Section key={group.domain} title={group.label}>
          <div className="space-y-3">
            {group.items.map((s, i) => (
              <div
                key={i}
                className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4"
              >
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <span className="font-medium">{s.topic}</span>
                  <span className="rounded bg-[var(--color-border)] px-1.5 py-0.5 text-[10px]">
                    {s.confidence}
                  </span>
                  <span className="text-xs text-[var(--color-muted)]">{s.retrieved_on}</span>
                </div>
                <p className="text-sm leading-relaxed">{s.finding}</p>
                <p className="mt-2 text-xs text-[var(--color-muted)]">
                  来源: {s.source}
                  {s.source_url && (
                    <>
                      {" · "}
                      <a href={s.source_url} target="_blank" rel="noreferrer" className="text-[var(--color-accent)]">
                        链接
                      </a>
                    </>
                  )}
                </p>
              </div>
            ))}
          </div>
        </Section>
      ))}

      {data.sectors.length > 0 && (
        <Section title="热门赛道池">
          <div className="grid gap-3 md:grid-cols-2">
            {data.sectors.map((sec) => (
              <div
                key={sec.name}
                className="rounded-xl border border-[var(--color-border)] p-4"
              >
                <p className="font-semibold">{sec.name}</p>
                {sec.why_hot && <p className="mt-1 text-sm">🔥 {sec.why_hot}</p>}
                {sec.value_is_in && (
                  <p className="mt-1 text-sm text-[var(--color-muted)]">价值在: {sec.value_is_in}</p>
                )}
                {sec.trap && (
                  <p className="mt-1 text-sm text-[var(--color-warn)]">⚠️ 陷阱: {sec.trap}</p>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}
