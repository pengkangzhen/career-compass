**English** | [简体中文](README.zh-CN.md)

# Beidou (北斗星)

One-liner: Beidou is an AI career **direction-choice** engine for people who feel stuck — not a resume bot, but a navigator before you apply.

> A **pre-application** career decision engine. Builds on two foundational layers — **profile × industry structure** — then evaluates along two dimensions — **industry trend** (tailwind/headwind, competition intensity) and **trial cost** (how reversible a wrong pick is) — to return **ranked direction options with rationale** — answering *which industry, which role, why you, and whether the timing is right*. **That's where Beidou stops**; resume optimization, apply strategy, and interview prep are left to downstream accelerator tools.

Repo codename: `career-compass`. Product name in Chinese: **北斗星** (Big Dipper — navigation metaphor).

## What problem it solves

Not “ask AI what job fits you,” but turn career choice into a **structured, evidence-based, iterable** system in hyper-competitive markets:

| Question | How Beidou helps |
|----------|-------------------|
| **Which industry?** | Value chain position, moats/traps, red vs blue ocean, competition density |
| **Which role?** | Role-family matching, seniority band, skill gaps, company tiers |
| **Why would they hire me?** | Evidence-linked profile: projects/papers → verifiable strengths vs JD requirements |
| **Is timing still OK?** | Trend signals + personal timeline (graduation, age, visa) |
| **What if I choose wrong?** | Low trial cost + optional stress-tests — try a direction before committing |

**Core principle**: the system returns **ranked options with rationale**; it does **not** pick for you. Values, family/geo constraints, and final direction stay with the user.

## Differentiation: navigator, not accelerator

Most career tools focus on **tactical** steps around applying. Beidou targets the **strategic gap** they share — *where should I actually go?* — and goes deep there.

### Three categories of existing tools

| Type | Examples | Strengths | Limits |
|------|----------|-----------|--------|
| **General LLMs** | ChatGPT, Claude | Broad, flexible chat | Generic advice; no structured profile; training priors as “trends”; one-shot, not replayable |
| **Job platforms** | LinkedIn, BOSS Zhipin, 51job | Large job inventory, short apply path | **Employer-aligned** — surfaces open roles on the platform, not your best direction |
| **Vertical AI tools** | Resume/interview/match SaaS | Deep on single tactics | “Job-search accelerators”; rarely answer *should I enter this track at all?* |

### Collective blind spots

| Blind spot | Common approach | Beidou |
|------------|-----------------|--------|
| **Symptoms, not cause** | Polish resume, mock interviews — direction assumed fixed | **Career navigator**: fit × track first, then how to enter |
| **No long-term view** | One-shot generation — no versioning, no iteration | **Long-term companion**: versioned profile/strategy; rescan stale signals |
| **Missing macro lens** | Match to open JDs only — industry structure absent | **Macro lens**: profile × industry structure as foundation; **industry trend** (tailwind/headwind, competition density, deep/shallow value chain) and **trial cost** feed into `composite` as evaluation dimensions |
| **Employer-aligned** | Push own listings — platform/employer interests first | **Direction, not listings** — no commissions, no employer KPIs; ranked options + rationale, user decides |

### Where Beidou stands

1. Not “optimize my resume,” but **career planning**.
2. **Long-term companion** — a durable partner for career decisions, not a one-shot chat.
3. **Macro vision** — industry trends and structural shifts in the algorithm, beyond the job in front of you.
4. **User-aligned** — neutral stance; trust through options and evidence, not a hidden agenda.

## Architecture (target)

**Terminology** (project-wide; see [`docs/user-journey.md`](docs/user-journey.md)):

