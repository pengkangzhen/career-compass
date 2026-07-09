"""浏览器模式 API shim — WSL / 无 GTK 时用 http://localhost 访问。"""

WEB_API_SHIM = """
(function () {
  if (window.pywebview && window.pywebview.api) return;
  const httpApi = {
    load_all: () => fetch('/api/load_all').then(r => r.json()),
    chat_state: () => fetch('/api/chat_state').then(r => r.json()),
    chat_send: (message) => fetch('/api/chat_send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    }).then(r => r.json()),
    chat_reset: () => fetch('/api/chat_reset', { method: 'POST' }).then(r => r.json()),
    run_command: (cmd) => fetch('/api/run_command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cmd }),
    }).then(r => r.json()),
  };
  window.pywebview = { api: httpApi };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      window.dispatchEvent(new Event('pywebviewready'));
    });
  } else {
    setTimeout(() => window.dispatchEvent(new Event('pywebviewready')), 0);
  }
})();
"""


def inject_web_shim(html: str) -> str:
    marker = "<script>"
    if marker not in html:
        return html
    return html.replace(marker, f"<script>\n{WEB_API_SHIM}\n", 1)
