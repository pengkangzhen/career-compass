**English** | [简体中文](CLAUDE.zh-CN.md)

# CLAUDE.md — Project instructions (auto-loaded when Claude Code opens this repo)

This project is **Beidou / 北斗星** (repo name `career-compass`): a pre-application career decision engine. When the user talks about career planning, direction choice, job search, industry trends, or application feedback, run the Beidou workflow.

## North star

Analyze **profile × industry structure × trends × competition** and return **ranked, evidence-backed, actionable** positioning and execution options. The system **never** chooses for the user.

## What it is

**Primary surfaces — conversational intake** (both write `data/` + `validate`):

| Surface | How |
|---------|-----|
| **Agent Skill** | Claude Code / Cursor — this file + `playbooks/` |
| **GUI chat** | `career-compass-app --web` → 对话 Tab |

**Also**: CLI pipeline; GUI tabs for viewing profile · trends · matrix.

- `SKILL.md` / `.cursor/skills/career-compass/` — installable agent skill
- `playbooks/` — stage scripts (intake / scan / analyze / …)
- `src/career_compass/` — CLI + optional GUI app
- `data/` — single source of truth per user (gitignored)

## Workflow

1. **intake** — guided profile → `profile.yaml`, `narrative.md`, `constraints.yaml`
2. **scan** — `scan-plan` → web research → `new-signal`
3. **analyze** — `brief` → `match --write-draft` → review `opportunities.yaml` → `render-opportunities` / `render-pack`
4. **execute (Phase 3)** — `render-execution` → `track` applications → `funnel` → `replan`
5. **plan / stress-test** — optional, only after user picks a direction

**Orchestration**: `status` / `run --stage`

## Command cheat sheet

| Command | Purpose |
|---------|---------|
| `status` / `run [--stage]` | Stage detection and preflight |
| `validate` / `brief` / `scan-plan` / `new-signal` / `scan-projects` | intake + scan |
| `match [--write-draft]` / `render-opportunities` / `render-pack` | analyze + job pack |
| `render-execution` | execution pack (pitch, resume hints, apply strategy) |
| `track add/list/update/funnel` | application tracking |
| `job add/list/show/analyze/remove` | saved JD watchlist → `saved_jobs.yaml` |
| `jd-analyze <file>` | JD vs profile skill gaps |

## Rules

- Every strength needs evidence; every signal needs source + date
- Opportunity matrix offers **several** directions — do not collapse to one
- Constraints are **hard walls**, not soft penalties
- Do not hand-edit rendered `.md` files; change YAML and re-render

## Current status

**v0.3 · Phases 1–3** — Industry graph, role taxonomy, match, render-pack, render-execution, track, replan, jd-analyze are available.

Docs: `docs/schema-v2.md`, `docs/matching-engine.md`, `docs/phase-3.md`, [SKILL.md](SKILL.md)

Chinese agent guide: [CLAUDE.zh-CN.md](CLAUDE.zh-CN.md)