**Core three layers (Beidou's boundary):**

| Layer | System (architecture/code) | User journey (GUI / chat) | Engine stage (CLI / Agent) |
|-------|----------------------------|---------------------------|----------------------------|
| L0 | Profile building | Know yourself | `intake` |
| L1 | Explore world | Explore world | `scan` |
| L2 | Decide | Decide | `analyze` |

> **fit / match / wind / risk** four-axis scoring inside `analyze` (see `playbooks/3-analyze.md`) is an *in-layer* scoring model — **not** the same numbering as L0–L2 above.

```
L0 Profile · Know yourself · intake
     resume/CV · code projects · dialogue (values/constraints) → profile / constraints / narrative
       ↓
L1 Explore · scan
     trends · supply/demand signals · industry graph · role taxonomy · saved JDs → signals/*.yaml · saved_jobs.yaml
       ↓
L2 Decide · analyze
     hard constraints → multi-axis scores → skill gaps → competition correction → opportunity matrix
       ⛔
     (Beidou stops here; resume optimization / apply strategy / interview prep / funnel tracking
      are left to downstream tools)
```

Competition intensity (credential filtering, JD skill stacking, shallow “API wrapper” roles, age/education gates) is a **scoring dimension** — “precision” means fit × window × enterability × trial cost on a Pareto frontier, not chasing the hottest track.

## What you get

The **signature deliverable** is an **opportunity matrix** (`opportunities.md`) — several evidence-backed, comparable directions, **ranked with rationale, not a verdict**. Rendered from `opportunities.yaml`; do not hand-edit `.md`.

### Opportunity matrix: four modules per direction

| Module | Answers |
|--------|---------|
| **Where to go** | Industry/track, suitable role families |
| **Why you** | Verifiable strengths, remaining gaps |
| **Worth entering now?** | Competition, tailwinds/headwinds, timing |
| **Traps** | Shallow hot roles, opportunity cost, trial price |

When `opportunities.md` is rendered, the **main Beidou flow is complete** (L2 Decide).

### Optional extension (decision deepening, not application execution)

| When | What | File / command |
|------|------|----------------|
| After **you pick** one direction from the matrix | Deepen direction | `strategy.md` (`4-plan`) + stress-test (`5-stress-test`) |

> Beidou does **not** cover: resume optimization, apply strategy, interview prep, application funnel tracking — these belong to downstream "job-search accelerator" tools. The repo retains `render-execution` / `track` / `replan` / `jd-analyze` CLIs as legacy implementations, but they are not part of the main narrative or maintenance focus.
>
> `render-pack` → `job_pack.md` is an overlapping summary view; usually skip unless you want a single rollup doc.

## Highlights

### Shipped (v0.4 · main scope L0–L2)

- **L0 Profile building** — Agent dialogue → `profile.yaml` / `narrative.md` / `constraints.yaml`; constraints as hard walls
- **Project scan (profile evidence)** — `scan-projects` harvests stack/deps/scale/papers from opted-in repos (not whole-disk)
- **L1 Explore world** — `scan-plan` derives queries; `new-signal` dedupes by topic (source + date required); `job add` for saved JD watchlist
- **Pipeline orchestration** — `status` / `run --stage` stage detection and next-step hints
- **Opportunity matrix (core)** — `render-opportunities` → `opportunities.md`; four modules per direction
- **L2 Match engine v1** — `match`: skill alignment, competition intensity, shallow-role penalties
- **Industry / role knowledge** — Industry Graph + Role Taxonomy backing matrix generation
- **(Optional) stress-test** — pre-mortem + tripwires (playbook 5) for direction-validation after you pick
- **Agent Skill** — conversational intake in Claude Code / Cursor
- **GUI chat** — same intake via `career-compass-app --web` 对话 Tab
- **CLI + GUI tabs** — validate, scan, match, view matrix
- **Legacy apply-side CLIs (non-core)** — `track` / `replan` / `render-execution` / `jd-analyze` / `saved_jobs`: retained from earlier phases, not actively developed

### Planned (Phase 4+)

#### L1 continuous intel (extending existing direction)

- **Scan agent cluster** — automated web research → signals
- **Periodic rescan** — stale-signal reminders
- **Multi-profile / forkable industry knowledge packs**

#### L2 decision augmentation (OR/ML data layer) — new direction

The matching engine is currently **deterministic heuristic** (transparent, auditable, no external API calls). Phase 4 will add an **opt-in data-driven layer** on top. Principle: always report delta vs heuristic baseline so the user can see what the ML changed and why; heuristic stays as the cold-start baseline, ML only takes over once enough data exists.

- 📊 **Data analysis layer** — funnel outcomes, JD corpora, and interview feedback become new data sources: isotonic regression calibrates the heuristic `match_score` into a verifiable `P(interview)`; skill co-occurrence embeddings replace keyword substring matching (solving semantic-neighbor cases like "reinforcement learning ↔ RLHF / agents"). This is the inflection point from "heuristic tool" to "data-driven decision system"
- 🎰 **Bayesian bandit apply recommendations** — each `(direction × employer type × company tier)` is treated as an arm; Thompson sampling balances exploration (trying new directions) and exploitation (reinvesting in high-conversion arms), replacing the hard-threshold rules in `replan`. **Requires opt-in use of `track`** (the main scope deliberately excludes apply tracking)
- 📐 **Pareto frontier view** — the six scoring dimensions of the opportunity matrix (core strength / Ikigai / industry trend / trial cost / hiring fit / competition) are incommensurable; the current A–F letter grade collapses them into a single rank and hides trade-offs (in practice, directions graded "A" can be strictly dominated). The Pareto frontier surfaces "which directions are incomparable and need your value judgment", paired with pairwise comparisons and preference sensitivity ("if I care most about trial cost, who wins"). Prototype exists at `career-compass pareto`; visualization format TBD (static charts carry limited information, leaning toward interactive GUI exploration)

## Who it’s for

- People choosing among academia vs industry, research vs engineering, hype vs durable tracks
- Anyone who needs **evidence-backed options** under intense competition (including CN market: tier-1/2 schools, age lines, etc.)
- Users who want choices **versioned and replayable**, not a one-off chat answer

## Quick start

### 1. Conversational intake (pick one)

| Channel | Usage |
|---------|--------|
| **Coding agent (Skill)** | Open repo in Claude Code / Cursor; say "help me with career planning"; or `./scripts/install-cursor-skill.sh` |
| **GUI chat** | Run `career-compass-app` or `./scripts/beidou.sh` — LLM preconfigured via repo `.env` (see `templates/llm.env.example`) |

Both write `data/profile.yaml` etc. and use `uv run career-compass validate`.

```bash
git clone https://github.com/pengkangzhen/career-compass.git
cd career-compass
uv sync
uv sync --group gui   # gui group for app only
```

### 2. GUI (chat + viewing)

```bash
./scripts/beidou.sh              # browser (recommended)
uv run career-compass-app        # same
uv run career-compass-app --desktop   # native window (pywebview)
```

LLM defaults to **Tencent CloudBase** (`hy3-preview`). Copy `templates/llm.env.example` → `.env` if needed; `beidou.sh` auto-loads `.env`.

## Workflow

Beidou covers only the **first three steps before the decision** — "pre-application" by strict definition. Completion criteria: [`docs/user-journey.md`](docs/user-journey.md).

```
Know yourself → Explore world → Decide   ⛔   (applying / resume polish / funnel tracking left to downstream tools)
    intake         scan        analyze
```

| Step | System layer | Main outputs | Required |
|------|--------------|--------------|----------|
| Know yourself | L0 Profile | `profile.yaml` · `constraints.yaml` · `narrative.md` | ✅ |
| Explore world | L1 Explore | `signals/*.yaml` · `saved_jobs.yaml` | ✅ |
| Decide | L2 Decide | `opportunities.yaml` → `opportunities.md` | ✅ **core** |

**Optional deepening** (after **you pick** a direction from the matrix): `plan` → `strategy.md`; `stress-test` → revise strategy. This is still an extension of the L2 decision layer — **not** application execution.

GUI top bar shows user journey; CLI / Agent use engine stage names. `uv run career-compass status` prints both layers.

## CLI

### Main flow (L0–L2, Beidou core)

| Command | Purpose |
|---------|---------|
| `uv run career-compass status` | Detect pipeline stage and next steps |
| `uv run career-compass run [--stage STAGE]` | Stage orchestration (intake → scan → analyze) |
| `uv run career-compass validate` | Profile/constraints completeness (errors vs warnings) |
| `uv run career-compass brief` | Aggregate analysis brief |
| `uv run career-compass scan-plan` | Derive search queries from profile |
| `uv run career-compass new-signal DOMAIN TOPIC FINDING SOURCE [URL]` | Append external signal |
| `uv run career-compass scan-projects <path>...` | Harvest project evidence |
| `uv run career-compass match [--write-draft]` | Matching engine; optional `opportunities.draft.yaml` |
| `uv run career-compass render-opportunities` | Render opportunity matrix (core deliverable) |
| `uv run career-compass render-strategy` | Render `strategy.md` skeleton (after you pick a direction) |
| `uv run career-compass render-pack [--stdout]` | Rollup view → `job_pack.md` (usually skip) |

### Legacy apply-side tools (not main flow)

> Not part of the main narrative or maintenance focus. Downstream resume/apply/interview tools usually do this better — prefer those.

| Command | Purpose |
|---------|---------|
| `uv run career-compass job add/list/show/analyze/remove` | Saved JD watchlist → `saved_jobs.yaml` |
| `uv run career-compass jd-analyze <file>` | JD skill clustering vs profile gaps |
| `uv run career-compass render-execution [--stdout]` | Tactical extension → `execution_pack.md` (pitch / resume hints / apply strategy) |
| `uv run career-compass track add/list/update/funnel` | Application tracking → `applications.yaml` |
| `uv run career-compass replan [--write]` | Feedback loop → suggestions / `opportunities.revised.yaml` |

See `docs/matching-engine.md` (Phase 2), `docs/schema-v2.md`.

## Documentation & languages

| Language | Files |
|----------|-------|
| **English (default)** | This file · [CLAUDE.md](CLAUDE.md) · [SKILL.md](SKILL.md) |
| 简体中文 | [README.zh-CN.md](README.zh-CN.md) · [CLAUDE.zh-CN.md](CLAUDE.zh-CN.md) · [SKILL.zh-CN.md](SKILL.zh-CN.md) |

Playbooks under `playbooks/` and some `docs/` remain Chinese (agent conversation scripts).

SaaS deploy: [docs/deployment.md](docs/deployment.md) (Vercel + Render + Neon). Live: https://career-compass-gilt.vercel.app

## Design principles

- **Evidence-driven** — strengths need proof; signals need sources; scores cite rationale; never treat model priors as "retrieved signals"
- **Constraints are walls** — geo, family, age, risk appetite filter out options, not just down-rank
- **Deep vs shallow** — shallow hot-track roles get explicit traps and score caps
- **Options, not verdicts** — top-N directions; user commits before `4-plan`
- **Data vs code** — facts in `data/`; agent logic in `playbooks/` (gradually codified in match engine); `src/` validates/renders
- **Iterable** — git history and signal staleness; rescan when signals age
- **Scope discipline** — stops at direction choice; resume optimization / apply strategy / interview prep left to downstream tools

## Roadmap

| Phase | Focus | Key outputs |
|-------|--------|-------------|
| **Phase 1** | Pipeline foundation | `run`/`status` orchestrator; tighter validate; Schema 2.0; scan dedup ✅ |
| **Phase 2** | Market sensing + role graph | Industry Graph, Role Taxonomy, competition index, skill gaps, job pack v1 ✅ |
| **Phase 3** | Apply-side legacy tools (out of main scope) | execution pack, track, replan, jd-analyze (kept for legacy users; not in main narrative) |
| **Phase 4** | Continuous intel OS | periodic rescan, multi-profile, forkable industry packs |

## Status

**v0.4 · main scope narrowed to L0–L2** — main flow: profile → explore → match → **opportunity matrix** (core deliverable). Phase 3 apply-side tools (`track`/`replan`/`render-execution`/`jd-analyze`) retained as legacy CLIs, no longer marketed. Phase 4 (automated scan agents, intel OS) still planned.

## License

MIT © Peng Kangzhen
