---
name: execute-task
description: Execute a single plan task with profile-based workflow selection (implementation, module_testing, verification)
user-invocable: false
---

# Execute-Task Skill

**Role**: Unified, domain-agnostic workflow skill for executing tasks during phase-5-execute. Handles all profiles: `implementation`, `module_testing`, and `verification`. Loaded in-context as a `Skill:` by the single `plan-marshall:phase-5-execute` envelope, once per task — this is leaf-legal in-context skill loading, NOT a per-task `Task:` subagent dispatch.

**Key Pattern**: The phase-5-execute envelope loads this skill in-context via `resolve-execute-task-skill --profile {profile}` (a `Skill:` load within the single envelope, not a subagent dispatch). The skill reads the task's profile and follows the appropriate workflow. Domain-specific knowledge comes from `task.skills` (loaded in-context alongside this skill).

**Base Contract**: This skill follows the execute-task skill contract defined in [execute-task-skills.md](../ref-workflow-architecture/standards/execute-task-skills.md) for input/output contracts, error handling, and script notations.

## Foundational Practices

```
Skill: plan-marshall:dev-agent-behavior-rules
```

## Enforcement

**Prohibited actions:**
- Never target file paths outside the active git worktree. The authoritative source for the worktree root is `manage-status get-worktree-path --plan-id {plan_id}` (resolved internally from the **Input Contract** below); every Edit/Write/Read tool call during task execution MUST resolve against the returned path.
- Never run git as a `cd {worktree_path} && git ...` compound. All git commands during task execution MUST use the `git -C {resolved_worktree_path} <subcommand>` form, where `{resolved_worktree_path}` is the value returned by `manage-status get-worktree-path --plan-id {plan_id}`.
- Never combine Bash commands with `&&`, `;`, `&`, or newlines in a single Bash tool call. Each Bash tool call MUST contain exactly ONE command. The compound form trips the host platform's permission UI and produces silent swallowing of intermediate exit codes — both are load-bearing failure modes during task execution.
- Never run polling loops (`for`/`while`/`until` loops, `$()` substitution, subshells, heredocs with `#` lines) inside a Bash tool call. Poll conditions belong in a `Monitor` tool call or are eliminated by running commands synchronously with an explicit timeout. Polling loops trip the host platform's security heuristics and are a structural signal that the verification step is wrong.
- Never use background-wait patterns (`command &`, then `wait` or `sleep` loops) to track a running step. Run verification commands synchronously via Bash with `timeout` set high enough; use `run_in_background: true` only when the task description explicitly requires a background process AND the step does not need to read the result.
- Never suppress errors in Bash tool calls (`2>/dev/null`, `|| true`, `|| :`, `-q` flags that hide exit codes). Every Bash tool call MUST surface its exit code cleanly so the verification loop can detect failures.

**Constraints:**
- Strictly comply with all rules from dev-agent-behavior-rules, especially tool usage and workflow step discipline
- Never bypass the manage-tasks next/finalize-step loop — if parallelization is needed, it must happen at the TASK level, not at the STEP level within a task
- A task in `implementation` or `module_testing` profile MUST NOT be marked `done` until the resolved canonical command (`quality-gate` or `verify` respectively) exits cleanly. Module-tests passing alone is necessary but not sufficient — mypy and ruff must also pass.
- Before every Bash tool call, emit an `[ATTEMPT]` work-log line that names the command being run. Use: `python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging work --plan-id {plan_id} --level INFO --message "[ATTEMPT] (plan-marshall:execute-task) {short description of command}"`. This provides an auditable trail when a Bash call hangs or produces unexpected output.

See `workflow-integration-git/standards/worktree-handling.md` for the worktree-specific application of this rule (never-edit-main-checkout invariant, `git -C` rule, dispatch header propagation).

---

## Common Workflow

### Input Contract

