**English** | [简体中文](CLAUDE.zh-CN.md)

# CLAUDE.md — Project instructions (auto-loaded when Claude Code opens this repo)

This project is **Beidou / 北斗星** (repo name `career-compass`): a pre-application career decision engine. When the user talks about career planning, direction choice, job search, industry trends, or application feedback, run the Beidou workflow.

## North star

Build on two foundational layers — **profile × industry structure** — then layer **trend signals** and **competition intensity** as evaluation metrics, to return **ranked, evidence-backed** direction options. Beidou stops at the decision (opportunity matrix); resume optimization, apply strategy, and interview prep are out of scope. The system **never** chooses for the user.

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

**Core flow (L0–L2):**

1. **intake** — guided profile → `profile.yaml`, `narrative.md`, `constraints.yaml`
2. **scan** — `scan-plan` → web research → `new-signal`; `job add` for saved JD watchlist
3. **analyze** — `brief` → `match --write-draft` → review `opportunities.yaml` → `render-opportunities` ★ core deliverable ★

**Optional deepening (still L2):**

4. **plan / stress-test** — only after the user explicitly picks one direction from the matrix

**Out of scope (legacy CLIs retained, not maintained):** `render-execution` / `track` / `replan` / `jd-analyze` — resume optimization, apply strategy, interview prep, funnel tracking belong to downstream accelerator tools.

**Orchestration**: `status` / `run --stage`

## Command cheat sheet

**Main flow:**

| Command | Purpose |
|---------|---------|
| `status` / `run [--stage]` | Stage detection and preflight |
| `validate` / `brief` / `scan-plan` / `new-signal` / `scan-projects` | intake + scan |
| `match [--write-draft]` / `render-opportunities` / `render-pack` | analyze + job pack |
| `job add/list/show/analyze/remove` | saved JD watchlist → `saved_jobs.yaml` (part of L1 explore) |

**Legacy (apply-side, not in main scope):**

| Command | Purpose |
|---------|---------|
| `render-execution` | execution pack (pitch, resume hints, apply strategy) |
| `track add/list/update/funnel` | application tracking |
| `replan [--write]` | feedback loop |
| `jd-analyze <file>` | JD vs profile skill gaps |

## Rules

- Every strength needs evidence; every signal needs source + date
- Opportunity matrix offers **several** directions — do not collapse to one
- Constraints are **hard walls**, not soft penalties
- Do not hand-edit rendered `.md` files; change YAML and re-render
- **Scope discipline**: stop at the opportunity matrix; do not pull Beidou into resume/apply/interview territory

## Current status

**v0.4 · main scope narrowed to L0–L2** — main flow ends at the opportunity matrix. Apply-side legacy tools (`render-execution` / `track` / `replan` / `jd-analyze`) retained from Phase 3 but no longer part of the narrative or active development.

Docs: `docs/schema-v2.md`, `docs/matching-engine.md`, [SKILL.md](SKILL.md). (`docs/phase-3.md` documents legacy apply-side tooling — read only if you must touch those CLIs.)

Chinese agent guide: [CLAUDE.zh-CN.md](CLAUDE.zh-CN.md)
