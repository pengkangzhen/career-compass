---
name: career-compass
description: Beidou (北斗星) — pre-application career decision engine. Profile × industry trends × match engine → opportunity matrix and job-search execution loop. Use when the user wants career planning, industry/role choice, or application feedback. **Intake: agent dialogue (Claude Code/Cursor) OR GUI chat** — both write data/ + CLI. Flow intake→scan→analyze→execute(track/replan)→optional plan/stress-test.
---

**English** | [简体中文](SKILL.zh-CN.md)

# Beidou (北斗星)

A **before-you-apply** career planning system.

**Conversational intake — two equivalent paths:**

1. **Coding agent** (Claude Code / Cursor) — this skill + `playbooks/`
2. **GUI chat** — `career-compass-app --web` → 对话 Tab (needs LLM env vars)

Both produce `profile.yaml`, `constraints.yaml`, `narrative.md` and run `validate`.

**Core deliverable: an opportunity matrix** — several comparable, evidence-backed directions. It **does not** pick a path for the user.

## Mental model

```
Profile (profile.yaml + narrative.md + constraints.yaml)
        ×
External signals (signals/*.yaml, sourced + dated)
        ↓
   Four-axis analysis
        ↓
Opportunity matrix: opportunities.yaml → opportunities.md
        ↓
Job pack · execution pack (Phases 2–3)
        ↓
Application tracking → replan (Phase 3)
        ↓ (optional)
   strategy.md → stress test
```

`data/` is the single source of truth; `playbooks/` holds analysis logic; `src/` (career-compass CLI) validates, harvests, and renders — it does not judge.

## Stages

| Stage | Required | When | Your job |
|-------|----------|------|----------|
| **1-intake** | yes | First visit / incomplete profile | Dialogue → fill profile files → `uv run career-compass validate` until clean |
| **2-scan** | yes | Profile ready, need market intel | `scan-plan` → web search → `new-signal` each finding (**source + date**) |
| **3-analyze** | yes | Profile + signals exist | `brief` → optional `match --write-draft` → review `opportunities.yaml` → `render-opportunities` → `render-pack` |
| **3b-execute** | optional | Applying | `render-execution` → `track add` → `track funnel` → `replan`; JD fit via `jd-analyze` |
| **4-plan** | optional | **User chose one** matrix direction | `playbooks/4-plan.md` → `strategy.md` |
| **5-stress-test** | optional | Plan done | `playbooks/5-stress-test.md` pre-mortem → revise `strategy.md` |

**Stages 1–3 end at the opportunity matrix.** 4–5 only if the user wants to go deep on one direction they selected.

## Where am I in the pipeline?

Run `uv run career-compass status`:

| Condition | Stage |
|-----------|-------|
| No `profile.yaml` or `validate` errors | **1-intake** |
| Profile OK, `signals/` empty or thin | **2-scan** |
| Profile + signals, no `opportunities.yaml` / rendered `.md` | **3-analyze** |
| Matrix exists, `strategy.md` present | **4-plan** (optional) |
| `opportunities.md` rendered | **done** (core deliverable) |

## Pipeline commands

```bash
uv run career-compass status
uv run career-compass run [--stage STAGE]
uv run career-compass match [--write-draft]
uv run career-compass render-pack
uv run career-compass render-execution
uv run career-compass track add "Company" "Role" [--tier B] [--direction "..."]
uv run career-compass track funnel
uv run career-compass replan [--write]
uv run career-compass jd-analyze jd.txt
```

**Analyze path**: `brief` → `match --write-draft` → playbook 3 review → `render-opportunities` → `render-pack` → `render-execution`

**Execute path**: log applications with `track`, check `funnel`, `replan --write` for revisions.

See `docs/phase-3.md`.

## Rules

1. **Every strength needs evidence** — `validate` blocks unsupported claims.
2. **Every external signal needs source and date** — vibes are not signals.
3. **The opportunity matrix is the deliverable** — offer **several** directions; do not collapse to one.
4. **Never choose for the user** — stage 4-plan only after explicit user choice.
5. **Facts in `data/`, logic in `playbooks/`** — edit `opportunities.yaml`, re-render `.md`.
6. **Constraints are walls** — violating options are removed, not down-ranked.

Chinese skill doc: [SKILL.zh-CN.md](SKILL.zh-CN.md)
