# 北斗星 SaaS 化迁移设计

> 状态: 草案 v1 · 等待用户确认后再动工
> 目标: 把单机桌面工具改造成多用户 web 产品
> 范围: 仅设计;本文件不含任何代码改动。批准后由分阶段 worker 任务实施。

---

## 1. 现状速览

北斗星 (`career-compass`) 目前是一个**单用户本地优先**的桌面 / CLI 工具:所有数据都以 YAML / Markdown / JSON 文件形式落在仓库根的 `data/` 目录里,通过 `CC_DATA` 环境变量切换数据目录。GUI 由 Python 标准库 `BaseHTTPRequestHandler` 起的本地 HTTP server 提供,前端是 Vite + React SPA (`frontend/`),经 `./scripts/build-frontend.sh` 构建到 `src/career_compass/gui/static/dist/` 后由同一 server 透出。LLM 调用通过 `.env` 里的 `CC_CLOUDBASE_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`,所有用户共享宿主机的同一份 key。整个仓库没有用户、鉴权、session、租户的概念 —— `data/` 是全局唯一事实源,`intake_session.json` 也是单文件。

| 层 | 当前实现 | 单机假设 | 多用户后必须改的点 |
|----|----------|----------|---------------------|
| 数据存储 | `data/*.yaml` + `data/signals/*.yaml` + `data/intake_session.json` (磁盘文件,见 `src/career_compass/schema.py`) | 一个 `data/` 目录 = 一个用户 | 引入 DB;按 `user_id` 隔离所有读写 |
| 数据访问层 | 直接 `load_profile(path)` / `save_opportunities(path, ...)`(`jobs.py`、`track.py`、`matrix_feedback.py`、`intake/writer.py`) | 调用方传 `Path` | 加 `user_id` 维度的 Repository 层;YAML 仅作为导入/导出格式 |
| HTTP server | `BaseHTTPRequestHandler` + `ThreadingHTTPServer`,`/api/*` 路由硬编码 (`src/career_compass/gui/web_server.py`) | `AppApi` 单例,`self.data_dir` 全局 | 加鉴权中间件;每个请求绑定 `user_id`;CORS / Cookie / CSRF |
| 业务编排 | `IntakeEngine`、`pipeline.detect_stage`、`render.brief` 等以 `data_dir: Path` 为输入 | 进程内单例 | 改为接收 `user_id`,内部按用户加载/持久化 |
| LLM 客户端 | `intake/llm.py::create_llm_client()` 读全局环境变量 | 全局共享一个 key | 改为按用户配置选择 key;配额/审计 |
| 前端 | React SPA,`fetch("/api/...")` 无任何 token (`frontend/src/api/types.ts`) | 本机 server 默认可信 | 加 `AuthProvider`、JWT 注入、登录页、路由保护 |
| CLI | `career-compass` 命令族,读写 `data/` | 本机直接跑 | 可保留为单机模式(开发/Agent Skill 用);SaaS 模式下退居导入/导出 + 后台任务 |
| 部署 | `./scripts/beidou.sh` 本机启动 | 一个进程 | 容器化 + 反向代理 + DB + 备份 |
| 配置/密钥 | `.env` 文件、`templates/llm.env.example` | 本机用户自己填 | 平台密钥放 secret manager;用户自带 key 加密入库 |

**已经具备的 SaaS-friendly 基础**:

- 数据契约清晰:Pydantic 模型在 `schema.py` 里集中定义,字段、校验、版本都齐全,迁表有现成的 source-of-truth。
- 前后端已经分离:SPA + JSON API,只要把 `/api/*` 路由迁到 FastAPI 并加鉴权,前端基本不动业务逻辑。
- LLM 调用已经抽象成 `LLMClient` Protocol,换实现/换 key 策略不需要改业务代码。
- intake / scan / analyze / execute / track 的 pipeline 阶段清晰,便于按用户隔离状态机。

---

## 2. 关键架构决策

下面每条都给**推荐方案 + 一句话理由 + 备选**。推荐方案默认"起步够用、未来可演进",不追求一步到位。

### 2.1 数据库选型

**推荐:PostgreSQL 16(单实例起步)**

理由:JSONB(存机会矩阵、matrix feedback 这类半结构化数据)、行级安全 (RLS) 可做租户隔离的兜底、生态成熟,迁移成本和 SQLite-per-user / MySQL 几乎一样,但天花板高得多。

备选:

- SQLite-per-user:零运维、天然隔离,但跨用户聚合(配额、运营报表)痛苦,备份和升级复杂;**仅适合纯单机离线模式**。
- MySQL 8:国内云厂商更熟悉,但 JSONB 与 RLS 弱于 Postgres。

### 2.2 认证方案

**推荐:FastAPI Users + JWT(access + refresh),邮箱+密码起步**

理由:FastAPI Users 自带注册/登录/邮箱验证/密码重置/JWT,与 FastAPI 原生集成,起步只装一个包;后续要加 OAuth (GitHub / Google / 微信扫码) 也只是 strategy 配置。

备选:

- Supabase Auth / Clerk / Auth0:BaaS,省事但锁定厂商、国内访问慢、定制化弱。
- 自研 JWT(不依赖 FastAPI Users):更可控但要自己写邮箱验证、刷新、撤销等一堆边角;**不推荐起步阶段**。
- 国内场景:后续可叠加短信验证码 / 微信扫码登录,作为 FastAPI Users 的额外 strategy。

### 2.3 部署形态

**推荐:Docker Compose 单机起步(Caddy + app + Postgres + Redis)**

理由:一台 2C4G 的 VPS 即可跑起全栈;Caddy 自动 HTTPS;后续用户量上来再迁 K8s / 多实例几乎无痛(已经是容器化部署)。

备选:

