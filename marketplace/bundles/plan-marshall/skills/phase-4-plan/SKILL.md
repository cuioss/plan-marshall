---
name: phase-4-plan
description: Domain-agnostic task planning from deliverables with skill resolution and optimization
user-invocable: false
---

# Phase Plan Skill

**Role**: Domain-agnostic workflow skill for transforming solution outline deliverables into optimized, executable tasks. Loaded by `plan-marshall:phase-agent`.

**Key Pattern**: Reads deliverables with metadata and profiles list from `solution_outline.md`, creates one task per deliverable per profile (1:N mapping), resolves skills from architecture based on `module` + `profile`, creates tasks with explicit skill lists. **No aggregation** - each deliverable maps to exactly one task per profile.

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

When a task step target lives under a skill test directory (any path matching `test/**/`) and represents a test helper (shared fixtures, sys.path shims, or other non-test Python module), the filename MUST NOT be `conftest.py`. Rename the target to `_fixtures.py` (or another descriptive `_*.py` name that is clearly not a pytest collection file) during task creation — before composing the JSON array passed to `manage-tasks batch-add`. Only the two repository-wide `conftest.py` files listed in the allow-list below are permitted; any additional `conftest.py` under `test/{bundle}/{skill}/` changes pytest's global collection semantics for that bundle and causes hidden coupling or spurious collection failures.

**Allow-list** (MUST NOT be duplicated or added to by task steps):
- `test/conftest.py`
- `test/adapters/conftest.py`

If a deliverable's `Affected files` list names a disallowed `conftest.py`, phase-4-plan MUST rewrite the target to `_fixtures.py` (preserving the parent directory) before persisting the step. Cross-reference: phase-3-outline owns the outline-time rule and rationale in [outline-workflow-detail.md §10d "Test Helper File Naming"](../phase-3-outline/standards/outline-workflow-detail.md#10d-test-helper-file-naming); this subsection enforces the same constraint at task-creation time so that any late-surviving `conftest.py` target is corrected before tasks reach phase-5-execute.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |

## Output

```toon
status: success | error
plan_id: {echo}
summary:
  deliverables_processed: N
  tasks_created: M
  parallelizable_groups: N
tasks_created[M]: {number, title, deliverable, depends_on}
execution_order: {parallel groups}
message: {error message if status=error}
```

## Related

| Document | Purpose |
|----------|---------|
| [Task Creation Flow](references/task-creation-flow.md) | Visual overview of the 1:N task creation flow and output structure |

## Workflow

### Step 1: Check for Unresolved Q-Gate Findings

**Purpose**: On re-entry (after Q-Gate flagged issues), address unresolved findings before re-creating tasks.

### Query Unresolved Findings

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate query --plan-id {plan_id} --phase 4-plan --resolution pending
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

### Step 5: Create Tasks from Profiles (1:N Mapping)

For each deliverable, create one task per profile in its `profiles` list:

**Verification-Only Guard**: Before iterating profiles, check if the deliverable is verification-only (`change_type: verification` or empty `affected_files`). If so, override `D.profiles` to `[verification]` regardless of what the outline specified. Log a warning if the original profiles differed:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level WARN --message "(plan-marshall:phase-4-plan) Deliverable {N} is verification-only but had profiles [{original_profiles}] — overriding to [verification]"
```

```
For each deliverable D:
  IF D.change_type == verification OR D.affected_files is empty:
    IF D.profiles != [verification]:
      Log warning (see above)
    D.profiles = [verification]
  1. Query architecture: module --name {D.module}
  For each profile P in D.profiles:
    IF P = verification:
      2v. Skip skill resolution (no architecture query needed)
      3v. Create task with profile=verification, empty skills, verification commands as steps
      4v. Add depends on all other tasks from this deliverable
    ELSE:
      2. Extract skills: module.skills_by_profile.{P}
         IF skills_by_profile is empty/missing OR skills_by_profile.{P} is empty/missing:
           - Log WARN: "(plan-marshall:phase-4-plan) Module {D.module} has empty skills_by_profile.{P} — task will have no domain skills. Run architecture enrichment to populate."
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
  module --name {deliverable.module} \
  --trace-plan-id {plan_id}
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
records in a single atomic call via `manage-tasks batch-add`. The batch path
replaces the legacy per-task `prepare-add` → Write → `commit-add` loop with
one atomic transaction (all-or-nothing semantics — see
`marketplace/bundles/plan-marshall/skills/manage-tasks/standards/task-contract.md`
§ "Atomic Batch Insertion (`batch-add`)" for the JSON array schema and
failure modes).

The legacy three-step path-allocate flow remains available for ad-hoc
single-task additions (Q-Gate auto-loop, fix tasks dispatched outside this
phase) but MUST NOT be used here when more than one task is being created in
the same phase invocation.

