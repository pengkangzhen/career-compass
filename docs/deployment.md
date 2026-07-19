# 北斗星 SaaS 部署手册

本指南把北斗星部署到 **Render（后端）+ Neon（Postgres）+ Vercel（前端）**，让任何朋友拿到一个 HTTPS URL 就能注册使用。

**全程预计 20-30 分钟**（不含 Neon / Render / Vercel 各自的注册时间）。

## 架构总览

```
┌─────────────────────────────────────────────────────┐
│ Vercel — 前端 React SPA                            │
│   URL: https://<your-app>.vercel.app               │
└─────────────────────────────────────────────────────┘
                       ↓ HTTPS fetch /api/*
┌─────────────────────────────────────────────────────┐
│ Render — FastAPI 后端                               │
│   URL: https://<your-api>.onrender.com             │
└─────────────────────────────────────────────────────┘
                       ↓ SQLAlchemy async
┌─────────────────────────────────────────────────────┐
│ Neon — Postgres 16                                  │
│   DATABASE_URL: postgresql+psycopg://...           │
└─────────────────────────────────────────────────────┘
```

**为什么选这三家**：免费档都够个人项目用，免备案，自动 HTTPS，自动从 GitHub 重新部署。

## 前置条件

- 一个 GitHub 账号（已有，仓库 `pengkangzhen/career-compass`）
- 一组 LLM API key（至少 `ANTHROPIC_API_KEY` 或 `OPENAI_API_KEY`）—— 用作 intake chat 的引擎
- 浏览器（Chrome / Edge / Safari 都行）

---

## 步骤 1：先把改动 push 到 GitHub

本地仓库已有所有 M3 改动（schema、Repository、router 切换、迁移脚本、render.yaml、vite 配置、CORS）。先 commit 并 push 到 `main`。

```bash
git add -A
git commit -m "M3: per-user data layer in Postgres + SaaS deployment configs

- New SQLAlchemy models (profile/constraints/narrative/saved_job/
  opportunity_matrix/matrix_feedback_action/chat_message/chat_session_state/
  projects) + Alembic migration 0002.
- New Repository class with tmpdir round-trip strategy — keeps every
  existing file-based view builder (build_all_views / IntakeEngine /
  pipeline / render) unchanged; syncs DB state to a per-request tmpdir
  on entry, upserts changes back on exit.
- routers/data.py swapped from AppApi(file) to Repository(DB); all 10
  endpoints now run against Postgres with user isolation.
- scripts/migrate_files_to_db.py — idempotent one-shot importer.
- render.yaml + frontend vite API_BASE + CORS_ALLOW_ORIGINS env support
  for production deployment.

195/195 tests passing."

git push origin main
```

---

## 步骤 2：在 Neon 创建 Postgres 数据库

1. 打开 https://neon.tech → Sign up with **GitHub**（最快）
2. 登录后点 **New Project** → 命名为 `beidou` → Region 选 **Singapore**（亚洲最近）→ 点 Create
3. Project 创建完成后，找到 **Connection Details** 区域
4. 复制 **Connection string**，形如：
   ```
   postgresql://user:password@ep-xxx.sg-region.aws.neon.tech/beidou?sslmode=require
   ```
5. **改成 SQLAlchemy 用的格式**（加 `+psycopg` 后缀）：
   ```
   postgresql+psycopg://user:password@ep-xxx.sg-region.aws.neon.tech/beidou?sslmode=require
   ```
6. 把这个 URL 记下来 —— 后面 Render 要用

> Neon 免费档：0.5 GB 存储 / 100 计算小时/月，对早期 SaaS 足够。

---

## 步骤 3：在 Render 部署后端

