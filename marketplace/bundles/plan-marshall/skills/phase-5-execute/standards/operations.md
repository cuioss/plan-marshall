# Delegation Operations

Reference for executing common checklist items. The executor uses these patterns when encountering specific checklist items.

**Manifest-driven execution**: This document does not encode any skip-conditional language for verification steps. Whether `quality-gate`, `module-tests`, or `coverage` fires at the end of Phase 5 is decided by the per-plan execution manifest (`manage-execution-manifest read`) Step 2 of `SKILL.md` consumes — the dispatch templates here are unconditional and only run when the manifest's `phase_5.verification_steps` list includes the corresponding step name.

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../../tools-script-executor/standards/exit-code-convention.md); it is not restated here.

## Worktree Header Protocol (Applies to ALL Dispatch Patterns)

When the plan runs in an isolated worktree, every `Task:` dispatch (and every other subagent dispatch that accepts a free-form prompt) below MUST have its `prompt:` block BEGIN with the following header, with `{worktree_path}` substituted by the active worktree absolute path surfaced by phase-5-execute's `[STATUS] Active worktree` work-log line:

```text
WORKTREE: {worktree_path}
All Edit/Write/Read tool calls MUST target paths under this worktree. Raw tool invocations (git, mvn, npm, uv, pytest, ruff, …) MUST use the tool's native cwd flag against this path — `git -C`, `mvn -f`, `npm --prefix`, `uv --directory`, `pytest --rootdir`, `ruff <path>` (positional). The compound `cd <path> && <tool>` form is forbidden for every tool, not just git — it violates Bash one-command-per-call. File contents MUST be written via the Write/Edit tools, never via Bash redirects (`echo >>`, `cat <<EOF >`, `python3 -c "open(...).write(...)"`, `printf >`). See `persona-plan-marshall-agent/standards/tool-usage-patterns.md` for the full rule and the native-cwd-flag table. NEVER edit the main checkout.
```

Omit the header only when no worktree is active (plan runs against the main checkout). The templates below show the header inline for every dispatch example.

## Step-owned dispatch bodies

Each dispatch pattern below declares `requires_prompt_fields` — the prompt-body fields the step owns. The generic dispatch envelope owns routing only (`subagent_type` / `Skill` / `SlashCommand` / script notation plus the `plan_id` input contract). Whenever a step declares a step-owned body, generic dispatch defers to that body and only supplies the generic envelope otherwise: it MUST NOT re-render, paraphrase, or default any field listed in `requires_prompt_fields`.

| Dispatch pattern | `requires_prompt_fields` (step-owned) |
|------------------|----------------------------------------|
| Maven Build (`Task:`) | `WORKTREE` header, build command (`mvn clean verify`), report shape (results plus coverage) |
| npm Build (`Task:`) | `WORKTREE` header, build command (`npm build and test`), report shape (results plus coverage) |
| JavaScript Implementation (`Task:`) | `WORKTREE` header, task identity (`Execute Task {N}: {name}`), `Goal`, `Criteria` |
| Commit (`Skill:`) | `operation: commit`, `message` (conventional commit derived from task title), `push` |
| Create PR (script) | `--plan-id`, `--title` (prepared via `pr prepare-body`) |
| Plugin Doctor (`SlashCommand:`) | `{type}={name}` selector — marketplace repository only |
| JSDoc Check (script) | `npm run docs:check` target |
| Work Log Entry (script) | `--plan-id`, `--level`, `--message` |
| Lesson Learned (script) | lesson trigger (unexpected behavior only) plus the three-gate creation policy input |

Author/verifier choreography per step-owned body:

