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

**Anti-pattern: shell-substitution shortcuts for batch task payloads**

When persisting the multi-task batch (Step 6 → 6a/6b), the following shell shortcuts are explicitly forbidden because they bypass the `--tasks-file` path-allocate flow and trip the host platform's bash safety rules (one command per call, no shell constructs, no heredocs with `#` lines):

- `$(cat …)` command substitution (e.g. `manage-tasks batch-add --tasks-json "$(cat /tmp/tasks.json)"`) — violates the no-`$()` rule and silently quotes the JSON through the shell argument boundary.
- Heredocs with `#` lines (e.g. `cat <<EOF | jq …` payloads that include `#`-prefixed comments) — heredocs containing `#` lines trigger the bash safety prompt and break execution.
- `python -c "open('…').write('…')"` one-liners that inline-write the batch JSON from a shell argument — this re-introduces the same shell-quoting fragility the path-allocate flow exists to eliminate.

**Rule-compliant alternative**: Use the `--tasks-file` path-allocate flow documented in Step 6a/6b. Stage the batch JSON via `manage-files write --file work/tasks-batch.json` (so the payload is written through a structured tool, not a shell argument), then call `manage-tasks batch-add --tasks-file .plan/local/plans/{plan_id}/work/tasks-batch.json`. This is the only sanctioned path for multi-task creation in this phase.

**Constraints:**
- Strictly comply with all rules from dev-general-practices, especially tool usage and workflow step discipline
- Batch JSON staging files MUST live under `.plan/local/plans/{plan_id}/work/`. Never use `Write` to `/tmp/`, `/var/`, or any path outside the plan's `work/` directory. (Cross-reference: see anti-pattern callout at SKILL.md:30 for the shell-substitution shortcut prohibition; both rules apply together.)

## cwd for `.plan/execute-script.py` calls

> `manage-*` scripts (Bucket A) resolve `.plan/` via `git rev-parse --git-common-dir` and work from any cwd — do **NOT** pin cwd, do **NOT** pass routing flags, and never use `env -C`. Build / CI / Sonar scripts (Bucket B) accept `--plan-id {plan_id}` (preferred — auto-resolves the worktree via `manage-status get-worktree-path`) or `--project-dir {worktree_path}` (explicit override / escape hatch); the two flags are mutually exclusive. See `plan-marshall:tools-script-executor/standards/cwd-policy.md`.

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
| `build-python` (findings module) | `test/.../test_findings_store.py` | `test_build_findings_store.py` |
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

The Phase Entry Protocol's `phase_handshake verify --phase 3-outline --strict` call (see [`ref-workflow-architecture/standards/phase-lifecycle.md`](../ref-workflow-architecture/standards/phase-lifecycle.md#phase-handshake-verify-phases-2-6)) asserts the worktree-resolution contract before any phase-4 work begins: when `metadata.use_worktree==true`, `metadata.worktree_path` MUST be non-empty AND filesystem-resolvable (the directory exists AND `git -C {path} rev-parse --show-toplevel` returns the same canonical path). When the assertion fails, the script returns `status: error, error: worktree_unresolved` and (under `--strict`) exits 1 — phase entry refuses to advance until the persisted metadata is repaired. Plans with `metadata.use_worktree==false` skip the assertion (main-checkout flow). The assertion fires uniformly at every phase boundary; see deliverable 8 in the originating lesson plan for the full contract.

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
| [Breaking-Refactor Task Split](standards/breaking-refactor-task-split.md) | Task-split contract for `tech_debt` / `feature_breaking` deliverables that intentionally invalidate existing test contracts (allocates `implementation` + `module_testing` task pair with `depends_on` linkage); paired with the phase-5-execute planned-failure exception |

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
  decision --plan-id {plan_id} --level WARNING --message "(plan-marshall:phase-4-plan) Deliverable {N} is verification-only but had profiles [{original_profiles}] — overriding to [verification]"
```

```
For each deliverable D:
  IF D.change_type == verification OR D.affected_files is empty:
    IF D.profiles != [verification]:
      Log warning (see above)
    D.profiles = [verification]
  1. Query architecture: module --module {D.module}
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

**Breaking-refactor task split**: When the deliverable's `compatibility=breaking` OR its `change_type` is `tech_debt` or `feature_breaking`, AND it touches code paths covered by existing module tests, allocate the implementation and `module_testing` tasks per the task-split contract in [standards/breaking-refactor-task-split.md](standards/breaking-refactor-task-split.md) — the test-contract task carries `depends_on: [TASK-{implementation_number}]` and its description enumerates both the pre-existing tests being rewritten and any new regression tests pinning the new contract. This is the planning-side half of the breaking-refactor pair; phase-5-execute applies the planned-failure exception when the implementation task's verification fails in exactly the way the test-contract task is scoped to fix.

