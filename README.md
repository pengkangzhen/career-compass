**English** | [简体中文](README.zh-CN.md)

# Beidou (北斗星)

One-liner: Beidou is an AI career **direction-choice** engine for people who feel stuck — not a resume bot, but a navigator before you apply.

> A **pre-application** career decision engine. Analyzes **profile × industry structure × market trends × competition** to produce evidence-backed, personalized, executable career options — from *which industry and role* to *how to enter, what to avoid, and how to validate*.

Repo codename: `career-compass`. Product name in Chinese: **北斗星** (Big Dipper — navigation metaphor).

## What problem it solves

Not “ask AI what job fits you,” but turn career choice into a **structured, evidence-based, iterable** system in hyper-competitive markets:

| Question | How Beidou helps |
|----------|-------------------|
| **Which industry?** | Value chain position, moats/traps, red vs blue ocean, competition density |
| **Which role?** | Role-family matching, seniority band, skill gaps, company tiers, geo strategy |
| **Why would they hire me?** | Evidence-linked profile: projects/papers → verifiable strengths vs JDs |
| **Is timing still OK?** | Trends + personal timeline (graduation, age, visa) |
| **What if I choose wrong?** | Low trial cost, stress-tests, tripwires — try before you commit |
| **No replies after applying?** | Application funnel → replan → revise opportunity matrix |

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
| **Treat symptoms, not cause** | Polish resume, mock interviews — direction assumed fixed | **Career navigator**: fit × track first, then how to enter |
| **No long-term view** | One-off consult or generation, then gone | **Long-term companion**: versioned profile/strategy; rescan signals; funnel → replan |
| **Missing macro lens** | “You × open JDs” only | **Profile × industry structure × trends × competition**; deep/shallow value chain, competition density in scores |
| **Not user-neutral** | Platforms push their listings; B2B tools serve employers | **No job listings to sell** — ranked options + rationale; user decides |

### Where Beidou stands

1. Not “optimize my resume,” but **career planning**.
2. **Long-term companion** — a durable partner for career decisions, not a one-shot chat.
3. **Macro vision** — industry trends and structural shifts in the algorithm, beyond the job in front of you.
4. **User-aligned** — neutral stance; trust through options and evidence, not a hidden agenda.

## Architecture (target)

**Terminology** (project-wide; see [`docs/user-journey.md`](docs/user-journey.md)):

| Layer | System (architecture/code) | User journey (GUI / chat) | Engine stage (CLI / Agent) |
|-------|----------------------------|---------------------------|----------------------------|
| L0 | Profile building | Know yourself | `intake` |
| L1 | Explore world | Explore world | `scan` |
| L2 | Decide | Decide | `analyze` |
| L3 | Act | Act | `execute` |
| L4 | Track | Track | `track` / `replan` |

> **fit / match / wind / risk** four-axis scoring inside `analyze` (see `playbooks/3-analyze.md`) is an *in-layer* scoring model — **not** the same numbering as L0–L4 above.

```
L0 Profile · Know yourself · intake
     resume/CV · code projects · dialogue (values/constraints) → profile / constraints / narrative
       ↓
L1 Explore · scan
     trends · supply/demand signals · industry graph · role taxonomy → signals/*.yaml · saved_jobs.yaml
       ↓
L2 Decide · analyze
     hard constraints → multi-axis scores → skill gaps → competition correction → opportunity matrix
       ↓
L3 Act · execute
     job pack · execution pack (pitch / resume hints / apply strategy)
       ↓
L4 Track · track
     application funnel → replan → revised matrix; optional plan + stress-test
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

### Optional extensions (not core deliverables)

| When | What | File / command |
|------|------|----------------|
| After **you pick** one direction from the matrix | Deepen direction | `strategy.md` (`4-plan` / `5-stress-test`) |
| Before real applications | Tactical extension (L3) | `render-execution` → `execution_pack.md` |
| While applying | Long-term correction (L4) | `track` / `replan` → revised matrix |

> `render-pack` → `job_pack.md` is an overlapping summary view; usually skip unless you want a single rollup doc.

## Highlights

### Shipped (v0.3 · Phases 1–3)

- **L0 Profile building** — Agent dialogue → `profile.yaml` / `narrative.md` / `constraints.yaml`; constraints as hard walls
- **Project scan (profile evidence)** — `scan-projects` harvests stack/deps/scale/papers from opted-in repos (not whole-disk)
- **L1 Explore world** — `scan-plan` derives queries; `new-signal` dedupes by topic (source + date required)
- **Pipeline orchestration** — `status` / `run --stage` stage detection and next-step hints
- **Opportunity matrix (core)** — `render-opportunities` → `opportunities.md`; four modules per direction
- **L2 Match engine v1** — `match`: skill alignment, competition intensity, shallow-role penalties
- **Industry / role knowledge** — Industry Graph + Role Taxonomy backing matrix generation
- **(Optional) execution pack** — `render-execution` → `execution_pack.md`
- **(Optional) track + replan** — application funnel feedback loop
- **JD analysis** — `jd-analyze` skill terms vs profile gaps
- **Saved JD watchlist** — `job add/list/show/analyze/remove` → `saved_jobs.yaml`
- **Preset hot-track pool** — 9 industries with deep/shallow trap labels
- **(Optional) stress-test** — pre-mortem + tripwires (playbook 5)
- **Agent Skill** — conversational intake in Claude Code / Cursor
- **GUI chat** — same intake via `career-compass-app --web` 对话 Tab
- **CLI + GUI tabs** — validate, scan, match, view matrix

### Planned (Phase 4+)

- **Scan agent cluster** — automated web research → signals
- **Periodic rescan** — stale-signal reminders
- **Multi-profile / forkable industry knowledge packs**

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

Five user-journey steps map 1:1 to engine stages (don’t mix aliases). Completion criteria: [`docs/user-journey.md`](docs/user-journey.md).

```
Know yourself → Explore world → Decide → Act → Track
    intake         scan        analyze  execute  track