- **Author — step body (pattern owner).** The step template authors every field in its `requires_prompt_fields`: it states the literal command, the prompt sentences, and the report shape the receiving side must produce. The generic dispatcher never authors these fields.
- **Author — generic dispatcher (envelope owner).** The dispatcher authors routing only: the `Task:` / `Skill:` / `SlashCommand:` / script selector and the `plan_id` input contract value. It carries the step-owned body verbatim into the dispatch prompt.
- **Verifier — pre-flight (dispatching side).** Before dispatch, the executor verifies that every field in the pattern's `requires_prompt_fields` is present and non-empty in the rendered prompt body. A missing field aborts the dispatch — the dispatcher MUST NOT fill it from the generic template.
- **Verifier — receiving side.** The receiving skill or agent verifies the rendered body against its own input contract and refuses a paraphrased or partially defaulted body.

Stale envelope references are step-owned-body defects, not envelope defects: when a template still names a removed envelope field or omits a current `requires_prompt_fields` entry, the fix lands in that pattern's template row above, never as a generic-envelope override.

## Verification-feedback loop-back returns (`loop_back_target`)

Every verification-feedback `loop_back` return MUST carry `loop_back_target`, and every `success` return MUST omit it. The computation matches `plan-marshall/workflow/triage.md` Step 7 verbatim in behaviour:

- Set `loop_back_target = "5-execute"` when `fix_tasks_created > 0` OR `overflow_deferred > 0` — fix tasks are first-class work items that flow through the execute pipeline, and deferred findings need the next dispatch's fresh budget, which only re-entry through the execute pipeline guarantees.
- Otherwise set `loop_back_target = "6-finalize"` — all loop-back-needing dispositions are SUPPRESS, narrow-rationale ACCEPT, or single-annotation FIX with no fix-task allocation and no overflow, so the calling step replays in place with no need to re-enter the execute pipeline.

Callers forward the field verbatim to `mark-step-done --outcome loop_back --loop-back-target {value}`; the phase-6-finalize dispatcher routes between full-phase rollback (`5-execute`) and inline replay (`6-finalize`) off the persisted value.

## Session-Start Tree Check (Before the First Repo Edit)

Before the first repo edit in a session, verify the working tree matches the plan's admitted location: the worktree path when `use_worktree=true` and the flag is materialized, else the main checkout. Run `git -C {tree} status --porcelain` against the admitted tree and refuse to edit on any unexpected dirt — stash, re-anchor, or re-run the hand-off admission gate first (see `plan-marshall:plan-marshall/workflow/planning.md` § Action: init → "Hand-off admission gate"). The check closes the session-restart hole where a re-pinned cwd lands on main with worktree state expected. Residual: no script gate binds a free agent's Edit tool — this check is the detection half of the dispatch-refusal pair (`inject_project_dir.guarded_inject` is the refusal half).

## Build Operations

### Maven Build
**Trigger**: "Run build", "maven", "mvn verify"

```text
Task:
  subagent_type: pm-dev-builder:maven-builder
  prompt: |
    WORKTREE: {worktree_path}
    All Edit/Write/Read tool calls MUST target paths under this worktree. Raw tool invocations (git, mvn, npm, uv, pytest, ruff, …) MUST use the tool's native cwd flag against this path. The `cd <path> && <tool>` form is forbidden. File contents MUST be written via Write/Edit, never via Bash redirects. See persona-plan-marshall-agent/standards/tool-usage-patterns.md. NEVER edit the main checkout.

    Execute mvn clean verify, report results and coverage
```

### npm Build
**Trigger**: "npm build", "npm test"

```text
Task:
  subagent_type: pm-dev-builder:npm-builder
  prompt: |
    WORKTREE: {worktree_path}
    All Edit/Write/Read tool calls MUST target paths under this worktree. Raw tool invocations (git, mvn, npm, uv, pytest, ruff, …) MUST use the tool's native cwd flag against this path. The `cd <path> && <tool>` form is forbidden. File contents MUST be written via Write/Edit, never via Bash redirects. See persona-plan-marshall-agent/standards/tool-usage-patterns.md. NEVER edit the main checkout.

    Execute npm build and test, report results and coverage
```

## Quality Operations

