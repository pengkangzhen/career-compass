import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  api,
  type MatrixRow,
  type MatrixView,
  type JobsView,
  type ProfileView,
  type TrendsView,
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

export function JobsViewPanel({
  data,
  onRefresh,
}: {
  data: JobsView;
  onRefresh?: () => Promise<void> | void;
}) {
  return (
    <div className="space-y-4">
      {onRefresh && <AddJobForm onRefresh={onRefresh} />}
      {data.empty ? (
        <Empty message={data.message ?? "暂无收藏"} hint={data.hint} />
      ) : (
        <>
          <p className="text-sm text-[var(--color-muted)]">
            共 {data.count ?? data.jobs.length} 个收藏
          </p>
          {data.jobs.map((job, i) => (
            <JobCard
              key={job.id ?? i}
              job={job}
              onRefresh={onRefresh}
            />
          ))}
        </>
      )}
    </div>
  );
}

function JobCard({
  job,
  onRefresh,
}: {
  job: import("../api/types").SavedJobItem;
  onRefresh?: () => Promise<void> | void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const editable = !!onRefresh && !!job.id;
  const hasPreview = !!job.description_preview;

  if (editing && editable) {
    return (
      <JobForm
        mode="edit"
        initial={job}
        onSubmit={async () => {
          await onRefresh!();
          setEditing(false);
        }}
        onCancel={() => setEditing(false)}
      />
    );
  }

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold">
            {job.company} · {job.role}
          </h3>
          <p className="text-xs text-[var(--color-muted)]">
            {job.location || "—"}
            {" · "}
            {job.saved_on}
            {" · ["}
            {job.status}]
            {job.source ? ` · 来源: ${job.source}` : ""}
            {job.linked_direction ? ` · 关联: ${job.linked_direction}` : ""}
          </p>
        </div>
        {editable && (
          <div className="flex flex-shrink-0 items-center gap-1">
            <button
              type="button"
              onClick={() => setEditing(true)}
              title="编辑"
              className="rounded-md border border-[var(--color-border)] px-2 py-0.5 text-xs text-[var(--color-muted)] hover:border-[var(--color-accent)] hover:text-[var(--color-accent)]"
            >
              📝
            </button>
            <button
              type="button"
              onClick={() => {
                if (!window.confirm("确定删除该岗位？")) return;
                void (async () => {
                  try {
                    const res = await api.jobsRemove(job.id!);
                    if (!res.ok) {
                      window.alert(res.error ?? "删除失败");
                      return;
                    }
                    await onRefresh!();
                  } catch (err) {
                    window.alert(
                      err instanceof Error
                        ? `删除失败：${err.message}`
                        : "删除失败：网络或服务器错误",
                    );
                  }
                })();
              }}
              title="删除"
              className="rounded-md border border-[var(--color-border)] px-2 py-0.5 text-xs text-[var(--color-muted)] hover:border-[var(--color-warn)] hover:text-[var(--color-warn)]"
            >
              ✕
            </button>
          </div>
        )}
      </div>
      {job.notes && <p className="mt-2 text-sm italic">{job.notes}</p>}
      {hasPreview && (
        <div className="mt-2">
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="text-xs text-[var(--color-accent)] hover:underline"
          >
            {expanded ? "收起 JD" : "展开 JD"}
          </button>
          {expanded && (
            <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap rounded-md bg-black/10 p-3 text-xs leading-relaxed">
              {job.description_preview}
            </pre>
          )}
        </div>
      )}
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
  );
}

const DEFAULT_SOURCE = "手动添加";

const JOB_STATUSES = [
  { value: "interested", label: "interested · 刚收藏" },
  { value: "researching", label: "researching · 调研中" },
  { value: "ready", label: "ready · 准备投递" },
  { value: "applied", label: "applied · 已投递" },
  { value: "archived", label: "archived · 归档" },
] as const;

type JobFormProps =
  | {
      mode: "create";
      onSubmit: () => Promise<void> | void;
      onCancel: () => void;
    }
  | {
      mode: "edit";
      initial: import("../api/types").SavedJobItem;
      onSubmit: () => Promise<void> | void;
      onCancel: () => void;
    };