- Fly.io / Railway / Render:PaaS,免运维,但国内访问可能不稳。
- K8s:为时过早;SaaS 化早期产品价值大于规模化能力。

### 2.4 LLM key 策略

**推荐:平台统一 key + 配额(默认);用户可选自带 key(BYOK)**

理由:绝大多数用户不愿自己申请 key,平台统一 key 降低门槛;高级用户/企业用户可填自己的 key 绕开配额、用更强模型。两种模式共存是商业上最稳的方案。

具体设计:

- 平台 key 放在后端环境变量(secrets),用户无感。
- 用户自带 key:存 `user_settings.llm_provider` / `llm_api_key_encrypted`(Fernet 加密,见 §6)。
- 配额:每用户每天 LLM token 上限;超出则提示升级或填自己的 key。
- 默认继续走现有 `cloudbase` (`hy3-preview`) 网关;`anthropic` / `openai` 作为高级用户可选。

备选:

- 纯 BYOK:门槛太高,大多数用户第一公里就流失。
- 纯平台 key:成本不可控,且无法服务重度用户。

### 2.5 数据隔离模型

**推荐:行级隔离 (shared database, shared schema, `user_id` 列 + 索引)**

理由:单一 Postgres 库,所有用户表带 `user_id`,通过应用层 Repository 强制注入;起步成本最低,聚合查询/统计/迁移都简单。未来要做企业版再叠 Postgres RLS 兜底。

备选:

- schema-per-tenant:隔离强,但迁移/升级 N 倍复杂度;**适合中后期上企业版时启用**。
- database-per-user:同上,运维成本更高。

### 2.6 API 重构策略

**推荐:重写为 FastAPI(保留 BaseHTTPRequestHandler 作为单机/桌面 fallback)**

理由:现有 `BaseHTTPRequestHandler` 没有中间件 / 依赖注入 / OpenAPI,继续打补丁成本反而比换框架高;FastAPI 的 Pydantic 与项目现有 `schema.py` 模型直接复用,代码资产几乎不丢。CLI / Agent Skill 模式下保留 `web_server.py` 作为本地单机入口(`--local` flag),桌面 / Skill 用户不受影响。

备选:

- 渐进式:在 `BaseHTTPRequestHandler` 上加 middleware 层;**不推荐,中间件生态几乎为零**。

### 2.7 支付(可选)

**推荐:暂不做;后续国内场景用 Lemonsqueezy / Paddle(海外)或微信 + 支付Entry / Stripe(海外)**

理由:SaaS 化优先验证留存,付费层等有了付费意愿信号再上;一旦决定,Lemonsqueezy / Paddle 是海外最快路径(免发票/税务/PCI),国内可走微信扫码 + 自研订单表。

备选:Stripe(海外金标准)、商汤/有赞(国内 SaaS)。

### 2.8 文件存储(JD 上传、机会矩阵导出包)

**推荐:起步直接存 Postgres `BYTEA` / `TEXT`(小文件);超过 5MB 的(导出包、上传 JD PDF)走 S3 兼容对象存储(MinIO 自建 或 Cloudflare R2)**

理由:JD 文本本身就入库了(`saved_jobs.description`),用户上传的 PDF/截图体积小、读多写少,先入库最简单;导出包(`opportunities.md` + `execution_pack.md` 打包)会超过几 MB,上 R2 / MinIO,URL 签名下发。

备选:纯本地磁盘(单机部署也能跑,但水平扩展即破)。

---

## 3. 数据模型迁移

### 3.1 当前文件 → 实体映射

| 当前文件 | 主实体 (Pydantic) | 建议表名 | 关键字段 | 索引 | 用户隔离字段 |
|----------|-------------------|----------|----------|------|--------------|
| `data/profile.yaml` | `Profile` | `profiles` | `user_id`、`name`、`current_role`、`content JSONB`(完整 Profile) | `(user_id)` unique | `user_id` |
| `data/profile.yaml`(教育子结构) | `Education` | `profile_educations` | `profile_id`、`level`、`school`、`major`、`school_tier`、`start_year`、`end_year` | `(profile_id)`、`(school_tier)` | 经 `profile_id` |
| `data/profile.yaml`(经历子结构) | `Experience` | `profile_experiences` | `profile_id`、`company`、`role`、`period` | `(profile_id)` | 经 `profile_id` |
| `data/profile.yaml`(优势证据) | `StrengthEvidence` | `profile_strengths` | `profile_id`、`claim`、`proof` | `(profile_id)` | 经 `profile_id` |
| `data/constraints.yaml` | `Constraints` | `constraints` | `user_id`、`risk_appetite`、`financial_runway_months`、`age`、`employer_preference JSONB` | `(user_id)` unique | `user_id` |
| `data/narrative.md` | (markdown) | `narratives` | `user_id`、`content TEXT`、`updated_at` | `(user_id)` unique | `user_id` |
| `data/signals/*.yaml` | `Signal` | `signals` | `user_id`、`domain`、`topic`、`finding`、`source`、`source_url`、`retrieved_on`、`confidence` | `(user_id, domain, retrieved_on)` | `user_id` |
| `data/saved_jobs.yaml` | `SavedJob` | `saved_jobs` | `user_id`、`company`、`role`、`description`、`location`、`source`、`saved_on`、`status`、`linked_direction` | `(user_id, status)`、`(user_id, company, role)` | `user_id` |
| `data/applications.yaml` | `Application` | `applications` | `user_id`、`company`、`role`、`tier`、`applied_on`、`channel`、`status`、`feedback` | `(user_id, status)`、`(user_id, applied_on)` | `user_id` |
| `data/opportunities.yaml` | `OpportunityMatrix` | `opportunity_matrices` | `user_id`、`generated_on`、`payload JSONB`(capability_axes / employer_axes / cross_matrix / primary 全量) | `(user_id)` | `user_id` |
| `data/opportunities.draft.yaml` / `opportunities.revised.yaml` | `OpportunityMatrix` | `opportunity_matrices`(用 `kind` 区分) | `kind`(`draft`/`published`/`revised`) | `(user_id, kind)` | `user_id` |
| `data/matrix_feedback.yaml` | `MatrixFeedbackAction` | `matrix_feedback_actions` | `user_id`、`action`、`direction`、`details JSONB`、`timestamp` | `(user_id, timestamp)` | `user_id` |
| `data/projects.yaml` | `ProjectsFile` + `ProjectEvidence` | `projects` | `user_id`、`path`、`name`、`languages JSONB`、`key_dependencies JSONB`、`scanned_on` | `(user_id)` | `user_id` |
| `data/intake_session.json` | `IntakeSession` + `ChatMessage` | `chat_messages` | `user_id`、`role`、`content`、`created_at`、`session_id` | `(user_id, session_id, created_at)` | `user_id` |
| —(新增) | — | `users` | `id`、`email`、`password_hash`、`created_at`、`is_active` | `(email)` unique | — |
| —(新增) | — | `user_settings` | `user_id`、`llm_provider`、`llm_model`、`llm_api_key_encrypted`、`daily_token_quota`、`daily_token_used` | `(user_id)` unique | `user_id` |
| —(新增) | — | `auth_refresh_tokens` | `user_id`、`token_hash`、`expires_at`、`revoked` | `(user_id)`、`(token_hash)` | `user_id` |

