import { useEffect, useRef, useState } from "react";
import { api, type ChatState } from "../api/types";

type Props = {
  onRefresh: () => Promise<void | unknown>;
  onIntakeComplete: () => void;
};

export function ChatPanel({ onRefresh, onIntakeComplete }: Props) {
  const [state, setState] = useState<ChatState | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [toast, setToast] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const load = async () => {
    try {
      const s = await api.chatState();
      setState(s);
      setLoadError(null);
    } catch (e) {
      // SaaS 迁移期:/api/chat_state 在新后端尚未实现 (M2 范围)。
      // 不能让组件渲染时崩溃 —— 记录到 loadError 让 UI 降级提示。
      console.error("[ChatPanel] load chat_state failed:", e);
      setLoadError(e instanceof Error ? e.message : "未知错误");
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [state?.messages.length, sending]);

  const send = async (text: string) => {
    const msg = text.trim();
    if (!msg || sending) return;
    setSending(true);
    setInput("");
    setState((prev) =>
      prev
        ? {
            ...prev,
            messages: [...prev.messages, { role: "user", content: msg }],
          }
        : prev,
    );
    try {
      const res = await api.chatSend(msg);
      setState(res);
      await onRefresh();
      if (res.files_updated?.length) {
        setToast(`已更新: ${res.files_updated.join(", ")}`);
      }
      if (res.just_completed) {
        setToast("🎉 「认识自己」已完成！");
        onIntakeComplete();
      }
    } catch (e) {
      setToast(`发送失败: ${e}`);
    } finally {
      setSending(false);
      setTimeout(() => setToast(""), 4000);
    }
  };

  if (!state) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center">
        {loadError ? (
          <>
            <p className="text-sm font-semibold text-[var(--color-warn)]">
              对话加载失败
            </p>
            <p className="max-w-md text-xs text-[var(--color-muted)]">
              {loadError}（SaaS 化迁移中，M2 里程碑会实现此接口）
            </p>
          </>
        ) : (
          <p className="text-[var(--color-muted)]">加载对话…</p>
        )}
      </div>
    );
  }

  const preview = state.profile_preview;
  const llm = state.llm;

  return (
    <div className="flex h-full min-h-0 gap-4">
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex-1 space-y-3 overflow-y-auto rounded-xl border border-[var(--color-border)] bg-black/20 p-4">
          {state.messages.map((m, i) => (
            <div
              key={i}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                  m.role === "user"
                    ? "rounded-br-md bg-[var(--color-accent)] text-white"
                    : "rounded-bl-md border border-[var(--color-border)] bg-[var(--color-surface-2)]"
                }`}
              >
                {m.content}
              </div>
            </div>
          ))}
          {sending && (
            <div className="text-sm text-[var(--color-muted)]">思考中…</div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="mt-3 flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(input);
              }
            }}
            rows={2}
            placeholder="随便聊聊你的背景、困惑或目标…"
            className="flex-1 resize-none rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2.5 text-sm outline-none focus:border-[var(--color-accent)]"
          />
          <button
            type="button"
            disabled={sending || !input.trim()}
            onClick={() => send(input)}
            className="self-end rounded-xl bg-[var(--color-accent)] px-5 py-2.5 text-sm font-medium text-white disabled:opacity-40"
          >
            发送
          </button>
        </div>
        {toast && (
          <p className="mt-2 text-xs text-[var(--color-accent-2)]">{toast}</p>
        )}
      </div>

      <aside className="hidden w-[280px] shrink-0 flex-col gap-3 overflow-y-auto lg:flex">
        <SideCard title="实时画像">
          {!preview.name && !preview.current_role && !preview.education.length ? (
            <p className="text-xs text-[var(--color-muted)]">尚无结构化信息，继续聊即可。</p>
          ) : (
            <>
              {preview.name && (
                <p className="font-semibold text-sm">{preview.name}</p>
              )}
              {preview.current_role && (
                <p className="text-xs text-[var(--color-muted)]">{preview.current_role}</p>
              )}
              {preview.core_skills.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {preview.core_skills.map((s) => (
                    <span
                      key={s}
                      className="rounded-md bg-[var(--color-accent)]/15 px-2 py-0.5 text-[11px] text-[var(--color-accent)]"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              )}
            </>
          )}
        </SideCard>

        <SideCard title={`完成度 ${state.progress.percent}%`}>
          <div className="mb-2 h-1.5 overflow-hidden rounded-full bg-[var(--color-border)]">
            <div
              className="h-full rounded-full bg-[var(--color-accent)] transition-all"
              style={{ width: `${state.progress.percent}%` }}
            />
          </div>
          <ul className="space-y-1 text-xs">
            {state.progress.checks.map((c) => (
              <li
                key={c.label}
                className={c.done ? "text-[var(--color-ok)]" : "text-[var(--color-muted)]"}
              >
                {c.done ? "✓ " : "○ "}
                {c.label}
              </li>
            ))}
          </ul>
        </SideCard>

        <SideCard title="认识自己">
          {state.intake_complete ? (
            <p className="text-xs text-[var(--color-ok)]">✅ 已完成，可进入「探索世界」</p>
          ) : state.validation.errors.length ? (
            <>
              <p className="text-xs">待补齐 {state.validation.errors.length} 项</p>
              <ul className="mt-1 space-y-0.5 text-[11px] text-[var(--color-muted)]">
                {state.validation.errors.slice(0, 5).map((e) => (
                  <li key={e}>· {e}</li>
                ))}
              </ul>
            </>
          ) : (
            <p className="text-xs text-[var(--color-muted)]">继续对话，完善对自己的认识</p>
          )}
        </SideCard>

        {state.gap_hints.length > 0 && (
          <SideCard title="建议追问">
            <div className="flex flex-col gap-1.5">
              {state.gap_hints.map((h) => (
                <button
                  key={h}
                  type="button"
                  onClick={() => setInput(h)}
                  className="rounded-lg border border-[var(--color-accent)]/25 bg-[var(--color-accent)]/10 px-2.5 py-2 text-left text-[11px] leading-snug hover:bg-[var(--color-accent)]/18"
                >
                  {h}
                </button>
              ))}
            </div>
          </SideCard>
        )}

        <SideCard title="LLM">
          <p
            className={`text-[11px] ${llm.configured ? "text-[var(--color-muted)]" : "text-[var(--color-warn)]"}`}
          >
            {llm.configured
              ? `${llm.provider} · ${llm.model}`
              : "未配置 LLM（CloudBase / Anthropic / OpenAI）"}
          </p>
        </SideCard>
      </aside>
    </div>
  );
}

function SideCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
      <h4 className="mb-2 text-xs font-semibold">{title}</h4>
      {children}
    </div>
  );
}

export async function resetChat(onRefresh: () => Promise<void | unknown>) {
  await api.chatReset();
  await onRefresh();
}
