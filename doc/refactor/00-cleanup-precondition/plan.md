# 00 — Cleanup / Precondition

## Objective

Strip Claude-Code-specific plumbing prose from skill bodies as a one-time source-side cleanup, **before** the multi-target refactor begins. The work is platform-agnostic improvement: cleaner source benefits Claude Code today and unblocks OpenCode (and any future target) tomorrow.

## Why This Cluster Exists

Several skill bodies currently mix **workflow instructions** (steps the agent should take) with **platform plumbing documentation** (descriptions of Claude Code hook events, cache paths, settings files, and tool-taxonomy rules naming specific Claude tools). The plumbing prose is:

1. **Not beneficial on Claude either** — it documents implementation details of mechanisms that exist outside the skill's workflow scope. Reference docs are the right home.
2. **Misleading on OpenCode** — the prose describes Claude-only mechanisms that have no equivalent (or a different equivalent), so the agent reading the body sees instructions tied to a platform it isn't running on.
3. **A precondition for clean target generation** — until skill bodies stop coupling themselves to one platform's tool names and filesystem layout, no body emitter can produce a clean OpenCode artifact, and no body transform can bridge the gap because the LLM has to interpret the prose against the wrong target.

This cluster is therefore **a precondition**, not a workaround. It runs first so the rest of the refactor (clusters 01–06) operates on already-clean source.

## Scope

### In scope

Source-side, pure prose changes to skill bodies and their `references/` siblings:

- Move Claude-only mechanism descriptions out of skill bodies into `references/{topic}.md`
- Rephrase tool-name rules platform-agnostically (no specific tool names in rules; describe the *role* instead)
- Remove `.claude/` filesystem references from prose that aren't part of `platform-runtime` call sites
- Remove cache/session-resolver descriptions from skill bodies

### Out of scope

- Any change to behaviour or the operations skills perform (those are addressed in [03 — Refactor for Portability](../03-refactor-for-portability/plan.md))
- The `platform-runtime` API design ([01](../01-design-platform-api/plan.md))
- The target generator framework ([02](../02-build-system/plan.md))
- Body transforms applied at emit time ([02](../02-build-system/plan.md) "Body Transforms")
- Any new skill, agent, or command

This cluster never runs `platform-runtime` calls, never adds `runtime.target` to `marshal.json`, never touches the executor. It is pure source housekeeping.

## Audit Checklist

Search every skill body in `marketplace/bundles/*/skills/*/SKILL.md` for these patterns:

| Pattern | Violation | Fix |
|---------|-----------|-----|
| Claude tool name in a rule (e.g. `EnterPlanMode`, `ExitPlanMode`, `AskUserQuestion`, `Agent(subagent_type=…)`, `TaskCreate`, `Task:`, etc.) | Couples skill prose to one target's tool taxonomy | Rephrase platform-agnostically — describe the *role* (e.g. "the host platform's plan-mode tools", "the user-question tool", "an unconstrained generic subagent"). Do not name a specific tool in instructional rules. |
| Skill body section describing a Claude Code hook mechanism (terminal title, statusLine, `SessionStart`, `UserPromptSubmit`, `PostToolUse`, `Stop`, etc.) | Documentation for a Claude-only mechanism inside a workflow body | Move section into `marketplace/bundles/{bundle}/skills/{skill}/references/{topic}.md` |
| Skill body section describing a Claude-only cache or session-resolver pipeline (e.g. `~/.cache/plan-marshall/sessions/...`, transcript-file walking, JSONL parsing) | Same as above — documents plumbing, not workflow | Move section into `references/{topic}.md` |
| `.claude/` path mentioned in passing prose outside of a `platform-runtime` call site | Couples skill prose to one target's filesystem layout | Either rephrase to use `platform-runtime` (if it describes a call), or remove the prose if it described platform plumbing now living in `references/`. |
| `~/.claude/...` path in prose outside of `platform-runtime` call sites | Same as above | Same as above |

## Concrete Cleanup Tasks

The walk-through of the `plan-marshall` entry skill identified these specific items. Other skills are swept against the audit checklist as a follow-up.

### `plan-marshall` (entry skill at `marketplace/bundles/plan-marshall/skills/plan-marshall/SKILL.md`)

| Issue | Action |
|-------|--------|
| "Terminal Title Integration" section (~25 lines describing `SessionStart`/`UserPromptSubmit`/`PostToolUse`/etc. hooks and `.claude/settings.local.json`) | Move to `marketplace/bundles/plan-marshall/skills/plan-marshall/references/terminal-title.md`. Add a one-line pointer in the SKILL body for users who want details. |
| "Session ID Resolver" section (~15 lines describing the Claude-only hook-populated cache at `~/.cache/plan-marshall/sessions/...`) | Move to `references/session-id-resolver.md`. Add a one-line pointer in the SKILL body. |
| Rule "Never use Claude Code's built-in `EnterPlanMode` or `ExitPlanMode`" | Rephrase as "Never use the host platform's built-in plan-mode tools — this skill implements its own plan system" |
| Rule "All user interactions use `AskUserQuestion` tool with proper YAML structure" | Rephrase as "All user interactions use the user-question tool with proper YAML structure" (omit the platform-specific tool name) |
| Rule "Never spawn `Agent(subagent_type=\"general-purpose\")`" | Rephrase as "Never spawn an unconstrained generic subagent — always specify a plan-marshall agent or skill" |