function JobForm(props: JobFormProps) {
  const { mode, onSubmit, onCancel } = props;
  const initial = mode === "edit" ? props.initial : undefined;
  const [open, setOpen] = useState(mode === "create");
  const [company, setCompany] = useState(initial?.company ?? "");
  const [role, setRole] = useState(initial?.role ?? "");
  const [location, setLocation] = useState(initial?.location ?? "");
  const [source, setSource] = useState(initial?.source ?? DEFAULT_SOURCE);
  const [linkedDirection, setLinkedDirection] = useState(initial?.linked_direction ?? "");
  const [notes, setNotes] = useState(initial?.notes ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [status, setStatus] = useState<string>(initial?.status ?? "interested");
  const [fileName, setFileName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = useCallback(() => {
    setCompany("");
    setRole("");
    setLocation("");
    setSource(DEFAULT_SOURCE);
    setLinkedDirection("");
    setNotes("");
    setDescription("");
    setStatus("interested");
    setFileName("");
    setError(null);
  }, []);

  const handleFile = useCallback(
    async (file: File | null) => {
      if (!file) return;
      setFileName(file.name);
      try {
        const text = await file.text();
        setDescription(text);
      } catch {
        setError("无法读取该文件，请改用纯文本 (.txt / .md)");
      }
    },
    [],
  );

  const canSubmit =
    !busy &&
    company.trim().length > 0 &&
    role.trim().length > 0 &&
    description.trim().length > 0;

  const handleSubmit = useCallback(async () => {
    if (!canSubmit) return;
    setBusy(true);
    setError(null);
    try {
      if (mode === "edit") {
        const res = await api.jobsUpdate(props.initial.id!, {
          company: company.trim(),
          role: role.trim(),
          description: description.trim(),
          location: location.trim(),
          source: source.trim() || DEFAULT_SOURCE,
          linked_direction: linkedDirection.trim(),
          notes: notes.trim(),
          status: status as import("../api/types").SavedJobStatus,
        });
        if (!res.ok) {
          setError(res.error ?? "保存失败");
          return;
        }
        await onSubmit();
      } else {
        const res = await api.jobsAdd({
          company: company.trim(),
          role: role.trim(),
          description: description.trim(),
          location: location.trim(),
          source: source.trim() || DEFAULT_SOURCE,
          linked_direction: linkedDirection.trim(),
          notes: notes.trim(),
        });
        if (!res.ok) {
          setError(res.error ?? "保存失败");
          return;
        }
        reset();
        setOpen(false);
        await onSubmit();
      }
    } catch (err) {
      // Without this catch, `void handleSubmit()` in the onClick swallows
      // network/parse errors silently — the user sees "click does nothing".
      console.error("[JobForm] save failed:", err);
      setError(
        err instanceof Error
          ? `保存失败：${err.message}`
          : "保存失败：网络或服务器错误，请重试",
      );
    } finally {
      setBusy(false);
    }
  }, [
    canSubmit,
    mode,
    props,
    company,
    role,
    description,
    location,
    source,
    linkedDirection,
    notes,
    status,
    reset,
    onSubmit,
  ]);

  if (mode === "create" && !open) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-[var(--color-muted)]">
          心仪的 JD 可直接粘贴或上传文件，存入「岗位收藏」供北斗星分析
        </p>
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="rounded-lg bg-[var(--color-accent)] px-3 py-1.5 text-xs font-medium text-white hover:opacity-90"
        >
          + 新增岗位
        </button>
      </div>
    );
  }

  const title = mode === "edit" ? "编辑岗位" : "新增心仪岗位";
  const submitLabel = mode === "edit" ? "保存修改" : "保存";

  return (
    <div className="space-y-3 rounded-xl border border-[var(--color-accent)]/40 bg-[var(--color-surface)] p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">{title}</h3>
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            if (mode === "create") {
              reset();
              setOpen(false);
            }
            onCancel();
          }}
          className="text-xs text-[var(--color-muted)] hover:text-[var(--color-text)] disabled:opacity-50"
        >
          取消
        </button>
      </div>
      <div className="grid gap-2 md:grid-cols-2">
        <LabeledInput
          label="公司 *"
          value={company}
          onChange={setCompany}
          placeholder="例如：字节跳动"
          disabled={busy}
        />
        <LabeledInput
          label="岗位 *"
          value={role}
          onChange={setRole}
          placeholder="例如：算法工程师"
          disabled={busy}
        />
        <LabeledInput
          label="地点"
          value={location}
          onChange={setLocation}
          placeholder="例如：北京 / 远程"
          disabled={busy}
        />
        <LabeledInput
          label="来源"
          value={source}
          onChange={setSource}
          placeholder="招聘软件 / 官网 / 内推"
          disabled={busy}
        />
        <LabeledInput
          label="关联方向（可选）"
          value={linkedDirection}
          onChange={setLinkedDirection}
          placeholder="对应机会矩阵 direction"
          disabled={busy}
        />
        <LabeledInput
          label="备注（可选）"
          value={notes}
          onChange={setNotes}
          placeholder="例如：暂无 CCF-A 一作"
          disabled={busy}
        />
        {mode === "edit" && (
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-[var(--color-muted)]">
              状态
            </span>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              disabled={busy}
              className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-sm outline-none focus:border-[var(--color-accent)] disabled:opacity-60"
            >
              {JOB_STATUSES.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      <div>
        <div className="mb-1 flex items-center justify-between">
          <label className="text-xs font-medium text-[var(--color-muted)]">
            JD 全文 *{" "}
            <span className="font-normal">
              （粘贴文本或上传 .txt / .md / .json）
            </span>
          </label>
          <span className="text-[11px] text-[var(--color-muted)]">
            {description.length} 字
          </span>
        </div>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          disabled={busy}
          placeholder="粘贴 JD 全文（招聘要求、岗位职责、技能清单…）"
          rows={6}
          className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 font-mono text-xs leading-relaxed outline-none focus:border-[var(--color-accent)] disabled:opacity-60"
        />
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <label className="cursor-pointer rounded-md border border-[var(--color-border)] bg-black/10 px-3 py-1.5 text-xs text-[var(--color-muted)] hover:border-[var(--color-accent)] hover:text-[var(--color-accent)]">
            📎 上传 JD 文件
            <input
              type="file"
              accept=".txt,.md,.markdown,.json,.text,text/*"
              className="hidden"
              disabled={busy}
              onChange={(e) => {
                const f = e.target.files?.[0] ?? null;
                void handleFile(f);
                e.target.value = "";
              }}
            />
          </label>
          {fileName && (
            <span className="text-xs text-[var(--color-muted)]">
              已加载: {fileName}
            </span>
          )}
          {description && (
            <button
              type="button"
              onClick={() => {
                setDescription("");
                setFileName("");
              }}
              disabled={busy}
              className="text-xs text-[var(--color-muted)] hover:text-[var(--color-text)] disabled:opacity-50"
            >
              清空
            </button>
          )}
        </div>
      </div>
      {error && (
        <p className="rounded-md bg-[var(--color-warn)]/15 px-3 py-2 text-xs text-[var(--color-warn)]">
          {error}
        </p>
      )}
      <div className="flex items-center justify-end gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            if (mode === "create") {
              reset();
              setOpen(false);
            }
            onCancel();
          }}
          className="rounded-md border border-[var(--color-border)] px-3 py-1.5 text-xs text-[var(--color-muted)] disabled:opacity-50"
        >
          取消
        </button>
        <button
          type="button"
          disabled={!canSubmit}
          onClick={() => void handleSubmit()}
          className="rounded-md bg-[var(--color-accent)] px-4 py-1.5 text-xs font-medium text-white disabled:opacity-50"
        >
          {busy ? "保存中…" : submitLabel}
        </button>
      </div>
    </div>
  );
}

