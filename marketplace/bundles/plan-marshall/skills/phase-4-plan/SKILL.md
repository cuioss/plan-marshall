---
name: phase-4-plan
description: Domain-agnostic task planning from deliverables with skill resolution and optimization
user-invocable: false
mode: workflow
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Phase Plan Skill

**Role**: Domain-agnostic workflow skill for transforming solution outline deliverables into optimized, executable tasks. Dispatched as the workflow body of `plan-marshall:execution-context-{level}` (`workflow: plan-marshall:phase-4-plan/SKILL.md`).

**Key Pattern**: Reads deliverables with metadata and profiles list from `solution_outline.md`, creates one task per deliverable per profile (1:N mapping), resolves skills from architecture based on `module` + `profile`, creates tasks with explicit skill lists. **No aggregation** - each deliverable maps to exactly one task per profile.

## Foundational Practices

```
Skill: plan-marshall:dev-agent-behavior-rules
```

## Enforcement

> **Shared lifecycle patterns**: See [phase-lifecycle.md](../ref-workflow-architecture/standards/phase-lifecycle.md) for entry protocol, completion protocol, and error handling convention.

**Execution mode**: Follow workflow steps sequentially. Each step that invokes a script has an explicit bash code block.

**Prohibited actions:**
- Never access `.plan/` files directly — all access must go through `python3 .plan/execute-script.py` manage-* scripts
- Never skip the phase transition — use `manage-status transition`
- Never improvise script subcommands — use only those documented below

**Anti-pattern: shell-substitution shortcuts for batch task payloads**

When persisting the multi-task batch (Step 6 → 6a/6b), the following shell shortcuts are explicitly forbidden because they bypass the `--tasks-file` path-allocate flow and trip the host platform's bash safety rules (one command per call, no shell constructs, no heredocs with `#` lines):

- `$(cat …)` command substitution (e.g. `manage-tasks batch-add --tasks-json "$(cat /tmp/tasks.json)"`) — violates the no-`$()` rule and silently quotes the JSON through the shell argument boundary.
- Heredocs with `#` lines (e.g. `cat <<EOF | jq …` payloads that include `#`-prefixed comments) — heredocs containing `#` lines trigger the bash safety prompt and break execution.
- `python -c "open('…').write('…')"` one-liners that inline-write the batch JSON from a shell argument — this re-introduces the same shell-quoting fragility the path-allocate flow exists to eliminate.

**Rule-compliant alternative**: Use the `--tasks-file` path-allocate flow documented in Step 6a/6b. Stage the batch JSON via `manage-files write --file work/tasks-batch.json` (so the payload is written through a structured tool, not a shell argument), then call `manage-tasks batch-add --tasks-file .plan/local/plans/{plan_id}/work/tasks-batch.json`. This is the only sanctioned path for multi-task creation in this phase.

**Constraints:**
- Strictly comply with all rules from dev-agent-behavior-rules, especially tool usage and workflow step discipline

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — the silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

Step-level exceptions — calls whose non-zero exit is itself the signal (e.g., `manage-files exists` returning `exists: false`) — are documented inline in the step that issues them.
- Batch JSON staging files MUST live under `.plan/local/plans/{plan_id}/work/`. Never use `Write` to `/tmp/`, `/var/`, or any path outside the plan's `work/` directory. (Cross-reference: see anti-pattern callout at SKILL.md:30 for the shell-substitution shortcut prohibition; both rules apply together.)

## Dispatched workflows vs inline steps

This phase dispatches under one role key: **`phase-4-plan`** (resolves through `phase-4-plan.default`). The bundled task-creation activity (Steps 5+6 — per-deliverable task creation, anchoring/breaking-refactor split, deriver-stamped verification) iterates *inside* one `phase-4-plan` envelope; the per-deliverable loop never spawns per-iteration subagents. Mechanical sub-procedures stay inline as scripts: Step 3 deliverable load, Step 4 dependency graph, Step 7 topological sort, Step 7b execution manifest composition, and Step 8 Q-Gate mechanical checks (via `manage-tasks:qgate-mechanical-checks` — coverage, skill-resolution, acyclic, files-exist, keyword-drift, structural-token-drift). Step 8b LLM Q-Gate activation is *signaled* by setting `qgate_validation_required: true` in the phase return TOON (unconditionally after every successful phase-4-plan invocation — both `module-mapping-validator` and `scope-criterion-validator` apply to every plan regardless of `plan_source`); the orchestrator (`plan-marshall:plan-marshall/workflow/planning-outline.md`) reads that flag and issues q-gate-validation as a sibling top-level `Task: plan-marshall:{target}` dispatch — the phase body cannot spawn it directly because the `Task` tool is unavailable inside an `execution-context-{level}` subagent. The mechanical script's `ambiguous=true` signal is informational only (it means `solution_outline.md` was missing or unparseable, in which case the orchestrator-dispatched LLM run is the *only* authoritative pass). For the rationale see [dispatch-granularity.md](../extension-api/standards/dispatch-granularity.md) § 2–4.

### Loop-invariant inputs (cached at phase entry)

The task-creation loop (Steps 5 + 6) iterates per deliverable — but the *inputs* feeding the per-deliverable task creation are loop-invariant: they are read once during phase entry / Step 3 deliverable load and Step 4 dependency-graph construction, and are not mutated by the loop body. The dispatched agent MUST read each of the following inputs ONCE at phase entry and reference the cached values throughout every per-deliverable iteration:

- The deliverable set (read via Step 3 deliverable-load from `solution_outline.md`).
- The architecture topology (read via `manage-architecture overview` at phase entry).
- The per-deliverable skill resolutions (resolved via `architecture module --module {D.module}` for each distinct module before the per-deliverable iteration begins — one query per unique module, cached; not re-queried per deliverable or per profile).
- The execution manifest composition inputs (the manifest is composed once at Step 7b — not per-deliverable).
- The relevant ADR summaries for the plan's declared module(s), read once via the `manage-adr scan` progressive-disclosure surface (NOT per-deliverable or per-profile). Run `manage-adr scan --affects {module}` (and/or `--tag {topic}`) for each declared module and load the returned `summary` fields into context so task derivation aligns with established architectural decisions and surfaces superseded/deprecated ADRs as constraints. This mirrors the phase-3-outline hook verbatim in shape — see `marketplace/bundles/plan-marshall/skills/manage-adr/SKILL.md` for the scan subcommand contract (do not restate it) and [`../phase-3-outline/standards/outline-workflow-detail.md` § ADR consultation](../phase-3-outline/standards/outline-workflow-detail.md#adr-consultation-loop-invariant-input) for the consultation procedure.

**Prohibited actions:**
- Never re-read loop-invariant inputs inside the task-creation loop body — re-reading inside the loop is envelope-cost waste; all invariant inputs must be resolved before the loop begins.

See [`extension-api/standards/dispatch-granularity.md`](../extension-api/standards/dispatch-granularity.md) § 5.1 (Heuristic 2 — bundle when steps share context) for the granularity rationale.

## cwd for `.plan/execute-script.py` calls

> `manage-*` scripts resolve `.plan/` via the uniform cwd walk-up (ADR-002) — the nearest ancestor of cwd containing `.plan/local`. Phase-4-plan runs on the main checkout, so they resolve to main's `.plan/`; do **NOT** pin cwd, do **NOT** pass routing flags, and never use `env -C`. Build / CI / Sonar scripts accept `--plan-id {plan_id}` (preferred — auto-resolves the worktree via `manage-status get-worktree-path`) or `--project-dir {worktree_path}` (explicit override / escape hatch); the two flags are mutually exclusive. See `plan-marshall:tools-script-executor/standards/cwd-policy.md`.

### Contract Compliance

**MANDATORY**: All tasks MUST follow the structure defined in the central contracts:

| Contract | Location | Purpose |
|----------|----------|---------|
| Task Contract | `plan-marshall:manage-tasks/standards/task-contract.md` | Required task structure and optimization workflow |

**CRITICAL - Steps Field**:
- The `steps` field MUST contain file paths from the deliverable's `Affected files` section
- Steps must NOT be descriptive text (e.g., "Update AuthController.java" is INVALID)
- Validation rejects tasks with non-file-path steps
- Exception: `verification` profile tasks use verification commands as steps (file-path validation is skipped)

### Test Helper File Naming

When a task step target lives under a skill test directory (any path matching `test/**/`) and represents a test helper (shared fixtures, sys.path shims, or other non-test Python module), the filename MUST NOT be `conftest.py`. Rename the target to `_fixtures.py` (or another descriptive `_*.py` name that is clearly not a pytest collection file) during task creation — before composing the JSON array passed to `manage-tasks batch-add`. Only the project's two top-level `conftest.py` files (`test/conftest.py` and `test/adapters/conftest.py`) are permitted; any additional `conftest.py` under `test/{bundle}/{skill}/` changes pytest's global collection semantics for that bundle and causes hidden coupling or spurious collection failures.

If a deliverable's `Affected files` list names a `conftest.py` other than those two top-level files, phase-4-plan MUST rewrite the target to `_fixtures.py` (preserving the parent directory) before persisting the step. Cross-reference: phase-3-outline owns the outline-time rule and rationale in [outline-workflow-detail.md §10d "Test Helper File Naming"](../phase-3-outline/standards/outline-workflow-detail.md#10d-test-helper-file-naming); this subsection enforces the same constraint at task-creation time so that any late-surviving `conftest.py` target is corrected before tasks reach phase-5-execute.

### Basename Collision Pre-check

When a planned task creates a NEW `test_*.py` file (an affected file with a `test_` basename prefix and a `.py` extension that does not yet exist on disk), the planning agent MUST verify that the chosen basename does not collide with any other `test_*.py` already in the repository — regardless of which directory the new file lives in. This rule applies most aggressively to **shared collection roots** (any `test/` subtree without `__init__.py` package markers); the canonical example is `test/plan-marshall/`, where every subdirectory contributes to the same pytest collection namespace.

