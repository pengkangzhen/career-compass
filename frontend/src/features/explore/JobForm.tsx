import { useState } from "react";
import { api } from "../../api/client";
import type { SavedJobItem, SavedJobStatus } from "../../api/types";
import { Button, Input, Textarea } from "../../components/ui";

const DEFAULT_SOURCE = "手动添加";

export const JOB_STATUSES = [
  { value: "interested", label: "interested · 刚收藏" },
  { value: "researching", label: "researching · 调研中" },
  { value: "ready", label: "ready · 准备投递" },
  { value: "applied", label: "applied · 已投递" },
  { value: "archived", label: "archived · 归档" },
] as const;

export type JobFormProps =
  | {
      mode: "create";
      onSubmit: () => Promise<void> | void;
      onCancel: () => void;
    }
  | {
      mode: "edit";
      initial: SavedJobItem;
      onSubmit: () => Promise<void> | void;
      onCancel: () => void;
    };

export function JobForm(props: JobFormProps) {
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

  const reset = () => {
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
  };

  const handleFile = async (file: File | null) => {
    if (!file) return;
    setFileName(file.name);
    try {
      const text = await file.text();
      setDescription(text);
    } catch {
      setError("无法读取该文件，请改用纯文本 (.txt / .md)");
    }
  };

  const canSubmit =
    !busy &&
    company.trim().length > 0 &&
    role.trim().length > 0 &&
    description.trim().length > 0;

  const handleSubmit = async () => {
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
          status: status as SavedJobStatus,
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
  };

  // Collapsed (closed) state for create mode — render an inline "+ 新增岗位" trigger.
  if (mode === "create" && !open) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-[var(--color-muted)]">
          心仪的 JD 可直接粘贴或上传文件，存入「岗位收藏」供北斗星分析
        </p>
        <Button size="sm" onClick={() => setOpen(true)}>
          + 新增岗位
        </Button>
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
        <Input
          label="公司 *"
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          placeholder="例如：字节跳动"
          disabled={busy}
        />
        <Input
          label="岗位 *"
          value={role}
          onChange={(e) => setRole(e.target.value)}
          placeholder="例如：算法工程师"
          disabled={busy}
        />
        <Input
          label="地点"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="例如：北京 / 远程"
          disabled={busy}
        />
        <Input
          label="来源"
          value={source}
          onChange={(e) => setSource(e.target.value)}
          placeholder="招聘软件 / 官网 / 内推"
          disabled={busy}
        />
        <Input
          label="关联方向（可选）"
          value={linkedDirection}
          onChange={(e) => setLinkedDirection(e.target.value)}
          placeholder="对应机会矩阵 direction"
          disabled={busy}
        />
        <Input
          label="备注（可选）"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
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
        <Textarea
          label={
            <>
              JD 全文 *{" "}
              <span className="font-normal">
                （粘贴文本或上传 .txt / .md / .json）
              </span>
            </>
          }
          labelAccessory={
            <span className="text-[11px] text-[var(--color-muted)]">
              {description.length} 字
            </span>
          }
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          disabled={busy}
          placeholder="粘贴 JD 全文（招聘要求、岗位职责、技能清单…）"
          rows={6}
          className="font-mono text-xs leading-relaxed"
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
        <Button
          variant="secondary"
          size="sm"
          loading={busy}
          onClick={() => {
            if (mode === "create") {
              reset();
              setOpen(false);
            }
            onCancel();
          }}
        >
          取消
        </Button>
        <Button
          size="sm"
          disabled={!canSubmit}
          loading={busy}
          onClick={() => void handleSubmit()}
        >
          {busy ? "保存中…" : submitLabel}
        </Button>
      </div>
    </div>
  );
}