function AddJobForm({ onRefresh }: { onRefresh: () => Promise<void> | void }) {
  return (
    <JobForm
      mode="create"
      onSubmit={onRefresh}
      onCancel={() => {}}
    />
  );
}

function LabeledInput({
  label,
  value,
  onChange,
  placeholder,
  disabled,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  disabled?: boolean;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-[var(--color-muted)]">
        {label}
      </span>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-sm outline-none focus:border-[var(--color-accent)] disabled:opacity-60"
      />
    </label>
  );
}

export function MatrixViewPanel({
  data,
  onRefresh,
}: {
  data: MatrixView;
  onRefresh?: () => Promise<void> | void;
}) {
  const [viewMode, setViewMode] = useState<"editable" | "document">("editable");

  if (data.empty) {
    return <Empty message={data.message ?? "暂无矩阵"} hint={data.hint} />;
  }

  const hasMarkdownDoc = !!data.content;
  const hasEditableRows = !!data.primary && data.primary.length > 0;
  const showToggleSwitch = hasMarkdownDoc && hasEditableRows;
  const showDocument = viewMode === "document" && hasMarkdownDoc && !hasEditableRows;

  if ((data.format === "markdown" && data.content) || showDocument) {
    return (
      <div className="space-y-4">
        {showToggleSwitch && (
          <ViewModeToggle mode={viewMode} onChange={setViewMode} />
        )}
        <div className="prose-beidou max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.content!}</ReactMarkdown>
        </div>
      </div>
    );
  }

  const editable = !!onRefresh && hasEditableRows;

  const handleAddNote = useCallback(
    async (direction: string, text: string) => {
      const res = await api.matrixFeedbackAdd("note", direction, { text });
      if (!res.ok) {
        window.alert(res.error ?? "记录备注失败");
        return;
      }
      await onRefresh!();
    },
    [onRefresh],
  );

  return (
    <div className="space-y-4">
      {showToggleSwitch && (
        <ViewModeToggle mode={viewMode} onChange={setViewMode} />
      )}
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
        {hasEditableRows && (
          <MatrixTable
            title="机会方向"
            rows={data.primary!}
            hidden={data.hidden_directions ?? []}
            orderOverrides={data.order_overrides ?? []}
            notes={data.notes ?? {}}
            editable={editable}
            onRefresh={onRefresh}
            onAddNote={editable ? handleAddNote : undefined}
          />
        )}
        {viewMode === "document" && hasMarkdownDoc && (
          <Section title="渲染文档">
            <div className="prose-beidou max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.content!}</ReactMarkdown>
            </div>
          </Section>
        )}
        {data.hint && <p className="text-xs text-[var(--color-muted)]">{data.hint}</p>}
      </div>
    </div>
  );
}