**Pre-check command** (run BEFORE persisting the task step that creates the new file):

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  find --pattern "test_{candidate_basename}.py"
```

Substitute `{candidate_basename}` with the basename minus the `test_` prefix and `.py` suffix (e.g., for `test_findings_store.py`, `{candidate_basename}` is `findings_store`).

**Glob fallback** — when the architecture verb returns elision (`status: elided`) or no result, fall back to the structured-Glob query:

```
Glob: test/**/test_{candidate_basename}.py
```

The Glob fallback covers the case where the new test file lives in a recipe / extension directory that the architecture inventory has not yet enriched. Both forms enumerate the existing collisions; an empty result means the basename is free.

**Collision response** — when at least one collision is detected, the planning agent MUST disambiguate by prefixing the basename with a **module-disambiguating prefix** derived from the module under test, NOT by appending a numeric suffix:

| Module under test | Existing collision | Disambiguated basename |
|-------------------|--------------------|------------------------|
| `manage-findings` | `test/.../test_findings_store.py` | `test_findings_findings_store.py` (or `test_findings_store_manage.py` — match the existing naming style of the target directory) |
| `build-pyproject` (findings module) | `test/.../test_findings_store.py` | `test_build_findings_store.py` |
| `recipe-lesson-cleanup` (parser) | `test/.../test_parser.py` | `test_lesson_cleanup_parser.py` |

The disambiguation prefix MUST be a substring of the module path (kebab-case stem, joined by `_`) so the basename remains greppable from the module name. Numeric suffixes (`test_findings_store_2.py`) and copy-cat ordinals are forbidden — they preserve the collision risk for the next addition and lose the module-under-test signal entirely.

**Decision logging** — every disambiguation MUST be recorded in `decision.log` with the chosen basename, the colliding pre-existing test file, and the rationale:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-4-plan) Basename-collision pre-check: requested test_{candidate_basename}.py collides with {existing_path} — disambiguated to test_{disambiguated_basename}.py (module-disambiguating prefix derived from {module_under_test})"
```

**Failure mode rationale** — pytest's default `--import-mode=prepend` collection mode adds each test file's parent directory to `sys.path` and then imports the module by its **basename** (the `test_` prefix plus the stem). Two `test_X.py` files in different subdirectories of a shared collection root (no `__init__.py` package markers between them) resolve to the same module name `test_X`. pytest imports the first match, silently discards the second, and emits no warning. The regression is that the second file's test cases never execute — `pytest -v` lists only the first file's tests, the CI tab shows green, and the missing coverage is invisible until a human notices the test count is wrong. The pre-check converts this silent failure into a planning-time decision the agent has to make explicitly.

**Counter-indication (when no pre-check is needed)** — the new `test_*.py` lives under a directory that contains an `__init__.py` (or has one in every ancestor up to the pytest rootdir), which makes the file a proper package module rather than a basename-keyed top-level module. In that case the basename collision is harmless because the import path includes the package prefix. The pre-check verb returns the collision, the planner records it in `decision.log` with the `__init__.py` evidence, and the original basename is kept.

**Cross-reference**: [outline-workflow-detail.md §10d](../phase-3-outline/standards/outline-workflow-detail.md#10d-test-helper-file-naming) — the outline-phase counterpart owns the rule rationale; this subsection enforces the basename check at task-creation time.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |

## Phase-Entry Worktree Assertion

The Phase Entry Protocol's `phase_handshake verify --phase 3-outline --strict` call (see [`ref-workflow-architecture/standards/phase-lifecycle.md`](../ref-workflow-architecture/standards/phase-lifecycle.md#phase-handshake-verify-phases-2-6)) asserts the worktree-resolution contract before any phase-4-plan work begins. Phase-4-plan runs on the main checkout — the worktree directory and feature branch are not created until phase-5-execute Step 2.5. An empty `worktree_path` while `metadata.use_worktree==true` is ALWAYS `worktree_unresolved` (there is no deferred-window carve-out): a `use_worktree==true` plan carries a real `worktree_path` only once phase-5 materializes the worktree, so an empty path is a metadata defect, not a legitimate transitional state. The strict path-not-found / path-stale failures also fire when `worktree_path` is set but does not resolve cleanly. Plans with `metadata.use_worktree==false` skip the assertion (main-checkout flow). See [`workflow-integration-git/standards/worktree-handling.md`](../workflow-integration-git/standards/worktree-handling.md) for the canonical lifecycle contract.

## Output

```toon
status: success | error
display_detail: "<{M} tasks across {N} groups>"
plan_id: {echo}
summary:
  deliverables_processed: N
  tasks_created: M
  parallelizable_groups: N
tasks_created[M]: {number, title, deliverable, depends_on}
execution_order: {parallel groups}
message: {error message if status=error}
```

`display_detail` shape: `"{tasks_created} tasks across {parallelizable_groups} groups"` on success; ≤80 chars, ASCII, no trailing period.

**Error codes** (returned in the `error` field when `status: error`):

| `error` | Raised by | Meaning |
|---------|-----------|---------|
| `tasks_already_exist` | Step 2.5 (re-entry guard) | phase-4-plan was re-entered against a plan that already has tasks (`counts.total > 0`). Task creation is not idempotent, so the phase aborts before Step 3 rather than duplicating the queue. The payload carries `existing_task_count`. To re-plan, clear the existing tasks first, then re-enter. |
| `invalid_manifest` | Step 7b (manifest validate) | The composed execution manifest failed validation; the phase aborts before Q-Gate. |

## Related

| Document | Purpose |
|----------|---------|
| [Task Creation Flow](references/task-creation-flow.md) | Visual overview of the 1:N task creation flow and output structure |
| [Breaking-Refactor Task Split](standards/breaking-refactor-task-split.md) | Task-split contract for `tech_debt` / `feature_breaking` deliverables that intentionally invalidate existing test contracts (allocates `implementation` + `module_testing` task pair with `depends_on` linkage); paired with the phase-5-execute planned-failure exception |
| [Dispatch Granularity](../extension-api/standards/dispatch-granularity.md) | The 10K rule, script-over-dispatch, bundle-over-iterate, per-iteration only when models differ or parallel — explains why Steps 5+6 bundle into one `phase-4-plan` dispatch and why Step 8's mechanical Q-Gate checks live in `manage-tasks:qgate-mechanical-checks` rather than a dispatch |

## Workflow

### Step 1: Check for Unresolved Q-Gate Findings

**Purpose**: On re-entry (after Q-Gate flagged issues), address unresolved findings before re-creating tasks.

### Query Unresolved Findings

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate list --plan-id {plan_id} --phase 4-plan --resolution pending
```

### Address Each Finding

If unresolved findings exist (filtered_count > 0):

For each pending finding:
1. Analyze the finding in context of deliverables and tasks
2. Address it (adjust skill resolution, fix dependencies, correct steps, etc.)
3. Resolve:
```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate resolve --plan-id {plan_id} --hash-id {hash_id} --resolution taken_into_account --phase 4-plan \
  --detail "{what was done to address this finding}"
```
4. Log resolution:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-4-plan:qgate) Finding {hash_id} [{source}]: taken_into_account — {resolution_detail}"
```

Then continue with normal Steps 3..11 (phase re-runs with corrections applied).

If no unresolved findings: Continue with normal Steps 3..11 (first entry).

### Step 2: Log Phase Start

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-4-plan) Starting plan phase"
```

### Step 2.5: Re-Entry Guard (Prevent Duplicate Task Creation)

**Purpose**: Task creation (Steps 5–6) is NOT idempotent — `batch-add` assigns fresh sequential `TASK-NNN` numbers in array order at call time and never reconciles against tasks that already exist. A second phase-4-plan invocation against a plan that already has tasks therefore re-creates the entire task set, leaving the plan with duplicate tasks (`TASK-001`…`TASK-NNN` from the first run plus a renumbered second copy of the same deliverables). This guard makes a re-entry that finds existing tasks abort loudly instead of silently doubling the queue.

This step runs after Step 2 (phase start logged) and BEFORE Step 3 (deliverable load), so the abort fires before any deliverable parsing or skill resolution work is done.

**Probe the existing task count**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks list \
  --plan-id {plan_id} --status all
```

Parse `counts.total` from the returned TOON.

**Decision**:

- **`counts.total == 0`** (first entry, expected case) → proceed to Step 3. No tasks exist yet; task creation is safe.
- **`counts.total > 0`** (re-entry with tasks already present) → ABORT the phase fail-loud. Do NOT proceed to Step 3, do NOT create tasks, do NOT transition the phase. Log the abort and return the structured `tasks_already_exist` error TOON to the orchestrator:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR \
  --message "[ERROR] (plan-marshall:phase-4-plan) Re-entry guard: {counts.total} task(s) already exist — refusing to re-create tasks (would duplicate the queue). Returning tasks_already_exist."
```

```toon
status: error
error: tasks_already_exist
existing_task_count: {counts.total}
display_detail: "tasks already exist ({counts.total}) — refusing to duplicate"
message: "phase-4-plan re-entered against a plan that already has {counts.total} task(s). Task creation is not idempotent; re-creating would duplicate the queue. To re-plan, clear the existing tasks first, then re-enter phase-4-plan."
```

**Q-Gate re-entry exemption**: The Step 1 Q-Gate auto-loop path (re-entering phase-4-plan to address unresolved Q-Gate findings) is the one legitimate re-entry that must NOT trip this guard. That path resolves its findings against the EXISTING task set and re-runs Steps 3..11 with corrections applied — it does not create a duplicate task batch from scratch. When Step 1 surfaced unresolved findings (`filtered_count > 0`) and the re-entry is driven by that auto-loop, the orchestrator clears the prior task set before re-dispatch (so `counts.total == 0` at this probe) — the guard sees an empty queue and the re-plan proceeds normally. A non-empty `counts.total` at this point therefore always signals an unintended duplicate-creating re-entry, never the sanctioned Q-Gate correction loop.

### Step 3: Load All Deliverables

Read the solution document to get all deliverables with metadata:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  list-deliverables \
  --plan-id {plan_id}
```

For each deliverable, extract:
- `metadata.change_type`, `metadata.execution_mode`
- `metadata.domain` (single value)
- `metadata.module` (module name from architecture)
- `metadata.depends`
- `profiles` (list: `implementation`, `module_testing`, `verification`)
- `affected_files`
- `verification`

### Step 4: Build Dependency Graph

Parse `depends` field for each deliverable:
- Identify independent deliverables (`depends: none`)
- Identify dependency chains
- Detect cycles (INVALID - reject with error)

**`depends_on` is the dependency surface, not `execution_order` (NORMATIVE)**: A functional compile-order / build-order dependency between deliverables — deliverable B cannot compile, build, or pass verification until deliverable A's edit lands — MUST be encoded as a `depends_on` edge on the derived task. It MUST NOT be expressed only through `execution_order` parallel-group placement. `execution_order` grouping (Step 7) is a parallelism schedule DERIVED FROM the `depends_on` graph; it is not a substitute for declaring the dependency. Relying on group placement alone leaves the dependency invisible to the executor's ordering and to the breaking-refactor planned-failure exception, both of which read `depends_on` directly. This rule is cross-referenced from Step 7 (Determine Execution Order) so the two surfaces stay consistent.

### Step 5: Create Tasks from Profiles (1:N Mapping)

For each deliverable, create one task per profile in its `profiles` list:

**Verification-Only Guard**: Before iterating profiles, check whether the deliverable is verification-only. The authoritative signal is the deliverable's per-file **write-intent set**, sourced from `affected_files[N].intent` (the same closed intent enum — `read` / `write-new` / `write-replace` / `delete` — surfaced by `manage-solution-outline list-deliverables`), NOT the explicit `implementation` profile. A deliverable is **write-bearing** when ANY entry in its `affected_files` carries an `intent` in `{write-new, write-replace, delete}`. The guard fires (override `D.profiles` to `[verification]`) ONLY when the deliverable is read-only: `affected_files` is empty OR every entry's `intent == read`. Any write-intent affected file forces an implementation-capable task (`implementation` or `module_testing`) and is never collapsed to verification-only — even when `D.change_type == verification`. Log a warning when the override fires and the original profiles differed:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level WARNING --message "(plan-marshall:phase-4-plan) Deliverable {N} is verification-only but had profiles [{original_profiles}] — overriding to [verification]"
```

```
# Pre-fetch: resolve architecture data for every distinct module referenced across deliverables.
# Do this ONCE before the per-deliverable loop — use cached values inside the loop body.
For each unique D.module in deliverables:
  Pre-fetch: architecture module --module {D.module}  → cache as arch_cache[D.module]

For each deliverable D:
  IF D.affected_files is empty OR (D.change_type == verification AND every affected_files entry has intent == read):
    IF D.profiles != [verification]:
      Log warning (see above)
    D.profiles = [verification]
  # else: any write-intent affected file blocks the override — declared profiles flow through unchanged
  1. Use cached architecture: arch_cache[D.module]  (do NOT re-query)
  For each profile P in D.profiles:
    IF P = verification:
      2v. Skip skill resolution (no architecture query needed)
      3v. Create task with profile=verification, empty skills, verification commands as steps
      4v. Add depends on all other tasks from this deliverable
    ELSE:
      2. Extract skills: module.skills_by_profile.{P}
         IF skills_by_profile is empty/missing OR skills_by_profile.{P} is empty/missing:
           - Log WARNING: "(plan-marshall:phase-4-plan) Module {D.module} has empty skills_by_profile.{P} — task will have no domain skills. Run architecture enrichment to populate."
           - Set task.skills = [] (continue with empty skills rather than erroring)
           - Record a Q-Gate triage finding via `python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate add --plan-id {plan_id} --phase 4-plan --source qgate --type triage --title "Missing skills_by_profile: {D.module}.{P}" --detail "Module {D.module} has empty skills_by_profile.{P} — task created with skills: []. Run architecture enrichment to populate the missing profile."` so phase-5-execute and phase-6-finalize can surface the gap.
         ELSE:
           - Load all `defaults` directly into task.skills
           - For each `optional`, evaluate its `description` against deliverable context
           - Include optionals whose descriptions match the task requirements
      3. Create task with profile P and resolved skills
      4. If P = module_testing, add depends on implementation task
```

**Query architecture**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  module --module {deliverable.module} \
  --audit-plan-id {plan_id}
```

**Skills Resolution** (new defaults/optionals structure):

The architecture returns skills in structured format:
```toon
skills_by_profile:
  implementation:
    defaults[1]{skill,description}:
      - pm-plugin-development:plugin-architecture,"Architecture principles..."
    optionals[2]{skill,description}:
      - pm-plugin-development:plugin-script-architecture,"Script development standards..."
      - plan-marshall:ref-toon-format,"TOON format knowledge for output specifications - use when migrating to/from TOON"
```

**Resolution Logic**:
1. Load ALL `defaults` directly into task.skills (always required)
2. For EACH `optional`, match its `description` against deliverable context:
   - Deliverable title
   - Change type (feature, fix, refactor, etc.)
   - Affected files and their types
   - Deliverable description
3. Include optional if description indicates relevance to the task
4. Log reasoning for each optional skill decision
5. Before finalizing optionals, apply the **Security-Skill Attachment Sub-pattern** (below): when the deliverable context matches an untrusted-inbound-input signal, deterministically force the mapped security skill(s) into `task.skills` regardless of the LLM optional-relevance verdict.

**Example Reasoning** (for JSON→TOON migration task):
```
Optional: plan-marshall:ref-toon-format
Description: "TOON format knowledge for output specifications - use when migrating to/from TOON"
Deliverable: "Migrate JSON outputs to TOON format"
Match: YES - description mentions "migrating to/from TOON", deliverable is TOON migration
→ INCLUDE

Optional: pm-plugin-development:plugin-script-architecture
Description: "Script development standards covering implementation patterns, testing, and output contracts"
Deliverable: "Migrate JSON outputs to TOON format"
Match: YES - this is a script output change, needs output contract standards
→ INCLUDE
```

**Log skill resolution** (for each task created):
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:phase-4-plan) Resolved skills for TASK-{N} from {module}.{profile}: defaults=[{defaults}] optionals_selected=[{optionals}]"
```

### Step 6: Create Tasks

For each deliverable, compose one task record per profile, then persist all
records in a single atomic call via `manage-tasks batch-add` — one atomic
transaction with all-or-nothing semantics. See
`marketplace/bundles/plan-marshall/skills/manage-tasks/standards/task-contract.md`
§ "Atomic Batch Insertion (`batch-add`)" for the JSON array schema and
failure modes.

The three-step path-allocate flow (`prepare-add` → Write → `commit-add`)
is available for ad-hoc single-task additions (Q-Gate auto-loop, fix tasks
dispatched outside this phase) but MUST NOT be used here when more than one
task is being created in the same phase invocation.

**Breaking-refactor task split**: When the deliverable's `compatibility=breaking` OR its `change_type` is `tech_debt` or `feature_breaking`, AND it touches code paths covered by existing module tests, allocate the implementation and `module_testing` tasks per the task-split contract in [standards/breaking-refactor-task-split.md](standards/breaking-refactor-task-split.md) — the test-contract task carries `depends_on: [TASK-{implementation_number}]` and its description enumerates both the pre-existing tests being rewritten and any new regression tests pinning the new contract. This is the planning-side half of the breaking-refactor pair; phase-5-execute applies the planned-failure exception when the implementation task's verification fails in exactly the way the test-contract task is scoped to fix.

**Value-change test-update rule (NORMATIVE)**: When a deliverable changes a default value, a constant, or an enum member and its `**Affected files:**` enumerate existing test files (per the [phase-3-outline value-change test-sweep rule](../phase-3-outline/SKILL.md#value-change-test-sweep-rule-normative)), phase-4-plan MUST carry those existing-test targets into the `module_testing` task's `steps[]` and anchor the test-update obligation into the `module_testing` task `description`, so the executing agent updates every existing test asserting the old value — not only any new test file the plan introduces. Each carried-over existing-test target is emitted with `intent: write-replace` (the test file already exists and is modified in place), so the `files_exist` Q-Gate does not flag it as a missing or unexpectedly-present target. Do NOT inline-copy the phase-3-outline enumeration heuristic; the cross-reference above is the single authoring surface, so the obligation is enforced at both planning surfaces without drift.

**Missing-profile guard (NORMATIVE)**: The carry-forward above presupposes the deliverable declares the `module_testing` profile. When a deliverable enumerates existing test files in its `**Affected files:**` (signalling a value-change test sweep) but `module_testing ∉ D.profiles[]`, there is no `module_testing` task to carry the existing-test targets into — the test-update obligation would be silently dropped. Phase-4-plan MUST NOT fail silently in this case. Instead, fire this guard for every value-change deliverable.

**Predicate**: the guard fires for a deliverable `D` when BOTH of the following hold:

1. `D`'s `**Affected files:**` enumerate one or more existing test files (paths matching the project's test tree, e.g. `test/**/test_*.py`), AND
2. `module_testing ∉ D.profiles[]`.

**Action on match**:

1. Do NOT silently create only the `implementation` task. Emit a Q-Gate finding of the canonical shape below via `manage-findings qgate add`. The finding is routed back to phase-3-outline through the existing Q-Gate auto-loop so the outline corrects the profile mismatch at its source (re-evaluates the deliverable against the File-type classifier and adds the `module_testing` profile to the `**Profiles:**` block, since enumerated test files mean the resolved bucket is `test_only`, `mixed_code`, or `mixed_with_docs`).
2. Log a decision-log entry naming the deliverable index, title, and enumerated test paths so the run record shows the mismatch was caught.

**Canonical Q-Gate finding TOON shape**:

```toon
type: triage
severity: error
title: "phase-3-outline contract violation: value-change deliverable enumerates existing tests but omits module_testing profile"
component: "plan-marshall:phase-3-outline"
detail: "Deliverable {N} ({title}) enumerates existing test files ({test_files}) in its affected-files list but omits `module_testing` from profiles[]. A value-change deliverable that sweeps existing tests must declare `module_testing` so the test-update obligation flows into a paired task. Re-classify the deliverable against the File-type classifier and add the `module_testing` profile. See marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md § Value-change test-sweep rule."
```

**Emit via `manage-findings`**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase 4-plan --source qgate \
  --type triage --severity error \
  --title "phase-3-outline contract violation: value-change deliverable enumerates existing tests but omits module_testing profile" \
  --component "plan-marshall:phase-3-outline" \
  --detail "Deliverable {N} ({title}) enumerates existing test files ({test_files}) in its affected-files list but omits module_testing from profiles[]. A value-change deliverable that sweeps existing tests must declare module_testing so the test-update obligation flows into a paired task. Re-classify the deliverable against the File-type classifier and add the module_testing profile."
```

**Decision-log entry**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level WARNING \
  --message "(plan-marshall:phase-4-plan) Value-change missing-profile guard fired for deliverable {N} ({title}): enumerated existing tests but module_testing absent from profiles[], Q-Gate finding emitted. Test files: {test_files}."
