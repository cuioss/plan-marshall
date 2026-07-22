---
lane:
  class: core
  cost_size: XXL
name: phase-5-execute
description: Execute phase skill for plan management. Manifest-driven task runner that executes tasks from TASK-*.json files sequentially and runs the per-deliverable plus end-of-phase verification sweep from manifest.phase_5.verification_steps.
user-invocable: false
mode: workflow
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Phase Execute Skill

**Role**: DUMB TASK RUNNER that executes tasks from TASK-*.json files sequentially.

**Execution Pattern**: Locate current task → Execute steps → Mark progress → Next task

**Phase Handled**: execute

## Foundational Practices

```text
Skill: plan-marshall:persona-plan-marshall-agent
```

## Enforcement

> **Shared lifecycle patterns**: See [phase-lifecycle.md](../ref-workflow-architecture/standards/phase-lifecycle.md) for entry protocol, completion protocol, and error handling convention.

**Execution mode**: DUMB TASK RUNNER — locate task, execute steps, mark progress, next task. Follow workflow steps sequentially.

**Prohibited actions:**
- Never access `.plan/` files directly — use manage-* scripts via Bash (Edit/Write tools trigger permission prompts on `.plan/` directories)
- Never skip the phase transition — use `manage-status transition`
- Never improvise script subcommands — use only those documented below
- Never target file paths outside the active git worktree.
- Never stop to ask the user "should I run the integration/e2e tests?" — every entry in `manifest.phase_5.verification_steps` runs automatically. The manifest is the single authority for which verification steps fire; the composer already footprint-gated and resolvability-skipped each entry at compose time, so there is no per-run human decision about whether to run a given canonical verify step.

**Constraints:**
- Strictly comply with all rules from persona-plan-marshall-agent, especially tool usage and workflow step discipline

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

**Phase 5 is the materialization phase.** Phases 1–4 only *declare* the worktree intent (`metadata.use_worktree`, written by `phase-1-init`); the feature branch is not recorded early — Step 2.5 below is the single point where the worktree directory and feature branch are actually created on disk, deriving the branch as `feature/{plan_id}` and persisting `metadata.worktree_branch` then. **Step 2.5 is unconditional and runs BEFORE the `early_terminate` short-circuit evaluation (Step 2.6 below).** Hoisting Step 2.5 above the short-circuit guarantees that `metadata.worktree_path` is always backfilled regardless of the manifest's `early_terminate` flag — otherwise an analysis-only plan that the composer marks `early_terminate=true` would transition to finalize without ever populating the worktree path, and the `phase_handshake verify` assertion at the 5→6 boundary would fail with `worktree_unresolved`. This ordering rules out an early-terminate path that transitions to finalize without ever populating the worktree path. Re-entry semantics: when phase-4-plan's capture ran without a populated `metadata.worktree_path` (because Step 2.5 had not yet executed), the `phase_handshake verify --phase 4-plan --strict` call MUST tolerate the still-empty value at phase-5 entry, then Step 2.5 populates `worktree_path` in both `references.json` and `status.metadata` before any task dispatch. On every subsequent phase-5 re-entry (orchestrator re-dispatch), Step 2.5's idempotence guard observes the populated `worktree_path` and short-circuits — no re-creation, no duplicate `git checkout -b`.

## Dispatch Protocol (cwd-Pinned Inheritance)

Under the move-based, cwd-pinned model (ADR-002), the worktree binding is carried by the **pinned current working directory**, not by per-call path forwarding. Step 2.5 pins the orchestrator's cwd to the worktree root after `prepare_execute.py` moves the plan directory and the executor in; every subprocess spawned and every subagent dispatched inherits that cwd, and `.plan/` resolution is cwd-relative (`file_ops.get_base_dir()` walks up to the nearest ancestor containing `.plan/local`). A dispatched subagent therefore resolves the worktree-resident state without being told a path. See [`../tools-script-executor/standards/cwd-policy.md`](../tools-script-executor/standards/cwd-policy.md) for the single cwd-unchanged invariant — it is not restated here.