function ViewModeToggle({
  mode,
  onChange,
}: {
  mode: "editable" | "document";
  onChange: (m: "editable" | "document") => void;
}) {
  const opts: { id: "editable" | "document"; label: string }[] = [
    { id: "editable", label: "可编辑视图" },
    { id: "document", label: "渲染文档" },
  ];
  return (
    <div className="flex items-center gap-1">
      {opts.map((o) => (
        <button
          key={o.id}
          type="button"
          onClick={() => onChange(o.id)}
          className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
            mode === o.id
              ? "bg-[var(--color-accent)]/20 text-[var(--color-accent)]"
              : "text-[var(--color-muted)] hover:text-[var(--color-text)]"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function MatrixTable({
  title,
  rows,
  hidden,
  orderOverrides,
  notes,
  editable,
  onRefresh,
  onAddNote,
}: {
  title: string;
  rows: MatrixRow[];
  hidden: string[];
  orderOverrides: string[];
  notes: Record<string, string>;
  editable: boolean;
  onRefresh?: () => Promise<void> | void;
  onAddNote?: (direction: string, text: string) => Promise<void> | void;
}) {
  const [busy, setBusy] = useState(false);
  // Mirror of `busy` that's safe to read inside async drag handlers without
  // recreating them on every state change.
  const busyRef = useRef(false);
  // Visual-only: which rendered row currently looks "grabbed".
  const [draggingIndex, setDraggingIndex] = useState<number | null>(null);
  // Source of truth for drop logic — keyed by direction (stable across
  // refreshes) and read at drop time. Held in a ref so handlers don't have
  // to be rebuilt on every drag.
  const dragFromRef = useRef<string | null>(null);
  const [editingNoteFor, setEditingNoteFor] = useState<string | null>(null);
  const [noteDraft, setNoteDraft] = useState("");

  // Always clear drag tracking on unmount so a remount can't read stale data.
  useEffect(() => {
    return () => {
      dragFromRef.current = null;
      busyRef.current = false;
    };
  }, []);

  const { displayed, hiddenCount } = useMemo(() => {
    const hiddenSet = new Set(hidden);
    const visible = rows.filter((r) => {
      const d = String(r.direction ?? "");
      return d !== "" && !hiddenSet.has(d);
    });
    // Apply user order overrides: directions in override list come first in given order,
    // remaining rows keep their engine rank.
    if (orderOverrides.length > 0) {
      const byDir = new Map<string, MatrixRow>();
      for (const r of visible) {
        const d = String(r.direction ?? "");
        if (d) byDir.set(d, r);
      }
      const ordered: MatrixRow[] = [];
      const seen = new Set<string>();
      for (const d of orderOverrides) {
        const r = byDir.get(d);
        if (r) {
          ordered.push(r);
          seen.add(d);
        }
      }
      for (const r of visible) {
        const d = String(r.direction ?? "");
        if (d && !seen.has(d)) ordered.push(r);
      }
      const totalCount = rows.length;
      return { displayed: ordered, hiddenCount: totalCount - ordered.length };
    }
    return { displayed: visible, hiddenCount: rows.length - visible.length };
  }, [rows, hidden, orderOverrides]);

  const cols = [
    "rank",
    "direction_label",
    "job_title",
    "related_companies",
    "summary",
    "employer",
    "fit",
    "match",
    "wind",
    "risk",
    "composite",
    ...(editable ? ["_actions"] : []),
  ];
  const labels: Record<string, string> = {
    rank: "#",
    direction: "方向",
    direction_label: "方向",
    job_title: "岗位名称",
    related_companies: "相关企业",
    summary: "核心工作",
    employer: "组织类型",
    fit: "核心竞争力",
    match: "Ikigai",
    wind: "行业趋势",
    risk: "试错成本",
    composite: "综合",
    _actions: "",
  };

  const renderCell = (row: MatrixRow, key: string) => {
    if (key === "direction_label") {
      const p = String(row.positioning ?? "");
      const t = String(row.track ?? "");
      if (p && t && p !== t) return `${p} · ${t}`;
      return p || t || "—";
    }
    if (key === "composite") {
      return <strong>{String(row[key] ?? "")}</strong>;
    }
    const v = row[key];
    return v === undefined || v === null || v === "" ? "—" : String(v);
  };

  const handleRemove = useCallback(
    async (direction: string) => {
      if (!direction || !onRefresh) return;
      setBusy(true);
      try {
        const res = await api.matrixFeedbackAdd("remove", direction);
        if (!res.ok) {
          window.alert(res.error ?? "记录反馈失败");
          return;
        }
        await onRefresh();
      } finally {
        setBusy(false);
      }
    },
    [onRefresh],
  );

  const handleReset = useCallback(async () => {
    if (!onRefresh) return;
    setBusy(true);
    try {
      await api.matrixFeedbackAdd("reset");
      await onRefresh();
    } finally {
      setBusy(false);
    }
  }, [onRefresh]);

  const handleDrop = useCallback(
    async (toIndex: number) => {
      const fromDir = dragFromRef.current;
      dragFromRef.current = null;
      // Defer the visual reset off the drag event tick — calling setState
      // synchronously inside drop/dragEnd handlers can interrupt the
      // browser's drag-end sequence and poison the *next* drag.
      window.queueMicrotask(() => setDraggingIndex(null));
      if (onRefresh === undefined || !fromDir) return;
      if (busyRef.current) return; // a reorder is already in flight
      // Drop target must currently exist; `displayed` is read at drop time.
      if (toIndex < 0 || toIndex >= displayed.length) return;
      const toDir = String(displayed[toIndex]?.direction ?? "");
      if (!toDir || toDir === fromDir) return;
      busyRef.current = true;
      setBusy(true);
      try {
        const res = await api.matrixFeedbackAdd("reorder", fromDir, {
          anchor_direction: toDir,
          to_rank: toIndex,
        });
        if (!res.ok) {
          window.alert(res.error ?? "记录排序失败");
          return;
        }
        await onRefresh();
      } finally {
        busyRef.current = false;
        setBusy(false);
      }
    },
    [displayed, onRefresh],
  );

  const startEditNote = useCallback((direction: string) => {
    setEditingNoteFor(direction);
    setNoteDraft(notes[direction] ?? "");
  }, [notes]);

  const cancelEditNote = useCallback(() => {
    setEditingNoteFor(null);
    setNoteDraft("");
  }, []);

  const submitNote = useCallback(
    async (direction: string) => {
      const text = noteDraft.trim();
      if (!text || !onAddNote) {
        cancelEditNote();
        return;
      }
      setBusy(true);
      try {
        await onAddNote(direction, text);
        cancelEditNote();
      } finally {
        setBusy(false);
      }
    },
    [noteDraft, onAddNote, cancelEditNote],
  );

  return (
    <Section title={title}>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-sm">
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
            {displayed.map((row, i) => {
              const direction = String(row.direction ?? "");
              const isDragging = draggingIndex === i;
              const note = notes[direction];
              const isEditing = editingNoteFor === direction;
              const colCount = cols.length;
              return (
                <Fragment key={direction || i}>
                  <tr
                    draggable={editable && !busy}
                    onDragStart={(e) => {
                      if (!direction || busyRef.current) {
                        e.preventDefault();
                        return;
                      }
                      // **Mandatory**: at least one setData call, otherwise
                      // Firefox (and strict Chromium) silently cancel the
                      // drag — and the second drag in a row fails first.
                      e.dataTransfer.setData("text/plain", direction);
                      e.dataTransfer.effectAllowed = "move";
                      dragFromRef.current = direction;
                      // Defer visual update off the dragstart tick so the
                      // browser can capture the drag image before React
                      // re-renders the row.
                      window.queueMicrotask(() => setDraggingIndex(i));
                    }}
                    onDragOver={(e) => {
                      if (!editable) return;
                      // Matching dropEffect is required for the drop event
                      // to fire on subsequent drags.
                      e.preventDefault();
                      e.dataTransfer.dropEffect = "move";
                    }}
                    onDrop={(e) => {
                      if (!editable) return;
                      e.preventDefault();
                      if (!busyRef.current) void handleDrop(i);
                    }}
                    onDragEnd={() => {
                      // Defer the cleanup; calling setState synchronously
                      // inside dragEnd can race with the browser's drag
                      // teardown and break the next drag attempt.
                      window.queueMicrotask(() => {
                        dragFromRef.current = null;
                        setDraggingIndex(null);
                      });
                    }}
                    className={`border-b border-[var(--color-border)]/40 ${
                      isDragging ? "opacity-40" : ""
                    } ${editable ? "cursor-grab active:cursor-grabbing" : ""}`}
                  >
                    <td className="py-2 pr-2 align-top text-[var(--color-muted)]">{i + 1}</td>
                    <td className="py-2 pr-2 align-top">{renderCell(row, "direction_label")}</td>
                    <td className="py-2 pr-2 align-top">{renderCell(row, "job_title")}</td>
                    <td className="py-2 pr-2 align-top">{renderCell(row, "related_companies")}</td>
                    <td className="py-2 pr-2 align-top">{renderCell(row, "summary")}</td>
                    <td className="py-2 pr-2 align-top">{renderCell(row, "employer")}</td>
                    <td className="py-2 pr-2 align-top">{renderCell(row, "fit")}</td>
                    <td className="py-2 pr-2 align-top">{renderCell(row, "match")}</td>
                    <td className="py-2 pr-2 align-top">{renderCell(row, "wind")}</td>
                    <td className="py-2 pr-2 align-top">{renderCell(row, "risk")}</td>
                    <td className="py-2 pr-2 align-top">{renderCell(row, "composite")}</td>
                    {editable && (
                      <td className="py-2 pr-2 align-top text-right whitespace-nowrap">
                        <button
                          type="button"
                          disabled={busy || !direction}
                          onClick={() => direction && startEditNote(direction)}
                          title={note ? "编辑备注" : "添加备注"}
                          className="rounded-md border border-[var(--color-border)] px-2 py-0.5 text-xs text-[var(--color-muted)] hover:border-[var(--color-accent)] hover:text-[var(--color-accent)] disabled:opacity-50"
                        >
                          📝
                        </button>
                        <button
                          type="button"
                          disabled={busy || !direction}
                          onClick={() => direction && void handleRemove(direction)}
                          title={direction ? `隐藏「${direction}」` : "无可识别方向"}
                          className="ml-1 rounded-md border border-[var(--color-border)] px-2 py-0.5 text-xs text-[var(--color-muted)] hover:border-[var(--color-warn)] hover:text-[var(--color-warn)] disabled:opacity-50"
                        >
                          ✕
                        </button>
                      </td>
                    )}
                  </tr>
                  {(isEditing || note) && (
                    <tr className="border-b border-[var(--color-border)]/40 bg-black/5">
                      <td colSpan={colCount} className="px-3 py-2">
                        {isEditing ? (
                          <div className="flex flex-wrap items-center gap-2">
                            <input
                              type="text"
                              autoFocus
                              value={noteDraft}
                              onChange={(e) => setNoteDraft(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") {
                                  e.preventDefault();
                                  void submitNote(direction);
                                } else if (e.key === "Escape") {
                                  e.preventDefault();
                                  cancelEditNote();
                                }
                              }}
                              placeholder="备注：例如「美团、滴滴等大厂已经饱和」"
                              className="min-w-[280px] flex-1 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1 text-sm outline-none focus:border-[var(--color-accent)]"
                            />
                            <button
                              type="button"
                              disabled={busy || !noteDraft.trim()}
                              onClick={() => void submitNote(direction)}
                              className="rounded-md bg-[var(--color-accent)] px-3 py-1 text-xs text-white disabled:opacity-50"
                            >
                              保存
                            </button>
                            <button
                              type="button"
                              disabled={busy}
                              onClick={cancelEditNote}
                              className="rounded-md border border-[var(--color-border)] px-3 py-1 text-xs text-[var(--color-muted)] disabled:opacity-50"
                            >
                              取消
                            </button>
                            <span className="text-[11px] text-[var(--color-muted)]">
                              Enter 保存 · Esc 取消 · 新备注会覆盖旧备注（历史保留在 YAML 中）
                            </span>
                          </div>
                        ) : (
                          <p className="text-xs leading-relaxed text-[var(--color-muted)]">
                            <strong className="text-[var(--color-text)]">备注：</strong>
                            {note}
                          </p>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
            {displayed.length === 0 && (
              <tr>
                <td colSpan={cols.length} className="py-6 text-center text-[var(--color-muted)]">
                  所有方向已隐藏
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {editable && hiddenCount > 0 && (
        <p className="mt-2 text-xs text-[var(--color-muted)]">
          {hiddenCount} 行已隐藏 ·{" "}
          <button
            type="button"
            onClick={() => void handleReset()}
            disabled={busy}
            className="text-[var(--color-accent)] hover:underline disabled:opacity-50"
          >
            还原
          </button>
        </p>
      )}
      {editable && (
        <p className="mt-1 text-[11px] text-[var(--color-muted)]">
          行可拖拽重排 · 点 ✕ 隐藏不感兴趣的方向 · 点 📝 加备注（用户观察）· 操作记录到 data/matrix_feedback.yaml 供 Agent 学习
        </p>
      )}
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