```

### Description Anchoring Contract

To prevent compound-word mis-interpretation (e.g. `check-coverage` being described as PR/CI review hygiene), phase-4-plan MUST anchor every `task.description` to literal tokens from the parent deliverable:

1. **Verbatim title quote (mitigation 1)**: The `description` value MUST begin with the exact deliverable title in single quotes, followed by a comma (or a period if an intent gloss follows per mitigation 2). Example for a deliverable titled `check-coverage`:

   description: 'check-coverage', which checks module test coverage against this plan's changes.

   This forces compound-word tokens to survive description generation as a single unit.

2. **Intent gloss copy (mitigation 2)**: If the parent deliverable carries an `**Intent gloss:**` field (per manage-solution-outline/templates/deliverable-template.md), phase-4-plan MUST copy its value verbatim into the `description` after the title quote. If absent, phase-4-plan falls back to mitigation 1 alone.

   Combined example when both are present:

   description: 'check-coverage'. Check module test coverage against this plan's changes. <additional task-specific detail>.

3. **Structural-token preservation (mitigation 3)**: Any structural token appearing in the parent deliverable body MUST be preserved verbatim in `task.description`. Structural tokens are:

   - **Numeric literals** from the deliverable body (e.g. `990`, `1000`, `85`, `3.14`) — including order values, priority values, port numbers, thresholds, and any other numeric constants.
   - **Flag-style tokens** (e.g. `--plan-id`, `--name`, `order:`, `priority:`) — including CLI flags, TOON/YAML field prefixes, and option names.
   - **Quoted identifiers** surfaced in Metadata, Intent gloss, Profiles, Affected files, Change per file, Verification, or Success Criteria — including backticked paths, single-quoted names, and double-quoted strings.

   Paraphrasing, reformatting, or "regularizing" these tokens into sequential multiples, rounded values, or stylistically neater forms is explicitly prohibited. In particular, rewriting `order: 990 / 1000` as `order: 90 / 100` to make the numbers "look nicer" — or collapsing `990`→`99`, `1000`→`100`, `85`→`80`, etc. — is forbidden, because the numeric values are load-bearing data from the source outline, not decorative placeholders.

   **Worked example**: A deliverable body specifies task-ordering values `order: 990 / 1000` in its Change per file section. The canonical violation is a task description that paraphrases these as `order: 90 / 100` — a "regularization" from the four-digit spacing (`990`/`1000`) down to a two-digit spacing (`90`/`100`). The description MUST instead carry the literal tokens `order: 990 / 1000` verbatim. This same rule applies whenever the outline supplies specific numeric or flag-shaped data: copy the tokens exactly as written, do not "improve" them.

**CRITICAL — Shell Metacharacter Sanitization**: Before writing values into the TOON task file, strip all markdown backticks (`` ` ``) from title, description, criteria, and step values. Backticks are shell metacharacters (command substitution) that trigger permission prompts if they later reach a shell. They are markdown formatting artifacts not needed in TOON task data. Replace `` `foo` `` with `foo` (plain text).

### Validation: Lesson-ID References

**Shape constraint** — A lesson ID is a five-segment token of the form `YYYY-MM-DD-HH-N+` (e.g., `2026-05-03-21-002`). The canonical regex is `LESSON_ID_RE` in `tools-input-validation` and is the single source of truth for the shape; this section never re-defines or re-spells the pattern.

**At-write-time enforcement** — Every task whose `title` or `description` contains a lesson-ID-shaped token MUST resolve that token against the live `manage-lessons` inventory before the task file is written. Enforcement lives in the write paths of `manage-tasks` (`commit-add` and `batch-add`), so neither phase-4-plan nor any other plan-author surface can bypass it by writing through the script:

1. The handler calls `scan_lesson_id_tokens(title + ' ' + description)` from `tools-input-validation` to extract every embedded lesson-ID token.
2. The handler calls `verify_lesson_ids_exist(tokens)` to check each token against the live `manage-lessons list` inventory (the same inventory the runtime live-anchor discipline uses).
3. **Plan-dir artifact exemption** — for any token NOT present in the active inventory, the handler ALSO checks whether the plan's own converted source lesson exists on disk at `.plan/local/plans/{plan_id}/lesson-{id}.md`. A token that resolves to such a plan-dir artifact is a legitimate reference — a lesson the plan itself converted lives in the plan directory even after it has left the active inventory — so it is dropped from the unresolved set and the write proceeds. Resolution is therefore two-tier: a token resolves when it is present in the active inventory OR when its `lesson-{id}.md` artifact exists under the plan directory.
4. On ANY token unresolved in BOTH tiers (absent from the active inventory AND with no `lesson-{id}.md` artifact in the plan directory), the entire write batch is aborted atomically — no `TASK-NNN.json` file is created, the on-disk state is untouched, and the response is the error payload described below.
5. The handler does NOT auto-rewrite descriptions to drop the offending IDs and does NOT downgrade the failure to a soft warning. A reference miss in both tiers is a hard error so the plan can be corrected before execution.

**Failure mode** — On an unresolved reference, both `commit-add` and `batch-add` return the canonical TOON error payload:

```toon
status: error
error: validation_error
validation_error: lesson_id_not_found
unresolved_ids[N]:
  - 2026-05-03-21-002
  - 2026-05-03-22-001
task_index: 0
message: "Task references lesson IDs that do not exist in the live manage-lessons inventory: ['2026-05-03-21-002', '2026-05-03-22-001']. ..."
```

`task_index` is the zero-based index of the offending task in the batch (`0` for `commit-add`, which always writes a single task). `unresolved_ids` carries the deduplicated, sorted list of unresolved tokens.

**Recovery procedure** — When a write fails with `validation_error: lesson_id_not_found`. The recovery below applies only to IDs that are unresolved in BOTH tiers — absent from the active inventory AND with no `lesson-{id}.md` artifact under the plan directory; an ID that resolves to a plan-dir converted source lesson never reaches this failure path:

1. Inspect `unresolved_ids` in the error payload to identify which lesson IDs are unknown to BOTH the active inventory and the plan directory.
2. Decide per ID: either (a) **create the lesson** via `manage-lessons add` if the reference was meant to point to a real (but not-yet-allocated) lesson — first running the canonical three-gate lesson-creation policy in [`../manage-lessons/standards/lesson-creation-policy.md`](../manage-lessons/standards/lesson-creation-policy.md) (Gate 1 dedup, Gate 2 active-plan check, Gate 3 create) so the recovery create-path is consistent with the policy — or (b) **drop the ID from the task description** and reword the narrative as a query against the live inventory (e.g., "archive any lessons matching component=X and category=resolved") so the task does not depend on a phantom ID.
3. Re-stage the corrected task batch (re-write the `tasks-batch.json` staging file) and re-invoke `batch-add --tasks-file PATH`. The atomic-write contract guarantees the previous failed attempt left no on-disk state behind, so the retry starts from a clean tasks directory.
4. NEVER bypass the validation by editing `TASK-NNN.json` files directly or by passing `--no-validate`-style flags — no such bypass exists, and the validation is the only point in the plan lifecycle that catches lesson-ID drift before tasks reach phase-5-execute.

This validation pushes the check into the write paths of `manage-tasks` so any lesson-ID drift surfaces at task-author time as a hard, structured error — the same point in the lifecycle where the operator can still correct it cheaply, rather than landing later as a silent no-op (`archived: 0`) at execute time.

Compose every task record for this phase invocation into one JSON array, then persist them atomically via the path-allocate flow. Each entry mirrors the TOON task schema:

```
{
  "title": "{task title}",
  "deliverable": {deliverable_number},
  "domain": "{domain}",
  "profile": "{profile}",
  "description": "{description}",
  "steps": [
    {"target": "{file1}", "intent": "{intent1}"},
    {"target": "{file2}", "intent": "{intent2}"}
  ],
  "depends_on": [],            // or ["TASK-1", ...]
  "skills": ["{bundle:skill}", ...],
  "verification": {
    "commands": ["{cmd1}"],
    "criteria": "{criteria}"
  }
}
```

