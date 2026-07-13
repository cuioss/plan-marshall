---
lane:
  class: prunable
  prunable_when: confidence_complete
  cost_size: M
name: phase-2-refine
description: Iterative request clarification until confidence threshold reached
user-invocable: false
mode: workflow
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Phase 2: Refine Request

Iterative workflow for analyzing and refining the request until requirements meet confidence threshold.

For detailed step-by-step procedures, see `standards/refine-workflow-detail.md`.

## Foundational Practices

```text
Skill: plan-marshall:persona-plan-marshall-agent
```

## Enforcement

> **Shared lifecycle patterns**: See [phase-lifecycle.md](../ref-workflow-architecture/standards/phase-lifecycle.md) for entry protocol, completion protocol, and error handling convention.

**Execution mode**: Follow workflow steps sequentially. Each step that invokes a script has an explicit bash code block.

**Prohibited actions:**
- Never access `.plan/` files directly — all access must go through `python3 .plan/execute-script.py` manage-* scripts
- Never skip the phase transition — use `manage-status transition`
- Never improvise script subcommands — use only those documented below
- **Never call mutating `manage-config` verbs during refine.** The verbs `set`, `init`, `sync-defaults`, and `sync-plan-defaults` are forbidden in this phase — they modify project configuration that must remain stable across the confidence loop. Reading config via `get` is permitted.
- **Never write to any path outside `.plan/local/plans/{plan_id}/**` or `.plan/local/worktrees/{plan_id}/**`.** Implementation edits — even when the request narrative reads like an implementation brief, even when an upstream lesson "obviously" needs a doc tweak, even when a test fixture would clarify intent — are the responsibility of phase-5-execute task bodies, NOT phase-2-refine. Refine produces refined-request artifacts only. The recurring anti-pattern (captured as `feedback_phase2_refine_never_implements` in the project memory log) is refine reaching for `Edit` / `Write` against `marketplace/bundles/**`, source files, or any other production path because the request narrative made the change "feel obvious". The Allowed write paths sub-section below is the only writable surface.

**Allowed write paths:**
- `.plan/local/plans/{plan_id}/**` — the plan's request, clarifications, references, status, decisions, and any other plan-scoped artifact.
- `.plan/local/worktrees/{plan_id}/**` — the plan's isolated worktree, EXCLUDING the `marketplace/**`, source, and build-system sub-trees within it. (Refine MAY persist plan-scoped artifacts under the worktree's `.plan/` symlink, but MUST NOT edit the worktree's checked-out source tree — that surface belongs to phase-5-execute.)

Every other path is forbidden. The orchestrator's post-dispatch main-checkout assertion (see `plan-marshall:plan-marshall:planning.md` § "2-Refine Phase" → "Post-dispatch contract assertion") detects violations structurally; the plugin-doctor `REFINE_CONTRACT_VIOLATION` analyzer detects them at edit time.

**Constraints:**
- Strictly comply with all rules from persona-plan-marshall-agent, especially tool usage and workflow step discipline

## cwd for `.plan/execute-script.py` calls

> `manage-*` scripts resolve `.plan/` via the uniform cwd walk-up (ADR-002) — the nearest ancestor of cwd containing `.plan/local`. Phase-2-refine runs on the main checkout, so they resolve to main's `.plan/`; do **NOT** pin cwd, do **NOT** pass routing flags, and never use `env -C`. Build / CI / Sonar scripts accept `--plan-id {plan_id}` (preferred — auto-resolves the worktree via `manage-status get-worktree-path`) or `--project-dir {worktree_path}` (explicit override / escape hatch); the two flags are mutually exclusive. See `plan-marshall:tools-script-executor/standards/cwd-policy.md`.

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

## Phase-Entry Worktree Assertion