### Description Anchoring Contract

To prevent compound-word mis-interpretation (e.g. `review-knowledge` being described as PR/CI review hygiene), phase-4-plan MUST anchor every `task.description` to literal tokens from the parent deliverable:

1. **Verbatim title quote (mitigation 1)**: The `description` value MUST begin with the exact deliverable title in single quotes, followed by a comma (or a period if an intent gloss follows per mitigation 2). Example for a deliverable titled `review-knowledge`:

   description: 'review-knowledge', which reviews prior-plan knowledge against this plan's changes.

   This forces compound-word tokens to survive description generation as a single unit.

2. **Intent gloss copy (mitigation 2)**: If the parent deliverable carries an `**Intent gloss:**` field (per manage-solution-outline/templates/deliverable-template.md), phase-4-plan MUST copy its value verbatim into the `description` after the title quote. If absent, phase-4-plan falls back to mitigation 1 alone.

   Combined example when both are present:

   description: 'review-knowledge'. Review knowledge captured by prior plans (lessons-learned and memories) against this plan's changes. <additional task-specific detail>.

3. **Structural-token preservation (mitigation 3)**: Any structural token appearing in the parent deliverable body MUST be preserved verbatim in `task.description`. Structural tokens are:

   - **Numeric literals** from the deliverable body (e.g. `990`, `1000`, `85`, `3.14`) — including order values, priority values, port numbers, thresholds, and any other numeric constants.
   - **Flag-style tokens** (e.g. `--plan-id`, `--name`, `order:`, `priority:`) — including CLI flags, TOON/YAML field prefixes, and option names.
   - **Quoted identifiers** surfaced in Metadata, Intent gloss, Profiles, Affected files, Change per file, Verification, or Success Criteria — including backticked paths, single-quoted names, and double-quoted strings.

   Paraphrasing, reformatting, or "regularizing" these tokens into sequential multiples, rounded values, or stylistically neater forms is explicitly prohibited. In particular, rewriting `order: 990 / 1000` as `order: 90 / 100` to make the numbers "look nicer" — or collapsing `990`→`99`, `1000`→`100`, `85`→`80`, etc. — is forbidden, because the numeric values are load-bearing data from the source outline, not decorative placeholders.

   **Worked example** (from source lesson `2026-04-17-20-001`): A deliverable body specifies task-ordering values `order: 990 / 1000` in its Change per file section. The canonical violation is a task description that paraphrases these as `order: 90 / 100` — a "regularization" from the four-digit spacing (`990`/`1000`) down to a two-digit spacing (`90`/`100`). The description MUST instead carry the literal tokens `order: 990 / 1000` verbatim. This same rule applies whenever the outline supplies specific numeric or flag-shaped data: copy the tokens exactly as written, do not "improve" them.