Each step is a `{target, intent}` object — bare-string steps are rejected by `batch-add`. Source each step's `intent` from the parent deliverable's `affected_files[N].intent`, surfaced by `manage-solution-outline list-deliverables` (the deliverable's `Affected files` markers authored in phase-3-outline). The intent vocabulary is the closed enum `read` / `write-new` / `write-replace` / `delete`; it threads unchanged from the deliverable annotation into the task step so the `files_exist` Q-Gate applies the per-intent existence predicate.

Sequential numbering is assigned in array order at call time. On any validation failure no `TASK-NNN.json` is written.

**Step 6a — Stage the JSON array under the plan's `work/` tree via the `Write` tool.** Use the `Write` tool directly to write the batch JSON to `.plan/local/plans/{plan_id}/work/tasks-batch.json`. This path is covered by the `Write(.plan/**)` permission rule, so no permission prompt is triggered, and writing through a structured tool keeps the JSON payload off the shell argument boundary.

If a script-mediated path is preferred (for example, when the staging file already lives outside `.plan/`), the optional `manage-files write --content-file PATH` form is documented separately in `marketplace/bundles/plan-marshall/skills/manage-files/SKILL.md` (write subcommand reference). Both forms produce the same staged file; only the canonical `Write`-tool form is exercised by this phase.

**Step 6b — Persist the batch atomically** by passing the staged file path to `batch-add --tasks-file`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  batch-add --plan-id {plan_id} --tasks-file .plan/local/plans/{plan_id}/work/tasks-batch.json
```

The `--tasks-file PATH` form is the canonical entrypoint for phase-4-plan (and any other caller that produces more than one task at a time). The inline `--tasks-json` form is mutually exclusive with `--tasks-file` and is reserved for trivial payloads only — it is NOT used by this phase.

> **TOON quoting rule for `verification.commands` (ENFORCED)**
>
> Each list item under `verification.commands:` MUST be emitted as a bare TOON list entry — a hyphen, a single space, then the raw command. Do **NOT** wrap the entire command in outer double-quotes. Literal inner double-quotes (e.g. around `--command-args` values) are allowed and MUST be written as plain `"` characters, not escaped as `\"`.
>
> This rule is enforced: `parse_stdin_task` in `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_core.py` raises `ValueError` at task-creation time when a `verification.commands` item starts with a `"` wrapper. Treat the rule as hard — do not fall back to the outer-quoted form "just to be safe".
>
> **DO** (bare list item, literal inner quotes):
> ```
> verification:
>   commands:
>     - python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "module-tests plan-marshall"
>   criteria: module-tests plan-marshall succeeds
> ```
>
> **DON'T** (outer-quoted wrapper with escaped inner quotes — this trips the parser):
> ```
> verification:
>   commands:
>     - "python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args \"module-tests plan-marshall\""
>   criteria: module-tests plan-marshall succeeds
> ```

**MANDATORY - Log each task creation**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[ARTIFACT] (plan-marshall:phase-4-plan) Created TASK-{N}: {title}"
```

**Key Fields**:
- `domain`: Single domain from deliverable
- `profile`: `implementation`, `module_testing`, or `verification` (determines workflow skill at execution)
- `skills`: Domain skills only (system skills loaded by agent). Empty for `verification` profile.
- `steps`: File paths from `Affected files` (NOT descriptive text). For `verification` profile: verification commands as steps instead of file paths.

**Verification**: Stamp each task's `verification.commands` from the deterministic deriver at plan time. Call `architecture derive-verification` with the task's changed-artifact list (the `steps[].target` paths, comma-joined) and stamp the returned command set into `verification.commands` so the task is self-describing:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  derive-verification --changed-artifacts {comma_joined_step_targets} \
  --audit-plan-id {plan_id}
```

Parse the returned `commands[]` rows and write each row's `executable` into the task's `verification.commands` list (preserving order; one list entry per derived command). The deriver classifies each changed artifact via the `build_map` — the file-to-build contract the build-system-owned `BuildExtensionBase` subclasses (`build-pyproject` / `build-maven` / `build-gradle` / `build-npm`) source through their declared `(pattern, role)` routes — and emits the architecture-resolved verification command set. The build-necessity decision itself is never re-derived inline here: whether a build applies to a task's changed set flows from the deriver consuming that build-extension-sourced `build_map`, and the centralized `manage-config build-decision` verb (over `should_execute_build`) owns the plan-footprint-level "is a build necessary?" verdict the finalize gates consult. The `build_class` names the canonical command directly — there is no indirection map between the class and the command it resolves. A changed set whose only role yields `none` (or whose paths are all documentation) derives no Python build — the deriver structurally cannot stamp a test command onto a docs-only task. The TOON-quoting rule for `verification.commands` (below) still governs how the derived commands are written. For the derive API contract and the build_class → command mapping, see [`manage-architecture` SKILL.md](../manage-architecture/SKILL.md) and [`manage-architecture/standards/resolve-command.md` § "Build-class → verification command"](../manage-architecture/standards/resolve-command.md#build-class--verification-command); for the centralized build-decision verb, see [`manage-config` SKILL.md](../manage-config/SKILL.md) § `build-decision` — do NOT inline-copy the mapping table or the decision table here.

**Cost prediction**: Stamp each task's `cost_size` + `predicted_cost_tokens` from the deterministic cost-sizing deriver at plan time — the sibling of the `verification.commands` deriver-stamp above, run from the same point where every input signal is already known. This stamp is **deterministic — no LLM estimation**. Build count is excluded as an input (builds are token-cheap, ~100 tokens/build); the size predicts **TOKENS, not wall-clock time**. For each task, compute the four plan-time signals from the task record and call `derive-cost-size`:

- `--step-count` = `len(task.steps)` (dominant signal)
- `--profile` = `task.profile` (`implementation` / `module_testing` / `verification`)
- `--skills-count` = `len(task.skills)`
- `--target-file-count` = count of **distinct** `steps[].target` values

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  derive-cost-size --step-count {step_count} --profile {profile} \
  --skills-count {skills_count} --target-file-count {target_file_count} \
  --size-table {cost_size_token_table_json}
```

Pass `--size-table` as the JSON object the config knob `plan.phase-5-execute.cost_size_token_table` holds (read once at phase entry alongside the other loop-invariant inputs) so the deriver maps the size to the operator-tunable `predicted_cost_tokens` magnitude; omit `--size-table` to fall back to the rubric default. Parse `cost_size` + `predicted_cost_tokens` from the returned TOON, then **persist both onto the task record via the `manage-tasks update` write-back verb** — `derive-cost-size` is pure and never writes, so the values land on disk only through the `update` cost-field flags. Run this once per task AFTER `batch-add` has created the `TASK-NNN.json` files (so the task number to target exists):

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks update \
  --plan-id {plan_id} --task-number {task_number} \
  --cost-size {cost_size} --predicted-cost-tokens {predicted_cost_tokens}
```

See [`manage-tasks` SKILL.md § "Canonical invocations" → `update`](../manage-tasks/SKILL.md) for the cost-field write-back contract and validation rules. The deriver is the deterministic default; the planner **consults** the legible rubric `phase-4-plan/standards/cost-sizing.md` (D1) — the single source of truth for the signals, weights, score thresholds, size→token table, and worked examples — to apply judgment (treat a task as one size larger) when a task's true token cost diverges from the mechanical step-count proxy (e.g. few steps but unusually large target files). Do NOT inline-copy the rubric's weight/threshold/token table here. The stamped `predicted_cost_tokens` is consumed by the bin-packer (Step 7a) and the stamped `cost_size`/`predicted_cost_tokens`/`envelope_id` are surfaced via `manage-tasks next` and read by the phase-5-execute envelope-group executor. See [`phase-4-plan/standards/cost-sizing.md`](standards/cost-sizing.md) for the rubric (signals, weights, thresholds, size→token table, and the deriver cross-reference) — it is the legible owner of the `derive-cost-size` model.

### Step 7: Determine Execution Order

Compute parallel execution groups:

```toon
execution_order:
  parallel_group_1: [TASK-1, TASK-3]    # No dependencies
  parallel_group_2: [TASK-2, TASK-4]    # Both depend on group 1
  parallel_group_3: [TASK-5]            # Depends on group 2
```

**Parallelism rules**:
- Tasks with no `depends_on` go in first group
- Tasks depending on same prior tasks can run in parallel
- Sequential dependencies remain sequential

`execution_order` is a parallelism schedule DERIVED FROM the `depends_on` graph — it never substitutes for it. A functional compile-order / build-order dependency between deliverables MUST be declared as a `depends_on` edge (see Step 4 § "`depends_on` is the dependency surface, not `execution_order`"); placing the dependent task in a later parallel group without the `depends_on` edge leaves the dependency invisible to the executor and is prohibited.

### Step 7a: Pack Tasks into Execution Envelopes

**Purpose**: Pre-compute the phase-5-execute continue-vs-yield decision at plan time. After every task carries a stamped `predicted_cost_tokens` (Step 6 cost prediction) and the execution order is fixed (Step 7), run the deterministic bin-packer to group tasks into budget-bounded **execution envelopes** and stamp each task's `envelope_id`. The phase-5-execute executor then performs NO runtime cost computation — it runs only the tasks whose `envelope_id` matches its assigned group and yields when that group is exhausted (a countable membership check). This step runs after Step 7 (execution order, which establishes `depends_on` ordering) and before Step 7b (manifest compose).

**Read the per-envelope budget** from config (read once at phase entry alongside the other loop-invariant inputs):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get --field per_envelope_budget_tokens
```

Parse the magnitude string `value` (e.g. `"400K"`) and convert it to an integer via `sensible_number.parse_sensible_int` to obtain `{per_envelope_budget_tokens}`.

**Run the bin-packer** — it reads the plan's tasks in number order, sums each task's pre-stamped `predicted_cost_tokens` (Next-Fit in task order, honouring the `depends_on`-derived ordering the tasks were created in), and assigns each a 1-based `envelope_id`. A single task whose own `predicted_cost_tokens` exceeds the budget lands alone in its envelope (the rubric's legitimate ~1-per-envelope XL case). The packer never re-derives a cost:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  pack-envelopes --plan-id {plan_id} --per-envelope-budget-tokens {per_envelope_budget_tokens}
```

Parse `envelope_count` and the `assignments_table` (one `{number, predicted_cost_tokens, envelope_id}` row per task) from the returned TOON. **Persist each returned `envelope_id` back onto its task record via the `manage-tasks update` write-back verb** — `pack-envelopes` is pure and never writes, so the assignment lands on disk only through the `update --envelope-id` flag. Run one `update` per `assignments_table` row so phase-5-execute can read `envelope_id` from `manage-tasks next`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks update \
  --plan-id {plan_id} --task-number {number} --envelope-id {envelope_id}
```

See [`manage-tasks` SKILL.md § "Canonical invocations" → `update`](../manage-tasks/SKILL.md) for the cost-field write-back contract. Cache `envelope_count` for Step 7b (manifest compose).

The packer's Next-Fit-in-task-order contract, the lone-oversized-task own-group rule, and the `assignments_table` / `envelopes_table` output shape are owned by [`manage-tasks` SKILL.md § "Canonical invocations" → `pack-envelopes`](../manage-tasks/SKILL.md); the size→token mapping that produced each `predicted_cost_tokens` is owned by [`phase-4-plan/standards/cost-sizing.md`](standards/cost-sizing.md). Do NOT inline-copy the packing algorithm or the token table here.

### Step 7b: Compose Execution Manifest

**Purpose**: Emit the per-plan execution manifest so that Phase 5 and Phase 6 can dispatch their steps as dumb manifest executors. The manifest is the single source of truth for which Phase 5 verification steps and Phase 6 finalize steps fire for this plan — per-doc skip logic in their standards is removed in favor of this single artifact.

This step runs after Step 7 (execution order) and before Step 8 (Q-Gate). It MUST run on every successful plan-phase invocation; the manifest is required by phase-5-execute on entry.

**Inputs**:
- `change_type` — read from solution outline metadata (use the first deliverable's `change_type` when the outline has more than one; the plan-level summary in `solution_outline.md` Summary block also surfaces it).
- `track` — read from `manage-references get --field track` (`simple` or `complex`).
- `scope_estimate` — read from `manage-references get --field scope_estimate` (deliverables 2 / 3 wire this in earlier in the plan lifecycle).
- `recipe_key` — OPTIONAL override only. The composer reads `status.json::metadata.plan_source` (falling back to `metadata.recipe_key`) on its own, so lesson- and recipe-derived plans select the `recipe` rule even when this flag is omitted. Pass `--recipe-key` only to force a recipe rule that status metadata does not already imply.
- `affected_files_count` — `manage-references get --field affected_files`, count entries.
- `phase-5-steps` candidate (`{p5_csv}`) — read via the bash call below, comma-join the returned `verification_steps` list (the phase-5 block stores its verification step list under `verification_steps`, not `steps`).
- `phase-6-steps` candidate (`{p6_csv}`) — read via the bash call below, comma-join the returned `steps` list.
- `commit_and_push` — read via the bash call below, from the `commit_and_push` field; omit `--commit-and-push` on `compose` when the field is absent (defaults to `true`).

**Read manifest inputs** (run before compose; do NOT skip or improvise alternative reads):

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get \
  --plan-id {plan_id} --field track
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get \
  --plan-id {plan_id} --field scope_estimate
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get \
  --plan-id {plan_id} --field affected_files
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get --field verification_steps
```

Parse `value` as a list and comma-join to produce `{p5_csv}`. (The phase-5 block stores its verification step list under `verification_steps`; phase-6 still uses `steps`.)

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize get --field steps
```

Parse `value` as a list and comma-join to produce `{p6_csv}`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get --field commit_and_push
```

Parse `value` as `{commit_and_push}` — omit `--commit-and-push` on `compose` when the field is absent.

**Compose**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  compose \
  --plan-id {plan_id} \
  --change-type {change_type} \
  --track {simple|complex} \
  --scope-estimate {scope_estimate} \
  [--recipe-key {recipe_key}] \
  --affected-files-count {N} \
  --phase-5-steps "{p5_csv}" \
  --phase-6-steps "{p6_csv}" \
  [--commit-and-push {commit_and_push}]
```

**Envelope count**: After the `compose` call succeeds, record `{envelope_count}` — the value cached from Step 7a (`pack-envelopes`), the number of execution envelope groups the bin-packer produced — into the composed manifest. Recording it tells the phase-5-execute orchestrator exactly how many envelope dispatches to drive (one `execution-context` dispatch per `envelope_id` group), so the orchestrator reads `envelope_count` from the manifest rather than re-running the packer. The manifest `envelope_count` field is owned by [`manage-execution-manifest` SKILL.md](../manage-execution-manifest/SKILL.md) (the consumer is the phase-5-execute budget-bounded task loop, which reads `envelope_count` on phase entry); use the manifest skill's canonical write surface for the field — do NOT raw-edit `execution.toon`.

**Validate** (immediately after compose, before Q-Gate):

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  validate \
  --plan-id {plan_id} \
  --phase-5-steps "{p5_csv}" \
  --phase-6-steps "{p6_csv}"
```

**Log manifest path** (after a successful compose+validate):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[ARTIFACT] (plan-marshall:phase-4-plan) Composed execution manifest at .plan/local/plans/{plan_id}/execution.toon (rule={rule_fired})"
```

**Error path**: If `validate` returns `status: error` (`error: invalid_manifest`), the phase MUST fail loudly — do NOT proceed to Q-Gate or Step 10 transition. Surface the error message in the phase return TOON and abort:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR \
  --message "[STATUS] (plan-marshall:phase-4-plan) Manifest validation failed — aborting phase. {validation_message}"
```

The composer's `decision.log` entry (one per applied rule) provides the audit trail; the manifest itself stays lean and diffable. The seven-row matrix is documented in `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md`.

**Per-task verification routing (data-driven)**: After the seven-row matrix runs, the composer performs an `execution_tier` routing pass over every `TASK-*.json` in the plan. For each `verification.commands` entry, the composer subprocesses `architecture resolve` to obtain the four-field augmented TOON (`bash_timeout_seconds`, `exceeds_bash_ceiling`, `execution_tier`, `hint`) and branches: `orchestrator` commands are mapped to their canonical phase-5 step ID — emitted as **bare** names per the boundary-normalization contract (`quality-gate → quality_check`, `verify`/`module-tests → build_verify`, `coverage → coverage_check`) so no stray `default:`-prefixed ID is appended alongside the bare names the matrix already produced — appended to `phase_5.verification_steps` (de-duped), and removed from the task's verification list; `per_task` commands stay per-task and the task's `verification.bash_timeout_seconds` field is set to the maximum measured timeout across surviving commands. Non-build / unresolvable executables pass through unchanged. The routing is data-driven — no hardcoded "long-running" command list — and the authoritative source is `architecture resolve` per the "Structured queries first" hard rule. The composer derives each canonical-verify step's matrix role from the trailing canonical segment of its `default:verify:{canonical}` ID (rather than a per-canonical role-file), then applies the generic footprint pre-filter that drops any footprint-gated whole-tree canonical (`integration` / `e2e`) the live footprint does not exercise. See `manage-execution-manifest/standards/decision-rules.md § execution_tier Routing`, § "Role derivation for canonical-verify steps", and § "Generic footprint pre-filter" for the full contracts, and `manage-architecture/standards/resolve-command.md` for the failure mode that motivated the routing.

### Step 8: Q-Gate Verification Checks

**Purpose**: Verify created tasks meet quality standards.

### Run Q-Gate Checks

Invoke the deterministic mechanical-checks subcommand once. It runs the six
mechanical verifications (coverage, skill-resolution, acyclic, files-exist,
keyword-drift, structural-token-drift) and emits one Q-Gate finding per
failure into the phase-4-plan store via the same `qgate add` API the inline
prose used to call — pure regex + graph + filesystem, no LLM dispatch:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  qgate-mechanical-checks --plan-id {plan_id}
```

The six checks correspond to:

1. **Deliverable Coverage**: Every deliverable has >= 1 task; no task references a deliverable that does not exist in `solution_outline.md`.
2. **Skill Resolution Valid**: Every non-verification task has a non-empty `domain` and every `skills[]` entry matches the `bundle:skill` shape.
3. **Dependency Graph Acyclic**: `depends_on` across all tasks forms a DAG (Kahn-style topological pass).
4. **Steps Valid**: Every step target on non-verification tasks resolves on disk.
5. **Keyword-drift**: Planning-domain keywords (`PR review`, `CI`, `merge comments`, `pipeline`, `automated review`, `build check`, `review comments`) appearing in a `task.description` but absent from the parent deliverable's haystack (title + metadata + profiles + affected files + verification).
6. **Structural-token-drift**: `TASK-NNN` numbering monotonic, starting at `TASK-001`, no gaps.

Parse the return TOON: `total_failed` is the aggregate finding count for the
inline checks (added to `qgate_pending_count` returned in Step 10), and
`ambiguous` is `true` when `solution_outline.md` was missing or unparseable —
in that case the orchestrator-dispatched q-gate-validation (signaled by
Step 8b via `qgate_validation_required: true`) is the only authoritative pass
and the orchestrator MUST still fire it.

### Log Q-Gate Result

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-4-plan:qgate) Verification: {passed_count} passed, {flagged_count} flagged"
```

### Description-token preservation check (warn-only)

This check is distinct from the script's `structural_token_drift` check
(which validates TASK-NNN file numbering monotonicity). It catches silent
regularization of structural tokens in `task.description` against the
parent deliverable's haystack.

After all tasks are created, scan each `task.description` for structural tokens that are not present in the parent deliverable body. Structural tokens are numeric literals, flag-style tokens, and quoted identifiers — the same three categories defined in Step 6 mitigation 3 ("Structural-token preservation"). This check catches silent regularization of structural data (e.g. `990 / 1000` rewritten as `90 / 100`) that the keyword-drift check does not cover.

1. Build an outline-text haystack: concatenate the parent deliverable's Title, Metadata, Intent gloss, Profiles, Affected files, Change per file, Verification, and Success Criteria sections as plain text. The Title is included because mitigation 1 requires `task.description` to begin with a verbatim title quote — any structural tokens in the title must therefore also be present in the haystack, otherwise they surface as false-positive drift findings.
2. Extract structural tokens from `task.description`:
   - **Numeric literals** (e.g. `990`, `1000`, `85`, `3.14`) — integers and decimals appearing as standalone tokens.
   - **Flag-style tokens** (e.g. `--plan-id`, `--name`, `order:`, `priority:`) — CLI flags and TOON/YAML field prefixes.
   - **Quoted identifiers** — single-quoted or double-quoted strings. (Backticks are stripped from `task.description` at creation time per the Shell Metacharacter Sanitization rule in Step 6, so backticked tokens never appear in the description and are not part of this extraction.)
3. For each extracted token present in `task.description` but ABSENT from the haystack (using anchored matching with word boundaries to prevent substring collisions — e.g. the token `90` must not match `990` in the haystack), emit a warning Q-Gate finding:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase 4-plan --source qgate \
  --type warning \
  --title "Description drift: TASK-{N} uses structural token '{token}' not present in deliverable outline" \
  --detail "{description excerpt}; deliverable {deliverable_number} outline does not mention '{token}'"
```

**Rigor**: this check is warn-only. Phase-4-plan MUST proceed to completion regardless of warnings — the operator reviews findings at the phase-4-plan gate.

### Step 8b: Dispatch q-gate-validation for mechanical validators

**Purpose**: Run the `module-mapping-validator` and `scope-criterion-validator` from `plan-marshall:plan-marshall/workflow/q-gate-validation.md` (§§ 2.11, 2.12) over the just-created tasks and the parent deliverables. Both validators reconcile LLM-authored task/deliverable shape against live ground truth (architecture which-module, architecture find/marketplace grep) and emit findings that the orchestrator's existing 3-iteration auto-loop consumes.

**Activation guard**: Runs after every successful phase-4-plan invocation, regardless of `plan_source`, EXCEPT when the surgical-scope bypass predicate (B2) below fires. Both validators apply to every plan (lesson-derived, issue-derived, recipe-derived, free-form). The phase sets `qgate_validation_required: true` in its return TOON on every successful completion; the orchestrator's existing `max_iterations` budget gates re-entry on its side. Skipping the signal is reserved for the unrecoverable error path (the phase has aborted with `status: error` before reaching the return-results step) AND the B2 surgical-scope bypass below.

**B2 — Surgical q-gate-validation bypass (deterministic)**: Before signalling `qgate_validation_required: true`, evaluate the surgical-scope predicate:

> `scope_estimate == surgical AND affected_files_count <= 2`

where `affected_files_count` is the cardinality of the deduplicated union of every deliverable's `Affected files:` list. When the predicate holds, override `qgate_validation_required` to `false` in the Step 10 return TOON instead of the unconditional `true` — the orchestrator's q-gate-validation dispatch site reads the flag and skips the validator envelope when it is `false`. When the predicate is false (non-surgical, or 3+ affected files), the unconditional `true` value documented above is preserved.

Log the bypass decision once at decision level:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-4-plan:qgate-bypass) skipped — scope_estimate=surgical, affected_files={N}"
```

When the bypass fires, also skip the `[STATUS] qgate_validation_required=true` log line emitted below; emit instead:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (plan-marshall:phase-4-plan) qgate_validation_required=false — surgical-scope bypass active (scope_estimate=surgical, affected_files={N})"
```

**Cross-reference (lesson-ID validation)**: Lesson-ID validation is intentionally NOT signaled here. PR #323 ships lesson-ID validation at **write time** in `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_crud.py` (via `tools-input-validation/scripts/input_validation.py`). Every `TASK-*.json` write hits the validator before disk and **hard-fails** with `validation_error: lesson_id_not_found` when a phantom ID is cited — distinct from this Step 8b's orchestrator-side q-gate auto-loop placement. Future maintainers extending phase-4-plan validation should preserve the placement split: write-time hard-fail for lesson-ID lookup against `manage-lessons list`; orchestrator-dispatched q-gate auto-loop for structural cross-checks (module mapping, scope criterion).

**Signal the validator requirement**.

When phase-4-plan completes successfully, the phase records the requirement by setting `qgate_validation_required: true` in the return TOON (see Step 10 § Output below). The orchestrator (`plan-marshall:plan-marshall/workflow/planning-outline.md`) reads that flag after the phase returns and dispatches `plan-marshall:plan-marshall/workflow/q-gate-validation.md` as a sibling top-level `Task: plan-marshall:{target}` invocation — the phase body cannot dispatch it directly because the `Task` tool is unavailable inside an `execution-context-{level}` subagent. The orchestrator-dispatched validator agent reads `solution_outline.md` (for the deliverables and their `success_criterion`/`affected_files` blocks) and the just-written `TASK-*.json` files (for `module_testing` task targets), runs the `module-mapping-validator` and `scope-criterion-validator` detection logic, and emits findings using `--source qgate-module-mapping` / `--source qgate-scope-criterion`. Aggregation of the validator's `qgate_pending_count` into the phase aggregate also moves to the orchestrator; this step only signals intent. See `plan-marshall/workflow/q-gate-validation.md` for the canonical detection logic and finding emission templates.

Log the intent so the run record shows the activation:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (plan-marshall:phase-4-plan) qgate_validation_required=true — orchestrator will dispatch q-gate-validation (module-mapping + scope-criterion validators) after phase return"
```

This signaling step runs AFTER the inline Q-Gate checks of Step 8 and BEFORE Step 9 (Record Issues as Lessons) / Step 10 (Transition Phase and Return Results). The placement is load-bearing: inline checks first means cheap structural findings are recorded before the phase return; the orchestrator-side validator dispatch ensures architecture-anchored findings can re-enter phase-4-plan alongside the inline ones via the existing auto-loop predicate.

### Step 9: Record Issues as Lessons

On ambiguous deliverable or planning issues, first run the canonical three-gate lesson-creation policy in [`../manage-lessons/standards/lesson-creation-policy.md`](../manage-lessons/standards/lesson-creation-policy.md) — Gate 1 (dedup), Gate 2 (active-plan check), Gate 3 (create). The two-step path-allocate flow below is Gate 3, reached only when Gates 1 and 2 both clear; when Gate 1 returns `merge_into` / `already_closed` or Gate 2 finds a covering active plan, extend the existing lesson or fold into the plan instead of allocating a new one. Do not restate the gate mechanics — follow the standard.

When the gates clear, follow the two-step path-allocate flow:

1. Allocate a lesson file and capture the returned `path`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component "plan-marshall:phase-4-plan" \
  --category improvement \
  --title "{issue summary}"
```

2. Parse `path` from the output and write the lesson body (context + resolution approach, with `##` sections as needed) directly to that path via the Write tool. This is the single supported API — there is no `--detail` inline form.

**Valid categories**: `bug`, `improvement`, `anti-pattern`

### Step 10: Transition Phase and Return Results

**Transition phase**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status transition \
  --plan-id {plan_id} \
  --completed 4-plan
```

**Log phase completion**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-4-plan) Plan phase complete - {M} tasks created from {N} deliverables"
```

**Add visual separator** after END log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  separator --plan-id {plan_id} --type work
```

See [Task Creation Flow](references/task-creation-flow.md) for the full output structure.

**Output**:
```toon
status: success
plan_id: {plan_id}

summary:
  deliverables_processed: {N}
  tasks_created: {M}
  parallelizable_groups: {count of independent task groups}

tasks_created[M]{number,title,deliverable,depends_on}:
1,Implement UserService,1,none
2,Test UserService,1,TASK-1
3,Implement UserRepository,2,none
4,Test UserRepository,2,TASK-3

execution_order:
  parallel_group_1: [TASK-1, TASK-3]
  parallel_group_2: [TASK-2, TASK-4]

lessons_recorded: {count}
qgate_pending_count: {0 if no findings}
qgate_validation_required: {true|false}
```

`qgate_validation_required` is `true` on every successful phase-4-plan completion (Step 8b signals unconditionally — both module-mapping and scope-criterion validators apply to every plan) and `false` only on the unrecoverable error path. The orchestrator (`plan-marshall:plan-marshall/workflow/planning-outline.md`) reads this flag after the phase returns and dispatches `q-gate-validation` as a sibling top-level Task when it is `true`.

## Integration Deliverable Narrative Constraint

**Applies when**: the plan has a **"central + integrations"** shape — one deliverable creates a central standard, regex, decision table, keyword list, or path heuristic (the *central* deliverable), and one or more downstream deliverables integrate / consume that central artifact (the *integration* deliverables).

**Rule**: each integration deliverable's task description and `success_criteria` MUST require **xref** to the central standard for any **enforcement-critical** content. The xref form is `see {central-standard-path} §{section}` (or `see {central-standard-path}#{anchor}` when the source supports markdown anchors). The list of enforcement-critical content categories is fixed:

- Path heuristics
- Keyword lists
- Decision tables
- Regex / glob patterns
- Threshold values that gate behavior

A 1-2-sentence inline summary is permitted for skim-readability — but the **normative rule body** (the text the q-gate validator, plugin-doctor, or runtime dispatcher actually consumes) MUST live in the central standard only. Integration deliverables that copy-paste the rule body have *every* drift surface that the central standard had, multiplied by the number of integrations: every subsequent edit to the rule has to find and update every copy, and the first missed copy silently regresses one of the integration points.

**Injection point**: when `phase-4-plan` materialises the per-task description for an integration deliverable, prepend the constraint to the task narrative so the task agent receives it in-context. Detection heuristic for "this is an integration deliverable":

1. The deliverable's `depends_on` list names at least one prior deliverable AND
2. The prior deliverable's affected_files include a `**.md` standards file (typically under `standards/`) AND
3. The current deliverable's affected_files include at least one file (typically `SKILL.md`, a validator agent's prompt, or any prose body) that integrates the central standard — the file MAY live in the same skill, a different skill, or a different bundle. The integration point is a consumer of the central standard's rule body, regardless of co-location with the standard.

