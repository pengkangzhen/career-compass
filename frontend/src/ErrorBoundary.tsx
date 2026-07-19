import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = { children: ReactNode };
type State = { error: Error | null };

/**
 * 捕获子树渲染期抛出的错误。
 *
 * 为什么需要它:React 18+ 在渲染期间抛出且无祖先 ErrorBoundary 时,
 * 会**卸载整个根节点**——表现就是 `<div id="root">` 被清空、页面白屏,
 * 而且错误只走 `console.error`，不触发 `window.onerror`，所以全局错误
 * 监听也抓不到。包一层 ErrorBoundary 后，渲染错误会落到这里的兜底
 * UI，而不是让整个 SPA 消失。
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[ErrorBoundary]", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 24, color: "#f0a030", fontFamily: "monospace" }}>
          <h2 style={{ margin: "0 0 12px", fontSize: 16 }}>渲染出错</h2>
          <p style={{ margin: "0 0 12px", wordBreak: "break-word" }}>
            {this.state.error.message}
          </p>
          <pre
            style={{
              margin: 0,
              padding: 12,
              background: "rgba(255,255,255,0.06)",
              borderRadius: 8,
              overflow: "auto",
              fontSize: 12,
              whiteSpace: "pre-wrap",
            }}
          >
            {this.state.error.stack}
          </pre>
          <button
            type="button"
            onClick={() => this.setState({ error: null })}
            style={{
              marginTop: 12,
              padding: "6px 12px",
              background: "#4f8cff",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              cursor: "pointer",
            }}
          >
            重试
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