**Self-modifying phasing enforcement**: When a deliverable's `Affected files:` list matches the path heuristic in [`ref-workflow-architecture/standards/self-modifying-classification.md`](../ref-workflow-architecture/standards/self-modifying-classification.md) AND the plan declares `compatibility: breaking` AND the deliverable describes a deletion/rename/hard-cutover, refuse to create tasks for the deliverable until ONE of the following holds:

1. **Inline phasing rationale present**: The deliverable contains a `**Phasing Rationale:**` block addressing all three points from the standard's Phasing-Rationale Contract (cache-sync ordering safe; verification gate runs against worktree post-final-edit; central narrative carries no transition hedges). When present, proceed with task creation as usual — the inline rationale satisfies the contract.
2. **Peer plan exists for the deletion phase**: A separate plan (lesson-derived or otherwise) carries the deletion scope per the PLAN A / PLAN B split pattern, AND the current plan's deliverables are restricted to the additive surface. Verify by scanning the deliverable narrative for an explicit follow-up plan id (e.g., a "Follow-up plan: `<plan-id>`" line, or a similar inline reference). The `status.metadata.plan_source` field records plan ORIGIN (`recipe` / `lesson` / fresh) — see `phase-1-init` Step 6 — and is NOT a peer-plan reference; do not consult it for this check. The deliverable narrative is the only authoritative source for peer-plan linkage. When the inline reference is present, proceed.