### JavaScript Lint
**Trigger**: "lint", "eslint" (JavaScript context)

```bash
npm run lint
```

### Sonar Check
**Trigger**: "sonar", "quality gate"

Dispatch PR-scoped new-code issues through the Sonar provider — the pre-filter (`sonar-rules.json`) applies before one `sonar-issue` finding is filed per surviving issue:

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-sonar:sonar fetch_findings \
  --plan-id {plan_id} --project {project_key} --pr {pr_number}
```

## Implementation Operations

### JavaScript Implementation
**Trigger**: "implement" (JavaScript context)

```text
Task:
  subagent_type: pm-dev-builder:npm-builder
  prompt: |
    WORKTREE: {worktree_path}
    All Edit/Write/Read tool calls MUST target paths under this worktree. Raw tool invocations (git, mvn, npm, uv, pytest, ruff, …) MUST use the tool's native cwd flag against this path. The `cd <path> && <tool>` form is forbidden. File contents MUST be written via Write/Edit, never via Bash redirects. See persona-plan-marshall-agent/standards/tool-usage-patterns.md. NEVER edit the main checkout.

    Execute Task {N}: {name}, Goal: {goal}, Criteria: {list}
```

### Post-dispatch: Persist subagent usage to accumulator

**Applies to**: every Task / `execute-task` Skill dispatch above that returns a `<usage>` tag (i.e., every concrete task agent dispatched from the phase-5-execute task loop). Inline-only tasks skip this call.

After parsing the agent's returned `<usage>...</usage>` block, persist the totals to the on-disk per-phase accumulator so the orchestrator's end-of-phase `manage-metrics phase-boundary` call can read them even when the model context has been compacted between dispatches. The parsed `<usage>` token key is canonically `total_tokens`, matching the `--total-tokens` flag below:

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics accumulate-agent-usage \
  --plan-id {plan_id} --phase 5-execute \
  --total-tokens {total_tokens} --tool-uses {tool_uses} --duration-ms {duration_ms}
```

This call is documented as **Step 8b** in `phase-5-execute/SKILL.md`. The accumulator file lives at `.plan/plans/{plan_id}/work/metrics-accumulator-5-execute.toon` — see `manage-metrics/standards/data-format.md` § "Per-Phase Subagent Accumulator" for the schema.

## Git Operations

### Commit
**Trigger**: "commit", "create commit"

```text
Skill: plan-marshall:workflow-integration-git
operation: commit
message: {from task title}
push: true
```

### Create PR
**Trigger**: "create PR", "pull request"

PR creation is plan-bound and runs through the CI abstraction. The body is prepared via `pr prepare-body` (writes the structured summary/changes), then `pr create` opens the PR against the plan's branch:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create \
  --plan-id {plan_id} --title "{task-title}"
```

## Plugin Operations

> **This whole section applies to the plan-marshall marketplace repository only.** `/plugin-doctor` is a marketplace-authoring command that exists where the marketplace bundles are authored; it is not installed into a consumer project, and a consumer is not expected to carry an equivalent. In any other project this section names no available operation — do not route a delegation to it, and do not record a deliverable as verified by it. Verify markdown components there through the project's own gates (the architecture-resolved `quality-gate` when the deliverable also touches buildable sources) or by declaring the verification manual.

### Plugin Doctor
**Trigger**: "/plugin-doctor", "verify component" — *marketplace repository only, per the note above*

```text
SlashCommand: /plugin-doctor {type}={name}
```

## Documentation Operations

### JSDoc Check
**Trigger**: "jsdoc", "documentation check" (JavaScript)

```bash
npm run docs:check
```

## Logging Operations

### Work Log Entry
**Trigger**: "**Log**:", "Record completion"

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "{what was done}: {outcome}"
```

### Lesson Learned
**Trigger**: "**Learn**:", "Capture lesson"

Only execute if unexpected behavior occurred. Follow `plan-marshall:script-runner` Error Handling workflow.