The Phase Entry Protocol's `phase_handshake verify --phase 1-init --strict` call (see [`ref-workflow-architecture/standards/phase-lifecycle.md`](../ref-workflow-architecture/standards/phase-lifecycle.md#phase-handshake-verify-phases-2-6)) asserts the worktree-resolution contract before any phase-2-refine work begins. Phase-2-refine runs on the main checkout — the worktree directory and feature branch are not created until phase-5-execute Step 2.5. An empty `worktree_path` while `metadata.use_worktree==true` is ALWAYS `worktree_unresolved` (there is no deferred-window carve-out): a `use_worktree==true` plan carries a real `worktree_path` only once phase-5 materializes the worktree, so an empty path is a metadata defect, not a legitimate transitional state. The strict path-not-found / path-stale failures also fire when `worktree_path` is set but does not resolve cleanly. Plans with `metadata.use_worktree==false` skip the assertion (main-checkout flow). See [`workflow-integration-git/standards/worktree-handling.md`](../workflow-integration-git/standards/worktree-handling.md) for the canonical lifecycle contract.

---

## Dispatched workflows vs inline steps

This phase dispatches under one role key: **`phase-2-refine`** (resolves through `phase-2-refine.default`). The confidence loop (Steps 3b/3c/8/9/10/11/12) iterates *inside* one dispatch envelope; the orchestrator never spawns per-iteration subagents. Mechanical sub-procedures stay inline: Step 3d baseline reconciliation runs via the `workflow-integration-git:baseline-reconcile` script (LLM-bearing classification is bundled into `phase-2-refine`); Step 10 confidence aggregation runs via the `manage-status:aggregate-confidence` script. Step 13.5 q-gate-validation activation is signaled by setting `qgate_validation_required: true` in the phase return TOON; the orchestrator (`plan-marshall:plan-marshall/workflow/planning.md`) reads that flag and issues q-gate-validation as a sibling top-level `Task: plan-marshall:{target}` dispatch — the phase body cannot spawn it directly because the `Task` tool is unavailable inside an `execution-context-{level}` subagent. For the rationale see [dispatch-granularity.md](../extension-api/standards/dispatch-granularity.md) § 3 (Heuristic 2 — bundle when steps share context).

### Loop-invariant inputs (cached at phase entry)

The confidence loop (Steps 3b/3c/8/9/10/11/12) re-evaluates classification, source-premise verification, and confidence aggregation across iterations — but the *inputs* feeding those re-evaluations are loop-invariant: they are written before the loop begins (phase-1-init, phase-2-refine entry) and are not mutated by the loop body. The dispatched agent MUST read each of the following inputs ONCE at phase entry and reference the cached values throughout every loop iteration:

- `request.md` — both `clarified_request` and `original_input` sections (read via `manage-plan-documents request read --plan-id {plan_id}`).
- `references.json` — `domains`, `base_branch`, `worktree_path`, `affected_files`, `change_type` (read via `manage-files read --plan-id {plan_id} --file references.json`). The cached `domains` value is the **widen-only base** for Step 9's file_globs re-merge: Step 9 may UNION newly-matched domains into `references.domains` (never narrow it), so treat the entry-cached `domains` as the lower bound rather than an immutable value — the one sanctioned in-loop write to a loop-invariant input, and monotonic.
- `module_mapping.toon` if present at `.plan/local/plans/{plan_id}/module_mapping.toon` (read via `manage-files read`).
- The architecture topology (read via `manage-architecture overview` at phase entry).

**Prohibited actions:**
- Never re-read loop-invariant inputs inside the confidence-loop body — re-reading inside the loop is envelope-cost waste; resolve all invariant inputs before the loop begins.

See [`extension-api/standards/dispatch-granularity.md`](../extension-api/standards/dispatch-granularity.md) § 5.1 (Heuristic 2 — bundle when steps share context) for the granularity rationale.

---

## Workflow Overview

The refine phase executes Steps 1-14 (with optional Steps 3b and 3c). Steps 8-12 form an iterative loop that repeats until confidence reaches the threshold.

### Step 1: Check for Unresolved Q-Gate Findings

On re-entry, address pending Q-Gate findings before re-running analysis. Query with `manage-findings qgate list --phase 2-refine --resolution pending`, resolve each finding, then continue with Steps 4-14.

### Step 2: Log Phase Start

Log `[STATUS] Starting refine phase` to work.log.

### Step 3: Recipe Shortcut

Recipe-sourced plans skip quality analysis entirely. Check `plan_source` metadata; if `recipe`, force `track=complex`, set `confidence=100`, transition phase, and return immediately. Otherwise continue with Steps 3b-14.

### Step 3b: Source Premise Verification