Every invocation of this skill MUST provide the following inputs:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier. Used by all manage-* script calls AND as the worktree-binding token: the skill resolves the active worktree internally via `plan-marshall:manage-status:manage-status get-worktree-path --plan-id {plan_id}`. The resolved path is the mandatory root for every Edit/Write/Read tool call during this task. When the plan runs against the main checkout (`metadata.use_worktree == false`), the resolved path is empty and operations target the main checkout directly. See `workflow-integration-git/standards/worktree-handling.md` for the canonical `--plan-id` two-state binding. |
| `task_number` | number | Yes | Numeric task id to execute |
| `worktree_path` | string | Deprecated | **Deprecated** — kept only for backward compatibility with callers that still pass an absolute path. New callers MUST forward only `plan_id`. When supplied, the value MUST agree with the path resolved from `plan_id`; treat any disagreement as fail-loud. |

Callers (the `phase-5-execute` envelope, itself dispatched as `execution-context-{level}` under the `phase-5-execute` role key, which then LOADS this skill in-context once per task — "dispatching this skill" here means in-context `Skill:` loading within that single envelope, never a per-task `Task:` subagent dispatch) MUST forward `plan_id` verbatim — no absolute-path forwarding is required. This skill runs as a leaf and issues no `Task:` subagent dispatches of its own; the path-free worktree binding is inherited via the pinned cwd (ADR-002), not echoed into any further dispatch.

All profiles share the steps below. Profile-specific steps are documented in each profile section.

### Step: Resolve Stale Targets

Check if a rename mapping exists and rewrite step targets before loading the task. This handles cases where earlier tasks renamed directories, making subsequent step targets stale.

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files exists \
  --plan-id {plan_id} --file work/rename_mapping.toon
```

If `exists: true`, the rename mapping has already been applied to task step targets at recording time (by the `rename-path` subcommand). No further action needed — proceed to Load Task Context. The mapping file serves as an audit trail of path changes during the plan.

### Step: Rewrite shadow-risk conftest targets

After resolving stale targets and BEFORE loading the task context, inspect every pending `step.target` on the incoming task. If a target matches the regex `test/.+/conftest\.py$` (a sibling `conftest.py` nested under a skill test directory) AND the full path is NOT in the allow-list below, rewrite the target in-place to the sibling `_fixtures.py` before execution.

**Allow-list** (these paths are the canonical top-level conftests and MUST NOT be rewritten):

- `test/conftest.py`
- `test/adapters/conftest.py`

**Rewrite rule**: Replace the trailing `conftest.py` segment with `_fixtures.py`, keeping the parent directory unchanged. For example, `test/plan-marshall/execute-task/conftest.py` becomes `test/plan-marshall/execute-task/_fixtures.py`.

**Decision log requirement**: For each rewrite, emit a decision.log entry via `plan-marshall:manage-logging:manage-logging` using the exact command below:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:execute-task) Deviation: rewrote {original_path} → {rewritten_path} (reason: sibling conftest.py would shadow top-level test/conftest.py)"
```

**Rationale**: A sibling `conftest.py` placed under `test/<bundle>/<skill>/` is auto-loaded by pytest and will shadow the top-level `test/conftest.py`, silently disabling shared fixtures and producing misleading green runs. The canonical convention is a sibling `_fixtures.py` imported explicitly where needed. See `plan-marshall:dev-general-module-testing` for the authoritative `_fixtures.py` convention and the reasoning behind the allow-list.

### Step: Load Task Context

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks read \
  --plan-id {plan_id} --task-number {task_number}
```

Extract key fields: `domain`, `profile`, `skills`, `description`, `steps`, `verification`, `depends_on`. Verify `profile` matches the expected profile for this execution.

### Step: Mark Step Complete

After completing each step:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step \
  --plan-id {plan_id} --task-number {task_number} --step {N} --outcome done
```

### Step: Run Verification

After all steps complete, run task verification using commands from `task.verification.commands`.

**Sub-step: Auto-inject `--plan-id` for Bucket B commands**

When the plan resolves to an active worktree, before executing any `task.verification.commands[N]`, route the command through the injection helper, passing `--plan-id {plan_id}` directly:

```bash
python3 .plan/execute-script.py plan-marshall:execute-task:inject_project_dir \
  run --command "{verification_command}" --plan-id {plan_id}
```

