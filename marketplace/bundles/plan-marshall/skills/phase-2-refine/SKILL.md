---
name: phase-2-refine
description: Iterative request clarification until confidence threshold reached
user-invocable: false
---

# Phase 2: Refine Request

Iterative workflow for analyzing and refining the request until requirements meet confidence threshold.

For detailed step-by-step procedures, see `standards/refine-workflow-detail.md`.

## Foundational Practices

```
Skill: plan-marshall:dev-general-practices
```

## Enforcement

> **Shared lifecycle patterns**: See [phase-lifecycle.md](../ref-workflow-architecture/standards/phase-lifecycle.md) for entry protocol, completion protocol, and error handling convention.

**Execution mode**: Follow workflow steps sequentially. Each step that invokes a script has an explicit bash code block.

**Prohibited actions:**
- Never access `.plan/` files directly — all access must go through `python3 .plan/execute-script.py` manage-* scripts
- Never skip the phase transition — use `manage-status transition`
- Never improvise script subcommands — use only those documented below

**Constraints:**
- Strictly comply with all rules from dev-general-practices, especially tool usage and workflow step discipline

## cwd for `.plan/execute-script.py` calls

> `manage-*` scripts (Bucket A) resolve `.plan/` via `git rev-parse --git-common-dir` and work from any cwd — do **NOT** pin cwd, do **NOT** pass `--project-dir`, and never use `env -C`. Build / CI / Sonar scripts (Bucket B) take `--project-dir {worktree_path}` explicitly when a worktree is active. See `plan-marshall:tools-script-executor/standards/cwd-policy.md`.

## Purpose

Before creating deliverables (phase-3-outline), ensure the request is:
- **Correct**: Requirements are technically valid
- **Complete**: All necessary information is present
- **Consistent**: No contradictory requirements
- **Non-duplicative**: No redundant requirements
- **Unambiguous**: Clear, single interpretation possible

---

## Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |

---

## Workflow Overview

The refine phase executes Steps 1-14 (with optional Steps 3b and 3c). Steps 8-12 form an iterative loop that repeats until confidence reaches the threshold.

### Step 1: Check for Unresolved Q-Gate Findings

On re-entry, address pending Q-Gate findings before re-running analysis. Query with `manage-findings qgate query --phase 2-refine --resolution pending`, resolve each finding, then continue with Steps 4-14.

### Step 2: Log Phase Start

Log `[STATUS] Starting refine phase` to work.log.

### Step 3: Recipe Shortcut

Recipe-sourced plans skip quality analysis entirely. Check `plan_source` metadata; if `recipe`, force `track=complex`, set `confidence=100`, transition phase, and return immediately. Otherwise continue with Steps 3b-14.

### Step 3b: Source Premise Verification

Verify code references in the request narrative against the current codebase before quality analysis. Activates when the request contains verifiable code references (file paths, flags, API names, behavior descriptions). Findings feed into the Correctness dimension in Step 8/10.

For the complete verification procedure, see [source-premise-verification.md](standards/source-premise-verification.md).

### Step 3c: Proposed-Fix Verification

Challenge whether a proposed fix actually solves the documented symptom before confidence aggregation. Activates via semantic LLM judgment when the request narrative proposes a specific code change (command, regex, function body, config edit) — source-agnostic, not gated on header tokens. Constructs a synthetic "would the proposed fix change behavior in the failure scenario?" probe and emits `CORRECTNESS: ISSUE — Proposed fix incomplete` when the probe exposes a gap. Findings feed the same Correctness dimension as Step 3b.

For the complete procedure (extraction, probe construction, result handling, worked example), see [proposed-fix-verification.md](standards/proposed-fix-verification.md).

### Step 4: Load Confidence Threshold

Read `confidence_threshold` from project config (`manage-config plan phase-2-refine get --field confidence_threshold`). Default: `95`.

### Step 5: Load Compatibility Strategy

Read `compatibility` from project config. Valid values:

| Value | Description |
|-------|-------------|
| `breaking` | Clean-slate approach, no deprecation nor transitionary comments |
| `deprecation` | Add deprecation markers to old code, provide migration path |
| `smart_and_ask` | Assess impact and ask user when backward compatibility is uncertain |

No fallback -- fail with error if not configured.

### Step 6: Load Architecture Context

Query architecture with `manage-architecture architecture info`. Extract `project_name`, `project_description`, `technologies`, `module_names`, and `module_purposes` into `arch_context` for use in Steps 8-9. Abort if architecture not found.

### Step 7: Load Request

Load request document with `manage-plan-documents request read`. Extract `title`, `description`, `clarifications`, and `clarified_request`.

### Step 8: Analyze Request Quality

Evaluate the request against five quality dimensions using `arch_context`:

| Dimension | Checks | Finding Format |
|-----------|--------|----------------|
| **Correctness** | Technology/module/API/pattern validity against architecture | `CORRECTNESS: {PASS\|ISSUE}` |
| **Completeness** | Scope clarity, success criteria, test requirements, dependencies | `COMPLETENESS: {PASS\|MISSING}` |
| **Consistency** | No contradictions, aligned constraints, coherent scope | `CONSISTENCY: {PASS\|CONFLICT}` |
| **Non-Duplication** | No repeated or overlapping requirements | `DUPLICATION: {PASS\|REDUNDANT}` |
| **Ambiguity** | Clear terminology, specific scope, measurable criteria, analysis intent | `AMBIGUITY: {PASS\|UNCLEAR}` |

### Step 9: Analyze Request in Architecture Context

Four sub-analyses using `arch_context`:

**Module Mapping**: Identify which modules are affected. Use `architecture module` for detailed info when confidence < 70%, `architecture graph` for cross-module changes.

**Feasibility Check**: Validate request against module boundaries, dependency direction, extension points, and technology fit.

**Scope Size Estimation**: Derive `scope_estimate` from the `module_mapping` using the standard derivation helper (see `standards/refine-workflow-detail.md` Step 9 — Derivation Rules). Allowed values: `none | surgical | single_module | multi_module | broad`. The same enum and rule of thumb is documented in `manage-solution-outline:standards/solution-outline-standard.md` so the value flows unchanged into the solution outline. Persist the derived value to `references.json` via `manage-references set --field scope_estimate` and include it in the Step 13 return TOON.

**Track Selection**: Determine `simple` vs `complex` track using hard-gate triggers:

```
Complex Track triggers (hard gates, OR logic):
  [T1] scope_estimate is multi_module or broad
  [T2] Request contains scope words (all, every, migrate, refactor, etc.)
  [T3] module_mapping uses patterns/globs instead of explicit file paths
  [T4] Domain requires discovery (plugin-dev, documentation, requirements)
       — skipped via escape hatch when explicit paths + narrow scope

If ANY trigger fires → track = complex
If NONE fire AND S1+S2+S3 all true → track = simple
Otherwise → track = complex
```

### Step 10: Evaluate Confidence

Aggregate findings into weighted confidence score:

| Dimension | Weight |
|-----------|--------|
| Correctness | 20% |
| Completeness | 20% |
| Consistency | 20% |
| Non-Duplication | 10% |
| Ambiguity | 20% |
| Module Mapping | 10% |

If confidence >= threshold → Step 13. Otherwise → Step 11.

### Step 11: Clarify with User

Formulate clarification questions from issues found in Steps 8-9. Use AskUserQuestion with specific options. At most 4 questions per iteration, prioritized: Correctness > Consistency > Completeness > Ambiguity > Duplication.

### Step 12: Update Request

Record clarifications via the three-step path-allocate flow: (1) call `manage-plan-documents request path` to get the canonical artifact path, (2) use Edit/Write to update the `## Clarifications` and `## Clarified Request` sections directly in that file, (3) call `manage-plan-documents request mark-clarified` to record the transition. Synthesize an updated request if significant clarifications were made. Loop back to Step 8. See `standards/refine-workflow-detail.md` Step 12 for the full procedure.