Verify code references in the request narrative against the current codebase before quality analysis. Activates when the request contains verifiable code references (file paths, flags, API names, behavior descriptions). Findings feed into the Correctness dimension scored in the Analyze Request Quality and Evaluate Confidence steps.

For the complete verification procedure, see [source-premise-verification.md](standards/source-premise-verification.md).

### Step 3c: Proposed-Fix Verification

Challenge whether a proposed fix actually solves the documented symptom before confidence aggregation. Activates via semantic LLM judgment when the request narrative proposes a specific code change (command, regex, function body, config edit) — source-agnostic, not gated on header tokens. Constructs a synthetic "would the proposed fix change behavior in the failure scenario?" probe and emits `CORRECTNESS: ISSUE — Proposed fix incomplete` when the probe exposes a gap. Findings feed the same Correctness dimension as the Source Premise Verification step.

For the complete procedure (extraction, probe construction, result handling, worked example), see [proposed-fix-verification.md](standards/proposed-fix-verification.md).

### Step 3d: Baseline Reconciliation

Sync the target branch and surface overlapping diffs before quality analysis runs against an outdated `main`. Activates whenever the plan has a configured base branch (the default flow). The reconcile script classifies the upstream drift into three outcomes:

1. **`no_overlap`** — upstream commits touch disjoint files. Fast-path: continue without findings.
2. **`overlap_no_content_conflict`** (focused reconcile) — upstream commits touch overlapping files but `git merge-tree` reports zero content conflicts. The script performs a focused `git merge origin/{base_branch}` against the worktree, surfaces ANY real conflicts that arise during the merge, and resolves the drift in-place without re-entering the iterate-to-confidence loop. When the merge succeeds cleanly, the auto-resolved drift produces no finding.
3. **`overlap_with_content_conflict`** — `git merge-tree` reports content conflicts. Emits Q-Gate findings that feed back into Steps 8-12 (the iterate-to-confidence loop is the right place to absorb baseline shifts that cannot be merged mechanically).

Skipped silently for main-checkout flow (`metadata.use_worktree=false`) and when no base branch is configured.