**共享知识**(全用户只读,继续走 YAML + 应用层缓存,**不入用户库**):

| 当前文件 | 处理 |
|----------|------|
| `data/sectors.yaml` | 共享;启动时加载进内存 / Redis 缓存 |
| `data/industry_graph.yaml` | 同上 |
| `data/role_taxonomy.yaml` + `role_taxonomy_public.yaml` | 同上;`load_role_taxonomy` 已经合并这两个文件 |
| `data/employer_types.yaml` | 同上 |
| `data/cross_track.yaml` | 同上 |
| `data/skill_aliases.yaml`、`capability_registry.yaml`、`method_patterns.yaml`、`jd_link_rules.yaml`、`hiring_eligibility_rules.yaml` | 同上(`registry.py` 加载) |

> 共享 YAML 文件后续可迁到独立 `knowledge` schema 或单独的"全局知识"表,但起步阶段保留为文件 + 内存缓存最简单,且 Agent / CLI 单机模式仍能复用。

### 3.2 核心表 DDL 草案

```sql
-- =========================================================
-- users:平台账户(FastAPI Users 管理密码哈希)
-- =========================================================
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT NOT NULL UNIQUE,
    hashed_password TEXT NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_superuser    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================================================
-- profiles:一个用户一份 profile(Schema 主键实体)
-- 兼容 schema.py::Profile;content JSONB 保留完整模型以便演进
-- =========================================================
CREATE TABLE profiles (
    user_id     UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT,
    current_role TEXT,
    content     JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- JSONB 里存 education / experience / skills / strength_evidence / preferences
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX profiles_name_trgm ON profiles USING gin (name gin_trgm_ops);

-- 教育子表(用于资格闸门 eligibility 高频查询,从 JSONB 拆出来)
CREATE TABLE profile_educations (
    id          BIGSERIAL PRIMARY KEY,
    profile_id  UUID NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    level       TEXT,                -- bachelor/master/phd
    school      TEXT NOT NULL,
    school_tier TEXT,                -- 985/211/双一流/二本/海外/...
    major       TEXT,
    start_year  INT,
    end_year    INT,
    status      TEXT,                -- enrolled/graduated
    sort_order  INT NOT NULL DEFAULT 0
);
CREATE INDEX idx_educations_profile ON profile_educations(profile_id);
CREATE INDEX idx_educations_tier    ON profile_educations(school_tier);

-- =========================================================
-- saved_jobs:感兴趣岗位库(jobs.py)
-- description 是 JD 全文,用于 jd-analyze
-- =========================================================
CREATE TABLE saved_jobs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company          TEXT NOT NULL,
    role             TEXT NOT NULL,
    description      TEXT NOT NULL DEFAULT '',
    location         TEXT NOT NULL DEFAULT '',
    source           TEXT NOT NULL DEFAULT '手动添加',
    saved_on         DATE NOT NULL DEFAULT CURRENT_DATE,
    status           TEXT NOT NULL DEFAULT 'interested',  -- interested/researching/ready/applied/archived
    linked_direction TEXT NOT NULL DEFAULT '',
    notes            TEXT NOT NULL DEFAULT '',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, company, role)
);
CREATE INDEX idx_saved_jobs_user_status ON saved_jobs(user_id, status);

-- =========================================================
-- opportunity_matrices:核心交付物(schema.py::OpportunityMatrix)
-- JSONB 存 capability_axes / employer_axes / cross_matrix / primary
-- kind 区分 draft / published / revised
-- =========================================================
CREATE TABLE opportunity_matrices (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind         TEXT NOT NULL DEFAULT 'published',  -- draft|published|revised
    generated_on DATE NOT NULL DEFAULT CURRENT_DATE,
    payload      JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- payload 含 unified_theme / shared_assets / capability_axes / employer_axes /
    --          cross_matrix / primary / synergy_notes
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_matrices_user_kind ON opportunity_matrices(user_id, kind, generated_on DESC);

-- =========================================================
-- matrix_feedback_actions:append-only 日志(matrix_feedback.py)
-- =========================================================
CREATE TABLE matrix_feedback_actions (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action      TEXT NOT NULL,                -- remove|reorder|reset|note
    direction   TEXT NOT NULL DEFAULT '',
    details     JSONB NOT NULL DEFAULT '{}'::jsonb,
    "timestamp" TIMESTAMPTZ NOT NULL DEFAULT now()  -- 与 schema 字段名兼容
);
CREATE INDEX idx_mf_user_ts ON matrix_feedback_actions(user_id, "timestamp");

-- =========================================================
-- chat_messages:intake 对话历史(替代 intake_session.json)
-- =========================================================
CREATE TABLE chat_messages (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id  UUID NOT NULL DEFAULT gen_random_uuid(),
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_chat_user_session ON chat_messages(user_id, session_id, created_at);

-- =========================================================
-- user_settings:LLM key / 配额
-- llm_api_key_encrypted 用 Fernet 加密,密钥放 secret(见 §6)
-- =========================================================
CREATE TABLE user_settings (
    user_id                UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    llm_provider           TEXT NOT NULL DEFAULT 'cloudbase',
    llm_model              TEXT NOT NULL DEFAULT 'hy3-preview',
    llm_api_key_encrypted  TEXT,                    -- nullable;空 = 走平台 key
    daily_token_quota      INT NOT NULL DEFAULT 50000,
    daily_token_used       INT NOT NULL DEFAULT 0,
    daily_token_reset_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================================================
-- auth_refresh_tokens:JWT 刷新令牌(可撤销)
-- =========================================================
CREATE TABLE auth_refresh_tokens (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash   TEXT NOT NULL UNIQUE,
    expires_at   TIMESTAMPTZ NOT NULL,
    revoked      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_rt_user ON auth_refresh_tokens(user_id);
```

