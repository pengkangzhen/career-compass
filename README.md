**English** | [简体中文](README.zh-CN.md)

# Beidou (北斗星)

> A **pre-application** career decision engine. Analyzes **profile × industry structure × market trends × competition** to produce evidence-backed, personalized, executable career options — from *which industry and role* to *how to enter, what to avoid, and how to validate*.

Repo codename: `career-compass`. Product name in Chinese: **北斗星** (Big Dipper — navigation metaphor).

## What problem it solves

Not “ask AI what job fits you,” but turn career choice into a **structured, evidence-based, iterable** system in hyper-competitive markets:

| Question | How Beidou helps |
|----------|------------------|
| **Which industry?** | Value chain position, moats/traps, red vs blue ocean, competition density |
| **Which role?** | Role-family matching, seniority band, skill gaps, company tiers, geo strategy |
| **Why would they hire me?** | Evidence-linked profile: projects/papers → verifiable strengths vs JDs |
| **Is timing still OK?** | Trends + personal timeline (graduation, age, visa) |
| **What if I choose wrong?** | Reversibility, stress-tests, tripwires — try before you commit |
| **No replies after applying?** | Application funnel → replan → revise opportunity matrix |

**Core principle**: the system returns **ranked options with rationale**; it does **not** pick for you. Values, family/geo constraints, and final direction stay with the user.

## Why not just ask ChatGPT?

| Generic AI / quizzes | Beidou |
|----------------------|--------|
| Empty forms or vague “what do you like?” | Guided intake + auto harvest from resume/projects |
| Training-data vibes as “signals” | Every signal: **source + date + confidence** |
| One hallucinated direction | Layered deliverables: industry → track → role → companies → 90-day steps |
| Tailwinds only | Explicit **competition density**, shallow-role traps, credential/age barriers |
| One-shot optimism | Pre-mortem + tripwires; un-stress-tested plans aren’t “done” |

## Architecture (target)

```
L0 Evidence     resume/CV · code projects · public info · short dialogue (values/constraints)
       ↓
L1 Intelligence trend · supply/demand · industry graph · role taxonomy agents
       ↓
L2 Matching       hard constraints → multi-axis scores → skill gaps → competition correction
       ↓
L3 Delivery       opportunity matrix · job pack · execution pack · optional plan/stress-test
```

Competition intensity (e.g. credential filtering, saturated tracks, shallow “API wrapper” roles) is a **scoring dimension**, not an afterthought.

## Deliverables

### Strategic — where to go
- Industry / sub-track ranking (deep vs shallow value-chain nodes + `trap` labels)
- Competition density index, timing windows

### Tactical — which door
- Role families (MLE, Applied Scientist, OR Engineer, …)
- Seniority bands, company tiers (stretch / main / safety), geo strategy

### Execution — how to enter
- Skill gap map (JD clusters vs evidence)
- Positioning narrative, resume/portfolio hints, application strategy

### Feedback — after you start applying
- `track funnel`: applied → interview → offer
- `replan`: downgrade composites, add skill gaps → `opportunities.revised.yaml`

### Signature artifact: **Opportunity matrix**
Two layers — **primary career** and **side paths** — sharing one capability stack (not mutually exclusive). Rendered from `opportunities.yaml` → `opportunities.md`.

## Highlights (v0.3 · Phases 1–3)

- Guided profile: `profile.yaml`, `narrative.md`, `constraints.yaml` + strict `validate`
- `scan-projects`: opt-in code/evidence harvest
- `scan-plan` / `new-signal`: profile-driven market signals
- Pipeline: `status` / `run --stage`
- Match engine v1 + Industry Graph + Role Taxonomy + geo filter
- `render-pack`, `render-execution`, `track`, `replan`, `jd-analyze`, saved JD watchlist
- **macOS app** (pywebview): Profile · Trends · Saved jobs · Matrix

## Who it’s for