When all three conditions hold, the task narrative MUST carry a sentence of the form: *"Reference the central standard via `see {central-standard-path} §{section}` — do not inline-copy the path heuristic / keyword list / decision table / regex; enforcement-critical content lives in the central standard only."*

**Failure-mode rationale**: this constraint was hardened in response to a recurring drift pattern — an integration site (a `SKILL.md`, a validator prompt, or a workflow doc) inlines a copy of an *enforcement-critical* rule body (a path heuristic, a keyword list, a decision table, or a regex) instead of xref-ing the central standard that owns it. A subsequent extension of the rule body lands only in the central standard; the integration site silently keeps the stale copy and drifts out of lockstep until a manual audit catches the divergence.

The failure shape is always the same: a copy-pasted *enforcement-critical* rule body that drifted because the integration site was not declared as a downstream consumer of the central standard. The constraint converts that latent contract ("everyone keep your copy in sync") into an explicit one ("xref the central standard; never inline-copy"). The q-gate validator §2.17 architecture-mismatch finding reinforces the same boundary at the outline phase, so the constraint is enforced at both planning time and validation time.

**Counter-indication (when inline copy is allowed)**: the integration deliverable extends a *closed-form, version-pinned reference value* that the central standard explicitly designates as a stable embedding target (e.g., a SemVer constant, a fixed enum). Inline embedding of such values is acceptable because they are not enforcement-critical rule bodies — drift is detected by the central standard's release/version contract, not by xref reachability.