### 3.3 迁移与版本管理

- **Schema 版本管理用 Alembic**。每个里程碑一张 migration,与 Pydantic 模型版本对齐(`schema-v2.md`、`schema-v2.2.md` 已有版本号体系)。
- **YAML 导入/导出保留**:SaaS 上线后,`career-compass import <yaml-zip>` / `export <yaml-zip>` 作为:
  1. 老用户从单机版迁历史数据到 SaaS;
  2. 用户备份 / 迁出 SaaS(数据可携权,GDPR / 个保法合规要求);
  3. CLI / Agent Skill 模式仍可继续在本地工作。
- **历史用户数据搬运**:写一次性脚本 `scripts/migrate_local_to_saas.py`,扫描 `data/` 生成 SQL insert;对单用户单机模式无影响。
- **时区**:所有 `TIMESTAMPTZ` 存 UTC,前端按浏览器 locale 显示;`Signal.retrieved_on` / `Application.applied_on` 等 `date` 类型保留为 `DATE`(用户语义就是日期,不带时间)。
- **货币**:短期内北斗星不涉及金额字段;配额用 token / 次数即可。
- **字符集**:Postgres 默认 UTF-8,中文无障碍。

---

## 4. API 改造范围

### 4.1 现有端点改造对照

| 当前端点 (`web_server.py`) | 改造后端点 (FastAPI) | 需要的鉴权 | 多用户改造点 |
|---------------------------|----------------------|-----------|--------------|
| `GET /api/load_all` | `GET /api/state` | JWT | Repository 按 `user.id` 加载所有 view(`view_data.py::build_all_views` 改为接 `user_id`) |
| `GET /api/chat_state` | `GET /api/chat/state` | JWT | 从 `chat_messages` 表读 `session_id` 最新一段(替代 `intake_session.json`) |
| `POST /api/chat_send` | `POST /api/chat/messages` | JWT | 写 `chat_messages`;`IntakeEngine(data_dir)` 改为 `IntakeEngine(user_id, repo)`;配额检查 |
| `POST /api/chat_reset` | `POST /api/chat/reset` | JWT | 新建 `session_id`,旧消息保留可查 |
| `POST /api/run_command` | `POST /api/jobs/{id}/analyze`、`POST /api/render/opportunities` 等专项端点 | JWT | 拆成细粒度端点;不再用通用 `run_command` 透 CLI |
| `GET /api/matrix_feedback` | `GET /api/matrix/feedback` | JWT | 从 `matrix_feedback_actions` 查 |
| `POST /api/matrix_feedback/add` | `POST /api/matrix/feedback` | JWT | 写表;`matrix_feedback.py::append_action` 改为接 repo |
| `POST /api/jobs/add` | `POST /api/jobs` | JWT | `jobs.py::add_saved_job` 改 repo;`UNIQUE(user_id, company, role)` 在 DB 层兜底 |
| `POST /api/jobs/update` | `PATCH /api/jobs/{id}` | JWT | 同上;校验 `job.user_id == request.user.id` |
| `POST /api/jobs/remove` | `DELETE /api/jobs/{id}` | JWT | 同上 |
| (无) | `GET /api/profile`、`PUT /api/profile` | JWT | 单独的画像读写端点(原来藏在 `load_all` 里) |
| (无) | `GET /api/applications`、`POST /api/applications`、`PATCH /api/applications/{id}` | JWT | 对应 `track.py` |
| (无) | `GET /api/signals`、`POST /api/signals` | JWT | 对应 `gather.add_signal` |
| (无) | `GET /api/opportunities` | JWT | 读 `opportunity_matrices` 最新 published |
| (无) | `POST /api/match` | JWT | 调 `match.generate_orthogonal_matrix`,写 draft |

### 4.2 新增端点

```
# 鉴权(FastAPI Users 提供)
POST   /api/auth/register           {email, password}
POST   /api/auth/jwt/login          {email, password} -> {access_token, refresh_token}
POST   /api/auth/jwt/refresh        {refresh_token} -> {access_token}
POST   /api/auth/jwt/logout
POST   /api/auth/forgot-password    {email}
POST   /api/auth/reset-password     {token, new_password}
GET    /api/users/me                -> 当前用户信息

# 用户设置 / LLM key
GET    /api/users/me/settings
PUT    /api/users/me/settings       {llm_provider?, llm_model?, llm_api_key?}
DELETE /api/users/me/settings/llm-key      # 清除 BYOK,回退平台 key
GET    /api/users/me/quota           -> {daily_token_used, daily_token_quota, reset_at}

# 数据导入/导出
POST   /api/import/yaml              # 上传 zip,反序列化为用户数据
GET    /api/export/yaml              # 下载 zip(profile + opportunities + ...)

# 账号
DELETE /api/users/me                 # 注销账号(GDPR/个保法);级联删所有用户数据
```

