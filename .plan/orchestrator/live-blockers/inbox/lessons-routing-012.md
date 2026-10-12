envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-12T13:53:18Z

# Lessons ingest: under Antigravity, the repository's CLAUDE.md is never loaded, and task verification omits the quality gate

Severity: **critical** (operator ruling 2026-10-12: Antigravity issues are the highest priority). Bundle: `plan-marshall` (`marshall-steward` / Antigravity installer, `platform-runtime`, `phase-4-plan`, `phase-5-execute`) and the Antigravity target rules.

Source: pm-mcp-core PLAN-41 (PR #34), Antigravity. Full body: `lessons-routing/lessons-archive/filed-live-blockers/pm-mcp-core-m2-m4-131.md`.

| Message | Statement |
|---|---|
| `pm-mcp-core-m2-m4-131` | Five cascading failures. (1) Antigravity auto-loads only `GEMINI.md`, `AGENTS.md` and `.agents/rules/*.md`; the repo has only `CLAUDE.md` and nothing bridged it, so every standing build rule and prohibition ("never add a plugin without asking", "quality gate: `verify -Ppre-commit`") was invisible. (2) `phase-4-plan` wrote task `verification.commands` with bare `test-compile`/`test -pl …` only, no `quality-gate`. (3) The manifest stamped `verify:quality-gate=per_task`, yet the per-task / Step 10b quality sweep was dropped — the gate ran once in the whole phase. (4) and (5) are filed in the `maven run` and pushed-head messages of this batch. |

Asked for: steward/installer mirrors or links `CLAUDE.md` into `AGENTS.md` (or `.agents/rules/`) for Antigravity; the target rules state the canonical-command-resolution invariant; phase-4 synthesizes the module-scoped `quality-gate` into task verification when the tier is `per_task`, or Step 10b is enforced.

Owner today: partly PLAN-LB-29 (`harness-sync`, running — target emitters and rules). Not re-checked at HEAD by the ingest.