## Path / Constant Migration Sub-pattern

**Applies when**: the planner detects a **cross-cutting rename** — a path constant, string literal, command name, log-level token, JSON key, or skill cross-reference appears > N times across the marketplace AND the deliverable list contains at least one `*.py` task targeting the rename AND **zero** `*.md` tasks for the same constant. The `*.py`-only signal is the activation key: a planner that would otherwise schedule only code-sweep tasks for a wide-scoped rename is the failure mode this sub-pattern fires against.

**Activation heuristic** (all four conditions MUST hold):

1. **Occurrence count** — the constant appears in > 10 locations across the marketplace (measure via `architecture find --pattern {constant}` or `Grep` fallback). The threshold is conservative; lower counts collapse into a single sweep task safely.
2. **Code presence** — at least one `*.py` file is affected.
3. **Test presence** — at least one `test_*.py` file references the constant (separate from the code under test).
4. **Prose absence** — zero `*.md` files appear in the deliverable's `Affected files`, AND `architecture find --pattern {constant}` reports at least one `*.md` hit (i.e., prose copies exist but the planner missed them).

When all four conditions hold, **auto-decompose** the deliverable into the canonical five-task sequence below. The sub-pattern is generic: it applies equally to log-level vocabulary changes, command-name renames, SKILL.md cross-references after a skill split, JSON-key renames in example payloads, and standards file relocations.

**Canonical five-task sequence**:

| Order | Task | Profile | Affected files | Responsibility |
|-------|------|---------|----------------|----------------|
| TASK-N | **Code sweep** | `implementation` | `*.py` (production source) | Update every code reference to the new constant; preserve the old constant only behind compatibility shims if the change is non-breaking. |
| TASK-N+1 | **Test sweep** | `module_testing` | `test/**/test_*.py` (test source) | Update every test reference. Test changes follow code changes so the production sweep is testable independently. |
| TASK-N+2 | **Prose sweep** | `implementation` | `SKILL.md`, `standards/**/*.md`, `README.md`, any `agents/*.md` referencing the constant | Update every documentation reference. MUST be its own task — appending prose updates to the code sweep dilutes the diff and hides the prose surface from the planner's task accounting. |
| TASK-N+3 | **Example sweep** | `implementation` | Fenced code blocks in `*.md` files, JSON / TOON fixtures, golden-output files | Distinguish *synthetic-but-old-path-format* examples (the rename applies; update verbatim) from *synthetic-and-format-neutral* examples (the rename does NOT apply; leave untouched and add a note explaining why). The distinction is load-bearing because format-neutral examples often look like targets and would be incorrectly rewritten by a naive grep-replace. |
| TASK-N+4 | **Holistic verification** | `verification` | `build_verify`, `module-tests`, plus a **final grep gate** | After every prior task has executed, run a final `Grep` (or `architecture find`) for the old constant across the marketplace; the expected count is zero (modulo the synthetic-and-format-neutral exemptions captured in TASK-N+3). Non-zero counts fail the verification task and trigger the Step 11 triage loop. |