### Step 13: Persist and Return Results

When confidence reaches threshold:

1. **Persist module mapping** to `work/module_mapping.toon`
2. **Persist `scope_estimate`** to `references.json` via `manage-references set --field scope_estimate --value {scope_estimate}` (one of `none | surgical | single_module | multi_module | broad`)
3. **Log decisions** to decision.log (scope, domains -- with duplicate guard)
4. **Run Q-Gate verification checks**: module mapping completeness, track-scope consistency, scope realism, confidence justification
5. **Return output**:

```toon
status: success
plan_id: {plan_id}
confidence: {achieved_confidence}
track: {simple|complex}
track_reasoning: {track_reasoning}
scope_estimate: {scope_estimate}
compatibility: {compatibility}
compatibility_description: {compatibility_description}
domains: [{detected domains}]
qgate_pending_count: {0 if no findings}
```

**Data Location Reference**:
- Track/scope decisions: `decision.log` filtered by `(plan-marshall:phase-2-refine)`
- Module mapping: `work/module_mapping.toon`
- Compatibility: marshal.json (phase-2-refine config)
- Clarifications: `request.md` → `clarifications`, `clarified_request`

### Step 14: Transition Phase

Transition from refine to outline with `manage-status transition --completed 2-refine`. Log completion and add visual separator.

---

## Error Handling

| Error | Action |
|-------|--------|
| Architecture not found | Return `{status: error, message: "Run /marshall-steward first"}` and abort |
| Compatibility not configured | Return `{status: error, message: "compatibility not configured. Run /marshall-steward first"}` and abort |
| Request not found | Return `{status: error, message: "Request document missing"}` |
| Max iterations reached (5) | Return with current confidence, flag for manual review |

---

## Related

- [workflow-overview.md](references/workflow-overview.md) - Visual workflow diagrams and data flow
- [refine-workflow-detail.md](standards/refine-workflow-detail.md) - Detailed step-by-step procedures
- [source-premise-verification.md](standards/source-premise-verification.md) - Source premise verification patterns for Step 3b
- [proposed-fix-verification.md](standards/proposed-fix-verification.md) - Proposed-fix verification patterns for Step 3c

### Phase-boundary metric bookkeeping

This skill does not invoke `manage-metrics` itself. The orchestrator
(`plan-marshall:plan-marshall` workflows) records the `2-refine → 3-outline`
boundary via the fused `manage-metrics phase-boundary` call — see
`marketplace/bundles/plan-marshall/skills/manage-metrics/SKILL.md` §
`phase-boundary` for the API. The legacy `end-phase` + `start-phase` +
`generate` sequence is no longer used at orchestrator boundaries.

---

## Integration

**Invoked by**: `plan-marshall:plan-marshall` skill (loaded directly in main context for user interaction)

**Script Notations** (use EXACTLY as shown):
- `plan-marshall:manage-architecture:architecture` - Architecture queries
- `plan-marshall:manage-plan-documents:manage-plan-documents` - Request operations
- `plan-marshall:manage-references:manage-references` - References persistence (track, scope, module_mapping, compatibility)
- `plan-marshall:manage-findings:manage-findings` - Q-Gate findings (qgate add/query/resolve)
- `plan-marshall:manage-logging:manage-logging` - Work and decision logging
- `plan-marshall:manage-config:manage-config` - Project config (threshold, compatibility)
- `plan-marshall:manage-status:manage_status` - Phase transition and lifecycle management

**Persistence Locations**:
- `work/module_mapping.toon`: Module mapping analysis state
- `decision.log`: Track/scope decisions, config reads, domain detection
- `work.log`: Workflow progress (REFINE:N entries)
- `request.md`: clarifications, clarified_request

**Consumed By**:
- `plan-marshall:phase-3-outline` skill (receives track/scope/compatibility in return output; reads module_mapping from work/)