### 4.3 其他

- **OpenAPI 自动文档**:FastAPI 默认在 `/docs`(Swagger)和 `/redoc` 暴露;生产环境用 `openapi_url=None` 关闭或加 admin 鉴权。
- **Rate limiting**:用 `slowapi`(基于 Redis);默认 `chat_send` 5 次/分钟、`auth/login` 10 次/分钟,可按用户等级调整。
- **CORS**:
  - 单机模式:`Access-Control-Allow-Origin: http://localhost:5173`(Vite dev)。
  - SaaS 模式:`Allow-Origin` 锁死正式域名 + `Allow-Credentials: true`(JWT 通过 `Authorization` header,不用 cookie,因此 CSRF 风险低)。
- **JWT 撤销**:`auth_refresh_tokens.revoked = TRUE` 用于强制下线;access token 短期(15min),refresh 长期(30d)。
- **WebSocket**(可选):`/api/chat/stream` 用于流式 LLM 输出;起步可以先 POST 同步返回,后置优化。

---

## 5. 前端改造范围

### 5.1 现有页面 / 组件改造

| 当前页面 / 组件 (`frontend/src/`) | 改造点 |
|------------------------------------|--------|
| `App.tsx` | 顶层包 `<AuthProvider>`,未登录跳 `/login`;header 加用户菜单(头像/邮箱/退出) |
| `api/types.ts::api` | 所有 `fetch` 加 `Authorization: Bearer <jwt>`(拦截器);401 自动 refresh,再失败跳登录 |
| `api/types.ts::post` | 改为统一的 `request<T>(...)`,内部带 token 注入与 error normalization |
| `components/ChatPanel.tsx` | 业务逻辑不变;chat_send 401 时降级提示登录 |
| `components/JourneyBar.tsx` | 不变(journey 由后端按 user 计算) |
| `components/ViewPanels.tsx` | 不变 |
| 头部 `data_dir` 显示(`App.tsx:111-113`) | SaaS 模式下隐藏;单机模式保留 |
| 静态资源 / build 产物路径 | SaaS 模式下由 FastAPI `StaticFiles` 挂在 `/`,API 在 `/api/*`;单机模式不变 |

### 5.2 新增页面 / 组件

- `pages/Login.tsx`、`pages/Register.tsx`、`pages/ForgotPassword.tsx`、`pages/ResetPassword.tsx` —— FastAPI Users 端点对应。
- `components/AuthProvider.tsx` —— 提供 `useUser()`、`useAuth()`;localStorage 存 refresh token,内存存 access token(防 XSS 偷)。
- `components/UserMenu.tsx` —— header 右上角下拉(头像、设置、退出)。
- `pages/Settings.tsx` —— 修改 LLM 配置(`provider` / `model` / `api_key`)、查看配额、注销账号。
- `api/interceptor.ts` —— `fetch` 包装器:
  - 自动注入 `Authorization`;
  - 401 时尝试 refresh,失败跳 `/login`;
  - 网络错误统一 toast。
- `router.tsx` —— `react-router-dom` 加路由保护 `<ProtectedRoute>`;公开路由(`/login`、`/register`)放白名单。
- (可选)`components/QuotaBar.tsx` —— chat 顶部细条,显示今日剩余 token。

### 5.3 是否换 Next.js / Remix

**推荐:继续 Vite + React SPA**。

理由:

- 当前业务是登录后工具型应用,**没有 SSR/SEO 需求**;落地页 / 营销页可以单独搭一个 Next.js 静态站,主产品仍是 SPA。
- 切框架成本(路由、状态、构建、Tailwind 配置全部要改)远大于收益。
- 若未来需要 SEO(博客/案例页),再做营销子站,不影响主应用。

备选:Next.js(App Router),如果团队后续要引服务端组件、或要做 SEO 内容站,可一次性切换。

---

## 6. 安全与合规

### 6.1 传输与认证

- **HTTPS 强制**:Caddy 自动签发 Let's Encrypt 证书;HTTP 80 跳转 443。
- **密码哈希**:`bcrypt`(cost=12)或 `argon2id`;FastAPI Users 默认 `bcrypt`,可换。
- **JWT 签名**:`HS256` + 服务端 secret(起步)→ 后期可迁 `RS256`(公私钥分离,便于多服务验证)。
- **Refresh token**:`token_hash` 入库,支持撤销;指纹绑定 UA/IP 减少被盗用风险。

### 6.2 用户机密数据

- **LLM API key 加密**:用 `cryptography.fernet`,主密钥放 secret manager(Docker secret / Vault / 云 KMS);DB 里只存密文。
- **JWT secret / DB 密码 / Cookie secret** 全部走环境变量,不入仓库;`.env.example` 只列字段名。

### 6.3 Web 安全

- **CSRF**:JWT 走 `Authorization` header 而非 cookie,理论上免疫;若以后改成 cookie 模式,再上 `SameSite=Strict` + CSRF token。
- **XSS**:React 默认转义;`dangerouslySetInnerHTML` 仅用于可信 markdown 渲染(`react-markdown` 已经过 `remark-gfm`),输入侧加 DOMPurify 兜底。
- **SQL 注入**:全走 SQLAlchemy / Dapper 风格的参数化查询,绝不拼字符串。
- **文件上传**:JD 上传限 `.pdf / .txt / .md`,大小 ≤ 5MB;服务端 magic-number 校验。

