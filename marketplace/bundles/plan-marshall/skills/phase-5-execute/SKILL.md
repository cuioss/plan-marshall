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
Skill: plan-marshall:dev-agent-behavior-rules
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
- Strictly comply with all rules from dev-agent-behavior-rules, especially tool usage and workflow step discipline

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

Step-level exceptions — calls whose non-zero exit is itself the signal (e.g., `manage-files exists` returning `exists: false`, `manage-status get-worktree-path` returning an empty `worktree_path`) — are documented inline in the step that issues them.
- On phase entry (Step 4), resolve the active worktree absolute path and surface it as a `[STATUS]` work-log line so it stays visible in model context throughout the run.
- Every subagent dispatch (Task / Skill / execution-context invocation) MUST pass `plan_id` as an input parameter to satisfy the subagent's Input Contract (e.g., `execute-task`, `execution-context`). Under the cwd-pinned model the worktree binding is inherited via the pinned cwd, not forwarded per call — subagents resolve `.plan/` cwd-relatively. A short reminder header MAY be embedded (see **Dispatch Protocol** below); it is a salience reminder, not a path-routing mechanism.

See `workflow-integration-git/standards/worktree-handling.md` for the worktree-specific application of this rule (path convention, never-edit-main-checkout invariant, cwd-pinned dispatch inheritance, `--plan-id`/`--project-dir` escape-hatch contract).

## Phase-Entry Worktree Assertion

The Phase Entry Protocol's `phase_handshake verify --phase {previous_phase_key} --strict` call (see [`ref-workflow-architecture/standards/phase-lifecycle.md`](../ref-workflow-architecture/standards/phase-lifecycle.md#phase-handshake-verify-phases-2-6)) asserts the worktree-resolution contract before any phase-5-execute work begins: when `metadata.use_worktree==true`, `metadata.worktree_path` MUST be non-empty AND filesystem-resolvable (the directory exists AND `git -C {path} rev-parse --show-toplevel` returns the same canonical path). When the assertion fails, the script returns `status: error, error: worktree_unresolved` and (under `--strict`) exits 1 — phase entry refuses to advance until the persisted metadata is repaired. Plans with `metadata.use_worktree==false` skip the assertion (main-checkout flow). The assertion fires uniformly at every phase boundary; see deliverable 8 in the originating lesson plan for the full contract.

**Phase 5 is the materialization phase.** Phases 1–4 only *declare* the worktree intent (`metadata.use_worktree` and `metadata.worktree_branch` written by `phase-1-init`); Step 2.5 below is the single point where the worktree directory and feature branch are actually created on disk. **Step 2.5 is unconditional and runs BEFORE the `early_terminate` short-circuit evaluation (Step 2.6 below).** Hoisting Step 2.5 above the short-circuit guarantees that `metadata.worktree_path` is always backfilled regardless of the manifest's `early_terminate` flag — otherwise an analysis-only plan that the composer marks `early_terminate=true` would transition to finalize without ever populating the worktree path, and the `phase_handshake verify` assertion at the 5→6 boundary would fail with `worktree_unresolved`. This ordering rules out an early-terminate path that transitions to finalize without ever populating the worktree path. Re-entry semantics: when phase-4-plan's capture ran without a populated `metadata.worktree_path` (because Step 2.5 had not yet executed), the `phase_handshake verify --phase 4-plan --strict` call MUST tolerate the still-empty value at phase-5 entry, then Step 2.5 populates `worktree_path` in both `references.json` and `status.metadata` before any task dispatch. On every subsequent phase-5 re-entry (orchestrator re-dispatch), Step 2.5's idempotence guard observes the populated `worktree_path` and short-circuits — no re-creation, no duplicate `git checkout -b`.

## Dispatch Protocol (cwd-Pinned Inheritance)

Under the move-based, cwd-pinned model (ADR-002), the worktree binding is carried by the **pinned current working directory**, not by per-call path forwarding. Step 2.5 pins the orchestrator's cwd to the worktree root after `prepare_execute.py` moves the plan directory and the executor in; every subprocess spawned and every subagent dispatched inherits that cwd, and `.plan/` resolution is cwd-relative (`file_ops.get_base_dir()` walks up to the nearest ancestor containing `.plan/local`). A dispatched subagent therefore resolves the worktree-resident state without being told a path. See [`../tools-script-executor/standards/cwd-policy.md`](../tools-script-executor/standards/cwd-policy.md) for the single cwd-unchanged invariant — it is not restated here.

