import { useState } from "react";
import { api } from "../../api/client";
import type { SavedJobItem } from "../../api/types";
import { IconButton } from "../../components/ui";
import { JobForm } from "./JobForm";

export function JobCard({
  job,
  onRefresh,
}: {
  job: SavedJobItem;
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
            <IconButton tone="accent" title="编辑" onClick={() => setEditing(true)}>
              📝
            </IconButton>
            <IconButton
              tone="danger"
              title="删除"
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
            >
              ✕
            </IconButton>
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