### 6.4 合规

- **GDPR / 个保法(中国《个人信息保护法》)**:
  - 用户数据删除:`DELETE /api/users/me` 级联删所有 user-owned 表;保留 30 天软删除窗口(防误删 / 滥用)。
  - 数据导出:`GET /api/export/yaml` 满足"数据可携权"。
  - 隐私政策 / 用户协议页面(法务文案后置)。
- **国内 ICP 备案**:若服务器在国内且面向国内用户,**必须**备案;香港 / 海外节点不需要,但访问速度差。
- **内容安全**:LLM 输入 / 输出过敏感词过滤;CloudBase 网关已自带内容审核,继续复用。

### 6.5 审计

- 所有敏感操作(登录、改密码、改 LLM key、注销账号)写 `audit_log` 表(`user_id`、`action`、`ip`、`ua`、`created_at`)。

---

## 7. 部署架构

### 7.1 单机 Docker Compose 起步

```
[Browser]
   │ HTTPS 443
   ▼
[Cloudflare / 阿里云 CDN]              (可选,DNS + 缓存 + DDoS)
   │
   ▼
[Caddy]   ← 自动 HTTPS / 反向代理
   │
   ├──────────────────┬─────────────────┬──────────────────┐
   ▼                  ▼                 ▼                  ▼
[FastAPI app]     [Postgres 16]     [Redis 7]          [MinIO / R2]
(2 replicas       (单实例,         (session /         (导出包 / 大 JD
 起,后续可横向)    每日 pg_dump)     rate limit)        附件,可选)
```

`docker-compose.yml`(草案,不在本设计里写完整实现):

- `caddy`:暴露 80/443,反代到 `app:8000`。
- `app`:FastAPI + uvicorn workers;非 root 用户运行;只挂载 `/app/static`(前端构建产物)。
- `postgres`:官方镜像,数据卷持久化;`POSTGRES_PASSWORD` 走 secret。
- `redis`:官方镜像,持久化 AOF。
- `minio`(可选):对象存储,或直接接 Cloudflare R2(S3 兼容)。

### 7.2 数据库备份

- **每日**:`pg_dump -Fc` 到对象存储,保留 30 天。
- **WAL**:启用 `archive_mode`,PITR(point-in-time recovery)窗口 7 天。
- **恢复演练**:CI 每月跑一次 restore 测试,校验可恢复。

### 7.3 监控 / 日志 / 错误追踪

- **错误追踪**:`sentry-sdk`(FastAPI / Python);前端 `@sentry/react`。
- **日志**:Python `structlog` 输出 JSON,经 Caddy stdout → Docker → 远程日志(Loki / 阿里云 SLS)。
- **指标**:Prometheus `/metrics`(用 `prometheus-fastapi-instrumentator`),Grafana 看板:QPS、p95 延迟、错误率、LLM token 消耗、注册/登录漏斗。
- **业务指标**:日活、机会矩阵生成数、intake 完成率,后端写一张 `events` 表 + 简易后台查询。

### 7.4 CI / CD

- **GitHub Actions**(已有 `.github/` 目录的预期位置):
  - `test`:跑 `pytest`(已有 `tests/`),前端 `npm run build`。
  - `build`:构建 `app` 镜像并推到 registry(GHCR / 阿里云 ACR)。
  - `deploy`:SSH 到 VPS,`docker compose pull && docker compose up -d`;Alembic `upgrade head` 作为 entrypoint 的一部分。
- **分支策略**:`main` → 生产;`staging` → 预发(可选);feature branch 用 PR。

---

## 8. 分阶段里程碑

每个阶段交付物严格可验收;后一阶段依赖前一阶段。

### 里程碑 M1:数据库 + 用户系统(注册登录跑通)

- **目标**:有一个能注册、登录、刷新 token 的 FastAPI 服务,跑在 Docker Compose 里。
- **交付物**:
  - `docker-compose.yml`(caddy + app + postgres + redis);
  - FastAPI app 骨架(`src/career_compass/saas/app.py`);
  - `users` / `auth_refresh_tokens` / `user_settings` 三张表 + Alembic migration 001;
  - `/api/auth/register`、`/api/auth/jwt/login`、`/api/auth/jwt/refresh`、`/api/users/me` 端点(基于 FastAPI Users);
  - 一个 `/api/health` 端点做存活探活;
  - README 章节《SaaS 启动》(`docs/saas-quickstart.md`)。
- **预估工作量**:1.5-2 天
- **依赖**:无
- **验收标准**:`curl POST /api/auth/register` 能注册;`POST /api/auth/jwt/login` 拿到 access token;`GET /api/users/me` 带 token 返回当前用户;不带 token 返回 401。

### 里程碑 M2:数据模型迁移(YAML → DB,保留 CLI 导入导出)

- **目标**:所有用户数据落 Postgres;Repository 层替代 `load_*/save_*` 文件函数;CLI 仍可在单机模式工作。
- **交付物**:
  - 全部 §3.1 列出的用户表 + Alembic migrations 002-008;
  - `src/career_compass/saas/repo.py` —— Repository 层,按 `user_id` 读写;
  - 改造 `schema.py` loader:新增 `load_profile_db(user_id)` 等并保留 `load_profile(path)` 用于 CLI;
  - `scripts/migrate_local_to_saas.py`:把现有 `data/` 一次性导入到一个指定 `user_id`;
  - `POST /api/import/yaml`、`GET /api/export/yaml` 端点;
  - 共享知识(sectors / industry_graph / role_taxonomy 等)在 app 启动时加载到内存,提供 `knowledge_repo.get_*`。
