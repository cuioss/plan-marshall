---
name: phase-5-execute
description: Execute phase skill for plan management. DUMB TASK RUNNER that executes tasks from TASK-*.json files sequentially.
user-invocable: false
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Phase Execute Skill

**Role**: DUMB TASK RUNNER that executes tasks from TASK-*.json files sequentially.

**Execution Pattern**: Locate current task → Execute steps → Mark progress → Next task

**Phase Handled**: execute

## Foundational Practices

```
Skill: plan-marshall:dev-general-practices
```

## Enforcement

> **Shared lifecycle patterns**: See [phase-lifecycle.md](../ref-workflow-architecture/standards/phase-lifecycle.md) for entry protocol, completion protocol, and error handling convention.

**Execution mode**: DUMB TASK RUNNER — locate task, execute steps, mark progress, next task. Follow workflow steps sequentially.

**Prohibited actions:**
- Never access `.plan/` files directly — use manage-* scripts via Bash (Edit/Write tools trigger permission prompts on `.plan/` directories)
- Never skip the phase transition — use `manage-status transition`
- Never improvise script subcommands — use only those documented below
- Never target file paths outside the active git worktree.

**Constraints:**
- Strictly comply with all rules from dev-general-practices, especially tool usage and workflow step discipline
- On phase entry (Step 4), resolve the active worktree absolute path and surface it as a `[STATUS]` work-log line so it stays visible in model context throughout the run.
- Every subagent dispatch (Task / Skill / execution-context invocation) MUST embed the Worktree Header in the dispatch prompt when a worktree is active (see **Dispatch Protocol** below) AND MUST pass `plan_id` as an input parameter to satisfy the subagent's Input Contract (e.g., `execute-task`, `execution-context`). Prompt embedding and parameter passing are both required — the former propagates the constraint through free-form delegation, the latter satisfies the structured interface.

See `workflow-integration-git/standards/worktree-handling.md` for the worktree-specific application of this rule (path convention, never-edit-main-checkout invariant, dispatch header propagation, `--plan-id` two-state contract).

## Phase-Entry Worktree Assertion

The Phase Entry Protocol's `phase_handshake verify --phase {previous_phase_key} --strict` call (see [`ref-workflow-architecture/standards/phase-lifecycle.md`](../ref-workflow-architecture/standards/phase-lifecycle.md#phase-handshake-verify-phases-2-6)) asserts the worktree-resolution contract before any phase-5-execute work begins: when `metadata.use_worktree==true`, `metadata.worktree_path` MUST be non-empty AND filesystem-resolvable (the directory exists AND `git -C {path} rev-parse --show-toplevel` returns the same canonical path). When the assertion fails, the script returns `status: error, error: worktree_unresolved` and (under `--strict`) exits 1 — phase entry refuses to advance until the persisted metadata is repaired. Plans with `metadata.use_worktree==false` skip the assertion (main-checkout flow). The assertion fires uniformly at every phase boundary; see deliverable 8 in the originating lesson plan for the full contract.

**Phase 5 is the materialization phase.** Phases 1–4 only *declare* the worktree intent (`metadata.use_worktree` and `metadata.worktree_branch` written by `phase-1-init`); Step 2.5 below is the single point where the worktree directory and feature branch are actually created on disk. Re-entry semantics: when phase-4-plan's capture ran without a populated `metadata.worktree_path` (because Step 2.5 had not yet executed), the `phase_handshake verify --phase 4-plan --strict` call MUST tolerate the still-empty value at phase-5 entry, then Step 2.5 populates `worktree_path` in both `references.json` and `status.metadata` before any task dispatch. On every subsequent phase-5 re-entry (orchestrator re-dispatch), Step 2.5's idempotence guard observes the populated `worktree_path` and short-circuits — no re-creation, no duplicate `git checkout -b`.

## Dispatch Protocol (Worktree Header)

**REQUIREMENT**: When the plan runs in an isolated worktree (see the `[STATUS] Active worktree` work-log line from Step 4), every subagent dispatch prompt — including `Task:`, `Skill:` invocations that accept free-form prompts, and `execution-context` delegations — MUST begin with the canonical path-free Worktree Header:

```
WORKTREE: --plan-id {plan_id}
Resolved internally via `manage-status get-worktree-path`. All Edit/Write/Read tool calls and tool invocations (git -C, mvn -f, etc.) MUST target the resolved worktree path, NOT the main checkout. See workflow-integration-git/standards/worktree-handling.md for the canonical contract.
```

The header is **path-free**: it carries `--plan-id {plan_id}` rather than the absolute worktree path. The dispatched skill resolves the path internally via `manage-status get-worktree-path --plan-id {plan_id}`. The worktree absolute path MUST NOT appear in dispatch prompts. The complete contract — header semantics, propagation rules, the `--plan-id` two-state binding, and rationale — is documented in `workflow-integration-git/standards/worktree-handling.md` § Dispatch Protocol.

The `[STATUS] Active worktree: ...` work-log line is the observability signal that the worktree was detected; embedding the header in every dispatch prompt is the active propagation mechanism. Skip the header only when no worktree is active.

This applies to every dispatch in the execution loop, including (but not limited to) **Step 6 (Execute Steps)** task dispatches and **Step 9 (Independent Change Verification)** subagent invocations. Child agents must echo the same header verbatim into any further dispatches they issue.

See `standards/operations.md` for the complete set of dispatch pattern templates and `workflow-integration-git/standards/worktree-handling.md` for the worktree-specific application of this rule.

### Common anti-patterns to avoid (mirrored from dev-general-practices)

Each Bash tool call dispatched during execute must contain exactly ONE command. Never combine with newlines, `&`, `&&`, `;`, or inline env-var assignment of the form `VAR=val cmd`. The `VAR=val cmd` shape combines the assignment and the command into one shell argument, which trips the host platform's permission UI and obscures the env-var contract by hiding the variable inside the command line rather than declaring it explicitly.

**Anti-pattern**: `MY_VAR=value python3 some_command.py ...`

**Safe alternative (option A)** — Pass the value as a flag arg:

`python3 some_command.py ... --my-var value`

**Safe alternative (option B)** — Set the env var in the command's invocation header (e.g., a separate `env MY_VAR=…` line, NOT inline) before launching the bash command, or define the value as a Python module-level constant lookup inside the script itself.