For the complete procedure (sync invocation, diff surfacing, finding-emission contract, three-way classification, focused reconcile/rebase routing), see [refine-workflow-detail.md § Step 3d](standards/refine-workflow-detail.md#step-3d-baseline-reconciliation).

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

### Step 5b: Load Simplicity Strategy

Read `simplicity` from project config (`manage-config plan phase-2-refine get --field simplicity`). The knob mirrors `compatibility`: it tunes how aggressively implementation tasks favour the minimum viable surface over speculative structure. Valid values:

| Value | Description |
|-------|-------------|
| `lean` | Implement the strict minimum; remove or inline surplus structure. Default. |
| `pragmatic` | Prefer minimal, but keep low-risk structure that aids readability. |
| `defensive` | Retain belt-and-suspenders structure (guards, abstraction seams) where the outcome is uncertain. |

The enforcement-critical anti-pattern catalogue lives in the central standard at `ref-code-quality/standards/code-organization.md` [#minimum-viable-code](../ref-code-quality/standards/code-organization.md#minimum-viable-code) and the agent-facing principle at `persona-plan-marshall-agent/standards/agent-behavior-rules.md` (Principle 7); it is intentionally not duplicated here. Default `lean` when unconfigured — unlike `compatibility`, the simplicity knob defaults rather than failing, so existing plans without the key behave as `lean`.

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

Three sub-analyses using `arch_context`:

**Module Mapping**: Identify which modules are affected. Use `architecture module` for detailed info when confidence < 70%, `architecture graph` for cross-module changes.

**Feasibility Check**: Validate request against module boundaries, dependency direction, extension points, and technology fit.

**Scope Size Estimation**: Derive `scope_estimate` from the `module_mapping` using the standard derivation helper (see `standards/refine-workflow-detail.md` Step 9 — Derivation Rules). Allowed values: `none | surgical | single_module | multi_module | broad`. The same enum and rule of thumb is documented in `manage-solution-outline:standards/solution-outline-standard.md` so the value flows unchanged into the solution outline. Persist the derived value to `references.json` via `manage-references set --field scope_estimate` and include it in the Persist and Return Results return TOON.

> **Coverage contract**: `scope_estimate` is the *scope* dial of the two-dial coverage contract; its orthogonal partner is *thoroughness* (how completely in-radius items are covered and how deeply their relations are traced). Refine defaults to roughly T2 / change-set unless the request signals otherwise. See the scope × thoroughness ladders, the grade-to-the-floor rule, and the coupling constraint in [`persona-plan-marshall-agent/standards/thoroughness.md`](../persona-plan-marshall-agent/standards/thoroughness.md).

**Domain Re-merge (file_globs against real `affected_files`)**: Once the module mapping has produced the concrete affected-files set, re-evaluate the `file_globs` (and `always_on`) domain-inclusion legs against the real paths — a stronger file signal than the narrative path tokens available at init. `domain-detect` is a **read verb** — it reads config + request and writes nothing, so this stays inside the refine read-only contract and is NOT a mutating `manage-config` verb. Re-invoke it with the real affected files:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  domain-detect --plan-id {plan_id} --affected-files {comma_separated_affected_files}
```

Read the current `references.domains` (the loop-invariant value cached at phase entry), union the returned `domains` / `glob_matched` / `always_on` sets into it, and re-persist the widened union — refine may **WIDEN** `domains`, never narrow it — via the plan-scoped `set-list` write (an allowed refine write path, not a config mutation):

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references set-list \
  --plan-id {plan_id} \
  --field domains \
  --values {union_csv}
```

Emit one decision-log entry naming any newly-merged domains. The union is monotonic (widen-only), so re-running the re-merge on a later confidence-loop iteration is idempotent once the affected-files set has stabilised.

### Step 10: Evaluate Confidence

Aggregate the per-dimension scores from the Analyze Request Quality and Analyze Request in Architecture Context steps into a single weighted confidence via the deterministic aggregator:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  aggregate-confidence --plan-id {plan_id} \
  --correctness {N} --completeness {N} --consistency {N} \
  --non-duplication {N} --ambiguity {N} --module-mapping {N} \
  --persist
```

The dimension weights are fixed (no LLM judgement remains in this step):

| Dimension | Weight |
|-----------|--------|
| Correctness | 20% |
| Completeness | 20% |
| Consistency | 20% |
| Non-Duplication | 10% |
| Ambiguity | 20% |
| Module Mapping | 10% |

For batch input, the analyzer can stage the per-dimension scores as JSON at `.plan/local/plans/{plan_id}/work/confidence-scores.json` and pass `--scores-file {path}` instead of individual flags. Missing dimensions default to 0 and surface in `missing_dimensions` so the caller can detect a malformed analyzer return.

The script returns `{confidence, breakdown[]{dimension, score, weight, weighted}, missing_dimensions, persisted}`; with `--persist`, the overall confidence also lands in `status.metadata.confidence` so phase-3-outline and downstream consumers can read it without re-running the math.

If confidence >= `confidence_threshold` → the Persist and Return Results step. Otherwise → the Assemble the `refine_prompt` Clarification Envelope step (the leaf assembles the batched envelope and still returns via Persist and Return Results; the orchestrator owns the prompt).

### Step 11: Assemble the `refine_prompt` Clarification Envelope

The dispatched refine leaf **NEVER fires `AskUserQuestion`** — operator input is unreachable inside a dispatched `execution-context` envelope (see [`ref-workflow-architecture/standards/agents.md`](../ref-workflow-architecture/standards/agents.md#leaf-cannot-fire-askuserquestion--return-a-prompt-required-envelope)). When confidence is below threshold, the leaf completes its analysis pass with a **best-judgment `clarified_request`** and batches EVERY open clarification question into ONE `refine_prompt` **prompt-required envelope** carried on the Step 13 return TOON. Formulate the questions from issues found in the Analyze Request Quality and Analyze Request in Architecture Context steps — at most 4, prioritized Correctness > Consistency > Completeness > Ambiguity > Duplication. Author each option string so its label names the branch the orchestrator selects when it is chosen (the option text is a two-sided contract with the behaviour it dispatches).

**HARD constraint (plan-1 one-context-per-phase):** a return → ask → re-dispatch cycle PER question round is rejected. The envelope carries all questions at once; the main-context orchestrator (`plan-marshall/workflow/planning.md` § 2-Refine Phase) fires ONE batched `AskUserQuestion` with each `recommended` default and re-dispatches phase-2-refine **AT MOST ONCE** with every answer baked in. A still-below-threshold second pass returns the current confidence flagged for manual review — the leaf does NOT loop with the operator in-envelope (mirrors the existing max-iterations behaviour). On the re-dispatch, the re-entered leaf records the baked-in answers via Step 12.

See `standards/refine-workflow-detail.md` Step 11 for the `refine_prompt{questions[N]{id,question,header,options,recommended}}` structure.

### Step 12: Update Request

Record clarifications via the three-step path-allocate flow — **mandatory whenever the re-dispatch carried operator answers baked in from the `refine_prompt` envelope**, never optional and never deferred: (1) call `manage-plan-documents request path` to get the canonical artifact path, (2) use Edit/Write to update the `## Clarifications` and `## Clarified Request` sections directly in that file from the baked-in answers, (3) call `manage-plan-documents request mark-clarified` to record the transition. A `not_clarified` return is a hard error that blocks continuation — re-run sub-steps (2) and (3) until `mark-clarified` succeeds. When confidence reaches threshold on the first pass with no clarification round, the Persist and Return Results step still writes a `## Clarified Request` section so `request.md` always carries a clarified narrative. See `standards/refine-workflow-detail.md` Step 12 for the full procedure.

### Step 13: Persist and Return Results

When confidence reaches threshold:

1. **Persist module mapping** to `work/module_mapping.toon`
2. **Persist `scope_estimate`** to `references.json` via `manage-references set --field scope_estimate --value {scope_estimate}` (one of `none | surgical | single_module | multi_module | broad`)
3. **Persist `track`** to `references.json` via `manage-references set --field track --value {track}` (one of `simple | complex`) — symmetric to the `scope_estimate` persist above. The value is **derived from the planning lane**, not from a refine-time classifier: `planning_lane == deep` ⇒ `track = complex` (the deep lane runs the Complex-Track outline); `planning_lane == light` ⇒ `track = simple` (the light lane reuses Simple-Track deliverable authoring by construction). `manage-execution-manifest compose --track` and phase-4-plan read this field as the single source of truth.
4. **Author and persist a commit-style PR title** to `status.json` metadata via `manage-status metadata --set --field pr_title --value "{authored_title}"` — symmetric to the `scope_estimate` / `track` persists above. Author a concise, conventional-commit-style PR title (≤72 chars, imperative mood, `type(scope): summary` shape consistent with this repo's commit convention) from the **clarified request**. `pr_title` is **distinct from the descriptive top-level `title` field** (the plan's human label authored at init): `title` is the human-readable plan label, while `pr_title` is the commit-style PR title consumed at phase-6-finalize `create-pr.md` as the deterministic `--title` source. The value is also returned in the Persist and Return Results return TOON (the **Return output** entry below) so downstream visibility exists.
5. **Log decisions** to decision.log (scope, domains -- with duplicate guard)
6. **Run Q-Gate verification checks**: module mapping completeness, track-scope consistency, scope realism, confidence justification
7. **Signal q-gate-validation activation for the narrative-vs-code-validator** — lesson-derived plans only. When `status.json` reports `plan_source` set to a non-recipe value (i.e., `plan_source` is present and not the literal string `recipe`), the phase sets `qgate_validation_required: true` in its return TOON so the orchestrator (`plan-marshall:plan-marshall/workflow/planning.md`) dispatches `plan-marshall:plan-marshall/workflow/q-gate-validation.md` as a sibling top-level Task after the phase returns. The phase body cannot dispatch q-gate-validation itself because the `Task` tool is unavailable inside an `execution-context-{level}` subagent. Lesson-derived plans encode the source lesson id directly in `plan_source` (e.g., `2026-05-11-08-004`), so the guard MUST treat any non-null, non-`recipe` value as lesson-derived. The orchestrator aggregates the validator's `qgate_pending_count` into the phase's running count before re-evaluating the existing 3-iteration auto-loop predicate. The validator classifies each code claim as `valid`, `stale`, or `invalid`: a `stale` finding is a low-confidence / outline-confirm-required signal (NOT an outright invalid finding), so refine **preserves** any deliverable carrying a `stale` finding as an outline-depth confirmation signal rather than discarding it — the STALE-vs-INVALID verdict definition lives in [`plan-marshall/workflow/q-gate-validation.md` § 2.14](../plan-marshall/workflow/q-gate-validation.md#214-narrative-vs-code-validator) only. See [`refine-workflow-detail.md` Step 13.5](standards/refine-workflow-detail.md#step-135-dispatch-q-gate-validation--lesson-derived-plans-only) for the activation-guard contract and the STALE-preservation rule. The flag is `false` when `plan_source` is absent or equals `recipe`.
8. **Return output**:

```toon
status: success
plan_id: {plan_id}
confidence: {achieved_confidence}
track: {simple|complex}
track_reasoning: {track_reasoning}
scope_estimate: {scope_estimate}
pr_title: {pr_title}
compatibility: {compatibility}
compatibility_description: {compatibility_description}
simplicity: {simplicity}
simplicity_description: {simplicity_description}
domains: [{widen-only multi-valued domain union}]
qgate_pending_count: {0 if no findings}
qgate_validation_required: {true|false}
refine_prompt:
  questions[N]{id,question,header,options,recommended}:
    ...
```

`domains` is the multi-valued union carried in `references.domains` — the detector, `always_on`, and `file_globs` legs plus any operator selections from init. Refine may **widen** it (Step 9's file_globs re-merge against the real `affected_files` unions newly-matched domains in) but never narrows it, so the returned set is a superset of the init-persisted domains.

`qgate_validation_required` is `true` when the lesson-derived plan path activated at Step 13.5 (`plan_source` set and not `recipe`), `false` otherwise. See the q-gate-validation activation entry of the Persist and Return Results step for the orchestrator dispatch contract.

`refine_prompt` is the **prompt-required envelope** assembled at Step 11. It is present **only when confidence is below threshold** and the leaf batched open clarification questions for the operator; on the threshold-reached path it is absent. The main-context orchestrator (`plan-marshall/workflow/planning.md` § 2-Refine Phase) reads it, fires ONE batched `AskUserQuestion` with each question's `recommended` default, and re-dispatches phase-2-refine at most once with every answer baked in. The leaf itself performs no operator-facing interaction. See `standards/refine-workflow-detail.md` Step 11 for the `questions[N]{id,question,header,options,recommended}` structure.

**Data Location Reference**:
- Track/scope decisions: `decision.log` filtered by `(plan-marshall:phase-2-refine)`
- Module mapping: `work/module_mapping.toon`
- Compatibility: marshal.json (phase-2-refine config)
- Simplicity: marshal.json (phase-2-refine config)
- Clarifications: `request.md` → `clarifications`, `clarified_request`

### Step 14: Transition Phase

Transition from refine to outline with `manage-status transition --completed 2-refine`. Log completion and add visual separator.

---

## Output

The Persist and Return Results step (above) is the single source of truth for the return TOON. The minimum contract every workflow doc that implements `ext-point-execution-context-workflow` MUST return is:

```toon
status: success | error
display_detail: "<{confidence}% confidence, track {track}, {qgate_pending_count} pending>"
```

`display_detail` shape on success: `"{confidence}% confidence, track {track}, {qgate_pending_count} pending"` (e.g. `"92% confidence, track complex, 0 pending"`); ≤80 chars, ASCII, no trailing period. On error, carries the short error label from § Error Handling.

All other fields (`plan_id`, `confidence`, `track`, `track_reasoning`, `scope_estimate`, `pr_title`, `compatibility`, `compatibility_description`, `simplicity`, `simplicity_description`, `domains`, `qgate_pending_count`, and the conditional `refine_prompt` batched-clarification envelope) are documented in the Persist and Return Results step above.

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
`phase-boundary` for the API.

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
- `plan-marshall:manage-status:manage-status` - Phase transition and lifecycle management

**Persistence Locations**:
- `work/module_mapping.toon`: Module mapping analysis state
- `decision.log`: Track/scope decisions, config reads, domain detection
- `work.log`: Workflow progress (REFINE:N entries)
- `request.md`: clarifications, clarified_request

**Consumed By**:
- `plan-marshall:phase-3-outline` skill (receives track/scope/compatibility in return output; reads module_mapping from work/)