### Other bundles (sweep)

Apply the audit checklist to every skill body in:

| Bundle | Expected scope of cleanup |
|--------|---------------------------|
| plan-marshall | Already largely covered above; sweep remaining skills (`marshall-steward`, `phase-*`, etc.) for any leftover Claude tool-name rules and `.claude/` prose |
| pm-plugin-development | Possible plugin-path references in `plugin-doctor`, `plugin-create`, `plugin-maintain` |
| pm-dev-java | Likely clean (Java standards) |
| pm-dev-java-cui | Likely clean |
| pm-dev-frontend | Likely clean |
| pm-dev-frontend-cui | Likely clean |
| pm-dev-oci | Likely clean |
| pm-dev-python | Likely clean |
| pm-documents | Likely clean |
| pm-requirements | Likely clean |

A bundle is "clean" for this cluster's purposes when no audit-checklist pattern matches. Findings get logged and fixed in the same pass.

## What Cleanup Does NOT Touch

These remain untouched by this cluster — they are the next cluster's concern:

- `platform-runtime` call sites (e.g. `python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime …`) — those are added in [03](../03-refactor-for-portability/plan.md), not removed here
- `Skill: bundle:skill` directives — the source line stays as-is; the OpenCode emitter rewrites them mechanically per [02](../02-build-system/plan.md) "Body Transforms"
- `/skill-name` slash references in usage examples — same; the emitter rewrites them per [02](../02-build-system/plan.md) "Body Transforms"
- `user-invocable: true` frontmatter — left as-is; the emitter dual-emits per [02](../02-build-system/plan.md) "User-Invocable Skills (Dual Emission)"
- Any `.claude/settings.local.json` write that **is** a behavioural call (e.g. inside a marshall-steward step that patches settings) — those move to `platform-runtime permission configure` calls in [03](../03-refactor-for-portability/plan.md)

## Verification

This cluster is complete when:

1. No skill body contains a Claude tool name (`EnterPlanMode`, `ExitPlanMode`, `AskUserQuestion`, `Agent(subagent_type=…)`, `TaskCreate`, `Task:`, etc.) inside an instructional rule. Rules describe the *role*, not the tool.
2. No skill body contains a section describing a Claude-only hook mechanism (terminal title, status-line, `SessionStart`, `UserPromptSubmit`, `PostToolUse`, etc.). Such content lives in `references/{topic}.md`.
3. No skill body contains a section describing a Claude-only cache or session-resolver pipeline. Same — `references/{topic}.md`.
4. Every `.claude/` and `~/.claude/...` mention in skill bodies is either:
   - inside a `platform-runtime` call site (left as-is for cluster 03 to refactor), or
   - removed because it described platform plumbing now living in `references/`.
5. The `plan-marshall` entry skill has its "Terminal Title Integration" and "Session ID Resolver" sections moved to `references/terminal-title.md` and `references/session-id-resolver.md` respectively, with a one-line pointer remaining in the SKILL body.
6. `./pw verify` passes — cleanup must not regress anything on Claude Code (this is the canary).
7. A grep over `marketplace/bundles/*/skills/*/SKILL.md` for the audit-checklist patterns returns no hits (or hits are explicitly classified as out-of-scope for this cluster — e.g. lines inside fenced code blocks demonstrating something).

## Dependencies

**None.** This is the precondition cluster. It must complete before [03 — Refactor for Portability](../03-refactor-for-portability/plan.md) starts, because cluster 03's behavioural rewrites apply on top of clean source. Clusters 01, 02, 05, and 06 do not depend on cluster 00 directly but benefit from running on cleaned-up source.

## Why This Is a Standalone Cluster

Pulling cleanup out of cluster 03 has three benefits:

1. **Risk separation.** Source prose changes are low-risk and reviewable independently of the platform-runtime API design and skill-behaviour rewrites in cluster 03. A bad rephrase is a one-line fix; a bad `platform-runtime permission configure` migration may break the wizard.
2. **Faster Claude Code wins.** Skill bodies focused on workflow rather than plumbing are a Claude-Code-only improvement that lands without waiting for any of the multi-target work.
3. **Clean precondition for any future target.** A cluster-00 sweep happens once. Future targets (Cursor, Codex, others) inherit the cleaned source without revisiting prose.