Injecting `--plan-id` (rather than `--project-dir {worktree_path}`) routes the executor's two-tier audit-log entry to the plan-scoped `.plan/local/plans/{plan_id}/logs/script-execution.log` — the log the `pre-commit-verify-freshness` gate reads — and lets the Bucket B script auto-resolve the worktree path itself via its `--plan-id`/`--project-dir` two-state contract. No separate `get-worktree-path` resolution is required.

Parse the TOON output from the script's stdout. Use the `rewritten_command` value as the command to execute. When `injected` is `true`, log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[VERIFY] (plan-marshall:execute-task) Auto-injected --plan-id for {notation} (routes build log to plan-scoped script-execution.log)"
```

The helper whitelists the eight Bucket B notations from `plan-marshall:tools-script-executor/standards/cwd-policy.md`; Bucket A `manage-*` notations and unknown notations pass through unchanged. The helper skips injection when the command already supplies `--plan-id` (no double injection) and when it already supplies an explicit `--project-dir` (a legacy override is respected untouched). See `scripts/inject_project_dir.py` for the authoritative whitelist.

**Safety net** (should not trigger in normal operation): If verification commands are missing, log a WARNING and resolve from architecture:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING --message "[VERIFY] (plan-marshall:execute-task) TASK-{N} missing verification — falling back to architecture resolve"

python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command {resolve_command} --module {module} \
  --audit-plan-id {plan_id}
```

Where `{resolve_command}` depends on profile: `implementation` → `quality-gate`, `module_testing` → `verify`. Verification profile uses commands from task steps directly.

### Step: Handle Verification Results

**If verification passes**: Mark task done via `manage-tasks update --status done`.

**If verification fails**:
1. Analyze error output and identify failing component
2. Fix the issue (see profile-specific scope below)
3. Re-run verification
4. Iterate until pass (max `verification_max_iterations` from config, default 5)

If still failing after max iterations: mark task as `blocked` and record details in work.log.

#### Scope-Deviation Escalation (per-task guard)

Before recording any per-task verification deviation that would soften a request-level hard requirement, this step MUST raise an `AskUserQuestion` per the canonical contract in [`../ref-workflow-architecture/standards/scope-deviation-escalation.md`](../ref-workflow-architecture/standards/scope-deviation-escalation.md). The standard is the single source of truth for the deviation taxonomy, the three-option AskUserQuestion shape (Hold / Accept-with-rationale / Split), and the prohibited "log-and-continue" anti-pattern.

**Detection**: A deviation softens a hard requirement when, mid-fix-iteration, the implementor concludes that satisfying the request as written is structurally riskier than estimated and the conservative response would be to keep both the old and new surfaces. Concrete signals: verification command reports a non-zero hit count against a "zero-hit grep" gate; tests pass against a legacy code path the deliverable was meant to delete; the implementor is about to add a transition hedge ("until X has fully landed", "callers may still see Y") to satisfy the test gate.

**Integration shape**: This guard mirrors the per-task `compatibility` AskUserQuestion already used by the `smart_and_ask` Compatibility Strategy in the implementation profile (Step: Compatibility Strategy above). Both guards are AskUserQuestion gates that fire BEFORE the deviation is committed; both pause the per-task fix loop until the user resolves the prompt; both persist the resolution to `decision.log`. The new guard adds one element the compatibility AskUserQuestion does not: when the user chooses "Accept with rationale", the rationale text is also surfaced in the PR body (the compatibility AskUserQuestion does not require this because compatibility decisions land in commit messages instead).

**Resolution**: On user resolution, follow the side-effect contract in `scope-deviation-escalation.md`. The `[VERIFY]`, `[STATUS]`, or `[OUTCOME]` work-log line confirming the user's chosen option IS allowed AFTER the AskUserQuestion has resolved — never as a stand-in for it. When the user chooses "Hold the line", the per-task fix loop resumes (do NOT mark the task `blocked` on the same iteration just because the user refused the softening).

### Step: Record Lessons