**Consequence for dispatch**: subagents do NOT forward `--plan-id` or `--project-dir` to working-tree-touching scripts for path resolution — the inherited pinned cwd binds them. The only structured input a dispatched workflow takes is `plan_id` as the *plan-identifier* prompt-body field (selecting which plan's metadata to operate on; unrelated to cwd binding), per the dispatched workflow's own Input Contract (`execute-task`, the per-phase workflow doc loaded by `execution-context-{level}`).

When the plan runs in an isolated worktree (see the `[STATUS] Active worktree` work-log line from Step 4), a short reminder header MAY be embedded as the first lines of the dispatch prompt to keep the never-edit-main-checkout invariant salient through free-form delegation:

```
WORKTREE: cwd is pinned to this plan's worktree (ADR-002 cwd-pinned model).
Resolution is cwd-relative — do NOT forward a worktree path; do NOT pass --project-dir.
All Edit/Write/Read tool calls and tool invocations (git, mvn, npm) operate against the pinned cwd.
NEVER edit the main checkout. See tools-script-executor/standards/cwd-policy.md.
```

The header is a **reminder, not a path-routing mechanism** — the binding holds whether or not the header is present, because cwd-pinning carries it. The worktree absolute path MUST NOT appear in dispatch prompts. `--project-dir <abs>` survives only as the **escape hatch** for callers invoked outside a pinned-cwd context (post-worktree-removal cleanup, fixture-driven test invocations); it MUST NOT be forwarded inside a phase-5+ pinned-cwd dispatch. The complete contract — cwd-pinned inheritance, the merge-lock exception, and the `--plan-id`/`--project-dir` three-state escape-hatch binding — is documented in `workflow-integration-git/standards/worktree-handling.md` § Dispatch Protocol and `../tools-script-executor/standards/cwd-policy.md`.

The `[STATUS] Active worktree: ...` work-log line is the observability signal that the worktree was materialized and cwd was pinned. Child agents inherit the same pinned cwd and MUST NOT re-derive or forward a worktree path into any further dispatch.

This applies to every dispatch in the execution loop, including (but not limited to) **Step 6 (Execute Steps)** task dispatches and **Step 9 (Independent Change Verification)** subagent invocations.

See `standards/operations.md` for the complete set of dispatch pattern templates and `workflow-integration-git/standards/worktree-handling.md` for the worktree-specific application of this rule.

### Common anti-patterns to avoid (mirrored from dev-agent-behavior-rules)

Each Bash tool call dispatched during execute must contain exactly ONE command. Never combine with newlines, `&`, `&&`, `;`, or inline env-var assignment of the form `VAR=val cmd`. The `VAR=val cmd` shape combines the assignment and the command into one shell argument, which trips the host platform's permission UI and obscures the env-var contract by hiding the variable inside the command line rather than declaring it explicitly.

**Anti-pattern**: `MY_VAR=value python3 some_command.py ...`

**Safe alternative (option A)** — Pass the value as a flag arg:

`python3 some_command.py ... --my-var value`

**Safe alternative (option B)** — Set the env var in the command's invocation header (e.g., a separate `env MY_VAR=…` line, NOT inline) before launching the bash command, or define the value as a Python module-level constant lookup inside the script itself.

See [`dev-agent-behavior-rules` Hard Rules](../dev-agent-behavior-rules/SKILL.md#bash-one-command-per-call) for the authoritative source.

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

### Coverage Contract (per-task scope × thoroughness)
```
Read ../dev-agent-behavior-rules/standards/thoroughness.md
```
Contains: the *scope × thoroughness* coverage contract each task body honors at its execution coverage point — the thoroughness ladder (T1–T5), the scope ladder, the grade-to-the-floor rule, and the coupling constraint `reject thoroughness ≥ T4 ∧ scope < component`. Per-task work covers its declared cell; the floor-graded self-report states asked-for vs achieved.

---

## Dispatched workflows vs inline steps

This phase dispatches under one role key: **`phase-5-execute`** (resolves through `phase-5-execute.default`). The dispatch unit is **budget-bounded** — explicitly NEITHER per-task NOR per-deliverable. The orchestrator dispatches phase-5-execute as ONE `execution-context` envelope that greedily drives the task loop over **as many tasks as the per-task budget reserve permits — which bundles several small deliverables into one envelope and may span a single large deliverable across several envelopes**. Per task the envelope LOADS the `execute-task` skill in-context as a `Skill:` (via `resolve-execute-task-skill`) with the task-declared skill list as runtime input — leaf-legal in-context skill loading per [`dev-agent-behavior-rules`](../dev-agent-behavior-rules/SKILL.md), explicitly NOT a per-task `Task:` subagent dispatch. `per_task_budget_reserve` is the RESERVE that must remain free before the loop starts another task, not an envelope ceiling, so a single envelope grows well past that reserve. The envelope yields to the orchestrator — which then re-dispatches a fresh envelope to resume the loop — only at one of three TASK-boundary re-dispatch points: (a) the token-budget sentinel; (b) `triage_required` (Step 11/11b verify / quality-gate failure); (c) `baseline_drift`. It is NOT one envelope per task and NOT one envelope per deliverable. Deliverable boundaries govern the COMMIT + FOCUSED-BUILD points only — the Step 10 Per-Deliverable Chain-Tail (an optional commit when `commit_strategy=per_deliverable`, plus a focused per-module build) is a **sub-event that fires within OR across envelopes, decoupled from where the budget sentinel yields, and is NOT a dispatch boundary**; because the sentinel yields at TASK boundaries (between `finalize-step` and the next `manage-tasks next`), a mid-deliverable yield is normal and lossless (`finalize-step` persists in-flight task state, and the Step 10 chain-tail commit still fires whenever the run reaches it, regardless of which envelope gets there). This per-task body runs as a **leaf** inside the `execution-context` envelope — it cannot itself issue a `Task:` dispatch (see [`ref-workflow-architecture/standards/agents.md`](../ref-workflow-architecture/standards/agents.md), the canonical leaf/dispatch-topology contract). The built-in verification steps (`default:quality_check`, `default:build_verify`, `default:coverage_check`) stay inline as pure build invocations — no LLM judgement, no envelope. Step 9 independent change verification stays inline (three deterministic re-checks: git-diff empty-test, obfuscation-pattern grep, exit-code compare). Steps 11 and 11b detect the verification-failure / quality-gate-failure, persist each finding to the per-plan Q-Gate store (`manage-findings qgate add` — a script call, legal inside a leaf), then **return a `triage_required` signal to the main-context orchestrator**; the orchestrator owns the **`verification-feedback`** dispatch (`--phase phase-5-execute --role verification-feedback`, `producer=build-runner`) and consumes its return to drive the fix-task / suppress / accept branch. The leaf never dispatches `verification-feedback` itself. For the rationale see [dispatch-granularity.md](../extension-api/standards/dispatch-granularity.md) § 2, § 4 (Heuristic 3 — per-iteration `Task:` dispatch only when models differ OR iterations parallelise; the budget-bounded task loop is the iterate-in-context application), and § 5.1 (script over dispatch; phase-scoped resolution + producer-mode bundling).

## Execution Loop

### Step 1: Get Routing Context (Once at start)

Get current phase, skill routing, and progress in a single call:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status get-routing-context \
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

Extract `phase_5.early_terminate` (bool) and `phase_5.verification_steps` (list[string]) from the output. **Do NOT evaluate `early_terminate` yet** — Step 2 only reads the manifest and caches the values. Step 2.5 (worktree materialization) MUST run before the `early_terminate` short-circuit fires, so the short-circuit evaluation is deferred to Step 2.6 below.

The verification steps to execute at end of phase come from `phase_5.verification_steps` — this **replaces** today's lookup of `marshal.json`'s `phase-5-execute.steps`. The list is consumed by Step 11b (Final Quality Sweep) and the verification dispatch loop. See **Verification Step Types** below for dispatch rules.

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
| `default:coverage_check` | Run resolved coverage build; threshold enforcement is native to the build tool | Coverage threshold verification |

**`coverage_check` dispatch**: Resolve via `architecture resolve --command coverage` and run the resolved executable. Threshold enforcement is native to the resolved command — pytest receives `--cov-fail-under={threshold}` from `build.py::cmd_coverage`, and JaCoCo (Maven/Gradle) enforces the threshold via build-tool configuration. No secondary parse-and-check call is required.

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
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id {plan_id}
```

Extract `metadata.use_worktree`, `metadata.worktree_branch`, `metadata.worktree_path`, and the plan's `base_branch` (from `references.json` via `manage-references get`). If `worktree_path` is non-empty, log the short-circuit and proceed to Step 3:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (plan-marshall:phase-5-execute) Step 2.5 short-circuit: worktree_path already populated ({worktree_path}) — skipping materialization"
```

**Materialization branch (when `worktree_path` is empty)**: branch on `metadata.use_worktree`.

**Case A — `use_worktree == true`**: CALL the atomic move-in script `prepare_execute`. In one call it materializes the worktree + feature branch (delegating to `worktree-create`), MOVES the plan directory and the executor into the worktree-resident `.plan/`, and RETURNS the canonical `worktree_path`:

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:prepare_execute prepare \
  --plan-id {plan_id} --branch {worktree_branch} --base {base_branch}
```

Parse `status` and `worktree_path` from the returned TOON. On `status: success`, capture `worktree_path`. The move is atomic-with-rollback and idempotent — a re-entry returns `action: noop` carrying the same path (the idempotence guard above normally short-circuits before this CALL, but the script's own guard is the structural backstop). See `workflow-integration-git` Canonical invocations → `prepare_execute` for the full contract.

**Pin cwd to the returned path**: immediately after a successful CALL, the phase-5 orchestrator pins ITS OWN cwd to `worktree_path` for the remainder of phase-5+ (the script does NOT change the caller's cwd — a subprocess cannot mutate its parent's cwd). Under the uniform cwd rule (ADR-002) every subsequent `.plan/` resolution then targets the worktree-resident state moved in by this CALL. The single execution-time invariant is that cwd is never changed away from the worktree until finalize moves the plan dir back. D8 owns the caller-side cwd-unchanged guard the lifecycle scripts assert.

**Case B — `use_worktree == false`**: the plan runs against the main checkout — there is NO worktree to materialize and NO move-in. Create the feature branch in place via `git -C .`:

```bash
git -C . checkout -b {worktree_branch}
```

Set `worktree_path` to the empty string (the main-checkout flow uses `.` everywhere `worktree_path` would otherwise apply; see Step 3's `worktree_path` absent → substitute `.` rule). Do NOT call `prepare_execute` in Case B — cwd stays on main and resolution is already main-relative.

**Fatal-error contract**: if either branch fails, abort the phase fail-loud and do NOT silently proceed to the task loop. Emit the canonical `[ERROR]` line per the Error Handling section and return the structured error TOON; the orchestrator surfaces the failure for human repair. The failure driver differs by case:

- **Case A failure** (`prepare_execute` returns `status: error` — worktree create failed, the plan dir is missing on main, or a move-in step failed and rolled back): the script's atomic-with-rollback contract guarantees the plan state is left WHOLLY on main, never half-moved. phase-1's expectation has already committed downstream consumers to the worktree path. Do NOT silently fall back to the main checkout — that would orphan every subsequent `--plan-id`-resolved Bucket B call. Do NOT pin cwd, and do NOT proceed to the task loop.
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
   python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
     --plan-id {plan_id} --set --field worktree_path --value {worktree_path}
   ```

Both writes are required: `references.json` is the canonical artifact Step 3 reads to resolve `worktree_path`; `status.metadata.worktree_path` is the value the `phase_handshake verify` assertion checks on every subsequent phase boundary, and the value the idempotence guard above reads on phase-5 re-entry.

Log the materialization outcome:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (plan-marshall:phase-5-execute) Step 2.5 materialized worktree at {worktree_path} on branch {worktree_branch}"
```

Proceed to Step 2.6.

### Step 2.6: Evaluate `early_terminate` Short-Circuit (Once at start)

This step evaluates the `phase_5.early_terminate` flag cached at Step 2 and is intentionally placed AFTER Step 2.5 so the worktree directory and `metadata.worktree_path` are always populated before any early-exit path runs. The manifest composer narrows `early_terminate=true` to plans where BOTH `verification_steps == []` AND the task queue is empty (no pending or in-progress tasks).

**Early-terminate decision**: If `phase_5.early_terminate == true`, log the decision and transition directly to `phase-6-finalize` — skip the entire execute loop including Steps 3 through 12:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-5-execute) Early terminate — manifest.phase_5.early_terminate=true; skipping execute loop and transitioning directly to phase-6-finalize"
```

Then jump directly to **Phase Transition** (below) to advance to finalize. Do NOT execute Steps 3–12. Because Step 2.5 already ran unconditionally, `metadata.worktree_path` is populated and the 5→6 `phase_handshake verify` assertion will succeed.

**Otherwise** (`early_terminate == false`): proceed to Step 3.

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

2. **Entry guard — stale `base_branch` check**: before fetching, verify that `origin/{base_branch}` still resolves on the remote. A merged-and-deleted feature branch produces an empty `ls-remote` result, and a downstream `git fetch origin {base_branch}` will fail with a misleading `could not find remote ref` error.

   ```bash
   git -C {worktree_path} ls-remote --heads origin {base_branch}
   ```

   When the output is empty, return a structured error and ABORT the phase:

   ```toon
   status: error
   error: base_branch_unresolvable
   base_branch: {value}
   suggested_fix: "Update references.json:base_branch to the repo default (main/master), then re-enter phase-5-execute. Run phase-2-refine to invoke baseline-reconcile auto-update."
   ```

   `baseline-reconcile` (invoked by phase-2-refine Step 3d) self-heals stale base-branch values by detecting the remote default and writing the new value to `references.json`; the canonical recovery is therefore to re-run phase-2-refine, not to manually fix-up references.json in-place. The entry guard here is purely a fail-loud surface so the orchestrator does not waste a `fetch` round-trip on a known-bad input.

3. **Fetch base** (read-only network round-trip):

   ```bash
   git -C {worktree_path} fetch origin {base_branch}
   ```

4. **Fast-path check** — verify the current branch tip already contains `origin/{base_branch}`:

   ```bash
   git -C {worktree_path} merge-base --is-ancestor origin/{base_branch} HEAD
   ```

   Exit code `0` means up to date. Log and continue to Step 4:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level INFO \
     --message "[STATUS] (plan-marshall:phase-5-execute) Baseline fast-path: worktree already up to date with origin/{base_branch}"
   ```

5. **Drift detected** — exit code non-zero means upstream has new commits the worktree does not contain. Do NOT merge, do NOT rebase, do NOT continue to Step 4 yet. First capture the divergent commits for both logging and the self-absorb decision below:

   ```bash
   git -C {worktree_path} log --oneline HEAD..origin/{base_branch}
   ```

   Record the output as `{divergent_commits}`.

6. **Invoke `baseline-reconcile` to obtain a deterministic overlap predicate**. The script runs `git merge-tree` against `HEAD` and `origin/{base_branch}` and returns `conflict_count` — the number of files where the three-way merge would conflict. This is the structural "overlap" signal: `conflict_count == 0` means the upstream commits and the worktree's in-flight changes touch disjoint sets of files, so absorbing the upstream tip into the baseline metadata is safe without any working-tree mutation. `--no-emit` suppresses Q-Gate finding emission — phase-5-execute self-absorption is the wrong place to surface refine-time findings:

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow \
     baseline-reconcile --plan-id {plan_id} --no-emit
   ```

   Parse `conflict_count`, `upstream_commit_count`, and `upstream_commits` from the returned TOON.

7. **Self-absorption branch — `conflict_count == 0`** (zero-overlap case): the upstream tip can be absorbed into the baseline metadata without re-authoring the request, the outline, or any task. Persist the new `worktree_sha` (the current HEAD sha after the fetch — unchanged, but recorded for audit) and the new `main_sha` (the resolved `origin/{base_branch}` sha) into `status.metadata` via a single fused `manage-status metadata --set` call:

   ```bash
   git -C {worktree_path} rev-parse HEAD
   ```

   Capture as `{worktree_sha}`.

   ```bash
   git -C {worktree_path} rev-parse origin/{base_branch}
   ```

   Capture as `{main_sha}`. Then write both keys:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
     --plan-id {plan_id} --set --field worktree_sha --value {worktree_sha}
   python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
     --plan-id {plan_id} --set --field main_sha --value {main_sha}
   ```

   Emit exactly ONE decision-log entry naming the absorbed commits — the entry is the audit trail that ties the new metadata to the specific upstream commits that were absorbed:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     decision --plan-id {plan_id} --level INFO \
     --message "(plan-marshall:phase-5-execute:self-absorb) Absorbed {upstream_commit_count} upstream commits with zero overlap: {divergent_commits}"
   ```

   Log the work-log `[STATUS]` line for grep-ability:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level INFO \
     --message "[STATUS] (plan-marshall:phase-5-execute) Self-absorbed zero-overlap drift: {upstream_commit_count} commits, new main_sha={main_sha}"
   ```

   Then **continue the task loop** — no return to orchestrator, no dispatch to phase-2-refine, no architecture reload, no source-premise verification, no Q-Gate. Self-absorption is metadata-only: the request narrative, solution outline, task list, and confidence score remain valid because the upstream commits touched no overlapping files. Proceed to Step 4.

8. **Drift contract — `conflict_count > 0`** (non-zero-overlap case): the upstream commits touch files that overlap with the worktree's in-flight changes. ABORT the phase fail-loud — re-authoring is required and only refine's iterate-to-confidence loop can absorb the overlap correctly. Return the structured drift TOON for the orchestrator's drift-recovery branch to act on (see `plan-marshall:plan-marshall/workflow/execution.md` § "Baseline drift recovery (non-zero overlap)"):

   ```toon
   status: error
   error_type: baseline_drift
   divergent_commits: {divergent_commits}
   upstream_commit_count: {upstream_commit_count}
   conflict_count: {conflict_count}
   display_detail: "baseline drift: {upstream_commit_count} upstream commits"
   ```

   Log the failure to work-log:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level ERROR \
     --message "[ERROR] (plan-marshall:phase-5-execute) Baseline drift at {worktree_path} with non-zero overlap ({conflict_count} conflicting files) — origin/{base_branch} contains commits not in HEAD: {divergent_commits}. Returning structured drift TOON; orchestrator will re-dispatch phase-2-refine."
   ```

   Phase-5-execute does NOT perform substantive reconciliation for non-zero overlap. The orchestrator's drift-recovery branch dispatches phase-2-refine, which surfaces the upstream commits as Q-Gate findings and runs the iterate-to-confidence loop to absorb the overlap.

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
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
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

Both forms emit exactly one `[STATUS]` line; the wording difference makes it possible to grep for re-entries during retrospective gap analysis.

**Surface the active worktree absolute path** so it remains visible in model context for every subsequent Edit/Write/Read call. Read the worktree path from status metadata:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
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
2. Execute the action (delegate if specified) — when delegating to a subagent via `Task:`, `Skill:` (prompt-accepting), or `execution-context`, the subagent inherits the pinned cwd per the **Dispatch Protocol** section above; pass `plan_id` as the structured input and optionally embed the reminder header.
3. Mark step complete via `manage-tasks:finalize-step`

### Step 6.5: Scope-Creep Guard (per-task)

After Step 6 completes its file-system changes but BEFORE running task verification (Step 7's `finalize-step` records "done" only after this guard clears), invoke the deterministic scope-creep helper. The helper computes the residual file-set drift — files modified since the plan was created that are NOT declared in the union of all deliverables' `affected_files` — and emits a `scope_creep_warning` finding when the residual cardinality exceeds the configured threshold.

```bash
python3 .plan/execute-script.py plan-marshall:phase-5-execute:scope_creep_check \
  check --plan-id {plan_id}
```

The helper reads `plan_creation_sha` from `references.json`, computes `git diff --name-only {plan_creation_sha}..HEAD` against the worktree, subtracts the union of `affected_files` from every deliverable, and returns:

```toon
status: success
residual_count: N
threshold: T
finding_emitted: true|false
residual_files[N]: [paths]
```

When `finding_emitted: true`, the helper has already persisted a `scope_creep_warning` finding to the Q-Gate findings store via `manage-findings qgate add --type scope_creep_warning`. The finding flows into the Step 11 triage loop alongside other verify findings (same resolution path: FIX / SUPPRESS / ACCEPT). No additional surface action required here — the standard triage loop handles it.

**Threshold configuration**: default is `5`; override via `phase_5.scope_creep_threshold` in `marshal.json`'s plan-scoped config. Set to `0` to disable the guard entirely.

### Step 7: Mark Step Complete

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step \
  --plan-id {plan_id} \
  --task-number {task_number} \
  --step {step_number} \
  --outcome done
```

### Step 8: Log Task Completion

After each task completes, the canonical `[OUTCOME]` work-log line is emitted **inside `manage-tasks finalize-step`** — see `manage-tasks/SKILL.md` § "Script-Level [OUTCOME] Emission" for the contract. The script fires exactly one `[OUTCOME] (plan-marshall:phase-5-execute) Completed TASK-NNN: {title} ({M} steps)` line on the task-closing finalize call. **Skills MUST NOT emit a manual `[OUTCOME]` line here** — duplicating the script-level guard creates double entries; the line is lost whenever an execution-context is re-dispatched and the original agent's working context is discarded before its caller-side `[OUTCOME]` can fire, which is exactly why the emission was moved into the script.

Immediately after the script-emitted `[OUTCOME]` line, emit one `[ARTIFACT]` work-log entry per file the task changed by diffing the task-start SHA (recorded at `in_progress` transition as `task_start_sha`) against the current HEAD. See `standards/workflow.md` § **Artifact Emission at Task Completion** for the authoritative procedure, status-code mapping, and rename-handling rule. The artifact entries use a deliberate three-segment caller prefix `(plan-marshall:phase-5-execute:{task_number})` — a documented exception to the usual two-segment `(bundle:skill)` convention in [manage-logging/standards/log-format.md](../manage-logging/standards/log-format.md). Emit nothing when the diff is empty. This step precedes `manage-tasks next` so the audit trail for each task is flushed before the orchestrator advances.

### Step 8b: Persist Per-Task Subagent Usage to Accumulator

**Applies when**: the task was executed by dispatching to a Task agent / `execute-task` Skill that returned a `<usage>` tag. Inline tasks (or task agents that produced no `<usage>` tag) skip this step.

Persist the agent's `<usage>` totals to the on-disk per-phase accumulator so `manage-metrics phase-boundary` can read them at end-of-phase, regardless of whether the model context survives until the next orchestrator turn:

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics accumulate-agent-usage \
  --plan-id {plan_id} --phase 5-execute \
  --total-tokens {total_tokens} --tool-uses {tool_uses} --duration-ms {duration_ms}
```

Replace the placeholders with the integers parsed from the dispatched agent's `<usage>...</usage>` block. The canonical token key inside the `<usage>` block is `total_tokens` — the same integer forwarded to `--total-tokens` — so emitters use the canonical key the `manage-metrics enrich` parser prefers. The script reads `.plan/plans/{plan_id}/work/metrics-accumulator-5-execute.toon` (initialising it on first call), sums in the supplied values, increments `samples`, and writes the file back. The on-disk file is the only source of truth — do NOT also keep a parallel tally in model context. See `manage-metrics/standards/data-format.md` § "Per-Phase Subagent Accumulator" for the file schema.

The orchestrator's `phase-boundary` call in `workflow/execution.md` (recorded at end of execute) reads this accumulator as a fallback when its `--total-tokens` / `--tool-uses` / `--duration-ms` flags are omitted. Inline tasks contribute nothing — `manage-metrics enrich` (run by `phase-6-finalize:default:record-metrics`) sweeps the transcript for any subagent `<usage>` tags whose timestamp falls inside the `5-execute` window and adds them to the per-phase `subagent_*` columns of the metrics report as a post-hoc safety net.

### Step 9: Independent Change Verification

**Applies to**: `implementation` and `module_testing` profile tasks only. Skip this step for `verification` profile tasks.

After task completion but before committing, independently verify that the task agent produced genuine results rather than trusting self-reports. Any subagent dispatch made during this step (e.g., a follow-up Task invocation) inherits the pinned cwd per the **Dispatch Protocol** section above and resolves `.plan/` cwd-relatively.

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

### Step 10: Per-Deliverable Chain-Tail (Commit + Focused Build)

Step 10 fires at the **per-deliverable chain-tail point** — the moment all tasks for the just-completed deliverable are done. Two independent concerns hang off this point: the conditional per-deliverable commit (gated on `commit_strategy`) and the focused per-deliverable build (gated on `per_deliverable_build`). Both evaluate the same chain-tail predicate; the commit decision runs first, then the build.

**Chain-tail predicate**: Does any other pending/in-progress task have `depends_on` pointing to the just-completed task?
- **YES** → a downstream task still needs to run → this is NOT the chain tail → skip both the commit and the focused build, proceed to Step 11.
- **NO** → all tasks for this deliverable are done → this IS the chain tail → run the commit decision (Step 10a) then the focused build (Step 10b).

#### Step 10a: Conditional Per-Deliverable Commit

If `commit_strategy == per_deliverable` (cached from Step 2):

1. **Commit**:
   ```
   Skill: plan-marshall:workflow-integration-git
   Parameters:
     - message: conventional commit derived from task title
     - push: false
     - create-pr: false
   ```

2. **Log commit outcome**:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level INFO --message "[OUTCOME] (plan-marshall:phase-5-execute) Per-deliverable commit: {task_id} ({commit_hash})"
   ```

If `commit_strategy` is `per_plan` or `none` → Skip the commit; still proceed to Step 10b.

#### Step 10b: Focused Per-Deliverable Build (buildable-stuff guarded)

The mid-execute per-deliverable build is **focused** by design: it resolves the single changed module from the just-completed deliverable and runs a depth-gated build scoped to that module — never a whole-tree sweep. The whole-tree quality sweep (`build_verify` / `quality_check`) stays **once** at end-of-phase (Step 11b) and is never repeated mid-execute. This step fires at the chain tail, after the Step 10a commit decision.

1. **Read the depth knob** — resolve `per_deliverable_build` from the plan-scoped config:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
     plan phase-5-execute get --field per_deliverable_build --audit-plan-id {plan_id}
   ```

   The knob is an enum with four execution depths (`off` / `compile-only` / `compile+scoped-test` / `full`); the default is `compile+scoped-test`. The enum vocabulary and its validator are owned by `plan-marshall:manage-config` (`per_deliverable_build` field) — do NOT restate the enum semantics here; this step consumes the resolved value.

2. **`off`** → skip the per-deliverable build entirely. The end-of-phase Step 11b sweep is the only build. Log the decision and proceed to Step 11:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     decision --plan-id {plan_id} --level INFO \
     --message "(plan-marshall:phase-5-execute) per_deliverable_build=off — skipping focused build for deliverable {deliverable}; end-of-phase sweep is the only build"
   ```

3. **Buildable-stuff guard** — classify the deliverable's changed paths against the canonical six-bucket file-type classifier before running any Python build. The classifier vocabulary, predicates, and overlap-resolution policy are the normative source of truth at [`../phase-3-outline/standards/outline-workflow-detail.md` § File-type classifier](../phase-3-outline/standards/outline-workflow-detail.md#file-type-classifier) — do NOT restate the bucket vocabulary here. When the deliverable's changed paths resolve to `documentation_only` (no `.py` touched — typical workflow-doc edit), the deliverable has no buildable Python stuff: skip `compile` / `module-tests` and run only the documentation gate. The doc-gate form depends on which docs changed: when any changed path is a marketplace skill `.md` body (`marketplace/bundles/**/skills/**/*.md`), the doc gate MUST use the rule-complete, scoped `pm-plugin-development:plugin-doctor:doctor-marketplace quality-gate --paths {skill-dir} --marketplace-root {worktree_path}/marketplace` form — NOT the rule-less `list-components`, because `list-components` runs zero rules (enumeration only) and omits the `analyze_lesson_id_in_skill_prose` (and other quality-gate) rules that CI's `verify / verify` stage runs, so a `list-components` pass is not a CI-equivalent gate; for non-marketplace docs, markdown validation is the gate. Never run the Python build for a `documentation_only` deliverable. This extends the plan-wide docs-only guard (manage-execution-manifest composer) down to the per-deliverable execute loop. Log the skip and proceed to Step 11:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     decision --plan-id {plan_id} --level INFO \
     --message "(plan-marshall:phase-5-execute) Buildable-stuff guard: deliverable {deliverable} resolved documentation_only — skipping Python build, running doc gate only"
   ```

4. **Focused build** (buildable deliverable — at least one `.py` changed). Resolve the changed module, then run the depth-gated commands scoped to that module only:

   a. **Resolve the changed module** from the deliverable's modified files:

      ```bash
      python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
        which-module --path {changed_path}
      ```

      Capture the returned module as `{module}`.

   b. **Resolve and run the depth-gated build** via `architecture resolve` (never hard-code `./pw` / `mvn` / `gradle` / `npm`):

      - **`compile-only`** → resolve and run `compile` scoped to the changed module:

        ```bash
        python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
          resolve --command compile --module {module} --audit-plan-id {plan_id}
        ```

      - **`compile+scoped-test`** (default) → run BOTH commands scoped to the changed module: first the `compile` command from the `compile-only` branch above, then resolve and run `module-tests`. The two are distinct checks (e.g. `compile` type-checks, `module-tests` runs the test suite); `module-tests` does not subsume `compile`, so both are required at this depth:

        ```bash
        python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
          resolve --command module-tests --module {module} --audit-plan-id {plan_id}
        ```

      - **`full`** → resolve and run whole-tree `quality-gate` (the legacy whole-tree-per-deliverable behavior; opt-in only):

        ```bash
        python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
          resolve --command quality-gate --audit-plan-id {plan_id}
        ```

      Execute the returned `executable` for each resolved command. Honor the architecture-resolved `bash_timeout_seconds` / `execution_tier` envelope: for `execution_tier=per_task` run the build inline with `timeout: bash_timeout_seconds * 1000`; for `execution_tier=orchestrator` return control to the orchestrator to run the long build (do NOT background it). After each build call, inspect the result TOON — read `status` and the `errors[]` rows, not the harness exit code (the build wrapper exits 0 even on failure).

5. **On non-zero exit** — route the failure through the **existing Step 11 per-task triage path**: persist each failing finding to the Q-Gate store (`manage-findings qgate add`) and return the `triage_required` signal to the orchestrator. Do NOT invent a new triage surface — reuse the Step 11 contract verbatim (`producer=build-runner`, `finding_type=verification-failure`).

### Step 11: Triage Verification Failure

**Applies when**:
- A `profile=verification` task completes with `verification.passed: false` / `next_action: requires_triage`, OR
- Step 9 marked a task `blocked` with reason `no_changes_detected` or `verification_mismatch`

The per-finding LLM core (FIX / SUPPRESS / ACCEPT / AskUserQuestion decisions over the failing findings) is owned by [`../plan-marshall/workflow/verification-feedback.md`](../plan-marshall/workflow/verification-feedback.md). This per-task body is a leaf and does NOT dispatch it — the leaf persists the findings and returns a `triage_required` signal; the main-context orchestrator dispatches `verification-feedback` under `--phase phase-5-execute --role verification-feedback` with `producer=build-runner` (see [`../plan-marshall/workflow/execution.md`](../plan-marshall/workflow/execution.md) and the canonical contract in [`ref-workflow-architecture/standards/agents.md`](../ref-workflow-architecture/standards/agents.md)).

#### Pre-triage scope cross-reference

Before composing the triage dispatch, classify the failing file paths against the plan's declared `modified_files` from `references.json`. The cross-reference is deterministic — a small Python helper that subtracts `modified_files` from the union of error paths and returns a `exclusively_out_of_scope` flag:

```bash
python3 .plan/execute-script.py plan-marshall:phase-5-execute:verify_failure_scope \
  classify --plan-id {plan_id} --error-paths {comma_separated_paths}
```

The script reads `modified_files` from `references.json`, classifies each error path, and returns:

```toon
status: success
total: N
in_scope_count: I
out_of_scope_count: O
exclusively_out_of_scope: true|false
out_of_scope_paths[O]: [paths]
```

**When `exclusively_out_of_scope: true`**: the failing tests originate ENTIRELY outside the plan's declared scope (a sibling refactor on the same branch surfaced unrelated breakage). The `[BLOCKED]` triage message MUST include the distinction (e.g., `"All N failures originate outside plan scope: {paths}"`) and the AskUserQuestion offered to the user MUST present **"Stash foreign files and re-verify"** as the default recommended action, alongside the standard FIX / SUPPRESS / ACCEPT options.

**When `exclusively_out_of_scope: false`** (the common case): proceed to the standard triage dispatch below without the foreign-failure annotation. The classification is informational only.

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
  --title "{finding_message}" --detail "{file}:{line}"
```

(One `qgate add` call per finding; the verification task's structured `findings[]` output drives this loop.)

**11d**: This per-task body is a **leaf** — it MUST NOT dispatch `verification-feedback` itself. After §11c has persisted each failing finding to the Q-Gate store, return a structured terminal payload to the main-context orchestrator and stop; the orchestrator owns the triage dispatch. See [`ref-workflow-architecture/standards/agents.md`](../ref-workflow-architecture/standards/agents.md) for the canonical leaf/dispatch-topology contract.

The leaf's return payload carries the discriminators the orchestrator needs to compose the dispatch:

```toon
status: blocked
display_detail: "{task_number} triage_required: {N} verification finding(s)"
triage_required: true
producer: build-runner
finding_type: verification-failure
plan_id: {plan_id}
```

(`finding_type: quality-gate-failure` for the Step 11b sweep path.) The findings are already in the per-plan store — the orchestrator's `verification-feedback` dispatch queries them by reference; the leaf does not embed the findings in its return.

The orchestrator-side handling — resolving the `verification-feedback` target via `manage-config effort resolve-target --phase phase-5-execute --role verification-feedback`, emitting the `[DISPATCH]` log line, dispatching `verification-feedback` (`producer=build-runner`, `caller_phase: phase-5-execute`) as a top-level `Task:` in the main context, and consuming the triage return to drive the §11e branch — lives in [`../plan-marshall/workflow/execution.md`](../plan-marshall/workflow/execution.md) § "Verification-feedback triage (leaf returned triage_required)". The per-finding triage core (FIX / SUPPRESS / ACCEPT / AskUserQuestion, smart grouping, overflow, and the Scope-Deviation Escalation guard) is owned by [`../plan-marshall/workflow/triage.md`](../plan-marshall/workflow/triage.md); the dispatch is by-reference (the subagent queries the store as its first workflow step).

**11e** (orchestrator-owned): The orchestrator inspects the `verification-feedback` return per [`../plan-marshall/workflow/execution.md`](../plan-marshall/workflow/execution.md):

- If `fix_tasks_created > 0` → increment `verify_iteration` in task metadata, reset the verification task to `pending`, continue the execution loop (fix tasks will execute before the re-queued verification task via `depends_on`).
- If `fix_tasks_created == 0` AND `overflow_deferred == 0` → mark the verification task complete (all findings suppressed / accepted / `taken_into_account`).
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

2. Execute the returned `executable`. On non-zero exit, persist the failures to the Q-Gate findings store (`manage-findings qgate add --type quality-gate-failure …`) and **return the `triage_required` signal to the orchestrator** with `producer=build-runner` and `finding_type=quality-gate-failure` — same leaf-returns-signal shape as Step 11d above, only the finding type changes. The leaf does NOT dispatch `verification-feedback` itself; the orchestrator owns the dispatch (see [`../plan-marshall/workflow/execution.md`](../plan-marshall/workflow/execution.md) § "Verification-feedback triage (leaf returned triage_required)") and drives the same fix-task / suppress / accept branch (Step 11e). After the orchestrator's triage resolves, the sweep is NOT re-run — Step 11b runs at most once per phase entry.

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

Before invoking `manage-status transition --completed 5-execute` (see **Phase Transition** section below), refuse to transition when any pending tasks remain AND when the on-disk worktree has not been observed by a fresh `verify` run. Pending-queue emptiness is **necessary but not sufficient**: a task that was marked `done` against a prior code state still leaves the queue empty, yet the codebase the orchestrator is about to ship has never been verified end-to-end. The canonical failure mode for this gap: `loop-exit-guard` returns `pending_count: 0` while the most recent `verify` predated the last source-file mutation, and CI fails on the pushed commit. Step 12a therefore enforces two co-equal gates: (a) `manage-tasks next` only surfaces the head of the queue, so a `null` next does NOT prove the queue is empty when downstream tasks are still in `pending` — fix tasks created by Step 11 triage commonly land here, and a premature transition silently abandons them; (b) the worktree state itself must be **fresh** with respect to the most recent build-runner log entry.

**Script-level enforcement**: the authoritative pending-count check is `python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks loop-exit-guard --plan-id {plan_id}` — see `manage-tasks/SKILL.md` § "Loop-Exit Guard". `status: continue` (with `pending_count > 0` and `pending_ids`) forces the orchestrator to re-dispatch the execution-context; `status: success` (with `pending_count: 0`) is the precondition for recording the `clean_exit_queue_empty` termination cause via the `manage-metrics record-dispatch-boundary` verb. The list-based check below remains documented for backwards compatibility with existing callers — both forms read the same on-disk state, but `loop-exit-guard` is the canonical surface and the verb the orchestrator MUST consult.

**Worktree-state freshness enforcement**: the authoritative freshness check is `python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks pre-commit-verify-freshness --plan-id {plan_id}` — see `manage-tasks/SKILL.md` § "Pre-Commit Verify Freshness". The script compares the most recent `plan-marshall:build-pyproject:pyproject_build run` line in `logs/script-execution.log` against the most recent file mtime in the worktree (using `references.modified_files` when populated, otherwise a worktree-root walk) and returns one of three statuses. `status: fresh` permits transition; `status: stale` or `status: undecidable` blocks transition with the same `[BLOCKED]` log line shape used for the pending-tasks branch. The gate fails closed by design — there is no LLM judgement and no "probably fine" fallback. Pending-queue emptiness and worktree freshness are **co-equal** gates: both MUST succeed before the phase may transition.

1. Query the pending-task list:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks list \
     --plan-id {plan_id} --status pending
   ```

2. Parse the row count from the returned `tasks_table`. **If the count is zero**, proceed to step 2.5 (freshness check). **If non-zero**, jump to step 3.

2.5. Run the freshness check:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
     pre-commit-verify-freshness --plan-id {plan_id}
   ```

   Parse `status` from the returned TOON. **On `status: fresh`**, proceed to Phase Transition. **On `status: stale` or `status: undecidable`**, log a `[BLOCKED]` line and abort the transition:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level ERROR \
     --message "[BLOCKED] (plan-marshall:phase-5-execute) Worktree state not verified: {reason} (newest_mtime_path={path}, t_build={t_build_iso}, t_worktree={t_worktree_iso}) — refusing to transition 5-execute → 6-finalize. Re-dispatch a verify run, or invoke with --force to override."
   ```

   Substitute the placeholders with the corresponding fields from the script's TOON output. Each branch omits a different field set: `stale` omits `reason`; `undecidable` (both `no_build_log_entry` and `worktree_mtime_unresolvable` sub-cases) omits `newest_mtime_path` and `t_worktree_iso`, and the `no_build_log_entry` sub-case additionally omits `t_build_iso`. Substitute `-` for any field absent in the returned TOON. Do NOT call `manage-status transition` and do NOT auto-continue to finalize. The orchestrator's recovery path is to dispatch a fresh `verify` run, after which Step 12a is re-entered.

3. **If the pending count is non-zero**, the phase is NOT complete. Log a `[BLOCKED]` line and abort the transition:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level ERROR \
     --message "[BLOCKED] (plan-marshall:phase-5-execute) Pending tasks: {ids} — refusing to transition 5-execute → 6-finalize. Re-enter the execute loop to complete pending tasks, or invoke with --force to override."
   ```

   `{ids}` is a comma-separated list of `TASK-{number}` identifiers parsed from the `tasks_table`. Do NOT call `manage-status transition` and do NOT auto-continue to finalize.

4. **`--force` escape** (mirrors the verification-cap escape in `Step 11b`): when the orchestrator is invoked with `--force`, log the override decision, then proceed to Phase Transition. The escape covers both gates — pending tasks left intact AND a non-`fresh` freshness status. Emit one decision line per gate that the override bypasses:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     decision --plan-id {plan_id} --level WARNING \
     --message "(plan-marshall:phase-5-execute) Pending-tasks guard overridden via --force — transitioning with {count} pending task(s): {ids}"
   ```

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     decision --plan-id {plan_id} --level WARNING \
     --message "(plan-marshall:phase-5-execute) Worktree-freshness guard overridden via --force — transitioning with status={status}"
   ```

   Append `reason={reason}` to the message body only when `status` is `undecidable`; the `stale` branch does not emit a `reason` field, so the appended fragment is omitted for that branch. This mirrors the `--force` escape format in `phase-6-finalize/standards/commit-push.md` § Freshness precondition.

   The `--force` escape is a deliberate safety valve for triage-driven aborts (the user has already decided the pending tasks are out-of-scope, or that the stale-freshness signal is being addressed elsewhere) — never invoke it programmatically from inside the loop.

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

### B7 — voluntary_checkpoint no-progress reclassification

After a phase-5-execute dispatch returns and the orchestrator's classification rules in [`plan-marshall/workflow/execution.md`](../plan-marshall/workflow/execution.md) provisionally label the return as `termination_cause: voluntary_checkpoint`, the orchestrator evaluates the deterministic no-progress predicate:

> `in_progress_count > 0 AND completed_tasks_delta == 0 AND consumed_tokens > 50000`

When all three sub-conditions hold, the orchestrator reclassifies `termination_cause` from `voluntary_checkpoint` to `error` BEFORE invoking `record-dispatch-boundary`. The reclassification routes the dispatch into the shorter retry-budget / escalation path already coded for `error`, instead of letting another round of voluntary-checkpoint re-dispatches burn budget on a loop that is not making progress. Plans that DO make progress — even a single task completed (`completed_tasks_delta >= 1`), or cheap no-op iterations under the 50K-token threshold — keep the `voluntary_checkpoint` classification and continue along the standard recovery path.

The reclassification is a forensic + control-flow decision: the dispatch is still recorded via `record-dispatch-boundary`, only the `--termination-cause` value changes. The full predicate definition, sub-condition resolution rules, and decision-log shape (carrying all three predicate values for forensic reconstruction) live in [`plan-marshall/workflow/execution.md`](../plan-marshall/workflow/execution.md) § "B7 — voluntary_checkpoint no-progress reclassification".

### Forbidden: agent-initiated checkpoints

Phase-5-execute MUST drive the task loop to one of three terminal outcomes inside a single dispatch:

1. All pending tasks complete and the phase transitions to `6-finalize`.
2. A fatal error captured via the **Error Handling** section (including the pending-task drift error below).
3. A triage-driven `blocked` outcome that the skill itself acknowledges via `manage-tasks` status updates.

**Improvising a "progress checkpoint" return is a workflow violation.** Specifically, the dispatched agent MUST NOT:

- Emit a "Returning control to orchestrator" / "checkpoint reached" / "partial-completion handoff" line and stop with pending tasks still in the queue.
- Return a TOON payload that summarises "N of M tasks done, please re-dispatch" without one of the three terminal outcomes above.
- Ask the user whether to continue when no genuine decision is required (loop fatigue is not a decision point).

Agent-initiated re-dispatch is a control-flow drift that can cause `[OUTCOME]` log coverage gaps — the script-level `[OUTCOME]` guard in `manage-tasks finalize-step` closes the audit-trail gap, but the underlying drift also needs to be ruled out at the skill level. The orchestrator (`plan-marshall` workflows) is the single component allowed to start, re-dispatch, or terminate phase-5-execute; the dispatched agent does not get to vote.

### Deterministic exit clause (token-budget sentinel)

The loop's continue-vs-yield decision is governed by exactly one deterministic clause — no per-task heuristics, no "this task feels expensive" intuition, no "context is filling up" sense-checks. The clause is evaluated in canonical order:

> **Small-plan short-circuit**: If `tasks_total <= 2` (read from `phase_5.tasks_total` in the execution manifest cached at Step 2), the sentinel is disabled for the dispatch lifetime — continue to the next task until the queue is empty or a terminal outcome fires.
>
> **Final-task long-running-verify short-circuit**: If BOTH (a) the current task is the final task in the queue (`task_index + 1 == tasks_total`) AND (b) its resolved verification command is in the known long-running build set (`verify`, `coverage`, `quality-gate` fully scoped), suppress the sentinel for this single task — continue and finish in-dispatch. The cost-benefit is asymmetric: re-dispatching at the queue tail to run a long-running build pays the full dispatch overhead for zero scheduling benefit (no subsequent task ever runs). Log the suppression decision via `manage-logging decision`.
>
> **Budget-vs-N comparison** (applies only when neither short-circuit fires): **If `remaining_budget > N`: continue to the next task. Else: yield.**

The small-plan short-circuit drops the orchestrator/task ratio from 3-5x to 1.0x for 1-task plans by suppressing the inter-task yield boundary that the budget-vs-N clause would otherwise impose. The threshold of `2` is deliberately conservative: a plan with at most two tasks completes well inside any reasonable per-dispatch budget, and the inter-task yield is pure overhead. The cross-phase analogue — per-phase caching of loop-invariant inputs — is documented in the phase-2/3/4 "Loop-invariant inputs (cached at phase entry)" subsections (see `phase-2-refine/SKILL.md`, `phase-3-outline/SKILL.md`, and `phase-4-plan/SKILL.md`) and in `extension-api/standards/dispatch-granularity.md` § 5.1 (Heuristic 2 — bundle when steps share context).

Where `N` is the per-task budget reserve (the minimum context window that must be available before the loop is allowed to start another task). The clause runs once after each task completes — between `manage-tasks finalize-step` of the closing step (which fires the canonical `[OUTCOME]`) and the next `manage-tasks next` call. There is no intermediate decision point.

**Budget items consumed per task** (the sentinel's accounting model — these are the costs `N` must reserve for):

1. **`execute-task` in-context skill load** — the per-task `Skill:` load of `execute-task` (within the single phase-5-execute envelope, not a subagent dispatch) that runs the actual implementation/test/verification work. This is the largest cost per task and includes the skill body plus the standards it loads on entry.
2. **Auto-injected `--project-dir` verify step** — when the plan resolves to a worktree, `plan-marshall:execute-task:inject_project_dir` rewrites each `task.verification.commands[N]` to forward the worktree path. The rewritten command consumes additional executor + build-system context that the budget model must NOT under-account; it is part of every implementation / module_testing task and a primary driver of per-task cost variance.

**Resolving `N`** — the threshold MUST come from a manifest-resolvable knob, not a literal:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get --field per_task_budget_reserve --audit-plan-id {plan_id}
```

When `per_task_budget_reserve` is set, use its value as `N`. **Fallback when the knob is absent**: use the conservative default `N = 50000` tokens. The fallback exists so plans that have not yet migrated to the manifest-driven model still observe a deterministic yield boundary rather than running until the host platform forces a `harness_cancellation`. Plans that need a different reserve raise the value in `marshal.json`'s `plan.phase-5-execute.per_task_budget_reserve` slot.

**Cross-reference to the three terminal outcomes** — the sentinel is the **continue-vs-yield** decision, not a fourth terminal outcome. When the sentinel says "yield", the agent still MUST exit via one of the three documented terminal paths above (queue empty → transition; fatal error → structured error TOON; triage `blocked` → manage-tasks status update). Yielding does NOT mean "return a partial-completion checkpoint" — that path is explicitly forbidden by the section above. The orchestrator re-dispatches the execution-context on the next round; the in-flight task's state is already persisted by `manage-tasks finalize-step` so resumption is lossless.

**Audit diagnostic ledger** — when investigating throughput regressions (e.g., "why did this run process 1 task at ~119k tokens while a prior run processed 4 at ~210k?"), inspect the per-dispatch overhead in the work log. Each `execution-context` dispatch carries a fixed cost (skill-load preamble + optional reminder-header echo + return-TOON marshalling); the ratio of overhead to useful work per dispatch is the first thing to check when budget accounting drifts.

---

## Phase Transition

When transitioning from execute phase to finalize:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status transition \
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

## Canonical invocations

The canonical argparse surface for the two entry-point scripts this skill registers: `scope_creep_check.py` and `verify_failure_scope.py`. The plugin-doctor analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for the `manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### scope_creep_check — check

```bash
python3 .plan/execute-script.py plan-marshall:phase-5-execute:scope_creep_check check \
  --plan-id PLAN_ID [--threshold THRESHOLD]
```

### verify_failure_scope — classify

```bash
python3 .plan/execute-script.py plan-marshall:phase-5-execute:verify_failure_scope classify \
  --plan-id PLAN_ID [--error-paths ERROR_PATHS]
```