**CRITICAL — Shell Metacharacter Sanitization**: Before writing values into the TOON task file, strip all markdown backticks (`` ` ``) from title, description, criteria, and step values. Backticks are shell metacharacters (command substitution) that trigger permission prompts if they later reach a shell. They are markdown formatting artifacts not needed in TOON task data. Replace `` `foo` `` with `foo` (plain text).

```bash
# Compose every task record for this phase invocation into one JSON array,
# then persist them atomically. Each entry mirrors the TOON task schema:
#   {
#     "title": "{task title}",
#     "deliverable": {deliverable_number},
#     "domain": "{domain}",
#     "profile": "{profile}",
#     "description": "{description}",
#     "steps": ["{file1}", "{file2}"],
#     "depends_on": [],            # or ["TASK-1", ...]
#     "skills": ["{bundle:skill}", ...],
#     "verification": {
#       "commands": ["{cmd1}"],
#       "criteria": "{criteria}"
#     }
#   }
#
# Sequential numbering is assigned in array order at call time. On any
# validation failure no TASK-NNN.json is written.
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  batch-add --plan-id {plan_id} --tasks-json '{json_array}'
```

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
>     - python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "module-tests plan-marshall"
>   criteria: module-tests plan-marshall succeeds
> ```
>
> **DON'T** (outer-quoted wrapper with escaped inner quotes — this trips the parser):
> ```
> verification:
>   commands:
>     - "python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args \"module-tests plan-marshall\""
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

**Verification**: Copy the deliverable's Verification block verbatim into the task:

- `verification.commands` = deliverable's `Verification: Command` value(s)
- `verification.criteria` = deliverable's `Verification: Criteria` value

The outline phase is the single source of truth for verification commands — this phase performs ZERO resolution. If a deliverable arrives without a Verification Command, this is an outline defect. Record a Q-Gate finding in Step 9 instead of resolving it here:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase 4-plan --source qgate \
  --type triage --title "Missing verification: deliverable {N} has no Verification Command" \
  --detail "Outline must provide Verification Command and Criteria for every deliverable"
```

### Step 7: Create Holistic Verification Tasks

After creating per-deliverable tasks, create plan-level verification tasks that depend on ALL previously created tasks.

**Module resolution for holistic tasks**: Holistic tasks are plan-level, not deliverable-level. Omit `--name` from `architecture resolve` to use the root module, which runs commands across all modules. Do NOT try to list or enumerate modules — the root module default handles cross-module verification.

**Read verification steps** (NOTE: `manage-config plan` is ONLY for phase configs — for architecture queries use `manage-architecture:architecture`):
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get --field steps --trace-plan-id {plan_id}
```

Iterate over the `steps` list. For each step, create a holistic verification task based on the step type:

**Built-in steps** (no colon in name):
- `quality_check` → Resolve via `architecture resolve --command quality-gate` (no `--name` — uses root module for cross-module check)
- `build_verify` → Resolve via `architecture resolve --command module-tests` (no `--name` — uses root module for cross-module check)

**Extension steps** (contain colon, e.g., `my-bundle:my-verify-step`):
- Use the step name directly as the step target (do NOT resolve via architecture)

All holistic verification tasks share: `profile: verification`, `deliverable: 0`, `origin: holistic`, `depends_on: [ALL non-holistic tasks]`

**Log each holistic task creation**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[ARTIFACT] (plan-marshall:phase-4-plan) Created holistic verification TASK-{N}: {title}"
```

### Step 8: Determine Execution Order

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

### Step 8b: Compose Execution Manifest

**Purpose**: Emit the per-plan execution manifest so that Phase 5 and Phase 6 can dispatch their steps as dumb manifest executors. The manifest is the single source of truth for which Phase 5 verification steps and Phase 6 finalize steps fire for this plan — per-doc skip logic in their standards is removed in favor of this single artifact.

This step runs after Step 8 (execution order) and before Step 9 (Q-Gate). It MUST run on every successful plan-phase invocation; the manifest is required by phase-5-execute on entry.

**Inputs**:
- `change_type` — read from solution outline metadata (use the first deliverable's `change_type` when the outline has more than one; the plan-level summary in `solution_outline.md` Summary block also surfaces it).
- `track` — read from `manage-references get --field track` (`simple` or `complex`).
- `scope_estimate` — read from `manage-references get --field scope_estimate` (deliverables 2 / 3 wire this in earlier in the plan lifecycle).
- `recipe_key` — read from `manage-status read` `plan_source` metadata (when sourced from a recipe).
- `affected_files_count` — `manage-references get --field affected_files`, count entries.
- `phase-5-steps` candidate — `manage-config plan phase-5-execute get --field steps` value, comma-joined.
- `phase-6-steps` candidate — `manage-config plan phase-6-finalize get --field steps` value, comma-joined.
- `commit_strategy` — read from `manage-config plan phase-5-execute get --field commit_strategy`. One of `per_plan|per_deliverable|none`. Forwarded to `compose --commit-strategy` so the manifest's `commit_strategy_none` pre-filter can omit `commit-push` when the value is `none`. Omit the flag when the field is unset; the composer defaults to `per_plan`.

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
  [--commit-strategy {commit_strategy}]
```

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

**Error path**: If `validate` returns `status: error` (`error: invalid_manifest`), the phase MUST fail loudly — do NOT proceed to Q-Gate or Step 11 transition. Surface the error message in the phase return TOON and abort:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR \
  --message "[STATUS] (plan-marshall:phase-4-plan) Manifest validation failed — aborting phase. {validation_message}"
```

The composer's `decision.log` entry (one per applied rule) provides the audit trail; the manifest itself stays lean and diffable. The seven-row matrix is documented in `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md`.

### Step 9: Q-Gate Verification Checks

**Purpose**: Verify created tasks meet quality standards.

### Run Q-Gate Checks

After tasks are created, verify:

1. **Deliverable Coverage**: Every deliverable has >= 1 task? No orphan tasks without a deliverable?
2. **Skill Resolution Valid**: Every task has skills resolved? No "skill not found" entries?
3. **Dependency Graph Acyclic**: No circular dependencies between tasks?
4. **Steps Valid**: Every step is a concrete file path (not glob/ellipsis)? Files exist on disk?

### Record Findings

For each issue found:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase 4-plan --source qgate \
  --type triage --title "{check}: {issue_title}" \
  --detail "{detailed_reason}"
```

### Log Q-Gate Result

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-4-plan:qgate) Verification: {passed_count} passed, {flagged_count} flagged"
```

### Keyword-drift check (warn-only)

After all tasks are created, scan each `task.description` for planning-domain keywords that the author may have substituted for the deliverable's actual semantics. For each task:

1. Build a deny-list of planning-domain keywords: `PR review`, `CI`, `merge comments`, `pipeline`, `automated review`, `build check`, `review comments`.
2. Build an outline-text haystack: concatenate the parent deliverable's Title, Metadata, Intent gloss, Profiles, Affected files, Change per file, Verification, and Success Criteria sections as plain text.
3. For each keyword present in the `description` but ABSENT from the haystack, emit a warning Q-Gate finding:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase 4-plan --source qgate \
  --type warning \
  --title "Description drift: TASK-{N} uses '{keyword}' not present in deliverable outline" \
  --detail "{description excerpt}; deliverable {deliverable_number} outline does not mention '{keyword}'"
```

**Rigor**: this check is warn-only. Phase-4-plan MUST proceed to completion regardless of warnings — the operator reviews findings at the phase-4 gate.

### Structural-token-drift check (warn-only)

After all tasks are created, scan each `task.description` for structural tokens that are not present in the parent deliverable body. Structural tokens are numeric literals, flag-style tokens, and quoted identifiers — the same three categories defined in Step 6 mitigation 3 ("Structural-token preservation"). This check catches silent regularization of structural data (e.g. `990 / 1000` rewritten as `90 / 100`) that the Keyword-drift check does not cover.

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

**Rigor**: this check is warn-only. Phase-4-plan MUST proceed to completion regardless of warnings — the operator reviews findings at the phase-4 gate.

### Step 10: Record Issues as Lessons

On ambiguous deliverable or planning issues, follow the two-step path-allocate flow:

1. Allocate a lesson file and capture the returned `path`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component "plan-marshall:phase-4-plan" \
  --category improvement \
  --title "{issue summary}"
```

2. Parse `path` from the output and write the lesson body (context + resolution approach, with `##` sections as needed) directly to that path via the Write tool. This is the single supported API — there is no `--detail` inline form.

**Valid categories**: `bug`, `improvement`, `anti-pattern`

### Step 11: Transition Phase and Return Results

**Transition phase**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status transition \
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
```

## Skill Resolution Guidelines

Skills are resolved from architecture based on `module` + `profile`:

| Scenario | Behavior |
|----------|----------|
| Single profile | Query `architecture.module --name {module}`, extract `skills_by_profile.{profile}` |
| Multiple profiles | Create one task per profile, each with its own resolved skills |
| `verification` profile | Skip architecture query — no skills needed, use verification commands as steps |
| Module not in architecture | Error - module must exist in project architecture |
| Profile not in module | Log WARN, set `task.skills = []`, record a Q-Gate triage finding with the architecture-enrichment recommendation in `--detail`, then continue. See Step 5 for the canonical procedure. |

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

- Log WARN: `(plan-marshall:phase-4-plan) Module {D.module} has empty skills_by_profile.{P} — task will have no domain skills. Run architecture enrichment to populate.`
- Set `task.skills = []` and continue creating the task.
- Record a Q-Gate triage finding via `python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate add --plan-id {plan_id} --phase 4-plan --source qgate --type triage`, with the architecture-enrichment recommendation inlined in `--detail`, so phase-5-execute and phase-6-finalize can surface the gap.

### Ambiguous Deliverable

If deliverable metadata incomplete:
- Generate task with defaults
- Add lesson-learned for future reference
- Note ambiguity in task description

## Integration

**Invoked by**: `plan-marshall:phase-agent` (with skill=plan-marshall:phase-4-plan)

**Script Notations** (use EXACTLY as shown):
- `plan-marshall:manage-solution-outline:manage-solution-outline` - Read deliverables (list-deliverables, read)
- `plan-marshall:manage-architecture:architecture` - Query module skills (module --name {module}) and resolve commands (resolve --command {cmd} --name {module}). Uses `--trace-plan-id`, NOT `--plan-id`.
- `plan-marshall:manage-tasks:manage-tasks` - Create tasks atomically via `batch-add` (preferred for multi-task creation in this phase). Single ad-hoc adds may use the path-allocate flow (`prepare-add` → Write TOON → `commit-add`).
- `plan-marshall:manage-findings:manage-findings` - Q-Gate findings (qgate add/query/resolve)
- `plan-marshall:manage-lessons:manage-lessons` - Record lessons on issues (add)
- `plan-marshall:manage-execution-manifest:manage-execution-manifest` - Compose / validate the per-plan execution manifest in Step 8b (compose, validate)

**Consumed By**:
- `plan-marshall:phase-5-execute` skill - Reads tasks and executes them

### Phase-boundary metric bookkeeping

This skill does not invoke `manage-metrics` itself. The orchestrator
(`plan-marshall:plan-marshall` workflows) records the `4-plan → 5-execute`
boundary via the fused `manage-metrics phase-boundary` call — see
`marketplace/bundles/plan-marshall/skills/manage-metrics/SKILL.md` §
`phase-boundary` for the API.