**Why prose-sweep is its own task** — the most common failure mode for cross-cutting renames is silently leaving prose behind: SKILL.md narrative paragraphs, standards/*.md decision tables, and README cross-references continue to reference the old constant after the code and tests are clean. Plugin-doctor and the test suite do not catch prose-level drift; the next reader (human or LLM) silently absorbs the stale documentation as if it were current. Making prose-sweep a separate task forces the planner to **enumerate** the prose surface (via `Grep --files-with-matches` over `*.md`) before the work begins, and the task agent has explicit affected files to sweep through, not a vague "and also update the docs" footer on the verify task.

**Why example-sweep precedes verification** — the same logic applies to example outputs: stale fenced TOON / JSON examples in `SKILL.md` and standards documents survive code+test+prose sweeps because they look like data, not code. The distinction between *synthetic-but-old-path-format* (update) and *synthetic-and-format-neutral* (leave) cannot be made by a generic grep-replace; it requires the task agent to read each fenced block and decide. Scheduling example-sweep before the final grep gate gives the agent a chance to surface and resolve every ambiguous case before the gate fires.

**Counter-indication (no split)**: the rename is **module-local** — all `<= 3` affected files live under a single skill directory AND no prose or example references exist outside that skill. In that case the deliverable collapses to a single `implementation` task that touches code + test + prose + examples in one diff, and the holistic verification rides on the standard Phase 5 verification steps. The split exists for cross-cutting work; over-applying it to surgical renames inflates the task count without improving correctness.

**Cross-reference**: this sub-pattern complements the **Integration Deliverable Narrative Constraint** above. The integration constraint prevents *new* enforcement-critical content from being inlined; the migration sub-pattern catches *existing* inlined content during renames so the drift surface is collapsed back to the central source.

## Default-Value / Constant / Enum-Member Change Sub-pattern

**Applies when**: a deliverable changes a **default value, a named constant, an enum member, or a threshold literal** that existing tests assert against. This is a sibling of the Path / Constant Migration Sub-pattern above, scoped to *value* changes rather than *name/path* renames: the production edit is small, but an unknown set of tests pin the old value, and a green local module run says nothing about test consumers elsewhere in the tree. The failure mode this sub-pattern fires against is a planner that schedules only the production change and lets the broken test assertions surface in CI, forcing a follow-up remediation commit.

**Three-step decomposition at trigger granularity** (the planner folds these into the deliverable's task touch set — it does NOT inline the enumeration procedure):

1. **Discovery** — grep the test tree for BOTH the symbol name AND the old literal value (a consumer can assert via the named symbol or via an inlined literal; searching only one misses half the consumers). Run across the whole test source root, not just the module under change.
2. **Enumeration** — classify each match as an *old-default assertion* (update to the new value) versus an *intentional explicit override* (a test that deliberately supplies the old value as an input — leave untouched). Add the update set to the deliverable's task touch set / `**Affected files:**`.
3. **Atomicity** — the production change and all forced test updates form a single atomic deliverable so verify passes on the first cut and every commit is independently buildable; never a production task followed by a separate "fix the tests" task.

**Cross-reference**: the substance of the discovery → classification → atomicity procedure — the two-pronged grep, the old-default-vs-override classification rule, and the single-atomic-change discipline — lives once in [`../dev-general-module-testing/standards/testing-methodology.md`](../dev-general-module-testing/standards/testing-methodology.md#enumerate-existing-test-consumers-before-changing-a-default--constant--enum-value) § "Enumerate Existing Test Consumers Before Changing a Default / Constant / Enum Value". This sub-pattern carries only the recognition trigger and the touch-set shape — **do NOT duplicate the enumeration procedure detail here**.

## Knowledge-Skill Body Expansion Sub-pattern

**Applies when**: a deliverable materially expands the **body of a knowledge or workflow skill** — adds a new section, rule, candidate-list entry, or sub-procedure to a `SKILL.md` or its `standards/*.md` — such that the skill's advertised scope grows. The frontmatter `description:` summarizes the skill's model; when the body grows but the description is not updated in lockstep, the description silently understates what the skill now covers, and the drift surfaces late at pre-submission self-review (the description-vs-body facet) rather than at authoring time.

**Pairing rule**: when a deliverable expands a knowledge/workflow skill body, the planner MUST fold the skill's frontmatter `description:` update into the SAME deliverable's touch set — never a body-expansion task followed by a separate "update the description" task. The body change and its description update form one atomic deliverable so the advertised scope stays in lockstep with the implemented scope at every commit. The trigger is the body expansion; the touch-set addition is the `description:` line of the same skill's frontmatter.

**Boundary**: this fires for *materially scope-growing* body edits — a new advertised capability, a new enumerated member, a new normative rule — not for prose polishing or a fix that leaves the advertised scope unchanged. When the description already accurately characterizes the post-expansion body, the pairing is a verify-and-confirm (no edit needed), not a forced rewrite.

## Security-Skill Attachment Sub-pattern

**Applies when**: a task's deliverable context indicates the code reads **untrusted inbound input** (HTTP requests, externally-sourced values crossing a trust boundary). The LLM optional-relevance match (Step 5 Resolution Logic) routinely misses security skills for these tasks — a "servlet reading an HTTP header" deliverable does not lexically resemble a security skill's description — so a domain that owns concrete security skills never attaches them. This sub-pattern removes that reliance on LLM judgment for the untrusted-inbound-input case by **deterministically forcing** the mapped security skill(s) into `task.skills`. It augments, and does not replace, the LLM optional matching — every other optional is still resolved by relevance as usual.

**Trigger predicate**: the trigger fires for a task when its deliverable context — the deliverable **title**, **description**, **`affected_files`** paths, and **change-per-file narrative** — contains any of the inbound-input signal keywords below.

**Inbound-input signal keywords** (the single normative source — this list MUST NOT be inline-copied elsewhere; reference this section by name):

- HTTP header(s) / request header
- URL / URI
- path segment / path parameter
- query parameter
- servlet
- request handler
- route / routing
- `X-`-prefixed header names
- untrusted input
- inbound

**Domain → security-skill mapping** (the single normative source — extensible by adding one row per domain as concrete per-domain security skills exist; NO speculative rows):

| Domain | Attach to `implementation`-profile task | Attach to paired `module_testing`-profile task |
|--------|------------------------------------------|------------------------------------------------|
| `java-cui` (`pm-dev-java-cui`) | `pm-dev-java-cui:cui-http` | `pm-dev-java-cui:cui-http-testing` |

**Mechanism (deterministic forced-inclusion)**: when the trigger predicate fires for a task whose domain has a mapping row, add the mapped skill(s) to `task.skills` regardless of the LLM optional-relevance verdict — the `implementation`-profile skill on the implementation task and the paired `module_testing`-profile skill on its paired test task. A task whose domain has no mapping row is unaffected (the trigger is a no-op for it). When the same skill is already present (declared as a default, or already matched as an optional), forced-inclusion is idempotent — do not duplicate the entry.

**Boundary respected**: this trigger operates at phase-4-plan **task-assembly** time by forcing the OPTIONAL into `task.skills`. It does NOT promote these skills to bundle-profile `defaults` — the defaults/optionals split is bundle-owned (`pm-dev-java-cui/extension.py`) and is not overridable from here. The forced-inclusion is per-task and does not mutate any bundle profile.

**Worked example** (the lesson's exact failure case): a deliverable titled "servlet reading an HTTP header" in the `java-cui` domain matches the keywords `servlet` and `HTTP header`; the `java-cui` mapping row therefore forces `pm-dev-java-cui:cui-http` onto the implementation task and `pm-dev-java-cui:cui-http-testing` onto its paired module_testing task — deterministically, even though neither skill's description lexically matched the deliverable.

## Skill Resolution Guidelines

Skills are resolved from architecture based on `module` + `profile`:

| Scenario | Behavior |
|----------|----------|
| Single profile | Query `architecture.module --module {module}`, extract `skills_by_profile.{profile}` |
| Multiple profiles | Create one task per profile, each with its own resolved skills |
| `verification` profile | Skip architecture query — no skills needed, use verification commands as steps |
| Module not in architecture | Error - module must exist in project architecture |
| Profile not in module | Log WARNING, set `task.skills = []`, record a Q-Gate triage finding with the architecture-enrichment recommendation in `--detail`, then continue. See Step 5 for the canonical procedure. |

## Error Handling

### Circular Dependencies

If deliverable dependencies form a cycle:
- Error: "Circular dependency detected: D1 -> D2 -> D1"
- Do NOT create tasks

### Module Not in Architecture

If `deliverable.module` is not found in architecture:
- Error: "Module '{module}' not found in architecture - run architecture discovery"
- Record as lesson learned

### Profile Not in Module

If a profile from `deliverable.profiles` is not in `module.skills_by_profile`, this is NOT plan-blocking. Follow Step 5's canonical procedure:

- Log WARNING: `(plan-marshall:phase-4-plan) Module {D.module} has empty skills_by_profile.{P} — task will have no domain skills. Run architecture enrichment to populate.`
- Set `task.skills = []` and continue creating the task.
- Record a Q-Gate triage finding via `python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate add --plan-id {plan_id} --phase 4-plan --source qgate --type triage --title {title} --detail {detail}`, with the architecture-enrichment recommendation inlined in `--detail`, so phase-5-execute and phase-6-finalize can surface the gap.

### Ambiguous Deliverable

If deliverable metadata incomplete:
- Generate task with defaults
- Add lesson-learned for future reference
- Note ambiguity in task description

## Integration

**Invoked by**: `plan-marshall:execution-context-{level}` (with `workflow: plan-marshall:phase-4-plan/SKILL.md`)

**Script Notations** (use EXACTLY as shown):
- `plan-marshall:manage-solution-outline:manage-solution-outline` - Read deliverables (list-deliverables, read)
- `plan-marshall:manage-architecture:architecture` - Query module skills (module --module {module}) and resolve commands (resolve --command {cmd} --module {module}). Uses `--audit-plan-id`, NOT `--plan-id`.
- `plan-marshall:manage-tasks:manage-tasks` - Create tasks atomically via `batch-add --tasks-file PATH` (preferred for multi-task creation in this phase, where `PATH` is staged via `manage-files write` to `.plan/local/plans/{plan_id}/work/tasks-batch.json`). Single ad-hoc adds may use the path-allocate flow (`prepare-add` → Write TOON → `commit-add`). Step 8 invokes `qgate-mechanical-checks` for the deterministic Q-Gate sweep.
- `plan-marshall:manage-files:manage-files` - Stage the batch JSON array (via `write --file work/tasks-batch.json`) so the payload never crosses the shell argument boundary.
- `plan-marshall:manage-findings:manage-findings` - Q-Gate findings (qgate add/query/resolve)
- `plan-marshall:manage-lessons:manage-lessons` - Record lessons on issues (add)
- `plan-marshall:manage-execution-manifest:manage-execution-manifest` - Compose / validate the per-plan execution manifest in Step 7b (compose, validate)
- `plan-marshall:manage-adr:manage-adr` - Read-only ADR scan (`scan --affects {module}`) consumed as a loop-invariant input at phase entry so task derivation aligns with established architectural decisions

**Consumed By**:
- `plan-marshall:phase-5-execute` skill - Reads tasks and executes them

### Phase-boundary metric bookkeeping

This skill does not invoke `manage-metrics` itself. The orchestrator
(`plan-marshall:plan-marshall` workflows) records the `4-plan → 5-execute`
boundary via the fused `manage-metrics phase-boundary` call — see
`marketplace/bundles/plan-marshall/skills/manage-metrics/SKILL.md` §
`phase-boundary` for the API.