```

| Step | System layer | Main outputs | Required |
|------|--------------|--------------|----------|
| Know yourself | L0 Profile | `profile.yaml` · `constraints.yaml` · `narrative.md` | ✅ |
| Explore world | L1 Explore | `signals/*.yaml` · `saved_jobs.yaml` | ✅ |
| Decide | L2 Decide | `opportunities.yaml` → `opportunities.md` | ✅ **core** |
| Act | L3 Act | `execution_pack.md` (`render-execution`) | optional |
| Track | L4 Track | `applications.yaml` → `replan` revised matrix | optional |

**Optional deepening** (after **you pick** a direction from the matrix): `plan` → `strategy.md`; `stress-test` → revise strategy.

GUI top bar shows user journey; CLI / Agent use engine stage names. `uv run career-compass status` prints both layers.

## CLI

| Command | Purpose |
|---------|---------|
| `uv run career-compass status` | Detect pipeline stage and next steps |
| `uv run career-compass run [--stage STAGE]` | Stage orchestration (intake → scan → analyze) |
| `uv run career-compass validate` | Profile/constraints completeness (errors vs warnings) |
| `uv run career-compass brief` | Aggregate analysis brief |
| `uv run career-compass scan-plan` | Derive search queries from profile |
| `uv run career-compass new-signal DOMAIN TOPIC FINDING SOURCE [URL]` | Append external signal |
| `uv run career-compass scan-projects <path>...` | Harvest project evidence |
| `uv run career-compass render-opportunities` | Render opportunity matrix |
| `uv run career-compass render-strategy` | Render `strategy.md` skeleton (after you pick a direction) |
| `uv run career-compass match [--write-draft]` | Matching engine; optional `opportunities.draft.yaml` |
| `uv run career-compass render-pack [--stdout]` | (Optional) rollup → `job_pack.md` |
| `uv run career-compass render-execution [--stdout]` | (Optional) tactical extension → `execution_pack.md` |
| `uv run career-compass track add/list/update/funnel` | Application tracking → `applications.yaml` |
| `uv run career-compass replan [--write]` | Feedback loop → suggestions / `opportunities.revised.yaml` |
| `uv run career-compass job add/list/show/analyze/remove` | Saved JD watchlist |
| `uv run career-compass jd-analyze <file>` | JD vs profile gaps |

See `docs/matching-engine.md` (Phase 2), `docs/phase-3.md` (Phase 3), `docs/schema-v2.md`.

## Documentation & languages

| Language | Files |
|----------|-------|
| **English (default)** | This file · [CLAUDE.md](CLAUDE.md) · [SKILL.md](SKILL.md) |
| 简体中文 | [README.zh-CN.md](README.zh-CN.md) · [CLAUDE.zh-CN.md](CLAUDE.zh-CN.md) · [SKILL.zh-CN.md](SKILL.zh-CN.md) |

Playbooks under `playbooks/` and some `docs/` remain Chinese (agent conversation scripts).

## Design principles

- **Evidence-driven** — strengths need proof; signals need sources; scores cite rationale; never treat model priors as “retrieved signals”
- **Constraints are walls** — geo, family, age, risk appetite filter out options, not just down-rank
- **Deep vs shallow** — shallow hot-track roles get explicit traps and score caps
- **Options, not verdicts** — top-N directions; user commits before `4-plan`
- **Data vs code** — facts in `data/`; agent logic in `playbooks/` (gradually codified in match engine); `src/` validates/renders
- **Iterable** — git history, signal staleness, tripwires → replan

## Roadmap

| Phase | Focus | Key outputs |
|-------|--------|-------------|
| **Phase 1** | Pipeline foundation | `run`/`status` orchestrator; tighter validate; Schema 2.0; scan dedup ✅ |
| **Phase 2** | Market sensing + role graph | Industry Graph, Role Taxonomy, competition index, skill gaps, job pack v1 ✅ |
| **Phase 3** | Execution + feedback | execution pack, track, replan, jd-analyze ✅ |
| **Phase 4** | Continuous intel OS | periodic rescan, multi-profile, forkable industry packs |

## Status

**v0.3 · Phases 1–3 shipped** — main flow: profile → match → **opportunity matrix** (core). Optional: execution pack, track, replan. Phase 4 (automated scan agents, intel OS) planned.

## License

MIT © Peng Kangzhen