See [`dev-general-practices` Hard Rules](../dev-general-practices/SKILL.md#bash-one-command-per-call) for the authoritative source.

## cwd for `.plan/execute-script.py` calls

> `manage-*` scripts (Bucket A) resolve `.plan/` via `git rev-parse --git-common-dir` and work from any cwd. Build / CI / Sonar scripts (Bucket B) bind to a working tree via `--plan-id` when a worktree is active. See `plan-marshall:tools-script-executor/standards/cwd-policy.md` for the Bucket A/B split and `workflow-integration-git/standards/worktree-handling.md` for the worktree-specific application of this rule.

---

## Standards (Load On-Demand)

### Workflow
```
Read standards/workflow.md
```
Contains: Task execution pattern, phase transition, auto-continue behavior

### Operations
```
Read standards/operations.md
```
Contains: Delegation patterns for builds, quality checks, PR creation

### Recovery Patterns
```
Read standards/recovery.md
```
Contains: First-line response to mid-plan `origin/main` advances — stash + merge + pop, with works/does-not-work conditions and rationale vs rebase.

### Test Scaffolding Patterns
```
Read standards/test-scaffolding.md
```
Contains: Canonical `# ruff: noqa: I001, E402` + `sys.path.insert(0, ...)` prologue for tests that import underscore-prefixed sibling modules from `marketplace/bundles/.../scripts/`. Citation: `test/plan-marshall/plan-marshall/test_phase_handshake.py` lines 2 and 20-29.

---

## Dispatched workflows vs inline steps

This phase dispatches under one role key: **`phase-5-execute`** (resolves through `phase-5-execute.default` — one per-task envelope). Each task in the queue gets its own `phase-5-execute` dispatch via the `execute-task` workflow with the task-declared skill list as runtime input. The built-in verification steps (`default:quality_check`, `default:build_verify`, `default:coverage_check`) stay inline as pure build invocations — no LLM judgement, no envelope. Step 9 independent change verification stays inline (three deterministic re-checks: git-diff empty-test, obfuscation-pattern grep, exit-code compare). Steps 11 and 11b verification-failure / quality-gate-failure triage dispatch **`verification-feedback`** under `--phase phase-5-execute --role verification-feedback` once with `producer=build-runner` — the findings live in the per-plan store and the subagent queries them by reference (no inline findings list in the prompt). For the rationale see [dispatch-granularity.md](../extension-api/standards/dispatch-granularity.md) § 2 and § 5.1 (script over dispatch; phase-scoped resolution + producer-mode bundling).

## Execution Loop

### Step 1: Get Routing Context (Once at start)

Get current phase, skill routing, and progress in a single call:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status get-routing-context \
  --plan-id {plan_id}
```

Returns:
```toon
status: success
plan_id: {plan_id}
current_phase: 5-execute
skill: plan-marshall:phase-5-execute
skill_description: Execute phase skill for task implementation
total_phases: 4
completed_phases: 2
phases:
- init: complete
- refine: complete
- execute: in_progress
- finalize: pending
```

Use `current_phase` for logging, `skill` for dynamic routing, and `completed_phases/total_phases` for progress display.

### Step 2: Read Commit Strategy and Execution Manifest (Once at start)

Cache the commit strategy for the entire execute loop:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get --audit-plan-id {plan_id}
```

Extract `commit_strategy` from output. Valid values: `per_deliverable`, `per_plan`, `none`.

**Read the execution manifest** — the manifest is the single source of truth for which Phase 5 verification steps fire. It is composed by `phase-4-plan` Step 8b and stored at `.plan/local/plans/{plan_id}/execution.toon`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  read --plan-id {plan_id}
```

Extract `phase_5.early_terminate` (bool) and `phase_5.verification_steps` (list[string]) from the output.

**Early-terminate decision**: If `phase_5.early_terminate == true`, log the decision and transition directly to `phase-6-finalize` — skip the entire execute loop including Steps 3 through 12:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-5-execute) Early terminate — manifest.phase_5.early_terminate=true; skipping execute loop and transitioning directly to phase-6-finalize"
```

Then jump directly to **Phase Transition** (below) to advance to finalize. Do NOT execute Steps 3–12.

**Otherwise** (`early_terminate == false`): the verification steps to execute at end of phase come from `phase_5.verification_steps` — this **replaces** today's lookup of `marshal.json`'s `phase-5-execute.steps`. The list is consumed by Step 11b (Final Quality Sweep) and the verification dispatch loop. See **Verification Step Types** below for dispatch rules.

The step IDs in the manifest are **bare** (e.g., `quality-gate`, `module-tests`, `coverage`) — translate them to the `default:` prefixed names used by the Built-in Step Dispatch Table by prepending `default:` for built-in steps. Steps that already contain `:` are passed through verbatim (project/skill steps).

---

## Verification Step Types

The `phase_5.verification_steps` list from the manifest contains verification step references. Three step types are supported, distinguished by prefix notation (same model as phase-6-finalize):

| Type | Notation | Resolution |
|------|----------|------------|
| **built-in** | `default:` prefix (e.g., `default:quality_check`) | Execute built-in verification command (see dispatch table) |
| **project** | `project:` prefix (e.g., `project:verify-step-lint`) | `Skill: {notation}` with interface contract |
| **skill** | fully-qualified `bundle:skill` (e.g., `my-bundle:my-verify-step`) | `Skill: {notation}` with interface contract |

**Type detection logic**:
- Starts with `default:` -> built-in type (strip prefix, execute built-in command)
- Starts with `project:` -> project type
- Contains `:` (other) -> fully-qualified skill type

Each verify step declares an `order: <int>` value in its authoritative source — frontmatter on built-in standards docs (`standards/{name}.md`), frontmatter on project-local `SKILL.md` for `project:` steps, and the return-dict `order` field for extension-contributed skills. `marshall-steward` sorts the `steps` list by this value when writing it to `marshal.json`. This skill iterates the list as written and does NOT re-sort or validate `order` at runtime — the persisted order is the runtime order.

### Built-in Step Dispatch Table

| Step Name | Action | Description |
|-----------|--------|-------------|
| `default:quality_check` | Run quality-gate build command | Code quality checks |
| `default:build_verify` | Run full test suite | Build verification |
| `default:coverage_check` | Run coverage build, then parse JaCoCo report | Coverage threshold verification |

**`coverage_check` dispatch**: Resolve via `architecture resolve --command coverage` to run the coverage build, then invoke `build-maven:maven coverage-report` (or `build-gradle:gradle coverage-report`) to parse the JaCoCo report. Pass `--report-path` pointing to the module's target directory and `--threshold` from config.

### Interface Contract for External Steps

Project and skill steps receive these parameters:

```
Skill: {step_reference}
  Arguments: --plan-id {plan_id}
```

Input contract: `--plan-id` only. Retry logic is managed by the task runner (Step 11 triage loop with `verification_max_iterations`), not by the step itself.

**Return Contract** (required TOON output from external steps):

```toon
status: passed|failed
message: "Human-readable summary"

# Optional — only when status: failed
findings[N]{file,line,message,severity}:
src/Foo.java,42,Unused import,warning
src/Bar.java,10,Missing null check,error
```

- `status: passed` → step complete, continue to next step
- `status: failed` + `findings[]` → findings fed into Step 11 triage (fix task creation, suppress, or accept)
- `status: failed` without `findings[]` → treated as single unstructured failure, triaged as one finding

---

### Step 2.5: Materialize Worktree and Feature Branch (Once per phase, idempotent)

Phase 5 is the materialization phase for the worktree. Earlier phases only persisted the *intent* (`metadata.use_worktree`, `metadata.worktree_branch` written by `phase-1-init`); this step creates the worktree directory and feature branch on disk and propagates the resolved path to both `references.json` and `status.metadata.worktree_path` BEFORE Step 3 reads them.

**Idempotence guard (must run first)**: read `metadata.worktree_path` and short-circuit when it is already populated — Step 2.5 has already executed on a prior phase-5 entry, the directory exists on disk, and no re-creation is needed.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read \
  --plan-id {plan_id}
```

Extract `metadata.use_worktree`, `metadata.worktree_branch`, `metadata.worktree_path`, and the plan's `base_branch` (from `references.json` via `manage-references get`). If `worktree_path` is non-empty, log the short-circuit and proceed to Step 3:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (plan-marshall:phase-5-execute) Step 2.5 short-circuit: worktree_path already populated ({worktree_path}) — skipping materialization"
```

**Materialization branch (when `worktree_path` is empty)**: branch on `metadata.use_worktree`.

**Case A — `use_worktree == true`**: create an isolated worktree at the canonical path under `.plan/local/worktrees/{plan_id}` and check out the feature branch from `origin/{base_branch}`:

```
Skill: plan-marshall:workflow-integration-git
  Arguments: worktree create --plan-id {plan_id} --branch {worktree_branch} --base {base_branch}
```

Capture the returned `worktree_path` from the skill's TOON output.

**Case B — `use_worktree == false`**: the plan runs against the main checkout. Create the feature branch in place via `git -C .`:

```bash
git -C . checkout -b {worktree_branch}
```

Set `worktree_path` to the empty string (the main-checkout flow uses `.` everywhere `worktree_path` would otherwise apply; see Step 3's `worktree_path` absent → substitute `.` rule).

**Fatal-error contract**: if either branch fails, abort the phase fail-loud and do NOT silently proceed to the task loop. Emit the canonical `[ERROR]` line per the Error Handling section and return the structured error TOON; the orchestrator surfaces the failure for human repair. The failure driver differs by case:

- **Case A failure** (worktree create exits non-zero, `git worktree add` fails, branch already exists with divergent history at the worktree destination): phase-1's expectation has already committed downstream consumers to the worktree path. Do NOT silently fall back to the main checkout — that would orphan every subsequent `--plan-id`-resolved Bucket B call.
- **Case B failure** (`git checkout -b {worktree_branch}` exits non-zero, branch already exists with divergent history on the main checkout): the plan is already bound to the main checkout; the failure is the inability to create the feature branch in place. Do NOT silently fall back to `main` or `--no-branch` — phase-1 committed downstream consumers to a dedicated feature branch.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR \
  --message "[ERROR] (plan-marshall:phase-5-execute) Worktree materialization failed for branch {worktree_branch} on base {base_branch}: {error_context}"
```

**Persist `worktree_path` to both stores** on success (skip when empty in Case B — the absence already signals the main-checkout flow):

1. Write to `references.json` via the manage-references typed setter:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-references:manage-references set \
     --plan-id {plan_id} --field worktree_path --value {worktree_path}
   ```

2. Write to `status.metadata.worktree_path` via the metadata setter:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
     --plan-id {plan_id} --set worktree_path={worktree_path}
   ```

Both writes are required: `references.json` is the canonical artifact Step 3 reads to resolve `worktree_path`; `status.metadata.worktree_path` is the value the `phase_handshake verify` assertion checks on every subsequent phase boundary, and the value the idempotence guard above reads on phase-5 re-entry.

Log the materialization outcome:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (plan-marshall:phase-5-execute) Step 2.5 materialized worktree at {worktree_path} on branch {worktree_branch}"
```

Proceed to Step 3.

### Step 3: Baseline Fast-Path Check (Once per phase)

Substantive baseline reconciliation now happens at refine time — see [phase-2-refine/standards/refine-workflow-detail.md § Step 3d](../../phase-2-refine/standards/refine-workflow-detail.md#step-3d-baseline-reconciliation). Phase-5-execute is a fast-path "still clean?" verification: if the worktree branch is still ahead of (or merged with) `origin/{base_branch}`, continue to the task loop; if upstream commits have landed since the refine baseline-reconciliation pass, error out with a clear redirect — re-running phase-2-refine is the documented path. Phase-5-execute MUST NOT perform substantive reconciliation (no merge, no rebase).

Full procedure, fast-path semantics, error contract, and main-checkout fallback are documented in [standards/sync-with-main.md](standards/sync-with-main.md).

Inlined flow:

1. **Resolve `base_branch` and `worktree_path`** from `references.json` (written at `phase-1-init` Step 6):

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-files:manage-files read \
     --plan-id {plan_id} --file references.json
   ```

   Extract `base_branch` and `worktree_path`. If `worktree_path` is absent, the plan runs against the main checkout; substitute `.` for `{worktree_path}` in every git command below.

2. **Fetch base** (read-only network round-trip):

   ```bash
   git -C {worktree_path} fetch origin {base_branch}
   ```

3. **Fast-path check** — verify the current branch tip already contains `origin/{base_branch}`:

   ```bash
   git -C {worktree_path} merge-base --is-ancestor origin/{base_branch} HEAD
   ```

   Exit code `0` means up to date. Log and continue to Step 4:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level INFO \
     --message "[STATUS] (plan-marshall:phase-5-execute) Baseline fast-path: worktree already up to date with origin/{base_branch}"
   ```

4. **Drift contract** — exit code non-zero means upstream has new commits the worktree does not contain. ABORT the phase fail-loud: do NOT merge, do NOT rebase, do NOT continue to Step 4. Capture the divergent commits:

   ```bash
   git -C {worktree_path} log --oneline HEAD..origin/{base_branch}
   ```

   Record the output as `{divergent_commits}`. Then log the failure with the documented redirect:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level ERROR \
     --message "[ERROR] (plan-marshall:phase-5-execute) Baseline drift at {worktree_path} — origin/{base_branch} contains commits not in HEAD: {divergent_commits}. Phase aborted; re-run phase-2-refine to absorb upstream changes via Step 3d (Baseline Reconciliation), then re-enter phase-5-execute."
   ```

   Phase-5-execute does NOT perform substantive reconciliation. Re-running phase-2-refine surfaces the upstream commits as Q-Gate findings, the iterate-to-confidence loop absorbs them, and the user explicitly drives the rebase/merge through the refine clarifications. The fast-path here is the structural complement: it ensures execute starts only when refine has already reconciled the baseline.

Proceed to Step 4.

### Step 4: Log Phase Start and Surface Active Worktree (Once per phase)

At the start of execute or finalize phase, resolve the pending-task count and emit the canonical `[STATUS]` entry:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks list \
  --plan-id {plan_id} --status pending
```

Parse the row count from the returned `tasks_table` and substitute it as `{N}`.

**Differentiate first entry from re-entry**: Read the persisted phase status from `manage-status read` to determine whether this is the first time phase-5-execute is being entered or a re-dispatch of an already-in-progress phase. The 5-execute phase row's `status` is `pending` on the very first entry and `in_progress` on every subsequent re-dispatch (the `manage-status transition --completed 4-plan` call sets it to `in_progress`).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read \
  --plan-id {plan_id}
```

Locate the `phases[name=5-execute]` row in the returned TOON and read its `status` field. Then:

- If `status == pending` (first entry) → emit:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-5-execute) Starting execute phase — {N} tasks pending"
  ```

- If `status == in_progress` (re-entry; e.g., orchestrator re-dispatched a execution-context after a previous turn ended without completing the queue) → emit:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-5-execute) Re-entering execute phase — {N} tasks pending"
  ```

Both forms emit exactly one `[STATUS]` line; the wording difference makes it possible to grep for re-entries during retrospective gap analysis (lesson `2026-05-08-14-001`).

**Surface the active worktree absolute path** so it remains visible in model context for every subsequent Edit/Write/Read call. Read the worktree path from status metadata:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read \
  --plan-id {plan_id}
```

Extract `worktree_path` from the output. If present (plan runs in an isolated worktree), emit:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-5-execute) Active worktree: {worktree_path} — all Edit/Write/Read tool calls MUST target this path. See workflow-integration-git/standards/worktree-handling.md for the full worktree contract."
```

If `worktree_path` is absent (plan runs against the main checkout), skip emission. See `workflow-integration-git/standards/worktree-handling.md` for the worktree-specific application of this rule (path binding, tool cwd flags, Write/Edit-only file authoring, never-edit-main-checkout invariant).

For each task in current phase:

### Step 5: Locate Task with Context

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks next \
  --plan-id {plan_id} \
  --include-context
```

Returns next task with status `pending` or `in_progress`, including embedded goal context (title, body) for immediate use without additional script calls.

### Step 6: Execute Steps

For each step in task's `steps[]` array:
1. Parse the step text
2. Execute the action (delegate if specified) — when delegating to a subagent via `Task:`, `Skill:` (prompt-accepting), or `execution-context`, the prompt MUST begin with the Worktree Header from the **Dispatch Protocol** section above (omit only when no worktree is active).
3. Mark step complete via `manage-tasks:finalize-step`

### Step 7: Mark Step Complete

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step \
  --plan-id {plan_id} \
  --task-number {task_number} \
  --step {step_number} \
  --outcome done
```

### Step 8: Log Task Completion

After each task completes, the canonical `[OUTCOME]` work-log line is emitted **inside `manage-tasks finalize-step`** — see `manage-tasks/SKILL.md` § "Script-Level [OUTCOME] Emission" for the contract. The script fires exactly one `[OUTCOME] (plan-marshall:phase-5-execute) Completed TASK-NNN: {title} ({M} steps)` line on the task-closing finalize call. **Skills MUST NOT emit a manual `[OUTCOME]` line here** — duplicating the script-level guard creates double entries, and re-implementing the emission in skill prose was the failure mode that lesson `2026-05-08-14-001` documents (the line was lost whenever a execution-context was re-dispatched and the original agent's working context was discarded before its caller-side `[OUTCOME]` could fire).

Immediately after the script-emitted `[OUTCOME]` line, emit one `[ARTIFACT]` work-log entry per file the task changed by diffing the task-start SHA (recorded at `in_progress` transition as `task_start_sha`) against the current HEAD. See `standards/workflow.md` § **Artifact Emission at Task Completion** for the authoritative procedure, status-code mapping, and rename-handling rule. The artifact entries use a deliberate three-segment caller prefix `(plan-marshall:phase-5-execute:{task_number})` — a documented exception to the usual two-segment `(bundle:skill)` convention in [manage-logging/standards/log-format.md](../manage-logging/standards/log-format.md). Emit nothing when the diff is empty. This step precedes `manage-tasks next` so the audit trail for each task is flushed before the orchestrator advances.

### Step 8b: Persist Per-Task Subagent Usage to Accumulator

**Applies when**: the task was executed by dispatching to a Task agent / `execute-task` Skill that returned a `<usage>` tag. Inline tasks (or task agents that produced no `<usage>` tag) skip this step.

Persist the agent's `<usage>` totals to the on-disk per-phase accumulator so `manage-metrics phase-boundary` can read them at end-of-phase, regardless of whether the model context survives until the next orchestrator turn:

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics accumulate-agent-usage \
  --plan-id {plan_id} --phase 5-execute \
  --total-tokens {total_tokens} --tool-uses {tool_uses} --duration-ms {duration_ms}
```

Replace the placeholders with the integers parsed from the dispatched agent's `<usage>...</usage>` block. The script reads `.plan/plans/{plan_id}/work/metrics-accumulator-5-execute.toon` (initialising it on first call), sums in the supplied values, increments `samples`, and writes the file back. The on-disk file is the only source of truth — do NOT also keep a parallel tally in model context. See `manage-metrics/standards/data-format.md` § "Per-Phase Subagent Accumulator" for the file schema.

The orchestrator's `phase-boundary` call in `workflow/execution.md` (recorded at end of execute) reads this accumulator as a fallback when its `--total-tokens` / `--tool-uses` / `--duration-ms` flags are omitted. Inline tasks contribute nothing — `manage-metrics enrich` (run by `phase-6-finalize:default:record-metrics`) sweeps the transcript for any subagent `<usage>` tags whose timestamp falls inside the `5-execute` window and adds them to the per-phase `subagent_*` columns of the metrics report as a post-hoc safety net.

### Step 9: Independent Change Verification

**Applies to**: `implementation` and `module_testing` profile tasks only. Skip this step for `verification` profile tasks.

After task completion but before committing, independently verify that the task agent produced genuine results rather than trusting self-reports. Any subagent dispatch made during this step (e.g., a follow-up Task invocation) MUST embed the Worktree Header per the **Dispatch Protocol** section above.

**9a. File-change invariant**: Verify that at least one file was modified in the worktree. Run in the worktree directory (or main checkout if no worktree):

```bash
git -C {worktree_path} diff --name-only HEAD
```

If the diff output is empty (no files changed) for an `implementation` or `module_testing` task:
- Mark task `blocked` with reason `no_changes_detected`
- Log:
  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    work --plan-id {plan_id} --level WARNING --message "[VERIFY] (plan-marshall:phase-5-execute) No file-system changes detected for {task_id} — marking blocked"
  ```
- Skip Steps 9b and 9c, proceed to Step 11 (Triage)

**9b. Obfuscation spot-check** (conditional): When the task's verification criteria include checking for absence of a specific token (e.g., "zero grep hits for `--body`"), grep the modified files for common obfuscation patterns around that token:
- String concatenation splitting the token (e.g., `'--' + 'body'`, `"--" + "body"`)
- Variable assignment that reconstructs the token from parts

If any obfuscation pattern is found:
- Log each hit:
  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    work --plan-id {plan_id} --level WARNING --message "[VERIFY] (plan-marshall:phase-5-execute) Obfuscation pattern detected in {file}: {pattern} — manual review recommended"
  ```
- Do NOT auto-block (false positives are possible) — flag for human review only

**9c. Verification cross-check**: Re-execute the task's `verification.commands` independently and compare the exit code against what the agent reported:

```bash
# Run the same verification command the agent claims to have passed
{verification_command}
```

If the agent reported `verification.passed: true` but the independent run returns a non-zero exit code:
- Mark task `blocked` with reason `verification_mismatch`
- Log:
  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    work --plan-id {plan_id} --level WARNING --message "[VERIFY] (plan-marshall:phase-5-execute) Verification mismatch for {task_id}: agent reported pass but independent run failed — marking blocked"
  ```
- Proceed to Step 11 (Triage)

If independent verification also passes, continue to Step 10.

### Step 10: Conditional Per-Deliverable Commit

If `commit_strategy == per_deliverable` (cached from Step 2):

1. **Check dependency chain**: Does any other pending/in-progress task have `depends_on` pointing to the just-completed task?
   - **YES** → Skip commit (a downstream task still needs to run)
   - **NO** → This is the chain tail (all tasks for this deliverable are done) → Commit

2. **Commit** (only when chain tail):
   ```
   Skill: plan-marshall:workflow-integration-git
   Parameters:
     - message: conventional commit derived from task title
     - push: false
     - create-pr: false
   ```

3. **Log commit outcome**:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level INFO --message "[OUTCOME] (plan-marshall:phase-5-execute) Per-deliverable commit: {task_id} ({commit_hash})"
   ```

If `commit_strategy` is `per_plan` or `none` → Skip this step entirely.

### Step 11: Triage Verification Failure

**Applies when**:
- A `profile=verification` task completes with `verification.passed: false` / `next_action: requires_triage`, OR
- Step 9 marked a task `blocked` with reason `no_changes_detected` or `verification_mismatch`

The per-finding LLM core (FIX / SUPPRESS / ACCEPT / AskUserQuestion decisions over the failing findings) is owned by [`../plan-marshall/workflow/verification-feedback.md`](../plan-marshall/workflow/verification-feedback.md) and dispatched under `--phase phase-5-execute --role verification-feedback` with `producer=build-runner`.

#### Planned-failure exception (breaking-refactor task split)

**Applies before** the standard triage branches below. When a task with `profile: implementation` produces a verification failure and a downstream task with `profile: module_testing` and explicit `depends_on: [TASK-{current_task_number}]` exists, the dispatcher MAY proceed to the dependent task without flagging the failure as an error — this is the only case where "tests fail" is the planned outcome of the implementation step.

**Boundary conditions** (ALL must hold; if any fails, fall through to the standard triage branches below):

1. The downstream task's `profile` is `module_testing` AND its `deliverable` matches the current task's `deliverable` AND its description enumerates the pre-existing tests being rewritten.
2. The downstream task has explicit `depends_on: [TASK-{current_task_number}]` linkage declared at planning time. A downstream task that happens to run later without a `depends_on` edge does NOT qualify.
3. The set of failing tests reported by the implementation task's verification command is a subset of the tests enumerated in the downstream task's description. New failures (tests not on the list) are real regressions and MUST fall through to standard triage.

When all three boundary conditions hold, log the planned-failure decision, mark the implementation task as `done` (not `blocked`), and proceed to the next task in the queue (which will be the test-contract task by `depends_on` ordering):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-5-execute) Planned-failure exception applied for {task_id}: verification failed as expected; downstream test-contract task TASK-{downstream_number} will rewrite the affected tests"
```

After the test-contract task completes, the standard verification path resumes — the test-contract task itself MUST produce a green test run; if it does not, that is a real failure and goes through standard triage.

**Rationale and boundary documentation**: see [`../phase-4-plan/standards/breaking-refactor-task-split.md`](../phase-4-plan/standards/breaking-refactor-task-split.md) for the full contract spanning phase-4-plan task allocation and this phase-5-execute exception.

**For `no_changes_detected` blocks**: The implementation task produced no file changes. Triage options:
- **RETRY** → reset task to `pending` for re-execution
- **FAIL** → mark task `failed` with outcome `no_changes_detected`, log, continue

**For `verification_mismatch` blocks**: The agent claimed verification passed but independent re-run failed. Triage options:
- **FIX** → create fix task to address the actual verification failure
- **RETRY** → reset task to `pending` for re-execution
- **FAIL** → mark task `failed` with outcome `verification_mismatch`, log, continue

**For verification task failures** (original behavior):

**11a**: Read `verify_iteration` counter from task metadata (default: 0).

**11b**: If `verify_iteration >= verification_max_iterations` (from phase-5-execute config, default 5) → mark task `blocked`, log, continue to Step 12.

**11c**: Persist each failing finding to the Q-Gate findings store (producer-side; the triage dispatch reads from the store by reference):

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase 5-execute \
  --source qgate --type verification-failure --severity {severity} \
  --message "{finding_message}" --detail "{file}:{line}"
```

