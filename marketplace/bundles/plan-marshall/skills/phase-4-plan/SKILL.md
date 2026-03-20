---
name: phase-4-plan
description: Domain-agnostic task planning from deliverables with skill resolution and optimization
user-invocable: false
---

# Phase Plan Skill

**Role**: Domain-agnostic workflow skill for transforming solution outline deliverables into optimized, executable tasks. Loaded by `plan-marshall:phase-agent`.

**Key Pattern**: Reads deliverables with metadata and profiles list from `solution_outline.md`, creates one task per deliverable per profile (1:N mapping), resolves skills from architecture based on `module` + `profile`, creates tasks with explicit skill lists. **No aggregation** - each deliverable maps to exactly one task per profile.

## Contract Compliance

**MANDATORY**: All tasks MUST follow the structure defined in the central contracts:

| Contract | Location | Purpose |
|----------|----------|---------|
| Task Contract | `plan-marshall:manage-tasks/standards/task-contract.md` | Required task structure and optimization workflow |

**CRITICAL - Steps Field**:
- The `steps` field MUST contain file paths from the deliverable's `Affected files` section
- Steps must NOT be descriptive text (e.g., "Update AuthController.java" is INVALID)
- Validation rejects tasks with non-file-path steps
- Exception: `verification` profile tasks use verification commands as steps (file-path validation is skipped)

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

## Related Documents

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
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-4-plan:qgate) Finding {hash_id} [{source}]: taken_into_account — {resolution_detail}"
```

Then continue with normal Steps 3..11 (phase re-runs with corrections applied).

If no unresolved findings: Continue with normal Steps 3..11 (first entry).

### Step 2: Log Phase Start

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
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

```
For each deliverable D:
  1. Query architecture: module --name {D.module}
  For each profile P in D.profiles:
    IF P = verification:
      2v. Skip skill resolution (no architecture query needed)
      3v. Create task with profile=verification, empty skills, verification commands as steps
      4v. Add depends on all other tasks from this deliverable
    ELSE:
      2. Extract skills: module.skills_by_profile.{P}
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
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:phase-4-plan) Resolved skills for TASK-{N} from {module}.{profile}: defaults=[{defaults}] optionals_selected=[{optionals}]"
```

### Step 6: Create Tasks

For each deliverable, create tasks using `--content` with `\n`-encoded TOON (one task per profile):

**CRITICAL — Shell Metacharacter Sanitization**: Before interpolating values into the `--content` string, strip all markdown backticks (`` ` ``) from title, description, criteria, and step values. Backticks are shell metacharacters (command substitution) that trigger permission prompts. They are markdown formatting artifacts not needed in TOON task data. Replace `` `foo` `` with `foo` (plain text).

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks add \
  --plan-id {plan_id} \
  --content "title: {task title}\ndeliverable: {deliverable_number}\ndomain: {domain}\nprofile: {profile}\ndescription: {description}\nsteps:\n  - {file1}\n  - {file2}\ndepends_on: {TASK-N | none}\nskills:\n  - {skill1}\n  - {skill2}\nverification:\n  commands:\n    - {cmd1}\n  criteria: {criteria}"
```

**MANDATORY - Log each task creation**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
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

**Read verification config** (NOTE: `manage-config plan` is ONLY for phase configs — for architecture queries use `manage-architecture:architecture`):
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get --trace-plan-id {plan_id}
```

**1. Quality check task** (if `verification_1_quality_check` is true):
- Resolve via `architecture resolve --command quality-gate` (no `--name` — uses root module for cross-module check)
- Create task with: `profile: verification`, `deliverable: 0`, `origin: holistic`
- `depends_on: [ALL non-holistic tasks]`

**2. Domain-specific verification tasks** (from `verification_domain_steps` config — see [extension-contract.md](../../../plan-marshall/skills/extension-api/standards/extension-contract.md)):
- For each enabled domain step in config → create a verification task
- Steps contain agent references from domain extensions (use the step value directly as the step target, do NOT resolve via architecture)
- `profile: verification`, `deliverable: 0`, `origin: holistic`
- `depends_on: [ALL non-holistic tasks]`

**3. Full test suite task** (if `verification_2_build_verify` is true):
- Resolve via `architecture resolve --command module-tests` (no `--name` — uses root module for cross-module check)
- Create task with: `profile: verification`, `deliverable: 0`, `origin: holistic`
- `depends_on: [ALL non-holistic tasks]`

**Log each holistic task creation**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
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
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-4-plan:qgate) Verification: {passed_count} passed, {flagged_count} flagged"
```

### Step 10: Record Issues as Lessons

On ambiguous deliverable or planning issues:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lesson add \
  --component "plan-marshall:phase-4-plan" \
  --category improvement \
  --title "{issue summary}" \
  --detail "{context and resolution approach}"
```

**Valid categories**: `bug`, `improvement`, `anti-pattern`

### Step 11: Transition Phase and Return Results

**Transition phase**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lifecycle:manage-lifecycle transition \
  --plan-id {plan_id} \
  --completed 4-plan
```

**Log phase completion**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-4-plan) Plan phase complete - {M} tasks created from {N} deliverables"
```

**Add visual separator** after END log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
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
| Profile not in module | Error - profile must exist in `module.skills_by_profile` (except `verification`) |

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

If a profile from `deliverable.profiles` is not in `module.skills_by_profile`:
- Error: "Profile '{profile}' not found in {module}.skills_by_profile"
- Record as lesson learned

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
- `plan-marshall:manage-tasks:manage-tasks` - Create tasks (add --plan-id X --content "...")
- `plan-marshall:manage-findings:manage-findings` - Q-Gate findings (qgate add/query/resolve)
- `plan-marshall:manage-lessons:manage-lesson` - Record lessons on issues (add)

**Consumed By**:
- `plan-marshall:phase-5-execute` skill - Reads tasks and executes them
