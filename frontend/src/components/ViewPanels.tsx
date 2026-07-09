import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type {
  JobsView,
  MatrixView,
  ProfileView,
  TrendsView,
} from "../api/types";

export function ProfileViewPanel({ data }: { data: ProfileView }) {
  if (data.empty) {
    return <Empty message={data.message ?? "暂无画像"} />;
  }

  const v = data.validation;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">{data.title}</h2>
        {v && v.errors.length > 0 && (
          <Alert tone="warn" title="待补齐">
            <ul className="list-disc pl-4">
              {v.errors.slice(0, 8).map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          </Alert>
        )}
        {v && !v.errors.length && v.warnings.length > 0 && (
          <Alert tone="hint" title="建议完善">
            <ul className="list-disc pl-4">
              {v.warnings.slice(0, 5).map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          </Alert>
        )}
        {v && !v.errors.length && !v.warnings.length && (
          <Alert tone="ok">✅ 画像校验通过</Alert>
        )}
      </div>

      {data.education && data.education.length > 0 && (
        <Section title="教育背景">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left text-[var(--color-muted)]">
                  <th className="py-2 pr-3">层次</th>
                  <th className="py-2 pr-3">院校</th>
                  <th className="py-2 pr-3">专业</th>
                  <th className="py-2 pr-3">时间</th>
                  <th className="py-2">备注</th>
                </tr>
              </thead>
              <tbody>
                {data.education.map((e, i) => (
                  <tr key={i} className="border-b border-[var(--color-border)]/50">
                    <td className="py-2 pr-3">{e.level}</td>
                    <td className="py-2 pr-3">
                      {e.school}
                      {e.school_tier && (
                        <span className="ml-1 rounded bg-[var(--color-border)] px-1.5 py-0.5 text-[10px]">
                          {e.school_tier}
                        </span>
                      )}
                    </td>
                    <td className="py-2 pr-3">
                      {e.major}
                      {e.department ? ` · ${e.department}` : ""}
                    </td>
                    <td className="py-2 pr-3">{e.time}</td>
                    <td className="py-2 text-[var(--color-muted)]">{e.notes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {data.core_skills && data.core_skills.length > 0 && (
        <Section title="核心技能">
          <TagList items={data.core_skills} />
        </Section>
      )}

      {data.adjacent_skills && data.adjacent_skills.length > 0 && (
        <Section title="相邻技能">
          <TagList items={data.adjacent_skills} muted />
        </Section>
      )}

      {data.evidence && data.evidence.length > 0 && (
        <Section title="优势证据">
          <div className="space-y-2">
            {data.evidence.map((ev, i) => (
              <div
                key={i}
                className="rounded-lg border border-[var(--color-border)] bg-black/15 p-3"
              >
                <p className="font-medium text-sm">{ev.claim}</p>
                <p className="mt-1 text-xs text-[var(--color-muted)]">{ev.proof}</p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {data.constraints && (
        <Section title="硬约束">
          <ul className="list-disc pl-5 text-sm text-[var(--color-muted)]">
            {data.constraints.age != null && <li>年龄: {data.constraints.age}</li>}
            <li>风险偏好: {data.constraints.risk_appetite}</li>
            {data.constraints.notes && <li>{data.constraints.notes}</li>}
          </ul>
        </Section>
      )}

      {data.narrative_md && (
        <Section title="叙事">
          <div className="prose-beidou">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.narrative_md}</ReactMarkdown>
          </div>
        </Section>
      )}
    </div>
  );
}

export function TrendsViewPanel({ data }: { data: TrendsView }) {
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

export function JobsViewPanel({ data }: { data: JobsView }) {
  if (data.empty) {
    return (
      <Empty
        message={data.message ?? "暂无收藏"}
        hint={data.hint}
      />
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-[var(--color-muted)]">共 {data.count ?? data.jobs.length} 个收藏</p>
      {data.jobs.map((job, i) => (
        <div
          key={i}
          className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4"
        >
          <h3 className="font-semibold">
            {job.company} · {job.role}
          </h3>
          <p className="text-xs text-[var(--color-muted)]">
            {job.location} · {job.saved_on} · [{job.status}]
          </p>
          {job.notes && <p className="mt-2 text-sm italic">{job.notes}</p>}
          {job.match && (
            <div className="mt-3 text-sm">
              <p>
                <strong>匹配摘要:</strong> {job.match.summary}
              </p>
              {job.match.linked_direction && (
                <p className="mt-1">关联方向: {job.match.linked_direction}</p>
              )}
              {job.match.barriers.length > 0 && (
                <ul className="mt-2 list-disc pl-5 text-[var(--color-warn)]">
                  {job.match.barriers.map((b) => (
                    <li key={b}>⚠️ {b}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export function MatrixViewPanel({ data }: { data: MatrixView }) {
  if (data.empty) {
    return <Empty message={data.message ?? "暂无矩阵"} hint={data.hint} />;
  }

  if (data.format === "markdown" && data.content) {
    return (
      <div className="prose-beidou max-w-none">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.content}</ReactMarkdown>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {data.unified_theme && (
        <Alert tone="hint" title="统一架构">
          {data.unified_theme}
        </Alert>
      )}
      {data.shared_assets && data.shared_assets.length > 0 && (
        <Section title="共享资产">
          <TagList items={data.shared_assets} />
        </Section>
      )}
      {data.primary && data.primary.length > 0 && (
        <MatrixTable title="主业（Primary）" rows={data.primary} />
      )}
      {data.side && data.side.length > 0 && (
        <MatrixTable title="副业（Side）" rows={data.side} showSynergy />
      )}
      {data.hint && <p className="text-xs text-[var(--color-muted)]">{data.hint}</p>}
    </div>
  );
}

function MatrixTable({
  title,
  rows,
  showSynergy,
}: {
  title: string;
  rows: Record<string, string | number>[];
  showSynergy?: boolean;
}) {
  const cols = showSynergy
    ? ["rank", "positioning", "track", "summary", "employer", "fit", "match", "wind", "risk", "composite", "synergy"]
    : ["rank", "positioning", "track", "summary", "employer", "fit", "match", "wind", "risk", "composite"];
  const labels: Record<string, string> = {
    rank: "#",
    direction: "方向",
    positioning: "价值定位",
    track: "赛道",
    summary: "核心工作",
    employer: "组织类型",
    fit: "比较优势",
    match: "Ikigai",
    wind: "顺风",
    risk: "试错成本",
    composite: "综合",
    synergy: "协同主业",
  };

  return (
    <Section title={title}>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="border-b border-[var(--color-border)] text-left text-[var(--color-muted)]">
              {cols.map((c) => (
                <th key={c} className="py-2 pr-2">
                  {labels[c] ?? c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-b border-[var(--color-border)]/40">
                {cols.map((c) => (
                  <td key={c} className="py-2 pr-2 align-top">
                    {c === "composite" ? (
                      <strong>{String(row[c] ?? "")}</strong>
                    ) : (
                      String(row[c] ?? "")
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="mb-3 text-base font-semibold">{title}</h3>
      {children}
    </section>
  );
}

function TagList({ items, muted }: { items: string[]; muted?: boolean }) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <span
          key={item}
          className={`rounded-lg px-2.5 py-1 text-xs ${
            muted
              ? "bg-[var(--color-border)]/60 text-[var(--color-muted)]"
              : "bg-[var(--color-accent)]/15 text-[var(--color-accent)]"
          }`}
        >
          {item}
        </span>
      ))}
    </div>
  );
}

function Alert({
  tone,
  title,
  children,
}: {
  tone: "ok" | "warn" | "hint";
  title?: string;
  children: React.ReactNode;
}) {
  const colors = {
    ok: "border-[var(--color-ok)]/30 bg-[var(--color-ok)]/10 text-[var(--color-ok)]",
    warn: "border-[var(--color-warn)]/30 bg-[var(--color-warn)]/10",
    hint: "border-[var(--color-accent)]/30 bg-[var(--color-accent)]/10",
  };
  return (
    <div className={`mt-3 rounded-xl border p-3 text-sm ${colors[tone]}`}>
      {title && <strong className="block mb-1">{title}</strong>}
      {children}
    </div>
  );
}

function Empty({ message, hint }: { message: string; hint?: string }) {
  return (
    <div className="py-12 text-center">
      <p className="text-[var(--color-muted)]">{message}</p>
      {hint && (
        <p className="mt-2 font-mono text-xs text-[var(--color-muted)]">{hint}</p>
      )}
    </div>
  );
}

export function ExecutionViewPanel({ data }: { data: import("../api/types").ExecutionView }) {
  if (data.empty) {
    return <Empty message={data.message ?? "暂无执行包"} hint={data.hint} />;
  }
  if (data.content) {
    return (
      <div className="prose-beidou max-w-none">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.content}</ReactMarkdown>
      </div>
    );
  }
  return null;
}

export function TrackViewPanel({ data }: { data: import("../api/types").TrackView }) {
  const f = data.funnel;
  const pct = (n: number) => `${Math.round(n * 100)}%`;

  return (
    <div className="space-y-6">
      <Section title="投递漏斗">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Stat label="总投递" value={String(f.total)} />
          <Stat label="回复率" value={pct(f.response_rate)} />
          <Stat label="面试率" value={pct(f.interview_rate)} />
          <Stat label="Offer 率" value={pct(f.offer_rate)} />
        </div>
        {(f.ghosted_count > 0 || f.rejected_count > 0) && (
          <p className="mt-2 text-xs text-[var(--color-warn)]">
            无回音 {f.ghosted_count} · 拒信 {f.rejected_count}
          </p>
        )}
      </Section>

      {data.empty ? (
        <Empty message={data.message ?? "暂无投递"} hint={data.hint} />
      ) : (
        <Section title="投递记录">
          <div className="space-y-3">
            {data.applications.map((app) => (
              <div
                key={app.id}
                className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4"
              >
                <h3 className="font-semibold">
                  {app.company} · {app.role}
                </h3>
                <p className="text-xs text-[var(--color-muted)]">
                  {app.applied_on} · [{app.status}] · 梯队 {app.tier}
                  {app.direction ? ` · ${app.direction}` : ""}
                </p>
                {app.feedback && (
                  <p className="mt-2 text-sm">
                    <strong>反馈:</strong> {app.feedback}
                  </p>
                )}
                {app.notes && <p className="mt-1 text-sm italic text-[var(--color-muted)]">{app.notes}</p>}
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-black/15 p-3 text-center">
      <p className="text-lg font-semibold">{value}</p>
      <p className="text-[11px] text-[var(--color-muted)]">{label}</p>
    </div>
  );
}