On issues or unexpected patterns, first run the canonical three-gate lesson-creation policy in [`../manage-lessons/standards/lesson-creation-policy.md`](../manage-lessons/standards/lesson-creation-policy.md) — Gate 1 (dedup), Gate 2 (active-plan check), Gate 3 (create). The two-step path-allocate flow below is Gate 3, reached only when Gates 1 and 2 both clear; when Gate 1 returns `merge_into` / `already_closed` or Gate 2 finds a covering active plan, extend the existing lesson or fold into the plan instead of allocating a new one. Do not restate the gate mechanics — follow the standard.

When the gates clear, use the two-step path-allocate flow:

1. Allocate a lesson file and capture the returned `path`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component "plan-marshall:execute-task" --category improvement \
  --title "{issue summary}"
```

2. Parse `path` from the output, then write the lesson body directly to that path via the Write tool. Markdown sections with `##` headings, code fences, and multiple paragraphs are all safe because the body never passes through a shell argument.

### Step: Return Results

Base output contract (profile-specific extensions noted in each section):

```toon
status: success | error
plan_id: {echo}
task_number: {echo}
execution_summary:
  steps_completed: N
  steps_total: M
  files_modified: [paths]
verification:
  passed: true | false
  command: "{cmd}"
next_action: task_complete | requires_attention
message: {error message if status=error}
```

---

## Profile: implementation

Production code creation and modification.

### Path Resolution

When the plan runs in an isolated worktree (resolvable via `plan-marshall:manage-status:manage-status get-worktree-path --plan-id {plan_id}` returning a non-empty path), every Edit/Write/Read tool call in this profile MUST resolve its file path against the returned path. If a subagent is dispatched from this profile, embed the path-free Worktree Header (`WORKTREE: --plan-id {plan_id}` plus the resolution-and-rationale block — see phase-5-execute § Dispatch Protocol) so the child propagates the constraint without leaking the absolute path. The auto-injection sub-step under Common Workflow → Step: Run Verification handles Bucket B forwarding structurally; Bucket A `manage-*` scripts remain cwd-agnostic. See `workflow-integration-git/standards/worktree-handling.md` for the canonical `--plan-id` two-state binding and `plan-marshall:tools-script-executor/standards/cwd-policy.md` for the Bucket A/B split.

### Compatibility Strategy

