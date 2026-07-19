# 交接文档 · 登录后白屏 Bug

> 状态: **✅ 已解决** · 2026-07-19 修复（根因与修复见 [§0](#0--已解决2026-07-19)）  
> 严重度: **P0**（SaaS 化 M1 里程碑验收被阻塞）  
> 创建时间: 2026-07-19 13:20 (UTC+8)  
> 项目: career-compass / 北斗星  
> 仓库: `/home/pengkangzhen/projects/products/career-compass`

## 给接手 AI 的话

这是一个 React 19 SPA 在 Vite dev server 下偶发的「整个 React 根 unmount」白屏 bug。我已经定位到根因的边界（不是组件错误，是 Vite HMR 状态污染），但**没能在会话内彻底修复**。本文件列出所有已做的调查 + 证据 + 复现步骤 + 下一步建议。

**请先完整读完本文件再动手**，避免重复劳动。文档生成时所在分支为默认工作分支（`git status` 自查）。

> ⚠️ 以下 §1–§9 是上一手 AI 的交接调查记录，保留作参考。它的根因假设 A/B/C/D 经验证**均非真正根因** —— 真正根因与修复见下面的 §0，不必再追那些方向。

---

## 0. ✅ 已解决（2026-07-19）

### 真正根因（前端 API 层，与 Vite HMR / StrictMode / AuthProvider 无关）

SaaS 后端只注册了 `/api/auth/*` 和 `/api/health`（见 [src/career_compass/web/app.py](src/career_compass/web/app.py#L39-L40)），**没有 `/api/load_all`**。curl 确认：

```
$ curl -s -w '\nHTTP:%{http_code}' http://127.0.0.1:8000/api/load_all
{"detail":"Not Found"}
HTTP:404
```

但旧版 `api.loadAll` 写成 `fetch(url).then(r => r.json())` —— **没检查 `r.ok`**，于是 404 响应被当成成功的 `AppData` 静默 `setData({"detail":"Not Found"})`。`MainApp` 重新渲染时绕过 `!data` 和 `loadError && !data` 两个守卫，在 [MainApp.tsx:134](frontend/src/MainApp.tsx#L134) `data.journey.steps` 上抛 `TypeError`（`data.journey` 是 `undefined`）。React 19 在渲染期抛错且**无祖先 ErrorBoundary** 时的默认行为是**卸载整个 root** —— 这就是 `<div id="root">` 全空、且 `window.onerror` 抓不到错误的真正原因（React 走 `console.error`，不触发全局 error 事件）。`api.chatState` / `api.matrixFeedback` 有同样的裸 `.then(r => r.json())` 缺陷。

### 修复（4 处）

| 文件 | 改动 |
|---|---|
| [frontend/src/api/types.ts](frontend/src/api/types.ts) | 新增 `getJson()` helper 检查 `r.ok`、失败抛 `ApiError`；`loadAll` / `chatState` / `matrixFeedback` 三个原本裸 `.then(r => r.json())` 的 GET 方法改用它 —— 404 现在会正确抛错，`MainApp.refresh` 的 catch 触发，显示「数据层暂未就绪」而非白屏 |
| [frontend/src/components/ChatPanel.tsx](frontend/src/components/ChatPanel.tsx) | `load()` 加 try/catch + `loadError` 状态；`chat_state` 未实现时降级提示而非崩溃 |
| [frontend/src/ErrorBoundary.tsx](frontend/src/ErrorBoundary.tsx) | 新建。渲染错误兜底页，防止未来任何渲染崩溃再导致全树白屏（也就是本 handoff §6 步骤 2） |
| [frontend/src/main.tsx](frontend/src/main.tsx) | 在 `<StrictMode>` 外包一层 `<ErrorBoundary>` |

### 验证

- `npm run build` 通过（tsc + vite，306 模块，无错）
- curl 坐实根因：`/api/load_all` → `HTTP 404 {"detail":"Not Found"}`
- 离线逻辑对照：旧 `loadAll` 对 404 静默返回 `{detail:...}`（`journey` 为 `undefined`，后续 `.steps` 必抛 `TypeError`）；新 `getJson` 抛 `HTTP 404`
- 浏览器端到端（**用户实测确认 ✅**）：硬刷新 5173 后登录，页面显示「数据层暂未就绪」橙色提示，`<div id="root">` 正常挂载，白屏消除。ErrorBoundary 未触发（符合预期 —— 走的是 `MainApp` 的 `loadError` 正常降级分支，非渲染崩溃）

### 后续（非本 bug 范围，记录给 M2）

真正修好体验需要实现 `/api/load_all` / `/api/chat_state` 等数据层接口（M2/M3 里程碑）。在那之前，登录后页面会停在「数据层暂未就绪」提示 —— 这是预期行为，不再是白屏。

---

## 1. 现象

**用户报错**：浏览器访问 `http://127.0.0.1:5173/`，输入邮箱密码点登录后，页面变为「纯色无内容、无响应」。

**前端代码栈**：
- React 19.1.0 + react-dom 19.1.0 + react-router-dom 7.9.4
- Vite 7.0.4 + `@vitejs/plugin-react`
- 入口: `frontend/src/main.tsx` → `<AuthProvider><App /></AuthProvider>` 包在 `<StrictMode>` 里
- `App.tsx` 用 `<BrowserRouter>` 配 3 条路由：`/login`、`/register`、`/`（受保护，渲染 `<MainApp>`）

---

## 2. 已经确认的事实（证据 + 命令）

### 2.1 后端没问题

```bash
$ curl -s http://127.0.0.1:8000/api/health
{"ok":true,"db":"up"}

$ curl -X POST http://127.0.0.1:8000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"full-test@beidou.dev","password":"test-12345"}'
{"access_token":"...","refresh_token":"...","token_type":"bearer"}  # HTTP 200
```

注册、登录、`/me`、refresh、logout 全部 200，token 字段齐全。

### 2.2 Vite dev server 没问题

```bash
$ curl -s http://127.0.0.1:5173/ | grep -E "main.tsx|root"
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>

$ curl -s http://127.0.0.1:5173/src/main.tsx | head -5
# 返回编译过的 JS，包含 createRoot(...).render(...)，无语法错误
```

Vite 启动日志 `ready in 127ms`，无报错。

### 2.3 浏览器实际状态（CDP `Runtime.evaluate` 结果）

| 检查 | 结果 |
|---|---|
| `localStorage` 是否有旧 token | ✅ 有 `beidou.access_token` + `beidou.refresh_token` |
| `document.querySelectorAll('script')` | ✅ 3 个 module script 全加载（含 `/src/main.tsx`） |
| `import('/src/main.tsx')` 是否报错 | ❌ **成功**（不抛错） |
| `window.onerror` / `unhandledrejection` | ❌ **null**（无错误被捕获） |
| `<div id="root">` 的 `childElementCount` | ❌ **0**（React 没 render 进去任何东西） |
| `document.body.innerText` | **空字符串** |
| 之前一次 Chrome tab 直接进了 `chrome-error://chromewebdata/` | 进程级崩溃一次 |

### 2.4 关键矛盾

- `main.tsx` **被加载成功**（3 个 script 都在）
- `import('/src/main.tsx')` **不抛错**
- 全局 error / unhandledrejection listener **没收到任何东西**
- 但 `<div id="root">` **完全是空的**

也就是说：`createRoot(...).render(<App />)` 这一句**执行了**，但 React 没把任何 DOM 节点挂到 root。

---

## 3. 根因推断（按可能性排序）

### 假设 A（最可能）: Vite HMR 状态污染 + React 19 StrictMode 双调用

观察到的间接证据：
- Vite 日志多次出现 `vite.config.ts changed, restarting server...` 和 `server restarted`，即使我没改 vite.config.ts
- `node_modules/.vite/deps/` 缓存被清掉重启后**问题依然存在**
- 浏览器曾经出现 `chrome-error://chromewebdata/src/App.tsx`（Chrome 把模块加载失败缓存成了内部错误页）

排查方向：
- 检查 `@vitejs/plugin-react` 与 React 19 的兼容性（plugin 4.6 + react-refresh 内部 hook 注入是否与 React 19 StrictMode dev-only 双调用冲突）
- 把 `<StrictMode>` 暂时去掉看是否还白屏
- 用 `npm run build` 产物（不经 Vite dev server）+ `npx serve dist` 部署，看是否还白屏 —— 如果不白屏，问题就在 Vite dev pipeline

### 假设 B: AuthProvider 死循环导致 React 调度卡死

`AuthProvider` 的 mount-time `useEffect` 逻辑（见 `frontend/src/auth/AuthProvider.tsx:42-61`）：

```tsx
useEffect(() => {
  (async () => {
    const tokens = loadTokens();
    if (!tokens) { setLoading(false); return; }
    try {
      const me = await fetchMe();  // 这里可能进入 fetchWithAuth 的 401→refresh→retry 循环
      setUser(me);
    } finally {
      setLoading(false);
    }
  })();
}, []);
```

如果 localStorage 里的 token 已过期，`fetchMe` 会触发 `fetchWithAuth` 的 401 → `attemptRefresh` → retry。`fetchWithAuth` 当前实现没有死循环（`attemptRefresh` 失败就 `clearTokens`），但**成功 refresh 后的 retry 可能触发新的 401**。

排查方向：
- 在浏览器 console 里 `localStorage.clear()` 然后刷新，看是否还白屏
- 在 `AuthProvider.useEffect` 第一行加 `console.log("AuthProvider mount")`，看 console 是否打出

### 假设 C: MainApp 加载错误被 React 19 静默吞掉

`MainApp.tsx` 的 `useEffect` 调 `api.loadAll()`，新后端没这个接口返回 404，`r.json()` 在 HTML 错误页上会抛 `SyntaxError`。我已经加了 try/catch + `loadError` 状态兜底，但可能没覆盖到所有路径。

排查方向：
- 在 `MainApp.tsx` 整个组件最外层包一个 ErrorBoundary（React 19 没有 default ErrorBoundary，需要自写或用 `react-error-boundary`）
- 在 `refresh()` 的 catch 里 `console.error` 看是否真有错被吞

### 假设 D（可能性低）: react-router-dom 7 + React 19 + Vite 7 三方兼容问题

`react-router-dom ^7.9.4` 是新加的依赖。React Router 7 在某些场景下和 Vite 7 的 ESM 解析有兼容问题。

排查方向：
- 临时把路由简化成不渲染任何 `<Route>`，看 root 是否还空
- 检查 `npm ls react react-dom`，确认没有重复 React 实例

---

## 4. 复现步骤（关键，请严格照做）

### 4.1 环境

```bash
cd /home/pengkangzhen/projects/products/career-compass

# 后端（FastAPI + sqlite，无需 Docker）
DATABASE_URL="sqlite+aiosqlite:///./dev.db" \
CC_CREATE_TABLES_ON_STARTUP=1 \
SECRET_KEY=$(openssl rand -hex 32) \
uv run uvicorn career_compass.web.main:app --host 127.0.0.1 --port 8000 &

# 前端（Vite dev server）
cd frontend && npm run dev &
```

两个 server 都起来后：
- 8000 → 后端 health 返回 200
- 5173 → 前端 HTML 返回 200

### 4.2 在全新浏览器实例里复现

**关键**：用**全新**的浏览器 profile（隐身模式 / `--user-data-dir=/tmp/foo`），不要用已有 tab —— 之前 tab 的 chrome-error 状态会干扰。

```bash
# 启动一个干净的 Chrome 实例（仅调试用）
google-chrome --user-data-dir=/tmp/cc-debug --remote-debugging-port=9222 http://127.0.0.1:5173/
```

### 4.3 操作序列

1. 访问 `http://127.0.0.1:5173/register`，注册一个账号（任意邮箱密码 ≥8 位）
2. 注册成功跳到 `/login?registered=1`
3. 输入邮箱密码点登录
4. **观察**：是否白屏

### 4.4 关键诊断命令（带 token 复现）

如果想跳过登录表单直接复现「已登录状态」：

```javascript
// 在浏览器 console 里执行
localStorage.setItem('beidou.access_token', '<从 curl 拿到的 access_token>');
localStorage.setItem('beidou.refresh_token', '<从 curl 拿到的 refresh_token>');
location.href = '/';
```

---

## 5. 已经尝试过的修复（都**没**解决问题）

| 尝试 | 文件 | 结论 |
|---|---|---|
| 给 `MainApp.refresh` 加 try/catch + `loadError` 状态 | `frontend/src/MainApp.tsx` | 改动保留，但**问题不是这里**（root 是空的，根本没渲染到 MainApp） |
| 清掉 Vite 缓存 `rm -rf node_modules/.vite` + 重启 | — | 无效 |
| 关闭浏览器所有旧 tab 重开 | — | 无效 |
| 检查 `vite.config.ts` 的 server.proxy 配置 | `frontend/vite.config.ts` | 配置正常 |

---

## 6. 接手建议（按顺序执行）

### 步骤 1: 用生产 build 排除 Vite dev 干扰

```bash
cd /home/pengkangzhen/projects/products/career-compass/frontend
npm run build
# dist 在 ../src/career_compass/gui/static/dist/
# 用 Python 内置 server 或 npx serve 起一个静态服务器
cd ../src/career_compass/gui/static/dist
python3 -m http.server 5500
```

然后浏览器访问 `http://127.0.0.1:5500/`。

**如果白屏消失** → 问题在 Vite dev pipeline（假设 A），可以临时改用 build + serve 模式开发。

**如果还白屏** → 问题在代码或运行时（假设 B/C/D），继续。

### 步骤 2: 加 React ErrorBoundary

新建 `frontend/src/ErrorBoundary.tsx`：

```tsx
import { Component, type ReactNode } from "react";

export class ErrorBoundary extends Component<
  { children: ReactNode },
  { error: Error | null }
> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  componentDidCatch(error: Error, info: { componentStack: string }) {
    console.error("[ErrorBoundary]", error, info);
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 20, color: "red" }}>
          <h2>渲染错误</h2>
          <pre>{this.state.error.message}</pre>
          <pre>{this.state.error.stack}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}
```

在 `main.tsx` 包一层：

```tsx
createRoot(document.getElementById("root")!).render(
  <ErrorBoundary>
    <StrictMode>
      <AuthProvider>
        <App />
      </AuthProvider>
    </StrictMode>
  </ErrorBoundary>
);
```

如果白屏变成红色错误页 → 拿到真实错误堆栈，根据堆栈定位。

### 步骤 3: 把 `<StrictMode>` 暂时去掉

```tsx
// main.tsx
createRoot(document.getElementById("root")!).render(
  <AuthProvider><App /></AuthProvider>
);
```

如果不白屏 → 假设 A（React 19 StrictMode dev-only 双调用 + Vite HMR 兼容问题）。

### 步骤 4: 把 `AuthProvider` 的 mount effect 临时禁用

```tsx
// AuthProvider.tsx
useEffect(() => {
  setLoading(false);  // 直接跳过 token 检查
  return;
}, []);
```

如果不白屏 → 假设 B（AuthProvider 的 fetchMe / fetchWithAuth 路径有问题）。

### 步骤 5: 检查依赖版本

```bash
cd frontend
npm ls react react-dom react-router-dom vite @vitejs/plugin-react
# 看是否有版本冲突 / 重复实例
```

### 步骤 6: 看 Chrome devtools Console（**必做**）

打开 F12 → Console，刷新页面，看**所有**红色错误（包括 dev-only warnings）。把完整错误堆栈贴出来 —— 我之前用 CDP 没抓到错误，但 devtools UI 可能更全。

---

## 7. 关键文件清单

| 路径 | 用途 |
|---|---|
| `frontend/src/main.tsx` | React 入口 |
| `frontend/src/App.tsx` | BrowserRouter 路由定义 |
| `frontend/src/MainApp.tsx` | 主应用（受保护，登录后渲染） |
| `frontend/src/auth/AuthProvider.tsx` | 用户上下文 + mount-time token 检查 |
| `frontend/src/auth/ProtectedRoute.tsx` | 路由保护（未登录跳 `/login`） |
| `frontend/src/auth/UserMenu.tsx` | 顶部用户菜单 |
| `frontend/src/auth/fetchWithAuth.ts` | fetch 包装 + 401→refresh→retry |
| `frontend/src/auth/tokens.ts` | localStorage token 读写 |
| `frontend/src/pages/LoginPage.tsx` | 登录页 |
| `frontend/src/pages/RegisterPage.tsx` | 注册页 |
| `frontend/vite.config.ts` | Vite 配置 + `/api` 代理到 8000 |
| `frontend/package.json` | 依赖 |
| `src/career_compass/web/main.py` | FastAPI 入口 |
| `src/career_compass/web/auth.py` | JWT 策略 |
| `src/career_compass/web/routers/users.py` | `/api/auth/*` 路由 |

---

## 8. 已知背景（不必重新查）

- **这是 SaaS 化迁移 M1 里程碑的验收阻塞 bug**。M1 = 数据库 + 用户系统，已完成的后端 / 前端代码见上表
- **后端 + 注册 API 完全正常**（curl 全 200）
- **前端 build 通过**（`tsc -b && vite build` 无错）
- **所有 lint 干净**
- **数据层 `/api/load_all` 在新后端没实现**（属于 M2/M3），会 404 —— 我已经在 `MainApp` 加了 try/catch 兜底
- **当前后端用 sqlite**（`./dev.db`），未来要切 Postgres（`docker compose up -d postgres redis`）
- **设计文档**在 `docs/saas-migration-plan.md`
- **旧桌面 Python server**（端口 8765）已停，不要再启动它来「对比测试」—— 它和新前端路由冲突

---

## 9. 联系信息

- 仓库本地路径: `/home/pengkangzhen/projects/products/career-compass`
- 上一手 AI 会话: 已结束（这是 handoff 文档）
- 创建本文件时 git 状态: `git status` 自查，所有 M1 改动尚未 commit

---

## 10. 接手后的第一句回应建议

> 「我已经读完交接文档。我打算先执行步骤 1（生产 build 排除 Vite dev 干扰），如果还白屏就执行步骤 2（加 ErrorBoundary 抓真实错误）。预计 5-10 分钟内有结论。」
