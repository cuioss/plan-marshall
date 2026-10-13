envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-12T13:53:18Z
revision=1
amended=2026-10-12T17:15:30Z

# Lessons ingest: under Antigravity, the repository's CLAUDE.md is never loaded, and task verification omits the quality gate

Severity: **critical** (operator ruling 2026-10-12: Antigravity issues are the highest priority). Bundle: `plan-marshall` (`marshall-steward` / Antigravity installer, `platform-runtime`, `phase-4-plan`, `phase-5-execute`, `persona-plan-marshall-agent`) and the Antigravity target rules.

Source: pm-mcp-core PLAN-41 (PR #34), Antigravity. Full bodies: `lessons-routing/lessons-archive/filed-live-blockers/pm-mcp-core-m2-m4-131.md` and `-126.md`.

| Message | Statement |
|---|---|
| `pm-mcp-core-m2-m4-131` | Five cascading failures. (1) Antigravity auto-loads only `GEMINI.md`, `AGENTS.md` and `.agents/rules/*.md`; the repo has only `CLAUDE.md` and nothing bridged it, so every standing build rule and prohibition ("never add a plugin without asking", "quality gate: `verify -Ppre-commit`") was invisible. (2) `phase-4-plan` wrote task `verification.commands` with bare `test-compile`/`test -pl …` only, no `quality-gate`. (3) The manifest stamped `verify:quality-gate=per_task`, yet the per-task / Step 10b quality sweep was dropped — the gate ran once in the whole phase. (4) see the Spotless symptom below. (5) is filed in the pushed-head message of this batch. |
| `pm-mcp-core-m2-m4-126` (symptom of item 1) | With `CLAUDE.md` unread, the agent guessed a formatter: `spotless:apply` failed (`No plugin found for prefix 'spotless'`), it retried with the fully qualified `com.diffplug.spotless:spotless-maven-plugin:apply`, Maven fetched the plugin from Central, and three whitespace/import commits followed. |

Asked for:

- steward/installer mirrors or links `CLAUDE.md` into `AGENTS.md` (or `.agents/rules/`) for Antigravity;
- the target rules state the canonical-command-resolution invariant (formatting resolves through `architecture resolve` to the project's declared quality gate);
- one agent rule, in the base persona and the Antigravity target rules: an unresolvable plugin prefix means the project does not use that plugin — stop, never retry it fully qualified;
- phase-4 synthesizes the module-scoped `quality-gate` into task verification when the tier is `per_task`, or Step 10b is enforced.

Not asked for: a goal guard in `build-maven maven run`. That wrapper is a deliberate pass-through; an effective-POM check would cost a POM evaluation per call and refuse undeclared-but-ordinary goals (`dependency:tree`, `help:effective-pom`, `versions:*`); restricting plugin repositories is the project's own `.mvn` configuration (operator ruling 2026-10-12, which superseded `lessons-routing-014`).

Owner today: partly PLAN-LB-29 (`harness-sync`, running — target emitters and rules). Not re-checked at HEAD by the ingest.