**Consequence for dispatch**: subagents do NOT forward `--plan-id` or `--project-dir` to working-tree-touching scripts for path resolution — the inherited pinned cwd binds them. The only structured input a dispatched workflow takes is `plan_id` as the *plan-identifier* prompt-body field (selecting which plan's metadata to operate on; unrelated to cwd binding), per the dispatched workflow's own Input Contract (`execute-task`, the per-phase workflow doc loaded by `execution-context-{level}`).

When the plan runs in an isolated worktree (see the `[STATUS] Active worktree` work-log line from Step 4), a short reminder header MAY be embedded as the first lines of the dispatch prompt to keep the never-edit-main-checkout invariant salient through free-form delegation:

```text
WORKTREE: cwd is pinned to this plan's worktree (ADR-002 cwd-pinned model).
Resolution is cwd-relative — do NOT forward a worktree path; do NOT pass --project-dir.
All Edit/Write/Read tool calls and tool invocations (git, mvn, npm) operate against the pinned cwd.
NEVER edit the main checkout. See tools-script-executor/standards/cwd-policy.md.
```

The header is a **reminder, not a path-routing mechanism** — the binding holds whether or not the header is present, because cwd-pinning carries it. The worktree absolute path MUST NOT appear in dispatch prompts. `--project-dir <abs>` survives only as the **escape hatch** for callers invoked outside a pinned-cwd context (post-worktree-removal cleanup, fixture-driven test invocations); it MUST NOT be forwarded inside a phase-5+ pinned-cwd dispatch. The complete contract — cwd-pinned inheritance, the merge-lock exception, and the `--plan-id`/`--project-dir` three-state escape-hatch binding — is documented in `workflow-integration-git/standards/worktree-handling.md` § Dispatch Protocol and `../tools-script-executor/standards/cwd-policy.md`.

The `[STATUS] Active worktree: ...` work-log line is the observability signal that the worktree was materialized and cwd was pinned. Child agents inherit the same pinned cwd and MUST NOT re-derive or forward a worktree path into any further dispatch.

This applies to every dispatch in the execution loop, including (but not limited to) **Step 6 (Execute Steps)** task dispatches and **Step 9 (Independent Change Verification)** subagent invocations.

See `standards/operations.md` for the complete set of dispatch pattern templates and `workflow-integration-git/standards/worktree-handling.md` for the worktree-specific application of this rule.

### Common anti-patterns to avoid (mirrored from persona-plan-marshall-agent)

Each Bash tool call dispatched during execute must contain exactly ONE command. Never combine with newlines, `&`, `&&`, `;`, or inline env-var assignment of the form `VAR=val cmd`. The `VAR=val cmd` shape combines the assignment and the command into one shell argument, which trips the host platform's permission UI and obscures the env-var contract by hiding the variable inside the command line rather than declaring it explicitly.

**Anti-pattern**: `MY_VAR=value python3 some_command.py ...`

**Safe alternative (option A)** — Pass the value as a flag arg:

`python3 some_command.py ... --my-var value`

**Safe alternative (option B)** — Set the env var in the command's invocation header (e.g., a separate `env MY_VAR=…` line, NOT inline) before launching the bash command, or define the value as a Python module-level constant lookup inside the script itself.

See [`persona-plan-marshall-agent` Hard Rules](../persona-plan-marshall-agent/SKILL.md#bash-one-command-per-call) for the authoritative source.

## cwd for `.plan/execute-script.py` calls

> `manage-*` scripts (Bucket A) resolve `.plan/` via `git rev-parse --git-common-dir` and work from any cwd. Build / CI / Sonar scripts (Bucket B) bind to a working tree via `--plan-id` when a worktree is active. See `plan-marshall:tools-script-executor/standards/cwd-policy.md` for the Bucket A/B split and `workflow-integration-git/standards/worktree-handling.md` for the worktree-specific application of this rule.

---

## Standards (Load On-Demand)

### Workflow
```text
Read standards/workflow.md
```
Contains: Task execution pattern, phase transition, auto-continue behavior

### Operations
```text
Read standards/operations.md
```
Contains: Delegation patterns for builds, quality checks, PR creation

### Recovery Patterns
```text
Read standards/recovery.md
```
Contains: First-line response to mid-plan `origin/main` advances — stash + merge + pop, with works/does-not-work conditions and rationale vs rebase.

### Coverage Contract (per-task scope × thoroughness)
```text
Read ../persona-plan-marshall-agent/standards/thoroughness.md
```
Contains: the *scope × thoroughness* coverage contract each task body honors at its execution coverage point — the thoroughness ladder (T1–T5), the scope ladder, the grade-to-the-floor rule, and the coupling constraint `reject thoroughness ≥ T4 ∧ scope < component`. Per-task work covers its declared cell; the floor-graded self-report states asked-for vs achieved.

---

## Dispatched workflows vs inline steps

**This document IS the phase-5 envelope workflow.** The orchestrator's Execute-phase dispatch (see [`../plan-marshall/workflow/execution.md`](../plan-marshall/workflow/execution.md) § "Execute Phase") MUST wire its `workflow:` field to `plan-marshall:phase-5-execute/SKILL.md` — THIS runner, which drives the envelope task loop and LOADS `execute-task` in-context per task. The `execution-context` dispatcher **executes the `workflow` doc**; the `skills[]` list is loaded only for context. Wiring the `workflow:` field to `plan-marshall:execute-task/SKILL.md` (the single-task runner that returns `next_action: task_complete` after ONE task) is the dispatch defeat: the leaf then runs exactly one task and echoes `task_complete`, forcing the orchestrator into a wasteful per-task re-dispatch loop. `execute-task` appears in `skills[]` because THIS workflow loads it in-context per task — never as the dispatched `workflow`.

**One-context-per-phase invariant (durable contract).** A core phase completes in exactly ONE `execution-context` dispatch per envelope group — precisely `envelope_count` dispatches (typically 1, and NEVER one dispatch per task). The bin-packer pre-computed the envelope grouping at plan time; the executor drives its whole assigned `envelope_id` group to exhaustion inside a single dispatch, yielding only at the three sanctioned TASK-boundary points (`budget_yield` / `triage_required` / `baseline_drift`). The only sanctioned sibling dispatches OUT of this envelope are the ones the main-context orchestrator owns (the `verification-feedback` triage and the adversarial validators) — the leaf returns a signal, it never dispatches. Returning a bare `task_complete` echo while pending same-envelope tasks remain is the **`task_complete_returned_verbatim`** defect (see § "Forbidden: agent-initiated checkpoints"): it collapses the envelope loop into a per-task re-dispatch and is a control-flow violation, NOT a legitimate yield.

This phase dispatches under one role key: **`phase-5-execute`** (resolves through `phase-5-execute.default`). The dispatch unit is **envelope-bounded** — explicitly NEITHER per-task NOR per-deliverable. The continue-vs-yield decision is **pre-computed at plan time**: phase-4-plan's bin-packer (`manage-tasks pack-envelopes`) groups tasks into execution envelopes in `depends_on` order under `per_envelope_budget_tokens`, stamps each task with an `envelope_id`, and records `envelope_count` in the manifest. The orchestrator then dispatches ONE `execution-context` envelope per `envelope_id` group (exactly `envelope_count` dispatches), passing each its assigned `envelope_id`; the dispatched executor runs **only the tasks whose `envelope_id` matches its assigned group** and yields when its group is exhausted — a trivial countable "is the next pending task in MY envelope?" equality check with **NO runtime cost-summing, NO threshold evaluation, NO self-measurement** (the subagent cannot measure its own mid-turn context usage; only the orchestrator sees post-return `<usage>`, which it feeds back to recalibrate the size→token table). Per task the envelope LOADS the unified `execute-task` skill in-context as a `Skill:` with the task-declared skill list as runtime input — leaf-legal in-context skill loading per [`persona-plan-marshall-agent`](../persona-plan-marshall-agent/SKILL.md), explicitly NOT a per-task `Task:` subagent dispatch. The envelope yields to the orchestrator — which then re-dispatches the next envelope group — only at one of three TASK-boundary re-dispatch points: (a) envelope-group exhaustion (the next pending task's `envelope_id` differs from the assigned group → a `budget_yield` decision is logged and a wrapped terminal TOON is returned); (b) `triage_required` (Step 11/11b verify / quality-gate failure); (c) `baseline_drift`. It is NOT one envelope per task and NOT one envelope per deliverable. Deliverable boundaries govern the COMMIT + FOCUSED-BUILD points only — the Step 10 Per-Deliverable Chain-Tail (an unconditional per-deliverable commit, plus a focused per-module build) is a **sub-event that fires within OR across envelopes, decoupled from where the budget sentinel yields, and is NOT a dispatch boundary**; because the sentinel yields at TASK boundaries (between `finalize-step` and the next `manage-tasks next`), a mid-deliverable yield is normal and lossless (`finalize-step` persists in-flight task state, and the Step 10 chain-tail commit still fires whenever the run reaches it, regardless of which envelope gets there). This per-task body runs as a **leaf** inside the `execution-context` envelope — it cannot itself issue a `Task:` dispatch (see [`ref-workflow-architecture/standards/agents.md`](../ref-workflow-architecture/standards/agents.md), the canonical leaf/dispatch-topology contract). The built-in verification steps (the single parameterized `default:verify:{canonical}` step) stay inline as pure build invocations — no LLM judgement, no envelope. Step 9 independent change verification stays inline (three deterministic re-checks: git-diff empty-test, obfuscation-pattern grep, exit-code compare). Steps 11 and 11b detect the test-failure / lint-issue, persist each finding to the per-plan Q-Gate store (`manage-findings qgate add` — a script call, legal inside a leaf), then **return a `triage_required` signal to the main-context orchestrator**; the orchestrator owns the **`verification-feedback`** dispatch (`--phase phase-5-execute --role verification-feedback`, `producer=build-runner`) and consumes its return to drive the fix-task / suppress / accept branch. The leaf never dispatches `verification-feedback` itself. For the rationale see [dispatch-granularity.md](../extension-api/standards/dispatch-granularity.md) § 2, § 4 (Heuristic 3 — per-iteration `Task:` dispatch only when models differ OR iterations parallelise; the budget-bounded task loop is the iterate-in-context application), and § 5.1 (script over dispatch; phase-scoped resolution + producer-mode bundling).

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

### Step 2: Read Execution Manifest (Once at start)

**Read the execution manifest** — the manifest is the single source of truth for which Phase 5 verification steps fire. It is composed by `phase-4-plan` Step 8b and stored at `.plan/local/plans/{plan_id}/execution.toon`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  read --plan-id {plan_id}
```

Extract `phase_5.early_terminate` (bool), `phase_5.verification_steps` (list[string]), and `phase_5.step_execution_tier` (list of `{step_id, tier}` records) from the output. **Do NOT evaluate `early_terminate` yet** — Step 2 only reads the manifest and caches the values. Step 2.5 (worktree materialization) MUST run before the `early_terminate` short-circuit fires, so the short-circuit evaluation is deferred to Step 2.6 below.

The verification steps to execute at end of phase come from `phase_5.verification_steps` — this **replaces** today's lookup of `marshal.json`'s `phase-5-execute.steps`. The list is consumed by Step 11b (Final Quality Sweep) and the verification dispatch loop. See **Verification Step Types** below for dispatch rules. Each verification step's runnability is governed by the `execution_tier` the leaf resolves LIVE when it runs that step; the cached `phase_5.step_execution_tier` entry is the advisory compose-time expectation — see **Per-step `execution_tier` (advisory compose-time stamp; live resolve routes)** below.

The step IDs in the manifest are **bare** — `cmd_compose`'s boundary normalization strips only the leading `default:` prefix, so a built-in canonical-verify step appears as `verify:{canonical}` (e.g., `verify:quality-gate`, `verify:module-tests`, `verify:coverage`). Translate them to the `default:` prefixed names used by the Built-in Step Dispatch Table by prepending `default:` for built-in steps — e.g., `verify:quality-gate` → `default:verify:quality-gate`. Steps that already contain `:` beyond the `verify:` segment for project/skill steps (a `project:` or `bundle:skill` prefix) are passed through verbatim.

---

## Verification Step Types

The `phase_5.verification_steps` list from the manifest contains verification step references. Three step types are supported, distinguished by prefix notation (same model as phase-6-finalize):

| Type | Notation | Resolution |
|------|----------|------------|
| **built-in** | `default:` prefix (e.g., `default:verify:quality-gate`) | Execute built-in verification command (see dispatch table) |
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
| `default:verify:{canonical}` | Resolve the trailing `{canonical}` via `architecture resolve --command {canonical}` and run the resolved executable | Single parameterized verify step backing every canonical (`quality-gate`, `module-tests`/`verify`, `coverage`, `integration-tests`, `e2e`, …); the canonical is a parameter, not a hardcoded branch — see `standards/canonical_verify.md` |

**Dispatch detection**: a step ID starting with the `default:verify:` prefix routes to the single parameterized canonical-verify step. The SKILL strips the `default:` prefix and feeds the trailing `{canonical}` segment to `architecture resolve --command {canonical}`. The full step body — canonical resolution, `execution_tier`/`bash_timeout_seconds` handling, the unresolved-canonical skip, and the module-scoped vs whole-tree invocation contract — lives in `standards/canonical_verify.md`; do NOT restate it here. Threshold enforcement for `coverage` is native to the resolved build command (pytest `--cov-fail-under`, JaCoCo build-tool config) — no secondary parse-and-check call is required.

### Footprint gating (build-decision consult) for the end-of-phase `default:verify:{canonical}` loop

The end-of-phase whole-tree verification dispatch — Step 11b Final Quality Sweep and the loop that runs each `default:verify:{canonical}` step from `phase_5.verification_steps` — is **footprint-gated at execution time** via the `manage-config build-decision` verb, the sole build/no-build authority (see ADR-004 § "Amendment: `build-decision` is the sole build/no-build authority"). The consult call, the `not_necessary` skip path, and the `decision != not_necessary` run path are the same mechanics Step 11b spells out below for `quality-gate`; do NOT restate them here for other canonicals — apply the identical shape per-canonical. This gate applies ONLY to the **whole-tree** end-of-phase surface — the one footprint-blind phase-5 build surface. **Steps 10b (focused per-deliverable build) and 11c (Execute-Exit Verify Gate) are already footprint-aware — they derive the live footprint on demand and already skip when no buildable module is present — and are UNCHANGED by this gate.**

### Per-step `execution_tier` (advisory compose-time stamp; live resolve routes)

Every entry of `phase_5.verification_steps` carries a stamped `execution_tier` in the manifest's `phase_5.step_execution_tier` record list (`{step_id, tier}` per step; `tier ∈ {per_task, orchestrator}` — see [`manage-execution-manifest/SKILL.md`](../manage-execution-manifest/SKILL.md) § "Per-step execution_tier stamping").

**The stamp is ADVISORY; the live re-resolve is the routing authority.** The stamped tier derives from the adaptive learned build duration, which every intervening build updates, so a ceiling-adjacent step's tier legitimately changes between compose and execute — the same plan has been composed with `verify:coverage=per_task` and then, after a single whole-tree build, `verify:coverage=orchestrator`. The leaf therefore **re-resolves the tier live** as it runs each step, per [`standards/canonical_verify.md`](standards/canonical_verify.md) § Workflow steps 1-2, and routes on THAT verdict. Read the stamp for planning — how many orchestrator-tier steps this plan expects — never as the sole routing input. A stamp that disagrees with the live tier is expected behaviour, not a defect: the live tier wins, always.

This dispatched phase-5 leaf branches on the **live-resolved** tier for every whole-tree verification step it would run (Step 11b Final Quality Sweep and Step 11c Execute-Exit Verify Gate) and for each `default:verify:{canonical}` end-of-phase step:

- **`tier == per_task`** — the step is in the leaf's **runnable slice**. Run the resolved executable inline (synchronously) per `standards/canonical_verify.md`, honouring the resolved `bash_timeout_seconds`. Read the result TOON.
- **`tier == orchestrator`** — the step is **NOT in the leaf's runnable slice**. The leaf MUST NOT run it (inline OR backgrounded). Return an orchestrator-tier yield signal (`status: blocked`, `voluntary_checkpoint`) naming the step so the main-context orchestrator runs it through the [`await-long-running`](../plan-marshall/workflow/await-long-running.md) detach-and-notify seam (the only component permitted to background a build).

A step whose stamped tier is absent (a manifest composed before this field existed) reads as `per_task`. `per_task` is the **permissive default, not a safe floor** — it is the value that would put a long build inline, where the host platform auto-backgrounds it past the Bash ceiling and this leaf cannot reap it. That default is safe only because the leaf re-resolves live before running: the live resolve, not the stamp, is what keeps a long build off the leaf.

### Interface Contract for External Steps

Project and skill steps receive these parameters:

```text
Skill: {step_reference}
  Arguments: --plan-id {plan_id}
```

Input contract: `--plan-id` only. Retry logic is managed by the task runner (Step 11 triage loop with `max_iterations`), not by the step itself.

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

Phase 5 is the materialization phase for the worktree. Earlier phases only persisted the *intent* (`metadata.use_worktree`, written by `phase-1-init`); this step derives the feature branch `feature/{plan_id}`, creates the worktree directory and that branch on disk, and propagates the resolved path to both `references.json` and `status.metadata.worktree_path` BEFORE Step 3 reads them. The derived branch is persisted to `metadata.worktree_branch` by `prepare_execute`'s bookkeeping loop (via the `--branch` argument below), so every phase-6 reader of `metadata.worktree_branch` stays valid.

**Idempotence guard (must run first)**: read `metadata.worktree_path` and short-circuit when it is already populated — Step 2.5 has already executed on a prior phase-5 entry, the directory exists on disk, and no re-creation is needed.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id {plan_id}
```

Extract `metadata.use_worktree`, `metadata.worktree_path`, and the plan's `base_branch` (from `references.json` via `manage-references get`). Derive the feature branch deterministically as `worktree_branch = feature/{plan_id}` — it is NOT read from metadata, since phase-1-init no longer records it. If `worktree_path` is non-empty, log the short-circuit and proceed to Step 3:

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

Substantive baseline reconciliation now happens at refine time — see [phase-2-refine/standards/refine-workflow-detail.md § Step 3d](../phase-2-refine/standards/refine-workflow-detail.md#step-3d-baseline-reconciliation). Phase-5-execute is a fast-path "still clean?" verification: if the worktree branch is still ahead of (or merged with) `origin/{base_branch}`, continue to the task loop; if upstream commits have landed since the refine baseline-reconciliation pass, error out with a clear redirect — re-running phase-2-refine is the documented path. Phase-5-execute MUST NOT perform substantive reconciliation (no merge, no rebase).

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
   error: baseline_drift
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

**Infeasible deliverable — report, never silently substitute**: when a step's declared deliverable turns out to be infeasible during execution — the target cannot be cleanly built as the task specifies (the required surface does not exist, a precondition the deliverable assumed is false, or building the named artifact is structurally impossible as scoped) — the agent MUST report the infeasibility back through the gate and MUST NOT silently substitute a different, weaker deliverable under the same name. Mark the task `infeasible` — a first-class terminal status — via `manage-tasks update --status infeasible`, and have the leaf return a structured `status: infeasible` TOON carrying an `infeasibility_reason` field naming why the deliverable cannot be built as scoped. The `infeasible` task flows into the **Step 11 (Triage Verification Failure)** path, where the dedicated "For infeasible blocks" sub-section routes it to a planning-level gate decision (drop / re-scope / abort) rather than the `verification-feedback` code-fix loop. Narrowing the deliverable into a buildable-but-valueless artifact under the original name — so the step "passes" while delivering none of the declared value — is prohibited; the infeasibility is a real failure and belongs on the triage surface, not hidden behind a substituted deliverable. `infeasible` is terminal: it is resolved by the gate decision, never by resuming the same task.

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

### Step 8c: Record Per-Step Execution Outcome to the Manifest

**Applies to**: every Phase 5 verification step the envelope dispatches — the per-task `default:verify:{canonical}` built-in steps, the Step 11b final quality sweep, and each external (`project:` / `bundle:skill`) verification step. This is the consuming side of the `record-step` contract published by `manage-execution-manifest` (see that skill's Producers table — `phase-5-execute` is named as a `record-step` producer).

After a verification step settles (its build/check completes with a known outcome), append one execution-log row to the manifest so per-step execution metadata is loggable per-plan deterministically, rather than relying on the fragile orchestrator `<usage>`-forwarding boundary call alone:

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest record-step \
  --plan-id {plan_id} --step-id {step_id} --phase 5-execute --outcome {executed|skipped|error} \
  --total-tokens {total_tokens} --tool-uses {tool_uses} --duration-ms {duration_ms}
```

See `manage-execution-manifest` Canonical invocations → `record-step` for the authoritative argument surface. Contract:

- `--phase` is always `5-execute` in this phase; `--step-id` is the verification step ID (e.g. `verify:quality-gate`, `verify:module-tests`, `verify:coverage`, or an external step's notation).
- `--outcome` is `executed` when the step ran, `skipped` when a skip rule fired (e.g. the Step 11b skip when `verification_steps` is empty, or the Step 10b documentation-only / empty-list skip), and `error` when the step's build/check exited non-zero (recorded BEFORE the Step 11/11b `triage_required` return so the failed attempt is on the execution log).
- The token-attribution triple (`--total-tokens` / `--tool-uses` / `--duration-ms`) is the per-step cost; supply the integers parsed from the dispatched agent's `<usage>` block when one is available, and `0` for inline build invocations that carry no `<usage>` tag (a skipped step legitimately reports zeros). These are the SAME integers forwarded to the Step 8b `accumulate-agent-usage` call — Step 8b sums them into the per-phase accumulator that fills the `total_tokens` column, while Step 8c records the per-step breakdown; the two are complementary, not redundant.
- The manifest MUST already exist (composed by `phase-4-plan` Step 8b); `record-step` returns `file_not_found` otherwise. The append is atomic and one decision-log line is emitted per record.

**Exec-blind contract**: Phase 5 exec token counts MUST be recorded on EVERY plan. The combination of Step 8b (`accumulate-agent-usage` → fills the per-phase `total_tokens` column) and the orchestrator's end-of-execute `phase-boundary` call (which always fires at the `5-execute → 6-finalize` transition, reading the accumulator as its fallback) guarantees the phase-5 `total_tokens` in `metrics.toon` is non-zero — closing the historical exec-blind path where phase-5 `total_tokens==0`. Step 8c's per-step `execution_log[]` rows are the auditable per-step breakdown behind that aggregate. Because the `phase-boundary` record is reached unconditionally at the transition (Step 12 → **Phase Transition**), there is no plan path that skips the closing-phase token record.

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

Step 10 fires at the **per-deliverable chain-tail point** — the moment all tasks for the just-completed deliverable are done. Two independent concerns hang off this point: the (unconditional) per-deliverable commit and the focused per-deliverable build (gated on `per_deliverable_build`). Both evaluate the same chain-tail predicate; the commit runs first, then the build.

**Chain-tail predicate**: Does any other pending/in-progress task have `depends_on` pointing to the just-completed task?
- **YES** → a downstream task still needs to run → this is NOT the chain tail → skip both the commit and the focused build, proceed to Step 11.
- **NO** → all tasks for this deliverable are done → this IS the chain tail → run the commit (Step 10a) then the focused build (Step 10b).

#### Step 10a: Per-Deliverable Commit

The per-deliverable commit fires UNCONDITIONALLY at every chain tail — **regardless of which tier ran the preceding build.** Whether the deliverable's verification ran as an inline `per_task` build (reaped synchronously by the leaf) or as an `orchestrator`-tier build detached through the [`await-long-running`](../plan-marshall/workflow/await-long-running.md) seam, the commit obligation is identical: it is owner-independent. The build's tier decides *who runs and reaps the build*, never *whether the commit fires*. The commit consumes only the tier-agnostic `kind=build` freshness stamp written at the executor dispatch boundary (see [`../manage-change-ledger/SKILL.md`](../manage-change-ledger/SKILL.md)), which is present for the detached orchestrator build exactly as for an inline per-task build.

**Commit-ownership contract**: the phase-5-execute envelope is the SOLE owner of every per-deliverable commit — Step 10a is the one place a deliverable's changes are committed. A leaf (`execute-task` load) returning `done` while its edits sit uncommitted past the deliverable's chain tail is a contract violation, which the clean-tree post-condition at the `5-execute → 6-finalize` transition converts into a `worktree_dirty_at_boundary` refusal (see `manage-status` `cmd_transition`). The boundary settlement bookkeeping documented in [`../plan-marshall/workflow/execution.md`](../plan-marshall/workflow/execution.md) § "Execute Phase Completion" is the RECOVERY for that refusal, not the norm — it attributes each dirty path back to its owning deliverable, cuts one settlement commit per implicated deliverable (each with its own Step 10a-shaped `kind=change` ledger append), and halts loudly on any path that maps to no deliverable; commits belong here, at the chain tail. The initial-envelope backgrounding concern is closed by the leaf's live tier re-resolve, which runs before EVERY whole-tree verification step it would execute — so the leaf's `per_task`-only runnable slice and the orchestrator's `await-long-running` ownership of `orchestrator`-tier steps apply uniformly from the very first envelope dispatch onward, with no step for a leaf to background-and-lose. The compose-time stamp (`manage-execution-manifest._stamp_phase_5_step_execution_tier`) is total over `verification_steps` but advisory — it records the expected tier for planning, and the live resolve is what routes.

1. **Commit**:
   ```text
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

3. **Resolve the git-sourced `commit_sha`** — capture the SHA the commit just produced:

   ```bash
   git -C {worktree_path} rev-parse HEAD
   ```

   Record the output as `{commit_sha}`.

4. **Source the changed paths from git** — the `kind=change` entry's `changed_paths` MUST be git-sourced (NOT self-computed from the deliverable's declared `affected_files`). Enumerate the paths the commit touched:

   ```bash
   git -C {worktree_path} diff-tree --no-commit-id --name-only -r {commit_sha}
   ```

   Record the newline-separated output as `{changed_paths}` (join into a comma-separated list for the verb's `--changed-paths` argument).

5. **Append the `kind=change` ledger entry** — record the per-deliverable commit transition to the unified change-ledger. The verb stores the supplied `changed_paths` list verbatim; do NOT inline-copy the ledger API details — see [`../manage-change-ledger/SKILL.md`](../manage-change-ledger/SKILL.md) § "Canonical invocations" → `append (kind=change)` for the authoritative argument surface:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-change-ledger:manage-change-ledger append \
     --kind change --deliverable-id {deliverable} --commit-sha {commit_sha} --changed-paths {changed_paths} \
     --task-id {task_id}
   ```

#### Step 10b: Focused Per-Deliverable Build (module-scoped canonical-verify steps)

The mid-execute per-deliverable build is **focused** by design: it runs the `per_deliverable_build` list of `default:verify:{canonical}` step IDs **module-scoped** over the changed module(s), never a whole-tree sweep. The whole-tree quality sweep stays **once** at end-of-phase (Step 11b/11c) and is never repeated mid-execute — whole-tree gates (e.g. `integration-tests`, `e2e`) are NOT permitted in `per_deliverable_build`; they live in `verification_steps`. This step fires at the chain tail, after the Step 10a commit decision.

1. **Read the `per_deliverable_build` list** from the plan-scoped config:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
     plan phase-5-execute get --field per_deliverable_build --audit-plan-id {plan_id}
   ```

   The value is a **LIST** of `default:verify:{canonical}` step IDs (the same vocabulary as `verification_steps`); the default is `[default:verify:compile, default:verify:module-tests]`, which reproduces today's compile + scoped-test behaviour. The empty list `[]` means "no per-deliverable build" (the end-of-phase sweep is the only build). The vocabulary and its list-membership validator are owned by `plan-marshall:manage-config` (`per_deliverable_build` field) — do NOT restate the validation here; this step consumes the resolved list.

2. **Empty list `[]`** → skip the per-deliverable build entirely. The end-of-phase Step 11b/11c sweep is the only build. Log the decision and proceed to Step 11:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     decision --plan-id {plan_id} --level INFO \
     --message "(plan-marshall:phase-5-execute) per_deliverable_build=[] — skipping focused build for deliverable {deliverable}; end-of-phase sweep is the only build"
   ```

3. **For each `default:verify:{canonical}` entry in the list**, invoke the **canonical-verify step module-scoped** over the changed module(s): resolve `architecture resolve --command {canonical} --module {changed_module}` and run the resolved executable, honouring the returned `execution_tier` / `bash_timeout_seconds`. Do NOT restate the resolution/execution-tier logic here — see [`standards/canonical_verify.md`](standards/canonical_verify.md) § "Module-scoped vs whole-tree invocation" and § "Workflow" for the authoritative step body (module-scoped invocation supplies `--module {changed_module}`; the unresolved-canonical skip and the tier hand-off apply identically). After each build call, inspect the result TOON — read `status` and the `errors[]` rows, not the harness exit code (the build wrapper exits 0 even on failure).

   **Documentation-only short-circuit**: a changed-path set with no buildable module yields no module-scoped run (the canonical does not resolve / there is no changed module). Log:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     decision --plan-id {plan_id} --level INFO \
     --message "(plan-marshall:phase-5-execute) No buildable module for deliverable {deliverable} — no module-scoped build runs for this deliverable"
   ```

4. **On non-zero exit** — route the failure through the **existing Step 11 per-task triage path**: persist each failing finding to the Q-Gate store (`manage-findings qgate add`) and return the `triage_required` signal to the orchestrator. Do NOT invent a new triage surface — reuse the Step 11 contract verbatim (`producer=build-runner`, `finding_type=test-failure`).

> **Guideline — file-relocation lint gap.** When a deliverable RELOCATES a file (moves it from one path/module to another), the focused module-scoped per-deliverable build above can MISS lint/structural findings that only surface in a whole-tree sweep: a moved file implicates BOTH its old and new module, but a module-scoped gate sees only one of them. Sequence a relocation deliverable so the whole-tree verify runs AFTER the move completes, and NEVER skip the orchestrator whole-tree gate (Step 11c, Execute-Exit Verify Gate) on a plan that relocates files. The module-scoped per-deliverable build is NOT a substitute for the whole-tree gate on relocations.

### Step 11: Triage Verification Failure

**Applies when**:
- A `profile=verification` task completes with `verification.passed: false` / `next_action: requires_triage`, OR
- Step 9 marked a task `blocked` with reason `no_changes_detected` or `verification_mismatch`, OR
- A task was marked `infeasible` per Step 6 ("Infeasible deliverable — report, never silently substitute") — the leaf returned `status: infeasible` with an `infeasibility_reason`; this routes to the dedicated "For infeasible blocks" sub-section below, NOT the `verification-feedback` code-fix loop, OR
- The in-context `execute-task` load returned `escalate_ask: true` with `prompt_options[]` — a scope-deviation and/or `smart_and_ask` gate fired and the task is left not-done; this routes to the dedicated "Scope-deviation / `smart_and_ask` escalation yield" sub-section below, NOT the `verification-feedback` code-fix loop

The per-finding LLM core (FIX / SUPPRESS / ACCEPT / AskUserQuestion decisions over the failing findings) is owned by [`../plan-marshall/workflow/verification-feedback.md`](../plan-marshall/workflow/verification-feedback.md). This per-task body is a leaf and does NOT dispatch it — the leaf persists the findings and returns a `triage_required` signal; the main-context orchestrator dispatches `verification-feedback` under `--phase phase-5-execute --role verification-feedback` with `producer=build-runner` (see [`../plan-marshall/workflow/execution.md`](../plan-marshall/workflow/execution.md) and the canonical contract in [`ref-workflow-architecture/standards/agents.md`](../ref-workflow-architecture/standards/agents.md)).

#### Scope-deviation / `smart_and_ask` escalation yield (`escalate_ask`)

**Applies when** the in-context `execute-task` load returned `escalate_ask: true` with `prompt_options[]` — a scope-deviation escalation (Handle Verification Results) and/or a `smart_and_ask` compatibility gate fired, and the leaf left the task not-done. This is a **planning-level operator decision, NOT a fixable code failure** — it is explicitly NOT routed through `verification-feedback` (there is no test/lint/build finding to FIX, SUPPRESS, or ACCEPT). The canonical deviation taxonomy, the three-option shape, and the prohibited "log-and-continue" anti-pattern live in [`ref-workflow-architecture/standards/scope-deviation-escalation.md`](../ref-workflow-architecture/standards/scope-deviation-escalation.md).

Because this per-task body is a **leaf**, it CANNOT fire `AskUserQuestion` and CANNOT dispatch. It collects the `prompt_options[]` from the returned `escalate_ask` — batching across every deviation / `smart_and_ask` gate that fired anywhere in this envelope into ONE `prompt_options[]` list — and **yields an `escalate_ask` envelope to the main-context orchestrator** as a new TASK-boundary yield reason alongside `budget_yield` / `blocked` / `infeasible`. The leaf returns a wrapped terminal payload and stops; the orchestrator fires ONE batched `AskUserQuestion` and applies each option's side effect post-return (see [`../plan-marshall/workflow/execution.md`](../plan-marshall/workflow/execution.md) § "Post-return `escalate_ask` batched deviation dispatch"). The leaf's return payload:

```toon
status: escalate_ask
display_detail: "{task_number} escalate_ask: {N} deviation prompt(s)"
escalate_ask: true
plan_id: {plan_id}
prompt_options[N]{id,question,header,options,recommended}:
  ...
```

The orchestrator resolves the prompt and re-dispatches phase-5-execute with each resolution baked in: **Hold the line** resumes the fix loop with the requirement intact; **Accept with rationale** persists the rationale to `decision.log` and the PR body; **Split into follow-up plan** seeds a successor lesson. The leaf performs none of the operator-facing interaction.

#### Pre-triage scope cross-reference

Before composing the triage dispatch, classify the failing file paths against the plan's live footprint (derived on demand from the worktree — `{base}...HEAD` ∪ porcelain). The cross-reference is deterministic — a small Python helper that subtracts the footprint from the union of error paths and returns a `exclusively_out_of_scope` flag:

```bash
python3 .plan/execute-script.py plan-marshall:phase-5-execute:verify_failure_scope \
  classify --plan-id {plan_id} --error-paths {comma_separated_paths}
```

The script derives the live footprint from the worktree (reading `references.json` only for the base ref), classifies each error path, and returns:

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

**For infeasible blocks**: The leaf returned `status: infeasible` with an `infeasibility_reason` — the declared deliverable cannot be built as scoped. This is a **planning decision, NOT a fixable code failure**: it is explicitly NOT routed through `verification-feedback` (there is no test/lint/build finding to FIX, SUPPRESS, or ACCEPT). The orchestrator's handling:

1. **Mark the task `infeasible` in the ledger** (the leaf has already done this via `manage-tasks update --status infeasible`; the orchestrator confirms the terminal status is recorded). Because `infeasible` is a terminal state the loop-exit guard does NOT count, it never re-enters the task loop.
2. **Raise `AskUserQuestion`** surfacing the `infeasibility_reason` and offering exactly three gate-level options:
   - **(a) Drop the task** — accept that this deliverable will not be built; remove it from the active scope and continue with the remaining queue.
   - **(b) Re-scope via a new task** — create a replacement task with a buildable, value-preserving deliverable that supersedes the infeasible one; the new task enters the queue.
   - **(c) Abort the plan** — the infeasible deliverable is load-bearing for the whole plan; stop and return control for re-planning.
3. **Record the chosen option to `decision.log`** and act on it. Do NOT dispatch `verification-feedback` on this path — the AskUserQuestion gate is the resolution mechanism.

**For `no_changes_detected` blocks**: The implementation task produced no file changes. Triage options:
- **RETRY** → reset task to `pending` for re-execution
- **FAIL** → mark task `failed` with outcome `no_changes_detected`, log, continue

**For `verification_mismatch` blocks**: The agent claimed verification passed but independent re-run failed. Triage options:
- **FIX** → create fix task to address the actual verification failure
- **RETRY** → reset task to `pending` for re-execution
- **FAIL** → mark task `failed` with outcome `verification_mismatch`, log, continue

**For verification task failures** (original behavior):

**11a**: Read `verify_iteration` counter from task metadata (default: 0).

**11b**: If `verify_iteration >= max_iterations` (from phase-5-execute config, default 5) → mark task `blocked`, log, continue to Step 12.

**11c**: Persist each failing finding to the Q-Gate findings store (producer-side; the triage dispatch reads from the store by reference):

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase 5-execute \
  --source qgate --type test-failure --severity {severity} \
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
finding_type: test-failure
plan_id: {plan_id}
```

(`finding_type: lint-issue` for the Step 11b sweep path.) The findings are already in the per-plan store — the orchestrator's `verification-feedback` dispatch queries them by reference; the leaf does not embed the findings in its return.

The orchestrator-side handling — resolving the `verification-feedback` target via `manage-config effort resolve-target --phase phase-5-execute --role verification-feedback`, emitting the `[DISPATCH]` log line, dispatching `verification-feedback` (`producer=build-runner`, `caller_phase: phase-5-execute`) as a top-level `Task:` in the main context, and consuming the triage return to drive the §11e branch — lives in [`../plan-marshall/workflow/execution.md`](../plan-marshall/workflow/execution.md) § "Verification-feedback triage (leaf returned triage_required)". The per-finding triage core (FIX / SUPPRESS / ACCEPT / AskUserQuestion, smart grouping, overflow, and the Scope-Deviation Escalation guard) is owned by [`../plan-marshall/workflow/triage.md`](../plan-marshall/workflow/triage.md); the dispatch is by-reference (the subagent queries the store as its first workflow step).

**11e** (orchestrator-owned): The orchestrator inspects the `verification-feedback` return per [`../plan-marshall/workflow/execution.md`](../plan-marshall/workflow/execution.md):

- If `fix_tasks_created > 0` → increment `verify_iteration` in task metadata, reset the verification task to `pending`, continue the execution loop (fix tasks will execute before the re-queued verification task via `depends_on`).
- If `fix_tasks_created == 0` AND `overflow_deferred == 0` → mark the verification task complete (all findings suppressed / accepted / `taken_into_account`).
- If `overflow_deferred > 0` → leave the verification task `pending`; the orchestrator re-fires the triage dispatch on the next phase-5-execute entry (the iteration cap is unchanged).

### Step 11b: Final Quality Sweep (After All Tasks)

After every task in the phase has completed (and Step 11 has resolved any per-task verification failures), but **before** Step 12 transitions the phase, run **one canonical `quality-gate` invocation** as a final sweep — but ONLY when BOTH (a) `phase_5.verification_steps` (cached from Step 2) is non-empty AND (b) the live footprint requires a build. The whole-tree quality sweep is the ONE footprint-blind phase-5 build surface (Steps 10b and 11c already derive the live footprint on demand and skip when no buildable module is present — see the **Footprint gating** note under the Built-in Step Dispatch Table); condition (b) closes that gap by consulting the **existing** `manage-config build-decision` verb (a thin wrapper over `extension_base.should_execute_build`, the same `build.map ∩ footprint` authority phase-6 uses — NOT a new verb and NOT a blanket phase-5 short-circuit).

**Skip rule (empty list)**: If `phase_5.verification_steps` is empty (e.g., docs-only plans where the manifest composer dropped all verification steps), skip this step entirely — no final sweep, no log, proceed directly to Step 12.

**Footprint-gate consult (fire condition (b))**: When `phase_5.verification_steps` is non-empty, consult the build-necessity verdict for `quality-gate` BEFORE resolving or running the sweep:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config build-decision \
  --command quality-gate --plan-id {plan_id}
```

Parse `decision` and `reason` from the returned TOON. **When `decision == not_necessary`** (the live footprint is empty or touches no registered `build.map` glob — the docs-only nifi scenario), SKIP the sweep: do NOT resolve, do NOT run any build. Emit a decision-log line naming the footprint `reason`, record the step as `skipped`, and proceed directly to Step 11c:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-5-execute) Final quality sweep skipped — build-decision quality-gate returned not_necessary: {reason}"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest record-step \
  --plan-id {plan_id} --step-id verify:quality-gate --phase 5-execute --outcome skipped \
  --total-tokens 0 --tool-uses 0 --duration-ms 0
```

**When `decision != not_necessary`** (the live footprint touches a buildable glob), the sweep fires — proceed to run exactly one quality sweep, regardless of whether `quality-gate` already appears in the list:

1. Resolve the canonical `quality-gate` build command via the architecture API:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
     resolve --command quality-gate --audit-plan-id {plan_id}
   ```

2. **Branch on the tier the resolve in step 1 just returned.** That live `execution_tier` is the routing authority (see **Per-step `execution_tier`** above); the manifest's `verify:quality-gate` stamp is the advisory expectation, not the decision. When the live `tier == orchestrator`, the sweep is NOT in the leaf's runnable slice — do NOT run it; return the orchestrator-tier yield signal (`status: blocked`, `voluntary_checkpoint`) naming the sweep so the orchestrator runs it via `await-long-running`. Only when the live `tier == per_task` does the leaf execute the returned `executable` inline. On non-zero exit, persist the failures to the Q-Gate findings store (`manage-findings qgate add --type lint-issue …`) and **return the `triage_required` signal to the orchestrator** with `producer=build-runner` and `finding_type=lint-issue` — same leaf-returns-signal shape as Step 11d above, only the finding type changes. The leaf does NOT dispatch `verification-feedback` itself; the orchestrator owns the dispatch (see [`../plan-marshall/workflow/execution.md`](../plan-marshall/workflow/execution.md) § "Verification-feedback triage (leaf returned triage_required)") and drives the same fix-task / suppress / accept branch (Step 11e). After the orchestrator's triage resolves, the sweep is NOT re-run — Step 11b runs at most once per phase entry.

3. Log the outcome:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level INFO \
     --message "[STATUS] (plan-marshall:phase-5-execute) Final quality sweep: {pass|fail}"
   ```

This step is the single source of "did the phase end clean?" — it appends the canonical `quality-gate` once after all task-level verification has settled, providing a stable end-of-phase quality signal. Only the manifest's `verification_steps` list controls whether it fires; per-doc skip logic has been removed in favor of this manifest-driven gate (the single parameterized `canonical_verify.md` step carries no embedded skip logic).

### Step 11c: Execute-Exit Verify Gate (One `verify` per Affected Bundle)

Per-task verification runs each task's pre-stamped `verification.commands` — the derived ladder the deriver wrote at compose time (per-class `compile` / `test-compile` / `module-tests`, scoped to the deliverable's changed module). That ladder is the per-deliverable gate. The **execute-exit verify gate** is the single end-of-phase whole-bundle `verify` that fires exactly **once per affected bundle** at the FINAL state of execute, after every deliverable has settled — replacing both the per-task full suites and the retired holistic verification tasks. Running it once at the queue tail, rather than once per task, is the asymmetric-cost collapse: a whole-bundle `verify` re-runs the same suite no matter how many deliverables touched the bundle, so one run at the final state covers them all.

This gate runs after Step 11b's quality sweep and before Step 12.

1. **Resolve the affected bundle set** from the live plan footprint. Derive the footprint (`{base}...HEAD` ∪ porcelain) and map each path to its owning module:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
     which-module --path {changed_path}
   ```

   Collect the distinct module values into the affected-bundle set. The build-class classification and the derived-command mapping are owned centrally by the deriver — see [`../manage-architecture/SKILL.md`](../manage-architecture/SKILL.md) (`derive-verification` subcommand) and [`../manage-architecture/standards/resolve-command.md`](../manage-architecture/standards/resolve-command.md) for the build_map consumer API. Do NOT inline-copy the path heuristics or the build_class → command table here; the central standards are the single source of truth.

2. **Run exactly one `verify` per affected bundle** — for each distinct `{bundle}` in the affected set, resolve and execute the whole-bundle `verify`:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
     resolve --command verify --module {bundle} --audit-plan-id {plan_id}
   ```

   Branch on the `execution_tier` this resolve just returned — the live tier is the routing authority (the manifest's `verify:module-tests` stamp, which backs the `verify` canonical, is the advisory expectation only). For `tier=per_task` run the build inline with `timeout: bash_timeout_seconds * 1000`; for `tier=orchestrator` the step is NOT in the leaf's runnable slice — return control to the orchestrator to run the long build via `await-long-running` (do NOT run it inline, do NOT background it). After each build call the leaf runs, inspect the result TOON — read `status` and the `errors[]` rows, not the harness exit code.

3. **On non-zero exit** — route the failure through the **same leaf-returns-signal path** as Step 11b: persist each failing finding to the Q-Gate store (`manage-findings qgate add --type lint-issue …`) and return the `triage_required` signal to the orchestrator with `producer=build-runner` and `finding_type=lint-issue`. The leaf does NOT dispatch `verification-feedback` itself. The gate runs at most once per phase entry.

4. Log the outcome per affected bundle:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level INFO \
     --message "[STATUS] (plan-marshall:phase-5-execute) Execute-exit verify for {bundle}: {pass|fail}"
   ```

**Skip rule**: when the affected-bundle set is empty (no buildable footprint — e.g., a documentation-only plan whose changed paths resolve to no module), skip the gate entirely. The deriver already stamped zero Python commands on each such deliverable's per-task ladder, so there is no whole-bundle `verify` to run.

### Step 12: Next Task or Phase

- If more tasks in phase → Continue to next task
- If phase complete → run **Step 12a (Pending-tasks transition guard)** below, then log phase outcome and auto-transition to next phase
- If all phases complete → Mark plan complete

#### Step 12a: Pending-tasks transition guard

Before invoking `manage-status transition --completed 5-execute` (see **Phase Transition** section below), refuse to transition when any pending tasks remain AND when the on-disk worktree has not been observed by a fresh `verify` run. Pending-queue emptiness is **necessary but not sufficient**: a task that was marked `done` against a prior code state still leaves the queue empty, yet the codebase the orchestrator is about to ship has never been verified end-to-end. The canonical failure mode for this gap: `loop-exit-guard` returns `pending_count: 0` while the most recent `verify` predated the last source-file mutation, and CI fails on the pushed commit. Step 12a therefore enforces two co-equal gates: (a) `manage-tasks next` only surfaces the head of the queue, so a `null` next does NOT prove the queue is empty when downstream tasks are still in `pending` — fix tasks created by Step 11 triage commonly land here, and a premature transition silently abandons them; (b) the worktree state itself must be **fresh** with respect to the change-ledger — a successful `kind=build` entry must exist whose `worktree_sha` matches the current working-tree currency hash.

**Script-level enforcement**: the authoritative pending-count check is `python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks loop-exit-guard --plan-id {plan_id}` — see `manage-tasks/SKILL.md` § "Loop-Exit Guard". `status: continue` (with `pending_count > 0` and `pending_ids`) forces the orchestrator to re-dispatch the execution-context; `status: success` (with `pending_count: 0`) is the precondition for recording the `clean_exit_queue_empty` termination cause via the `manage-metrics record-dispatch-boundary` verb. The list-based check below remains documented for backwards compatibility with existing callers — both forms read the same on-disk state, but `loop-exit-guard` is the canonical surface and the verb the orchestrator MUST consult.

**Worktree-state freshness enforcement**: the authoritative freshness check is `python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks pre-commit-verify-freshness --plan-id {plan_id}` — see `manage-tasks/SKILL.md` § "Pre-Commit Verify Freshness". The script recomputes the current working-tree currency hash (`worktree_sha`) and scans the unified change-ledger for a `kind=build` entry with `exit_code == 0` whose `worktree_sha` matches. The query is tier-agnostic and build-tool-agnostic — it filters on `kind`, `exit_code`, and `worktree_sha` only, never `notation` or `plan_id`, so a Maven/Gradle/npm build or an orchestrator-driven global-tier build satisfies the gate exactly as a plan-scoped pyproject build does. See `marketplace/bundles/plan-marshall/skills/manage-change-ledger/SKILL.md` for the ledger and `worktree_sha` primitive. The script returns one of three statuses. `status: fresh` permits transition; `status: stale` or `status: undecidable` blocks transition with the same `[BLOCKED]` log line shape used for the pending-tasks branch. The gate fails closed by design — there is no LLM judgement and no "probably fine" fallback. Pending-queue emptiness and worktree freshness are **co-equal** gates: both MUST succeed before the phase may transition.

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
     --message "[BLOCKED] (plan-marshall:phase-5-execute) Worktree state not verified: {reason} (worktree_sha={worktree_sha}, ledger_path={ledger_path}) — refusing to transition 5-execute → 6-finalize. Re-dispatch a verify run, or invoke with --force to override."
   ```

   Substitute the placeholders with the corresponding fields from the script's TOON output. Each branch omits a different field set: `stale` omits `reason`; `undecidable` carries `reason` set to one of `no_registry` (the ledger file is absent or empty) or `head_unresolvable` (the working-tree sha cannot be computed), and the `head_unresolvable` sub-case omits `worktree_sha` and `ledger_path`. Substitute `-` for any field absent in the returned TOON. Do NOT call `manage-status transition` and do NOT auto-continue to finalize. The orchestrator's recovery path is to dispatch a fresh `verify` run, after which Step 12a is re-entered.

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

   Append `reason={reason}` to the message body only when `status` is `undecidable`; the `stale` branch does not emit a `reason` field, so the appended fragment is omitted for that branch. This mirrors the `--force` escape format in `phase-6-finalize/standards/push.md` § Freshness precondition.

   The `--force` escape is a deliberate safety valve for triage-driven aborts (the user has already decided the pending tasks are out-of-scope, or that the stale-freshness signal is being addressed elsewhere) — never invoke it programmatically from inside the loop.

### Step 4.5: Capture Session Token (Once per phase)

At phase start, capture the runtime session token so downstream metrics operations can reference it:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime \
  session capture --plan-id {plan_id}
```

On Claude Code the runtime reads the stored `session_id` from the `SessionStart` hook. On OpenCode it returns `no-op` (no platform session id available) — the phase proceeds normally and uses manual `--total-tokens` for metrics.

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
- Return the bare `task_complete` payload from the in-context `execute-task` load verbatim while pending tasks in the SAME `envelope_id` group remain. This is the **`task_complete_returned_verbatim`** defect and the direct violation of the one-context-per-phase invariant (§ "Dispatched workflows vs inline steps"): the phase completes in exactly ONE dispatch per envelope group — `envelope_count` dispatches, NEVER one per task — so a bare `task_complete` echo collapses the envelope loop into a wasteful per-task re-dispatch. `execute-task`'s `next_action: task_complete` is a PER-TASK signal THIS envelope loop consumes to advance to the next same-`envelope_id` task; it is never the envelope's terminal return. The envelope MUST keep looping over its own group until the group is exhausted, then yield via the wrapped `budget_yield` payload (§ "Deterministic exit clause") — never a bare `task_complete`.

Agent-initiated re-dispatch is a control-flow drift that can cause `[OUTCOME]` log coverage gaps — the script-level `[OUTCOME]` guard in `manage-tasks finalize-step` closes the audit-trail gap, but the underlying drift also needs to be ruled out at the skill level. The orchestrator (`plan-marshall` workflows) is the single component allowed to start, re-dispatch, or terminate phase-5-execute; the dispatched agent does not get to vote.

**The one legitimate yield — `budget_yield`:** the envelope-group read (see § "Deterministic exit clause (envelope-group read)") yields when the next pending task's `envelope_id` differs from the assigned group. This is NOT a forbidden checkpoint — it is the plan-time-packed dispatch boundary the bin-packer pre-computed. It is distinguished from a forbidden checkpoint by two MANDATORY observable signals: (1) a `budget_yield` decision-log entry naming the assigned and next `envelope_id`, and (2) a wrapped terminal TOON carrying `budget_yield: true` with `tasks_remaining > 0` — never the bare `task_complete` echo. A yield that omits either signal IS a forbidden checkpoint. The orchestrator classifies the wrapped, logged yield as `termination_cause: budget_yield` (a legitimate yield) and re-dispatches the next envelope group; a bare `task_complete` return with pending tasks is still classified as the `task_complete_returned_verbatim` drift.

### Deterministic exit clause (envelope-group read)

The loop's continue-vs-yield decision is **pre-computed at plan time** by the bin-packer (phase-4-plan's `manage-tasks pack-envelopes`, deliverable 3) — the executor makes NO runtime cost decision at all. **Harness reality (the WHY):** a running subagent CANNOT measure its own context-window usage mid-turn — no tool, env var, signal, or API returns "tokens used/remaining" to the model during execution; the `<usage>` block reaches the *caller* only AFTER the subagent returns. A runtime `remaining_budget` therefore has no source and cannot be the comparand. The packing decision is consequently moved entirely to plan time, where every task's `predicted_cost_tokens` is a known constant: the bin-packer groups tasks (in `depends_on` order, accumulating cost under `per_envelope_budget_tokens`) and stamps each with an `envelope_id`. At runtime the executor only READS that grouping.

The continue-vs-yield clause is therefore a trivial countable check, evaluated in canonical order:

> **Small-plan short-circuit**: If `tasks_total <= 2` (read from `phase_5.tasks_total` in the execution manifest cached at Step 2), the queue is trivially one envelope — continue to the next task until the queue is empty or a terminal outcome fires. (Informational only under plan-time packing; a small plan already packs to a single envelope.)
>
> **Final-task long-running-verify short-circuit**: If BOTH (a) the current task is the final task in the queue (`task_index + 1 == tasks_total`) AND (b) its resolved verification command is in the known long-running build set (`verify`, `coverage`, `quality-gate` fully scoped), continue and finish in-dispatch. Re-dispatching at the queue tail to run a long-running build pays the full dispatch overhead for zero scheduling benefit (no subsequent task ever runs). Log the suppression decision via `manage-logging decision`. (Informational only under plan-time packing; the final task is already inside the last envelope.)
>
> **Envelope-group read** (applies when neither short-circuit fires): After the just-completed task, peek the next pending task via `manage-tasks next` and read its `envelope_id` (surfaced on the `next` result dict). **If the next pending task's `envelope_id` equals the assigned group: continue to it. Else (the next task belongs to a different envelope, or the queue is empty): yield.** This is a pure equality check — NO cost summing, NO threshold evaluation, NO `remaining_budget`, NO self-measurement.

The packing already encodes the budget decision, so the two short-circuits above are now informational rather than the budget mechanism. The clause runs once after each task completes — between `manage-tasks finalize-step` of the closing step (which fires the canonical `[OUTCOME]`) and the next `manage-tasks next` call. There is no intermediate decision point.

**Group-exhausted yield path** — when the envelope-group read decides to yield because the next pending task's `envelope_id` differs from the assigned group (and the queue is NOT empty), the executor MUST distinguish this legitimate plan-time-packed yield from a forbidden checkpoint by doing BOTH:

1. **Log a `budget_yield` decision** naming the assigned `envelope_id`, the just-completed task, and the next task's differing `envelope_id`:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     decision --plan-id {plan_id} --level INFO \
     --message "(plan-marshall:phase-5-execute) budget_yield: envelope {my_envelope_id} exhausted after {task_id}; next pending task TASK-{next_number} belongs to envelope {next_envelope_id} — yielding to orchestrator for the next envelope-group dispatch"
   ```

2. **Return a wrapped, discriminated terminal TOON** carrying an explicit yield discriminator — `status: success`, a `display_detail` naming the envelope-group yield, and `tasks_remaining > 0` — NEVER the bare `task_complete` echo from `execute-task`:

   ```toon
   status: success
   display_detail: "envelope {my_envelope_id} exhausted — {tasks_remaining} task(s) remain in later envelopes"
   plan_id: {plan_id}
   tasks_completed: {N}
   tasks_remaining: {M}
   budget_yield: true
   envelope_id: {my_envelope_id}
   next_envelope_id: {next_envelope_id}
   ```

   The orchestrator classifies this return as `termination_cause: budget_yield` (see [`plan-marshall/workflow/execution.md`](../plan-marshall/workflow/execution.md) § "Termination-cause classification") — distinct from the `task_complete_returned_verbatim` failure mode — and re-dispatches the next envelope group.

**Cross-reference to the three terminal outcomes** — the envelope-group read is the **continue-vs-yield** decision, not a fourth terminal outcome. When it says "yield", the agent still exits via the group-exhausted yield path above (a wrapped terminal TOON with `budget_yield: true`), which is a legitimate use of the queue-not-empty success return — NOT a partial-completion checkpoint (that path is explicitly forbidden by the section above). The in-flight task's state is already persisted by `manage-tasks finalize-step` so resumption by the next envelope dispatch is lossless.

**Audit diagnostic ledger** — when investigating throughput or calibration questions, compare each envelope's per-dispatch ACTUAL tokens (the orchestrator's post-return `<usage>`) against the SUM of `predicted_cost_tokens` for the tasks in that envelope (prediction-vs-actual calibration of the size→token table). A systematic over- or under-prediction across envelopes is the signal that the `cost_size_token_table` magnitudes (`per_envelope_budget_tokens` consumers) need recalibration; the orchestrator owns that feedback loop because only it sees the post-return token counts.

---

## Phase Transition

When transitioning from execute phase to finalize, first record phase metrics through the platform runtime:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime \
  metrics capture --plan-id {plan_id} --phase 5-execute
```

On Claude Code the runtime reads the stored `session_id` and captures token usage from the transcript. On OpenCode it returns `no-op` — the phase still transitions and accepts manual `--total-tokens` when available.

Then update the phase status:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status transition \
  --plan-id {plan_id} \
  --completed 5-execute
```

This automatically updates status.json and moves to the next phase.

**After transition**, check `finalize_without_asking` config:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize get --field finalize_without_asking
```

- **IF `finalize_without_asking == true`**: Log and auto-continue to finalize phase
- **ELSE (default)**: Stop and display `"Run '/plan-marshall action=finalize plan={plan_id}' when ready."`

---

## Output

phase-5-execute returns on five terminal paths (queue empty → transition; fatal error; triage `blocked`; deliverable `infeasible`; scope-deviation `escalate_ask`). The minimum contract every workflow doc that implements `ext-point-execution-context-workflow` MUST return is:

```toon
status: success | error | blocked | infeasible | escalate_ask
display_detail: "<{tasks_completed} tasks complete, {tasks_remaining} remaining>"
plan_id: {plan_id}
tasks_completed: {N}
tasks_remaining: {N}
infeasibility_reason: {required when status=infeasible — why the declared deliverable cannot be built as scoped}
prompt_options[N]{id,question,header,options,recommended}: {required when status=escalate_ask — the batched scope-deviation / smart_and_ask questions for the orchestrator to fire}
```

`display_detail` shape on success: `"{tasks_completed} tasks complete, {tasks_remaining} remaining"` (e.g. `"7 tasks complete, 0 remaining"`). On `blocked`: `"{task_number} blocked: {short reason}"`. On `infeasible`: `"{task_number} infeasible: {short reason}"`. On `escalate_ask`: `"{task_number} escalate_ask: {N} deviation prompt(s)"`. On error: short error label from § Error Handling. All values are ≤80 chars, ASCII, no trailing period. The `infeasible` return carries `infeasibility_reason`; the orchestrator routes it to the Step 11 "For infeasible blocks" planning gate (drop / re-scope / abort via AskUserQuestion), NOT the `verification-feedback` code-fix loop. The `escalate_ask` return carries `prompt_options[]`; the orchestrator fires ONE batched `AskUserQuestion` (§ "Post-return `escalate_ask` batched deviation dispatch" in `execution.md`) and re-dispatches with the resolutions baked in, NOT the `verification-feedback` code-fix loop.

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

**Loop-back re-entry and boundary monotonicity.** A finalize loop-back
re-enters `5-execute` and re-records its work under `phase=5-execute`, so a
later phase's `start_time` can end up preceding this phase's already-closed
`end_time`. `manage-metrics generate` carries a render-time monotonicity
detector that surfaces the resulting non-monotonic boundary (a top-level
`boundary_monotonicity` warning plus a per-phase annotation) and guards the
idle residual for the affected phase, rather than silently emitting a corrupt
residual derived from the overlapping window. The detector is read-only — it
never rewrites the recorded `start_time` / `end_time` fields and never touches
the `#812` `end_time`-keyed partial verdict. See
`manage-metrics/standards/data-format.md` § "Boundary Monotonicity (Loop-Back
Re-entry)".

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