- **预估工作量**:3-4 天
- **依赖**:M1 的 `users` 表
- **验收标准**:
  - 通过 `/api/import/yaml` 上传现有 data zip,DB 里能查到 profile / opportunities / saved_jobs;
  - `GET /api/export/yaml` 下载 zip,与原 `data/` 结构对齐;
  - 单元测试覆盖每张表的 CRUD + 用户隔离(用户 A 不能查到用户 B 的数据)。

### 里程碑 M3:API 重写为 FastAPI(端点对齐)

- **目标**:SaaS 模式下 `/api/*` 全部由 FastAPI 提供;旧 `web_server.py` 退化为单机 / 桌面入口(`--local` flag)。
- **交付物**:
  - §4.1 改造对照表里的所有 FastAPI 端点(15-20 个);
  - `IntakeEngine(user_id, repo, llm_client)` 改造;`intake/writer.py::apply_updates` 改为写 repo;
  - `match.py` / `render.py` / `replan.py` / `track.py` / `jobs.py` / `matrix_feedback.py` 全部支持 `user_id` 入口;
  - JWT 依赖注入:`def get_current_user(token: str = Depends(oauth2_scheme)) -> User`;
  - `slowapi` rate limit 配置;CORS 配置;OpenAPI 关闭或加 admin 锁;
  - pytest 集成测试:`tests/saas/test_*.py`,覆盖每个端点的 200/401/403/404。
- **预估工作量**:4-5 天
- **依赖**:M2 的 Repository 层
- **验收标准**:从 Postman / curl 走完一个完整用户旅程(注册 → 修改 profile → chat → 生成机会矩阵 → 收藏 JD → 跟踪投递),全部 200;跨用户访问返回 403/404。

### 里程碑 M4:前端加登录 + 多用户

- **目标**:浏览器打开站点,未登录跳登录页;登录后所有现有功能不变。
- **交付物**:
  - `AuthProvider` / `useUser` / `useAuth`;
  - `Login.tsx` / `Register.tsx` / `ForgotPassword.tsx` / `ResetPassword.tsx`;
  - `UserMenu.tsx`(header 右上角);
  - `Settings.tsx`(改 LLM 配置、看配额、注销账号);
  - `api/interceptor.ts`(自动注入 token、401 refresh、失败跳登录);
  - `react-router-dom` + `<ProtectedRoute>`;
  - header 隐藏 `data_dir`(SaaS 模式);
  - Sentry 接入(`@sentry/react`)。
- **预估工作量**:2-3 天
- **依赖**:M3 的所有端点
- **验收标准**:本地起 `npm run dev`,浏览器走完"注册 → 登录 → chat → 渲染矩阵 → 退出 → 重新登录数据还在";token 过期后自动 refresh;refresh 失效跳登录页。

### 里程碑 M5:LLM key 管理 + 配额

- **目标**:用户可在 Settings 里填自己的 LLM key;平台 key 走配额;每日重置。
- **交付物**:
  - `user_settings.llm_api_key_encrypted` 加密读写;
  - `LLMClientFactory.for_user(user_id)`:有 BYOK 用 BYOK,否则用平台 key;
  - 配额计数中间件:每次 LLM 调用后写 `daily_token_used += n`,超限返回 429;
  - 配额重置 cron(或懒加载:每次调用前检查 `daily_token_reset_at` 是否跨日);
  - Settings 页配额条 + 接近上限提示。
- **预估工作量**:1.5 天
- **依赖**:M3、M4
- **验收标准**:用户 A 不填 key 跑到上限后被 429;用户 B 填自己的 key 不受限;切换日期后配额归零。

### 里程碑 M6:部署 + 监控

- **目标**:线上可访问;备份 / 监控 / 错误追踪就绪。
- **交付物**:
  - 生产 `docker-compose.yml`;
  - Caddyfile(自动 HTTPS);
  - GitHub Actions CI/CD pipeline(`.github/workflows/ci.yml` + `deploy.yml`);
  - `pg_dump` 每日备份脚本 + 上传到对象存储;
  - Sentry DSN 配置;Prometheus `/metrics`;Grafana 看板 JSON;
  - 隐私政策 / 用户协议页面(占位文案);
  - 运维 runbook:常见故障处理、DB 恢复步骤。
- **预估工作量**:2 天
- **依赖**:M3、M4、M5
- **验收标准**:`https://<domain>` 能注册登录完整走完用户旅程;手动 kill `app` 容器后 Caddy 返回 502 而非 200;`pg_restore` 能恢复到测试库。

### 里程碑 M7(可选):支付

- **目标**:订阅 / 升级配额。
- **交付物**:
  - `subscriptions` / `invoices` 表;
  - Stripe(海外)或 Lemonsqueezy / 微信扫码(国内)集成;
  - Settings 页"升级方案";
  - 配额按订阅等级动态计算。
- **预估工作量**:3-5 天
- **依赖**:M5、M6
- **验收标准**:付费后配额立即提升;退款/订阅取消后下个周期降级;webhook 消息有签名校验。

---

## 9. 风险与未决问题

以下问题需要**用户拍板**才能继续,顺序按优先级:

1. **目标市场:面向国内还是海外?** —— 决定备案 / 认证方案(邮箱 vs 手机号 vs 微信扫码)/ 支付渠道 / LLM 网关选择。这是最大的分叉。
2. **商业模式:免费 / 订阅 / 按用量?** —— 决定配额设计的颗粒度(按 token / 按对话轮 / 按矩阵生成次数)。建议起步免费 + 重度用户 BYOK,先验证留存。
3. **LLM key 用户自带还是平台统一?** —— 影响 M5 工作量与成本预算。推荐混合(见 §2.4),但需确认平台愿意承担多少 token 成本(预估:cloudbase `hy3-preview` 单用户每月成本上限 ~¥5,100 用户 = ¥500/月)。
4. **数据库起步用 Postgres 还是 SQLite?** —— 若用户量确定 < 50(纯内测),SQLite-per-user 0 运维;若确定要上 SaaS,直接 Postgres 省一次迁移。**本设计推荐 Postgres**,但需用户认可"加一台 DB"的成本。
5. **前端要不要换 Next.js?** —— 影响营销页 / SEO 内容站规划。**推荐继续 Vite + React**,落地页另搭。
6. **是否保留单机模式 / 桌面模式?** —— `pywebview` 桌面入口在 SaaS 化后是否还维护?这关系到 Agent Skill 用户(单机 Claude Code / Cursor)的体验。建议保留 CLI + Skill,但 `--desktop` 可逐步弃用。
7. **Agent Skill 模式(Claude Code / Cursor)与 SaaS 的关系?** —— Skill 是仍然读本地 `data/`,还是改成调用 SaaS API?若改 API,意味着 Skill 用户必须先注册账户。**建议起步阶段 Skill 继续走本地 YAML**,SaaS 与 Skill 各服务一类用户,数据通过 §3.3 的导入/导出互通。
8. **数据隔离强度?** —— 行级隔离够吗,还是要 schema-per-tenant(企业版)?决定是否启用 Postgres RLS、是否要做多 DB。
9. **历史用户数据怎么搬?** —— 现在仓库里的 `data/profile.yaml` 等是项目维护者自己的真实数据。SaaS 化时是否要把它当"种子用户"导入?涉及隐私(数据里包含真实姓名、学校)。
10. **域名 / 服务器预算** —— 是否已有域名?VPS 配置(2C4G 起步够 Postgres + app + redis)?国内还是海外节点?

---

## 10. 推荐立即执行的下一步

按顺序:

1. **回答 §9 中的问题 1、2、3、4**(目标市场 / 商业模式 / LLM key 策略 / DB 起步形态)。这四个决策会直接改变 M1-M5 的范围,其他问题可以边做边定。
2. **准备一台 VPS + 注册一个域名**。M1 / M6 都需要这台机器;域名 + DNS 是 Caddy 自动 HTTPS 的前提。建议配置:2C4G、Ubuntu 22.04、50GB SSD。
3. **启动里程碑 M1 的 worker 任务**:建 Postgres + users 表 + FastAPI Users 注册登录跑通。M1 完成后即可启动 M2(数据模型迁移),不需要等其他里程碑。

---

## 附录 A:技术栈速查

| 层 | 选型 | 版本 | 备注 |
|----|------|------|------|
| 后端框架 | FastAPI | latest | 替换 `BaseHTTPRequestHandler` |
| ORM | SQLAlchemy 2.x + Alembic | latest | 异步支持 |
| 数据库 | PostgreSQL | 16 | JSONB + RLS |
| 缓存 / Rate limit | Redis | 7 | session、quota cache |
| 认证 | FastAPI Users | latest | JWT + bcrypt |
| 反向代理 | Caddy | 2.x | 自动 HTTPS |
| 容器 | Docker / Docker Compose | latest | 单机起步 |
| 监控 | Sentry + Prometheus + Grafana | latest | 错误 + 指标 |
| CI/CD | GitHub Actions | — | 已有 `.github/` 目录 |
| 前端 | Vite + React 19 + TypeScript + Tailwind 4 | 现有 | 不变 |
| 前端路由 | react-router-dom | latest | 新增 |
| 前端鉴权 | 自研 AuthProvider | — | 见 §5.2 |
| 对象存储(可选) | MinIO 自建 / Cloudflare R2 | — | 大文件 |

## 附录 B:与现有代码的接触面

下表列出迁移过程中**会被改动**的现有文件,作为 PR 评审清单:

| 文件 | 改动类型 | 影响范围 |
|------|----------|----------|
| `src/career_compass/schema.py` | 新增 `from_db_row` / `to_db_row` 辅助,模型本身不动 | Pydantic 模型复用 |
| `src/career_compass/intake/engine.py` | 改造为接 `user_id` + repo | intake 入口 |
| `src/career_compass/intake/writer.py` | `apply_updates` 改为写 repo | intake 写入 |
| `src/career_compass/intake/llm.py` | 新增 `LLMClientFactory.for_user(user_id)` | LLM 客户端 |
| `src/career_compass/jobs.py` | 函数签名加 `user_id` 入口,或全部下沉到 repo | saved_jobs |
| `src/career_compass/track.py` | 同上 | applications |
| `src/career_compass/matrix_feedback.py` | 同上 | matrix_feedback |
| `src/career_compass/render.py` | 入参从 `Path` 改为模型对象 | 渲染 |
| `src/career_compass/replan.py` | 同上 | replan |
| `src/career_compass/gui/web_server.py` | 单机模式下保留;SaaS 模式下不再使用 | HTTP 入口 |
| `src/career_compass/gui/app.py` | `AppApi` 仅在 `--local` 模式下使用 | 单机入口 |
| `src/career_compass/cli.py` | 加 `--local` 默认值,仍可读写 `data/` | CLI |
| `frontend/src/api/types.ts` | 加 token 注入、401 处理 | API 客户端 |
| `frontend/src/App.tsx` | 包 `AuthProvider`、加 header 用户菜单 | 顶层 |
| `frontend/package.json` | 加 `react-router-dom`、`@sentry/react` | 依赖 |
| `pyproject.toml` | 加 `fastapi`、`sqlalchemy`、`alembic`、`fastapi-users`、`cryptography`、`slowapi`、`structlog`、`sentry-sdk` 等依赖 | 依赖 |

新增目录:

- `src/career_compass/saas/` —— FastAPI app、repo、auth、middleware、routes;
- `alembic/` —— migration 版本目录;
- `deploy/` —— `docker-compose.yml`、`Caddyfile`、运维脚本;
- `frontend/src/pages/`、`frontend/src/components/auth/` —— 登录注册相关。