1. 打开 https://render.com → Sign up with **GitHub**
2. 点 **New +** → **Blueprint** → 选你的 `career-compass` 仓库
3. Render 会自动识别 `render.yaml`，看到 `beidou-api` 服务
4. 点 **Apply** 进入配置页
5. 在 **Environment** 标签下逐个填入以下变量（标记为 `sync: false` 的）：

   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | 步骤 2 拿到的 `postgresql+psycopg://...?sslmode=require` |
   | `SECRET_KEY` | 终端跑 `openssl rand -hex 32` 生成 |
   | `ANTHROPIC_API_KEY` | 你的 Anthropic key（或留空，但 chat 会不可用） |
   | `OPENAI_API_KEY` | 你的 OpenAI key（可选） |
   | `LLM_PROVIDER` | `anthropic` 或 `openai` |
   | `CORS_ALLOW_ORIGINS` | 步骤 5 拿到 Vercel URL 后回填，**先留空** |

6. 点 **Create Web Service**，等首次部署（约 3-5 分钟，会装依赖 + 跑 `alembic upgrade head` + 启 uvicorn）
7. 部署完成后，访问 `https://<your-api>.onrender.com/api/health`，应该看到：
   ```json
   {"ok": true, "db": "up"}
   ```

> Render 免费档：Web Service 15 分钟无请求会自动休眠，首次唤醒有 30-60s 冷启动延迟。生产级用 Starter（$7/月）。

---

## 步骤 4：在 Vercel 部署前端

1. 打开 https://vercel.com → Sign up with **GitHub**
2. 点 **Add New...** → **Project** → 选 `career-compass` 仓库
3. 配置：
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`（**重要**！点 Edit 选 frontend 子目录）
   - **Build Command**: `npm run build`（默认即可）
   - **Output Directory**: `dist`（默认即可）
4. 展开 **Environment Variables**，添加：
   - Name: `VITE_API_BASE`  
     Value: `https://<your-api>.onrender.com`（步骤 3 的 Render URL，**不要带尾部 `/`**）
5. 点 **Deploy**，等 1-2 分钟构建完成
6. 拿到 `https://<your-app>.vercel.app`

---

## 步骤 5：把 Vercel 域名加进 CORS 白名单

回到 Render 控制台：

1. 打开 `beidou-api` 服务的 **Environment** 标签
2. 编辑 `CORS_ALLOW_ORIGINS` → 填入 `https://<your-app>.vercel.app`（**不要带尾部 `/`**）
3. 保存 → Render 自动重新部署（约 1 分钟）

---

## 步骤 6：验收

1. 浏览器打开 `https://<your-app>.vercel.app`
2. 点 **注册** → 输入邮箱密码 → 应该跳到登录页
3. 登录 → 应该看到 Beidou 主界面（Journey Bar + 空 views）
4. 在「对话」Tab 发条消息 → 如果配了 LLM key，会收到 AI 回复；profile 自动入库
5. 在「岗位收藏」加一条 JD → 刷新页面，应该还在
6. **重启 Render 服务**（手动 trigger redeploy）后再登录 → 数据应该还在（DB 持久化验证）

---

## 常见问题

### Q: 注册后 401 / load_all 401
检查浏览器 devtools Network 面板：登录请求是否成功？token 是否写到 localStorage？

### Q: chat_send 报 500
LLM key 没配。Render 控制台 → Environment → 设置 `ANTHROPIC_API_KEY` 或 `OPENAI_API_KEY`，再 redeploy。

### Q: 浏览器报 CORS 错误
`CORS_ALLOW_ORIGINS` 没设或拼错。检查 Render Environment，必须严格匹配 Vercel URL（含 `https://`，无尾部 `/`）。

### Q: Render 服务冷启动慢
免费档会休眠。要么忍受 30-60s 唤醒，要么升级 Starter。

### Q: 国内访问慢
Render / Vercel / Neon 都在境外。早期忍受，后续 M6 接 Cloudflare CDN 或迁国内云备案。

### Q: 想换域名
Vercel 设置 → Domains → 添加自定义域名（你需要拥有该域名并配 DNS）。

---

## 撤销 / 重置

- **删除 Neon 数据库**：Neon 控制台 → Project → Settings → Delete
- **删除 Render 服务**：Render 控制台 → 服务 → Settings → Delete
- **删除 Vercel 项目**：Vercel 控制台 → Project → Settings → Delete

三个都删干净后，没有残留费用（免费档本来也没有）。