When NEITHER holds, escalate via `AskUserQuestion` (mirroring phase-3-outline Step 10b's options — split / inline rationale / switch to additive). On user resolution, log to `decision.log` and proceed with the chosen path. This enforcement complements (does not replace) the breaking-refactor task split above: the breaking-refactor split allocates the test-rewrite task pair when the runtime contract changes, while self-modifying phasing enforcement ensures the breaking-deletion task itself has a valid phasing rationale before tasks are emitted at all.

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

   **Worked example** (from source lesson `2026-04-17-20-001`): A deliverable body specifies task-ordering values `order: 990 / 1000` in its Change per file section. The canonical violation is a task description that paraphrases these as `order: 90 / 100` — a "regularization" from the four-digit spacing (`990`/`1000`) down to a two-digit spacing (`90`/`100`). The description MUST instead carry the literal tokens `order: 990 / 1000` verbatim. This same rule applies whenever the outline supplies specific numeric or flag-shaped data: copy the tokens exactly as written, do not "improve" them.

**CRITICAL — Shell Metacharacter Sanitization**: Before writing values into the TOON task file, strip all markdown backticks (`` ` ``) from title, description, criteria, and step values. Backticks are shell metacharacters (command substitution) that trigger permission prompts if they later reach a shell. They are markdown formatting artifacts not needed in TOON task data. Replace `` `foo` `` with `foo` (plain text).

### Validation: Lesson-ID References

**Shape constraint** — A lesson ID is a five-segment token of the form `YYYY-MM-DD-HH-N+` (e.g., `2026-05-03-21-002`). The canonical regex is `LESSON_ID_RE` in `tools-input-validation` and is the single source of truth for the shape; this section never re-defines or re-spells the pattern.

**At-write-time enforcement** — Every task whose `title` or `description` contains a lesson-ID-shaped token MUST resolve that token against the live `manage-lessons` inventory before the task file is written. Enforcement lives in the write paths of `manage-tasks` (`commit-add` and `batch-add`), so neither phase-4-plan nor any other plan-author surface can bypass it by writing through the script:

1. The handler calls `scan_lesson_id_tokens(title + ' ' + description)` from `tools-input-validation` to extract every embedded lesson-ID token.
2. The handler calls `verify_lesson_ids_exist(tokens)` to check each token against the live `manage-lessons list` inventory (the same inventory the runtime live-anchor discipline uses — see lesson 2026-04-29-10-001).
3. On ANY unresolved token, the entire write batch is aborted atomically — no `TASK-NNN.json` file is created, the on-disk state is untouched, and the response is the error payload described below.
4. The handler does NOT auto-rewrite descriptions to drop the offending IDs and does NOT downgrade the failure to a soft warning. A reference miss is a hard error so the plan can be corrected before execution.

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

**Recovery procedure** — When a write fails with `validation_error: lesson_id_not_found`:

1. Inspect `unresolved_ids` in the error payload to identify which lesson IDs are unknown to the inventory.
2. Decide per ID: either (a) **create the lesson** via `manage-lessons add` if the reference was meant to point to a real (but not-yet-allocated) lesson, or (b) **drop the ID from the task description** and reword the narrative as a query against the live inventory (e.g., "archive any lessons matching component=X and category=resolved") so the task does not depend on a phantom ID.
3. Re-stage the corrected task batch (re-write the `tasks-batch.json` staging file) and re-invoke `batch-add --tasks-file PATH`. The atomic-write contract guarantees the previous failed attempt left no on-disk state behind, so the retry starts from a clean tasks directory.
4. NEVER bypass the validation by editing `TASK-NNN.json` files directly or by passing `--no-validate`-style flags — no such bypass exists, and the validation is the only point in the plan lifecycle that catches lesson-ID drift before tasks reach phase-5-execute.

This validation operationalises lesson 2026-05-03-21-002: the plan-author surface (this phase) was emitting tasks that named lesson IDs that did not exist in the inventory, and the at-execute-time signal was a silent no-op (`archived: 0`) that did not surface the discrepancy. Pushing the check into the write paths of `manage-tasks` means the discrepancy surfaces at task-author time as a hard, structured error — the same point in the lifecycle where the operator can still correct it cheaply.

Compose every task record for this phase invocation into one JSON array, then persist them atomically via the path-allocate flow. Each entry mirrors the TOON task schema:

```
{
  "title": "{task title}",
  "deliverable": {deliverable_number},
  "domain": "{domain}",
  "profile": "{profile}",
  "description": "{description}",
  "steps": ["{file1}", "{file2}"],
  "depends_on": [],            // or ["TASK-1", ...]
  "skills": ["{bundle:skill}", ...],
  "verification": {
    "commands": ["{cmd1}"],
    "criteria": "{criteria}"
  }
}
```

Sequential numbering is assigned in array order at call time. On any validation failure no `TASK-NNN.json` is written.

**Step 6a — Stage the JSON array under the plan's `work/` tree via the `Write` tool.** Use the `Write` tool directly to write the batch JSON to `.plan/local/plans/{plan_id}/work/tasks-batch.json`. This path is covered by the `Write(.plan/**)` permission rule, so no permission prompt is triggered, and writing through a structured tool keeps the JSON payload off the shell argument boundary. The intermediate `manage-files write` call is **no longer required** for this canonical flow.

If a script-mediated path is preferred (for example, when the staging file already lives outside `.plan/`), the optional `manage-files write --content-file PATH` form is documented separately in `marketplace/bundles/plan-marshall/skills/manage-files/SKILL.md` (write subcommand reference). Both forms produce the same staged file; only the canonical `Write`-tool form is exercised by this phase.

**Step 6b — Persist the batch atomically** by passing the staged file path to `batch-add --tasks-file`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  batch-add --plan-id {plan_id} --tasks-file .plan/local/plans/{plan_id}/work/tasks-batch.json
```

The `--tasks-file PATH` form is the canonical entrypoint for phase-4-plan (and any other caller that produces more than one task at a time). The legacy inline `--tasks-json` form is mutually exclusive with `--tasks-file` and remains supported as a secondary option for trivial payloads only — it is NOT used by this phase.

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

**Module resolution for holistic tasks**: Holistic tasks are plan-level, not deliverable-level. Omit `--module` from `architecture resolve` to use the root module, which runs commands across all modules. Do NOT try to list or enumerate modules — the root module default handles cross-module verification.

**Read verification steps** (NOTE: `manage-config plan` is ONLY for phase configs — for architecture queries use `manage-architecture:architecture`):
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get --field steps --audit-plan-id {plan_id}
```

Iterate over the `steps` list. For each step, create a holistic verification task based on the step type:

**Built-in steps** (no colon in name):
- `quality_check` → Resolve via `architecture resolve --command quality-gate` (no `--module` — uses root module for cross-module check)
- `build_verify` → Resolve via `architecture resolve --command module-tests` (no `--module` — uses root module for cross-module check)

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

### Step 9b: Spawn q-gate-validation-agent for mechanical validators

**Purpose**: Run the `module-mapping-validator` and `scope-criterion-validator` from `q-gate-validation-agent.md` (§§ 2.11, 2.12) over the just-created tasks and the parent deliverables. Both validators reconcile LLM-authored task/deliverable shape against live ground truth (architecture which-module, architecture find/marketplace grep) and emit findings that the orchestrator's existing 3-iteration auto-loop consumes.

**Activation guard**: Unconditional — runs after every successful phase-4-plan invocation, regardless of `plan_source`. Both validators apply to every plan (lesson-derived, issue-derived, recipe-derived, free-form). Skip only when the Q-Gate inline checks above (Step 9) have already exhausted the orchestrator's `verification_max_iterations` budget — in that case the orchestrator will already be aborting the auto-loop.

**Cross-reference (lesson-ID validation)**: The lesson-id-validator that was originally part of the umbrella lesson `2026-05-03-21-002` is intentionally NOT spawned here. PR #323 ships lesson-ID validation at **write time** in `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_crud.py` (via `tools-input-validation/scripts/input_validation.py`). Every `TASK-*.json` write hits the validator before disk and **hard-fails** with `validation_error: lesson_id_not_found` when a phantom ID is cited — distinct from this Step 9b's q-gate auto-loop placement. Future maintainers extending phase-4-plan validation should preserve the placement split: write-time hard-fail for lesson-ID lookup against `manage-lessons list`; q-gate auto-loop for structural cross-checks (module mapping, scope criterion).

**Dispatch the validator agent**.

(1) Resolve the level for role `q_gate_validation`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  models read --role q_gate_validation
```

(2) Compute the target:
- `level == "inherit"` or empty → `target = q-gate-validation-agent`
- otherwise → `target = q-gate-validation-agent-<level>`

(3) Dispatch:

```
Task: plan-marshall:{target}
  Input:
    plan_id: {plan_id}
    activation_context: 4-plan
    validators: [module-mapping-validator, scope-criterion-validator]
```

The agent reads `solution_outline.md` (for the deliverables and their `success_criterion`/`affected_files` blocks) and the just-written `TASK-*.json` files (for `module_testing` task targets), runs the validator detection logic documented in q-gate-validation-agent.md §§ 2.11–2.12, and emits findings using `--source qgate-module-mapping` / `--source qgate-scope-criterion`. See those sections for the canonical detection logic and finding emission templates.

**Aggregate the findings** — read pending findings to update the running count returned in Step 11:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate query --plan-id {plan_id} --phase 4-plan --resolution pending
```

Parse `filtered_count` from the output and ADD it to the `qgate_pending_count` already aggregated by Step 9's inline checks. Both finding sources flow into the same aggregate, so the orchestrator's existing 3-iteration auto-loop handles re-entry uniformly.

**Log dispatch outcome**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-4-plan:qgate) Spawned q-gate-validation-agent for module-mapping + scope-criterion validators; pending findings now {qgate_pending_count}"
```

This step runs AFTER the inline Q-Gate checks of Step 9 and BEFORE Step 10 (Record Issues as Lessons) / Step 11 (Transition Phase and Return Results). The placement is load-bearing: inline checks first means cheap structural findings are recorded before the more expensive cross-bundle queries; validator second ensures architecture-anchored findings can re-enter phase-4-plan alongside the inline ones.

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

**Failure-mode rationale**: this constraint was hardened in response to two recurring drift patterns:

1. **PR #348 path-heuristic copy-paste** — `phase-3-outline/standards/outline-workflow-detail.md` Step 10b inlined the self-modifying-plan path list instead of xref-ing `ref-workflow-architecture/standards/self-modifying-classification.md` § Path Heuristic. A subsequent extension of the path heuristic landed only in the central standard; the integration site silently kept the old list and missed two new path classes (`marketplace/targets/**`, `.../skills/sync-plugin-cache/**`).
2. **q-gate-validator §2.16 keyword-list drift** — the validator's hard-cutover keyword list was duplicated in `q-gate-validation-agent.md` §2.16. An extension of the keyword list landed only in the central standard; the validator agent continued matching the stale list until a manual audit caught the divergence.

Both failures share the same shape: a copy-pasted *enforcement-critical* rule body that drifted because the integration site was not declared as a downstream consumer of the central standard. The constraint converts that latent contract ("everyone keep your copy in sync") into an explicit one ("xref the central standard; never inline-copy"). The q-gate validator §2.16 architecture-mismatch finding (added in deliverable 9 of this plan) reinforces the same boundary at the outline phase, so the constraint is enforced at both planning time and validation time.

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
- `plan-marshall:manage-architecture:architecture` - Query module skills (module --module {module}) and resolve commands (resolve --command {cmd} --module {module}). Uses `--audit-plan-id`, NOT `--plan-id`.
- `plan-marshall:manage-tasks:manage-tasks` - Create tasks atomically via `batch-add --tasks-file PATH` (preferred for multi-task creation in this phase, where `PATH` is staged via `manage-files write` to `.plan/local/plans/{plan_id}/work/tasks-batch.json`). Single ad-hoc adds may use the path-allocate flow (`prepare-add` → Write TOON → `commit-add`).
- `plan-marshall:manage-files:manage-files` - Stage the batch JSON array (via `write --file work/tasks-batch.json`) so the payload never crosses the shell argument boundary.
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