Before implementing, read the compatibility approach:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-2-refine get --field compatibility --audit-plan-id {plan_id}
```

**No fallback** — if field not found, fail with error and abort task.

Apply throughout all subsequent steps:

- **breaking**: Make changes directly. Remove old code, rename freely, no backward compatibility.
- **deprecation**: Keep old APIs/methods with `@Deprecated` markers. Add new code alongside old. Provide migration notes in commit messages.
- **smart_and_ask**: For each change that could break consumers, evaluate impact. If uncertain, ask user via AskUserQuestion before proceeding.

### Workflow

1. **Understand Context**: Read affected files (`step.target`) if they exist. Use `architecture files --module {module}` to enumerate the module's components and `architecture which-module --path P` / `architecture find --pattern P` for module-spanning lookups; fall back to `Grep` for content-level searches inside known files and `Glob` for sub-module path patterns or when the architecture verb returns elision. Apply domain knowledge from loaded skills. *How completely the in-radius items are read and how deeply their relations are traced is the task's declared* thoroughness *over its declared* scope *— see the two-dial coverage contract (thoroughness ladder T1–T5, scope ladder, grade-to-the-floor, coupling constraint `reject thoroughness ≥ T4 ∧ scope < component`) in [`dev-agent-behavior-rules/standards/thoroughness.md`](../dev-agent-behavior-rules/standards/thoroughness.md).*
2. **Plan Implementation**: For each step, determine changes needed, domain skill patterns to apply, modification order, and integration considerations.
3. **Implement Changes**: For each step — create new files with `Write`, modify existing files with `Edit`. Apply domain patterns and maintain existing code style.
4. **Mark Step Complete** (common step)
5. **Run Verification** — resolve command: `quality-gate` (static analysis — mypy + ruff on production sources; full tests belong to module_testing)
6. **Handle Verification Results** — fix scope: production code
7. **Record Lessons**, **Return Results**

### Error Handling

| Failure | Action |
|---------|--------|
| Conflicting changes | Analyze conflict, prefer preserving existing behavior, ask for clarification if needed |

---

## Profile: module_testing

Unit and module test creation.

### Path Resolution

When the plan runs in an isolated worktree (resolvable via `plan-marshall:manage-status:manage-status get-worktree-path --plan-id {plan_id}` returning a non-empty path), every Edit/Write/Read tool call in this profile MUST resolve its file path against the returned path. If a subagent is dispatched from this profile, embed the path-free Worktree Header (`WORKTREE: --plan-id {plan_id}` plus the resolution-and-rationale block — see phase-5-execute § Dispatch Protocol) so the child propagates the constraint without leaking the absolute path. The auto-injection sub-step under Common Workflow → Step: Run Verification handles Bucket B forwarding structurally; Bucket A `manage-*` scripts remain cwd-agnostic. See `workflow-integration-git/standards/worktree-handling.md` for the canonical `--plan-id` two-state binding and `plan-marshall:tools-script-executor/standards/cwd-policy.md` for the Bucket A/B split.

### Workflow

1. **Understand Implementation Context**: Use `architecture files --module {module}` to enumerate the module's components and `architecture find --pattern '*{name}*'` for module-spanning lookups; fall back to `Grep` for content-level searches inside known files and `Glob` for sub-module path patterns or when the architecture verb returns elision. Read and examine the matched implementation files. Identify testable elements: public methods, edge cases, error conditions, input validation, integration points.
2. **Plan Test Implementation**: For each step, determine test scenarios, test structure (unit vs integration per domain skills), assertions needed, setup/teardown requirements.
3. **Implement Tests**: For each step — create new test files with `Write`, modify existing test files with `Edit`. Follow the AAA pattern (Arrange-Act-Assert). Include positive and negative test cases with descriptive names.
4. **Mark Step Complete** (common step)
5. **Run Verification** — resolve command: `verify` (full verify pipeline for the module — quality-gate + module-tests)
6. **Handle Verification Results**:

   **Sub-step: Diff written test identifiers against the module-test log**

   After a green `module-tests` run that produced new test files during step 3 (Implement Tests):

   1. Collect pytest nodeids for every newly-written test file: `{rel_path}::{test_function}` for each test function. Write them to a temp file under `.plan/temp/` (one identifier per line).
   2. Run the diff assertion helper:

   ```bash
   python3 .plan/execute-script.py plan-marshall:execute-task:assert_test_identifiers \
     run --identifiers-file "{temp_identifiers_file}" --log "{module_test_log_path}"
   ```

   3. On `passed: true`: proceed to the standard "Mark task done" path.
   4. On `passed: false`: do NOT mark the task `done` — the run was silently incomplete. Log, mark the task `requires_attention`, and surface the mismatch in the return value:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level WARNING \
     --message "[VERIFY] (plan-marshall:execute-task) Diff assertion failed: {missing_count} written test identifiers absent from module-test log — {missing}"
   ```

   On test failure: determine if test logic is wrong or implementation has a bug. If test logic → fix test. If implementation bug → fix production code AND the test. Adapting production code to make tests pass is expected within this profile.
7. **Record Lessons**, **Return Results**

### Output Extensions

```toon
execution_summary:
  tests_written: N
  coverage_impact: {if available}
verification:
  tests_passed: N
  tests_failed: N
  diff_assertion:
    passed: true | false
    missing_count: N
    missing[]: [identifier, ...]
```

Note: `diff_assertion.passed: false` overrides `tests_passed` — a green test count does not imply a successful run if written identifiers are absent from the log.

### Error Handling

| Failure | Action |
|---------|--------|
| Implementation not found | Check if implementation task is in dependencies. If yes → mark task as blocked. If no → note in lessons learned |

---

## Profile: verification

Run verification commands without modifying files.