- People choosing among academia vs industry, research vs engineering, hype vs durable tracks
- Anyone who needs **evidence-backed options** under intense competition (including CN market: tier-1/2 schools, age lines, etc.)
- Users who want choices **versioned and replayable**, not a one-off chat answer

## Quick start

```bash
git clone https://github.com/pengkangzhen/career-compass.git
cd career-compass
uv sync
claude   # open Claude Code in this repo; say "help me with career planning"
```

**macOS desktop app (MVP)** — four tabs: Profile · Trends · Saved jobs · Opportunity matrix

```bash
uv sync --group gui
uv run career-compass-app
```

Requires [uv](https://docs.astral.sh/uv/) + [Claude Code](https://claude.com/claude-code) (or any agent that reads `CLAUDE.md`). App icon: `assets/app-icon.png`.

## Workflow

```
1-intake       guided profile        → profile / narrative / constraints     [required]
2-scan         web research          → signals/*.yaml (sourced + dated)      [required]
3-analyze      four-axis scoring     → opportunities.yaml → .md  ★core★   [required]
3b-execute     applications          → execution pack → track → replan      [optional]
4-plan         deepen one direction  → strategy.md                         [optional, user picks]
5-stress-test  pre-mortem            → revise strategy                     [optional]
```

Phases 1–3 end at the **opportunity matrix**. Phases 4–5 only after the **user** selects a direction.

## CLI

| Command | Purpose |
|---------|---------|
| `uv run career-compass status` | Detect pipeline stage and next steps |
| `uv run career-compass run [--stage STAGE]` | Stage orchestration |
| `uv run career-compass validate` | Profile/constraints completeness |
| `uv run career-compass brief` | Aggregate analysis brief |
| `uv run career-compass scan-plan` | Derive search queries from profile |
| `uv run career-compass new-signal DOMAIN TOPIC FINDING SOURCE [URL]` | Append external signal |
| `uv run career-compass scan-projects <path>...` | Harvest project evidence |
| `uv run career-compass render-opportunities` | Render opportunity matrix |
| `uv run career-compass match [--write-draft]` | Matching engine |
| `uv run career-compass render-pack` | Job positioning pack |
| `uv run career-compass render-execution` | Execution pack |
| `uv run career-compass track add/list/update/funnel` | Application tracking |
| `uv run career-compass replan [--write]` | Feedback loop |
| `uv run career-compass job add/list/show/analyze/remove` | Saved JD watchlist |
| `uv run career-compass jd-analyze <file>` | JD vs profile gaps |

See `docs/matching-engine.md`, `docs/phase-3.md`, `docs/schema-v2.md`.

## Design principles

- **Evidence-driven** — strengths need proof; signals need sources; scores cite rationale
- **Constraints are walls** — geo, family, age, risk appetite filter out options, not just down-rank
- **Deep vs shallow** — shallow hot-track roles get explicit traps and score caps
- **Options, not verdicts** — top-N directions; user commits before `4-plan`
- **Data vs code** — facts in `data/`; agent logic in `playbooks/`; `src/` validates/renders
- **Iterable** — git history, signal staleness, tripwires → replan

## Documentation & languages

| Language | Agent / skill |
|----------|----------------|
| **English (default)** | [CLAUDE.md](CLAUDE.md) · [SKILL.md](SKILL.md) |
| 简体中文 | [CLAUDE.zh-CN.md](CLAUDE.zh-CN.md) · [SKILL.zh-CN.md](SKILL.zh-CN.md) |

Playbooks under `playbooks/` are currently **Chinese** (agent conversation scripts). Technical docs in `docs/` are mixed; PRs for English docs welcome.

## Roadmap

| Phase | Focus | Status |
|-------|--------|--------|
| 1 | Pipeline, validate, Schema 2.0 | ✅ |
| 2 | Industry graph, match, job pack | ✅ |
| 3 | Execution pack, track, replan, JD | ✅ |
| 4 | Continuous intel OS, multi-profile | planned |

## Status

**v0.3** — Phases 1–3 shipped. Phase 4 (automated scan agents, intel OS) planned.

## License

MIT © Peng Kangzhen
