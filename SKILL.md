---
name: career-compass
description: Beidou (北斗星) — pre-application career decision engine. Foundational layers (profile × industry structure) layered with trend/competition metrics → opportunity matrix. Stops at the decision; apply-side tools are legacy. Use when the user wants career planning, industry/role choice, or direction validation. **Intake: agent dialogue (Claude Code/Cursor) OR GUI chat** — both write data/ + CLI. Flow intake→scan→analyze→optional plan/stress-test.
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
External signals (signals/*.yaml, sourced + dated) · saved JDs (saved_jobs.yaml)
        ↓
   Four-axis analysis
        ↓
Opportunity matrix: opportunities.yaml → opportunities.md  ★ core deliverable ★
        ⛔  (Beidou stops here)
        ↓ (optional, still within L2 decision layer)
   strategy.md → stress test
```

`data/` is the single source of truth; `playbooks/` holds analysis logic; `src/` (career-compass CLI) validates, harvests, and renders — it does not judge.

Resume optimization, apply strategy, interview prep, and application-funnel tracking are **out of scope** — left to downstream accelerator tools. Legacy CLIs (`render-execution` / `track` / `replan` / `jd-analyze`) remain in the repo but are not part of the main narrative.

## Stages

**Core flow (L0–L2):**

| Stage | Required | When | Your job |
|-------|----------|------|----------|
| **1-intake** | yes | First visit / incomplete profile | Dialogue → fill profile files → `uv run career-compass validate` until clean |
| **2-scan** | yes | Profile ready, need market intel | `scan-plan` → web search → `new-signal` each finding (**source + date**); `job add` for JD watchlist |
| **3-analyze** | yes | Profile + signals exist | `brief` → optional `match --write-draft` → review `opportunities.yaml` → `render-opportunities` (★ core ★) |

**Optional deepening (still within L2 decision layer):**

| Stage | When | Your job |
|-------|------|----------|
| **4-plan** | **User chose one** matrix direction | `playbooks/4-plan.md` → `strategy.md` |
| **5-stress-test** | Plan done | `playbooks/5-stress-test.md` pre-mortem → revise `strategy.md` |

**Legacy (apply-side, out of main scope):** `render-execution` / `track` / `replan` / `jd-analyze` — retained from Phase 3, not actively developed.

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

**Main flow:**

```bash
uv run career-compass status
uv run career-compass run [--stage STAGE]
uv run career-compass match [--write-draft]
uv run career-compass render-opportunities
uv run career-compass job add "Company" "Role" [--direction "..."]   # saved JD watchlist
```

**Legacy apply-side CLIs (out of main scope):**

```bash
uv run career-compass render-pack
uv run career-compass render-execution
uv run career-compass track add "Company" "Role" [--tier B] [--direction "..."]
uv run career-compass track funnel
uv run career-compass replan [--write]
uv run career-compass jd-analyze jd.txt
```

**Main analyze path**: `brief` → `match --write-draft` → playbook 3 review → `render-opportunities` ★ core deliverable ★

Legacy apply-side flow (`docs/phase-3.md`): `render-execution` → `track` → `funnel` → `replan --write`. Not maintained as product surface.

## Rules

1. **Every strength needs evidence** — `validate` blocks unsupported claims.
2. **Every external signal needs source and date** — vibes are not signals.
3. **The opportunity matrix is the deliverable** — offer **several** directions; do not collapse to one.
4. **Never choose for the user** — stage 4-plan only after explicit user choice.
5. **Facts in `data/`, logic in `playbooks/`** — edit `opportunities.yaml`, re-render `.md`.
6. **Constraints are walls** — violating options are removed, not down-ranked.
7. **Scope discipline** — stop at the opportunity matrix; do not pull Beidou into resume/apply/interview territory.

Chinese skill doc: [SKILL.zh-CN.md](SKILL.zh-CN.md)