**Note**: The `verification` profile is distinct from the `verification` change-type (see [change-types.md](../ref-workflow-architecture/standards/change-types.md)). The profile determines HOW a task executes; the change-type describes WHY a request was made.

### Workflow

1. **Resolve Worktree Path**: Before executing any verification step, resolve the active worktree path from `plan_id`:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-status:manage-status get-worktree-path \
     --plan-id {plan_id}
   ```

   Capture the returned `worktree_path`. When `metadata.use_worktree == false` the returned path is empty — skip the auto-injection sub-step below and execute each raw `step.target` directly against the main checkout.

2. **Execute Verification Steps with `--plan-id` Auto-Injection**: Steps contain verification commands (not file paths). Execute sequentially. For each `step.target`:

   a. Route the command through the injection helper, passing `--plan-id {plan_id}`:

      ```bash
      python3 .plan/execute-script.py plan-marshall:execute-task:inject_project_dir \
        run --command "{step.target}" --plan-id {plan_id}
      ```

      Parse the `TOON` output. Use the `rewritten_command` value as the command to execute. When the worktree path resolved in Step 1 is empty (main-checkout flow), skip the helper and execute the raw `step.target`. Injecting `--plan-id` routes the executor's audit-log entry to the plan-scoped `script-execution.log` and lets the Bucket B script auto-resolve the worktree via its two-state contract.

   b. Execute the resulting command with a Bash timeout derived from the architecture-resolved canonical envelope. See `plan-marshall:dev-agent-behavior-rules` § "Bash: Timeout from architecture-resolved canonical command" for the authoritative rule: read `bash_timeout_seconds` and `execution_tier` from the resolved TOON, pass `timeout: bash_timeout_seconds * 1000` when `execution_tier=per_task`, and hand off to the orchestrator when `execution_tier=orchestrator`. The 600000ms floor still applies to ad-hoc invocations that do not flow through architecture resolve, and matches `CLAUDE.md` § Build Commands.

   c. On `injected: true`, emit the standard auto-injection work-log entry:

      ```bash
      python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
        work --plan-id {plan_id} --level INFO \
        --message "[VERIFY] (plan-marshall:execute-task) Auto-injected --plan-id for {notation} (routes build log to plan-scoped script-execution.log)"
      ```

   Check exit code and output of the executed command. This step mirrors the Common Workflow → Step: Run Verification sub-step; see that section for the authoritative whitelist of `Bucket B` notations, the no-inject pass-through rule for `Bucket A` `manage-*` notations, and the rationale for skipping injection when the command already supplies `--plan-id` or an explicit `--project-dir`.

3. **Mark Step Complete** (common step)
4. **Handle Failures**: This is a verification task — do NOT modify source files. Report failures with structured output for triage. If verification fails, mark task as `blocked`.
5. **Record Lessons** (on unexpected failures or environment issues), **Return Results**

No domain skills are needed for this profile.

### Output Extensions

```toon
execution_summary:
  commands_run: [commands]
verification:
  exit_code: {exit_code}
  stderr: "{truncated stderr, max 2000 chars}"
  findings:
    - type: {compile-error|test-failure|lint-issue}
      file: {file_path}
      line: {line_number}
      message: "{error message}"
```

On **success**: `next_action: task_complete`.
On **failure**: `status: error`, `next_action: requires_attention`, plus the extension fields. The `findings` array is best-effort: parse compiler errors, test failures, or lint output into structured entries. If parsing fails, include the raw `stderr`.

## Canonical invocations

The canonical argparse surface for the two entry-point scripts this skill registers: `inject_project_dir.py` and `assert_test_identifiers.py`. The plugin-doctor analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for the `manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### inject_project_dir — run

```bash
python3 .plan/execute-script.py plan-marshall:execute-task:inject_project_dir run \
  --command COMMAND --plan-id PLAN_ID
```

### assert_test_identifiers — run

```bash
python3 .plan/execute-script.py plan-marshall:execute-task:assert_test_identifiers run \
  --identifiers-file IDENTIFIERS_FILE --log LOG
```