(One `qgate add` call per finding; the verification task's structured `findings[]` output drives this loop.)

**11d**: Dispatch the per-finding triage core via [`../plan-marshall/workflow/triage.md`](../plan-marshall/workflow/triage.md) — single source of truth for the FIX / SUPPRESS / ACCEPT / AskUserQuestion decisions, smart grouping, action bodies, overflow handling, and the Scope-Deviation Escalation guard. The dispatch is by-reference (the subagent queries the store as its first workflow step).

Compute the target via the role resolver, then dispatch:

```bash
target=$(python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --phase phase-5-execute --role verification-feedback)
```

Emit the standardized post-resolve dispatch log line — see [`../ref-workflow-architecture/standards/dispatch-logging.md`](../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[DISPATCH] (plan-marshall:phase-5-execute) target={target} level={level} role=verification-feedback workflow=plan-marshall:plan-marshall/workflow/verification-feedback.md plan_id={plan_id}"
```

```
Task: plan-marshall:{target}
  prompt: |
    name: verification-feedback
    plan_id: {plan_id}
    skills[4]:
    - plan-marshall:manage-findings
    - plan-marshall:manage-tasks
    - plan-marshall:manage-architecture
    - plan-marshall:manage-config
    workflow: plan-marshall:plan-marshall/workflow/verification-feedback.md

    producer: build-runner
    caller_phase: phase-5-execute

    WORKTREE: {worktree_path}
```

The Scope-Deviation Escalation guard lives in [`triage.md`](../plan-marshall/workflow/triage.md) § Step 6 — the triage subagent raises `AskUserQuestion` with the four canonical options (Hold / Accept-with-rationale / Split / FIX-here-anyway) when a decision would soften a request-level hard requirement (zero-hit grep gates, "no transition window" intents, "remove flag entirely" cutovers, etc.). The canonical contract is documented in [`../ref-workflow-architecture/standards/scope-deviation-escalation.md`](../ref-workflow-architecture/standards/scope-deviation-escalation.md); the work-log line `[STATUS] Gate N deferred status accepted` is forbidden as a stand-in for the AskUserQuestion thread — the escalation MUST happen first; logging confirms the user's decision afterward.

**11e**: Inspect the triage subagent's return:

- If `fix_tasks_created > 0` → increment `verify_iteration` in task metadata, reset the verification task to `pending`, continue the execution loop (fix tasks will execute before the re-queued verification task via `depends_on`).
- If `fix_tasks_created == 0` AND `overflow_deferred == 0` → mark the verification task complete (all findings suppressed / accepted / `taken_into_account`), continue to Step 11b.
- If `overflow_deferred > 0` → leave the verification task `pending`; the orchestrator re-fires the triage dispatch on the next phase-5-execute entry (the iteration cap is unchanged).

### Step 11b: Final Quality Sweep (After All Tasks)

After every task in the phase has completed (and Step 11 has resolved any per-task verification failures), but **before** Step 12 transitions the phase, run **one canonical `quality-gate` invocation** as a final sweep — but ONLY when `phase_5.verification_steps` (cached from Step 2) is non-empty.

**Skip rule**: If `phase_5.verification_steps` is empty (e.g., docs-only plans where the manifest composer dropped all verification steps), skip this step entirely — no final sweep, no log, proceed directly to Step 12.

**When `phase_5.verification_steps` is non-empty** — exactly one quality sweep, regardless of whether `quality-gate` already appears in the list:

1. Resolve the canonical `quality-gate` build command via the architecture API:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
     resolve --command quality-gate --audit-plan-id {plan_id}
   ```

2. Execute the returned `executable`. On non-zero exit, persist the failures to the Q-Gate findings store (`manage-findings qgate add --type quality-gate-failure …`) and dispatch [`../plan-marshall/workflow/verification-feedback.md`](../plan-marshall/workflow/verification-feedback.md) under `--phase phase-5-execute --role verification-feedback` with `producer=build-runner` and `finding_type=quality-gate-failure` — same shape as Step 11d above, only the finding type changes. The subagent's return drives the same fix-task / suppress / accept branch (Step 11e). After triage resolves, do **NOT** re-run the sweep — Step 11b runs at most once per phase entry.

3. Log the outcome:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level INFO \
     --message "[STATUS] (plan-marshall:phase-5-execute) Final quality sweep: {pass|fail}"
   ```

This step is the single source of "did the phase end clean?" — it appends the canonical `quality-gate` once after all task-level verification has settled, providing a stable end-of-phase quality signal. Only the manifest's `verification_steps` list controls whether it fires; per-doc skip logic in `quality_check.md` / `build_verify.md` / `coverage_check.md` has been removed in favor of this manifest-driven gate.

### Step 12: Next Task or Phase

- If more tasks in phase → Continue to next task
- If phase complete → run **Step 12a (Pending-tasks transition guard)** below, then log phase outcome and auto-transition to next phase
- If all phases complete → Mark plan complete

#### Step 12a: Pending-tasks transition guard

Before invoking `manage-status transition --completed 5-execute` (see **Phase Transition** section below), refuse to transition when any pending tasks remain. `manage-tasks next` only surfaces the head of the queue — a `null` next does NOT prove the queue is empty when downstream tasks are still in `pending`. Fix tasks created by Step 11 triage commonly land here, and a premature transition silently abandons them.

**Script-level enforcement**: the authoritative pending-count check is `python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks loop-exit-guard --plan-id {plan_id}` — see `manage-tasks/SKILL.md` § "Loop-Exit Guard". `status: continue` (with `pending_count > 0` and `pending_ids`) forces the orchestrator to re-dispatch the execution-context; `status: success` (with `pending_count: 0`) is the precondition for `manage-metrics record-dispatch-boundary --termination-cause clean_exit_queue_empty`. The list-based check below remains documented for backwards compatibility with existing callers — both forms read the same on-disk state, but `loop-exit-guard` is the canonical surface and the verb the orchestrator MUST consult.

1. Query the pending-task list:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks list \
     --plan-id {plan_id} --status pending
   ```

2. Parse the row count from the returned `tasks_table`. **If the count is zero**, proceed to Phase Transition.

3. **If the count is non-zero**, the phase is NOT complete. Log a `[BLOCKED]` line and abort the transition:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level ERROR \
     --message "[BLOCKED] (plan-marshall:phase-5-execute) Pending tasks: {ids} — refusing to transition 5-execute → 6-finalize. Re-enter the execute loop to complete pending tasks, or invoke with --force to override."
   ```

   `{ids}` is a comma-separated list of `TASK-{number}` identifiers parsed from the `tasks_table`. Do NOT call `manage-status transition` and do NOT auto-continue to finalize.

4. **`--force` escape** (mirrors the verification-cap escape in `Step 11b`): when the orchestrator is invoked with `--force`, log the override decision, then proceed to Phase Transition with the pending tasks intact:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     decision --plan-id {plan_id} --level WARNING \
     --message "(plan-marshall:phase-5-execute) Pending-tasks guard overridden via --force — transitioning with {count} pending task(s): {ids}"
   ```

   The `--force` escape is a deliberate safety valve for triage-driven aborts (the user has already decided the pending tasks are out-of-scope) — never invoke it programmatically from inside the loop.

### Step 13: Log Phase Completion (When phase completes)

Substitute `{N}` with the count of tasks marked `done` during this phase entry and `{M}` with the total task count from the plan, then emit the canonical phase-exit `[STATUS]` line:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-5-execute) Execute phase complete — {N}/{M} tasks done"
```

**Add visual separator** after END log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  separator --plan-id {plan_id} --type work
```

---

## Delegation

When checklist items specify delegation, invoke the appropriate agent/skill:

| Checklist Pattern | Delegation |
|-------------------|------------|
| "Run build" / "maven" / "npm" | See `standards/operations.md` |
| "Delegate to {agent}" | `Task: {agent}` |
| "Load skill: {skill}" | `Skill: {skill}` |
| "Run /command" | `SlashCommand: /command` |

---

## Auto-Continue Behavior

Execute continuously without user prompts except:
- Error blocks progress
- Decision genuinely required
- User explicitly requested confirmation

**Do NOT prompt for**:
- Phase transitions
- Task transitions
- Routine confirmations

### Forbidden: agent-initiated checkpoints

Phase-5-execute MUST drive the task loop to one of three terminal outcomes inside a single dispatch:

1. All pending tasks complete and the phase transitions to `6-finalize`.
2. A fatal error captured via the **Error Handling** section (including the pending-task drift error below).
3. A triage-driven `blocked` outcome that the skill itself acknowledges via `manage-tasks` status updates.

**Improvising a "progress checkpoint" return is a workflow violation.** Specifically, the dispatched agent MUST NOT:

- Emit a "Returning control to orchestrator" / "checkpoint reached" / "partial-completion handoff" line and stop with pending tasks still in the queue.
- Return a TOON payload that summarises "N of M tasks done, please re-dispatch" without one of the three terminal outcomes above.
- Ask the user whether to continue when no genuine decision is required (loop fatigue is not a decision point).

The motivating gap: lesson `2026-05-08-14-001` documents that agent-initiated re-dispatch was the trigger for losing `[OUTCOME]` log coverage. The script-level `[OUTCOME]` guard in `manage-tasks finalize-step` (D1) closes the audit-trail gap, but the underlying control-flow drift — agents deciding on their own to hand control back — also needs to be ruled out at the skill level. The orchestrator (`plan-marshall` workflows) is the single component allowed to start, re-dispatch, or terminate phase-5-execute; the dispatched agent does not get to vote.

### Deterministic exit clause (token-budget sentinel)

The loop's continue-vs-yield decision is governed by exactly one deterministic clause — no per-task heuristics, no "this task feels expensive" intuition, no "context is filling up" sense-checks. The clause is:

> **If `remaining_budget > N`: continue to the next task. Else: yield.**

Where `N` is the per-task budget reserve (the minimum context window that must be available before the loop is allowed to start another task). The clause runs once after each task completes — between `manage-tasks finalize-step` of the closing step (which fires the canonical `[OUTCOME]`) and the next `manage-tasks next` call. There is no intermediate decision point.

**Budget items consumed per task** (the sentinel's accounting model — these are the costs `N` must reserve for):

1. **`execute-task` agent dispatch** — the per-task subagent invocation that runs the actual implementation/test/verification work. This is the largest cost per task and includes the agent's own context plus the standards it loads on entry.
2. **Auto-injected `--project-dir` verify step** — when the plan resolves to a worktree, `plan-marshall:execute-task:inject_project_dir` rewrites each `task.verification.commands[N]` to forward the worktree path. The rewritten command consumes additional executor + build-system context that the budget model must NOT under-account; it is part of every implementation / module_testing task and a primary driver of per-task cost variance.

**Resolving `N`** — the threshold MUST come from a manifest-resolvable knob, not a literal:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get --field per_task_budget_reserve --audit-plan-id {plan_id}
```

When `per_task_budget_reserve` is set, use its value as `N`. **Fallback when the knob is absent**: use the conservative default `N = 50000` tokens. The fallback exists so plans that have not yet migrated to the manifest-driven model still observe a deterministic yield boundary rather than running until the host platform forces a `harness_cancellation`. Plans that need a different reserve raise the value in `marshal.json`'s `plan.phase-5-execute.per_task_budget_reserve` slot.

**Cross-reference to the three terminal outcomes** — the sentinel is the **continue-vs-yield** decision, not a fourth terminal outcome. When the sentinel says "yield", the agent still MUST exit via one of the three documented terminal paths above (queue empty → transition; fatal error → structured error TOON; triage `blocked` → manage-tasks status update). Yielding does NOT mean "return a partial-completion checkpoint" — that path is explicitly forbidden by the section above. The orchestrator re-dispatches the execution-context on the next round; the in-flight task's state is already persisted by `manage-tasks finalize-step` so resumption is lossless.

**Audit diagnostic ledger** — when investigating throughput regressions (e.g., "why did this run process 1 task at ~119k tokens while a prior run processed 4 at ~210k?"), inspect the per-dispatch overhead in the work log. Each `execution-context` dispatch carries a fixed cost (skill-load preamble + Worktree Header echo + return-TOON marshalling); the ratio of overhead to useful work per dispatch is the first thing to check when budget accounting drifts.

---

## Phase Transition

When transitioning from execute phase to finalize:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status transition \
  --plan-id {plan_id} \
  --completed 5-execute
```

This automatically updates status.json and moves to the next phase.

**After transition**, check `finalize_without_asking` config:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get --field finalize_without_asking --audit-plan-id {plan_id}
```

- **IF `finalize_without_asking == true`**: Log and auto-continue to finalize phase
- **ELSE (default)**: Stop and display `"Run '/plan-marshall action=finalize plan={plan_id}' when ready."`

---

## Output

phase-5-execute returns on three terminal paths (queue empty → transition; fatal error; triage `blocked`). The minimum contract every workflow doc that implements `ext-point-execution-context-workflow` MUST return is:

```toon
status: success | error | blocked
display_detail: "<{tasks_completed} tasks complete, {tasks_remaining} remaining>"
plan_id: {plan_id}
tasks_completed: {N}
tasks_remaining: {N}
```

`display_detail` shape on success: `"{tasks_completed} tasks complete, {tasks_remaining} remaining"` (e.g. `"7 tasks complete, 0 remaining"`). On `blocked`: `"{task_number} blocked: {short reason}"`. On error: short error label from § Error Handling. All values are ≤80 chars, ASCII, no trailing period.

---

## Error Handling

On any error, **first log the error** to work-log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-5-execute) {task_id} failed - {error_type}: {error_context}"
```

### Script Failure (Lessons-Learned Capture)

**ON SCRIPT FAILURE**: When any `python3 .plan/execute-script.py` invocation exits non-zero, emit the canonical `[ERROR]` script-failure line to work-log BEFORE any retry or abort. This is distinct from the `[ERROR]` task-failure line above — that one captures end-of-task failure context; this one captures every individual non-zero script exit so caller-name drift, argparse rejections, and "Unknown notation" failures stay visible in `work.log` instead of hiding in `script-execution.log`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-5-execute) Script {notation} {sub} failed: exit_code={N}, args={...}"
```

Substitute `{notation}` with the failing script's `bundle:skill:script` notation, `{sub}` with the subcommand (or `-` when none), `{N}` with the observed exit code, and `{...}` with a compact rendering of the call's arguments (mask any obviously sensitive values).

After the emit:
1. Capture error context (script path, exit code, stderr)
2. Continue with normal error recovery (retry, fail task, etc.)

### Pending-task drift (fatal)

**ON `manage-tasks next` returning a `null` next while pending tasks remain**: this is a fatal control-flow drift, not a routine "no work to do" signal. The two known triggers are (a) a malformed `depends_on` graph that leaves every pending task waiting on a non-existent predecessor and (b) a misclassified `in_progress` task that the loop cannot advance. Either way, transitioning to finalize would silently abandon the pending tasks.

When the loop receives `next: null` from `manage-tasks next`, immediately query `manage-tasks list --status pending`. If the pending count is non-zero, treat it as a fatal error:

1. Emit the canonical `[ERROR]` line to work-log:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-5-execute) Pending-task drift: manage-tasks next returned null while {N} task(s) still pending — {ids}. This is a fatal control-flow error; do NOT transition to finalize."
   ```

2. Do NOT call `manage-status transition --completed 5-execute`. Do NOT auto-continue. Return a structured error payload (see **Error Handling** above) so the orchestrator can either re-enter execute (if the cause is a recoverable dependency-graph repair) or surface the failure for human review.

The Step 12a "Pending-tasks transition guard" (in the Execution Loop) is the structural check that prevents the transition; this section names the failure mode at the error-taxonomy level so the orchestrator can route the recovery.

### Other Errors

| Error | Options |
|-------|---------|
| Build failure | Fix and retry / View log / Skip task |
| Test failure | Fix tests / View details / Skip task |
| Dependency not met | Complete dependency / Skip check |

---

## Integration

### Command Integration
- **/plan-marshall action=execute** - Primary entry point invoking this skill

### Related Skills
- **phase-4-plan** - Creates tasks from deliverables (previous phase)
- **phase-6-finalize** - Shipping workflow (commit, PR) (next phase)

### Phase-boundary metric bookkeeping

The `5-execute → 6-finalize` phase boundary itself is recorded by the
orchestrator (`plan-marshall:plan-marshall` workflows) via the fused
`manage-metrics phase-boundary` call — see
`marketplace/bundles/plan-marshall/skills/manage-metrics/SKILL.md` §
`phase-boundary` for the API. Per-task `manage-tasks finalize-step` calls
during the execution loop are unchanged.

Per-task subagent token aggregation is handled by Step 8b
(`accumulate-agent-usage`) which persists each dispatched agent's `<usage>`
totals to `.plan/plans/{plan_id}/work/metrics-accumulator-5-execute.toon`.
The orchestrator's `phase-boundary` call reads this accumulator file as a
fallback when its explicit token flags are omitted — so the orchestrator
does not need to maintain a parallel running sum in model context.

