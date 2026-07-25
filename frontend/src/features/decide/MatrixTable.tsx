import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../../api/client";
import type { MatrixRow } from "../../api/types";
import { IconButton, Section } from "../../components/ui";

type Props = {
  title: string;
  rows: MatrixRow[];
  hidden: string[];
  orderOverrides: string[];
  notes: Record<string, string>;
  editable: boolean;
  onRefresh?: () => Promise<void> | void;
  onAddNote?: (direction: string, text: string) => Promise<void> | void;
};

export function MatrixTable({
  title,
  rows,
  hidden,
  orderOverrides,
  notes,
  editable,
  onRefresh,
  onAddNote,
}: Props) {
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
                        <IconButton
                          tone="accent"
                          title={note ? "编辑备注" : "添加备注"}
                          disabled={busy || !direction}
                          onClick={() => direction && startEditNote(direction)}
                        >
                          📝
                        </IconButton>
                        <IconButton
                          tone="danger"
                          className="ml-1"
                          title={direction ? `隐藏「${direction}」` : "无可识别方向"}
                          disabled={busy || !direction}
                          onClick={() => direction && void handleRemove(direction)}
                        >
                          ✕
                        </IconButton>
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
