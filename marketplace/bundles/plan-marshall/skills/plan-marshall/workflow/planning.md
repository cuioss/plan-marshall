---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Planning Workflows (Phases 1-4)

Workflows for plan creation and setup phases: init, refine, outline, and plan.

> **cwd for `.plan/execute-script.py` calls**: `manage-*` scripts (Bucket A) resolve `.plan/` via `git rev-parse --git-common-dir` and work from any cwd — do **NOT** pin cwd, do **NOT** pass routing flags, and never use `env -C`. Build / CI / Sonar scripts (Bucket B) accept `--plan-id {plan_id}` (preferred — auto-resolves the worktree via `manage-status get-worktree-path`) or `--project-dir {worktree_path}` (escape hatch / explicit override); the two flags are mutually exclusive. See `plan-marshall:tools-script-executor/standards/cwd-policy.md`.

**CRITICAL CONSTRAINT**: These workflows create and manage **plans only**. NEVER implement tasks directly. All task descriptions MUST result in plans - not actual implementation. After completing 1-init through 4-plan phases, check `execute_without_asking` config. If false (default): STOP and wait for execute action. If true: Auto-continue to execute phase.

## Action Routing

| Action | Workflow |
|--------|----------|
| `list` (default) | List all plans |
| `init` | Create new plan, auto-continue |
| `refine` | Clarify request until confident |
| `outline` | Run 3-outline and 4-plan phases |
| `cleanup` | Remove completed plans |
| `lessons` | List and convert lessons to plans |
| `lessons-aggregate` | Aggressive cross-lesson aggregation + superseded-stub prune in a single command |
| `recipe` | Create plan from recipe (routes to `workflow/recipe.md`) |

---

## Action: list (default)

Display all plans with numbered selection, recipe option, and conditional lessons.

**Step 1**: Get existing plans:
```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status list
```

**Step 2**: Check if lessons exist:
```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list
```
Parse `total` from output. If `total > 0`, lessons are available.

**Step 3**: Present interactive menu using `AskUserQuestion`:

Build options dynamically from Step 1 and Step 2 results:

```
AskUserQuestion:
  questions:
    - question: "Which plan would you like to work on?"
      header: "Plans"
      options:
        # For each plan from Step 1 (dynamic):
        - label: "{plan_name} [{phase}]"
          description: "{task_count} tasks - {title or summary}"
        # Always include these static options:
        - label: "Create new plan"
          description: "Start a new plan from a task description or GitHub issue"
        - label: "Create plan from recipe"
          description: "Start a new plan using a project recipe"
        # Only include if Step 2 returned total > 0:
        - label: "List lessons"
          description: "Browse lessons learned and convert to plans"
      multiSelect: false
```

- Always include "Create new plan" and "Create plan from recipe" as options
- Only include "List lessons" when Step 2 returned `total > 0`
- Maximum 4 options per `AskUserQuestion` — if plans + static options exceed 4, present plans first with a "More actions..." option, then show static options in a follow-up question

**Step 4**: Handle selection:
- **Plan selected**: Auto-detect action from plan's current phase
- **"Create new plan"**: Route to `Action: init`
- **"Create plan from recipe"**: Route to `Action: recipe` (load `workflow/recipe.md`)
- **"List lessons"**: Route to `Action: lessons`

---

## Action: init

Create a new plan and automatically continue to 2-refine/3-outline/4-plan phases.

**1-Init Phase** uses a single agent.

Compute the dispatch target via the role resolver:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --role phase-1-init
```

Extract the `target` field from the TOON output. Use that value as `{target}` in the dispatch and the post-resolve log line below.

Emit the standardized post-resolve dispatch log line — see [`ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id none --level INFO \
  --message "[DISPATCH] (plan-marshall:plan-marshall) target={target} level={level} role=phase-1-init workflow=plan-marshall:phase-1-init/SKILL.md plan_id=none"
```

Dispatch:

```
Task: plan-marshall:{target}
  prompt: |
    name: phase-1-init
    plan_id: none
    skills[1]:
    - plan-marshall:phase-1-init
    workflow: plan-marshall:phase-1-init/SKILL.md
    WORKTREE: .

    source: {source}
    content: {content}
```

The agent returns `plan_id` and `domains` in its TOON.

**Metrics**: After the init agent completes and `plan_id` is known, record the
`1-init → 2-refine` boundary in a single fused call (forwarding the agent's
`<usage>` data to the closing phase). The fused command persists the same
state as the prior `end-phase` + `start-phase` + `generate` sequence:
```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics phase-boundary \
  --plan-id {plan_id} --prev-phase 1-init --next-phase 2-refine \
  --total-tokens {total_tokens from <usage>} \
  --duration-ms {duration_ms from <usage>} \
  --tool-uses {tool_uses from <usage>}
```

**Phase handshake**: Capture invariants for the just-completed phase so drift is detected at the next phase entry:

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake capture \
  --plan-id {plan_id} --phase 1-init
```

**Automatic Continuation**:
1. Check `stop-after-init` parameter
2. If true: Stop and display plan summary
3. If false (default): Continue through 2-refine, 3-outline, and 4-plan phases with the new plan_id

**2-Refine Phase**: Dispatch the refine phase under role key `phase-2-refine` (single-workflow phase per [`call-graph.md`](../../ref-workflow-architecture/standards/call-graph.md) § 2.2 and [`dispatch-walkthrough.md`](../../ref-workflow-architecture/standards/dispatch-walkthrough.md) § Example A).

The `phase-boundary` call above already recorded the start of `2-refine` — do
not call `start-phase 2-refine` again.

**Phase handshake (verify)**: Before entering 2-refine, verify the captured invariants for the previous phase still match the live state. Stop on `status: drift`.

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake verify \
  --plan-id {plan_id} --phase 1-init --strict
```

Compute the dispatch target via the role resolver and resolve the active worktree path so the Worktree Header can be populated explicitly (when `metadata.use_worktree==false`, `get-worktree-path` returns the main checkout, so the same call covers both flows):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --role phase-2-refine
```

Extract the `target` field from the TOON output. Use that value as `{target}` in the dispatch and the post-resolve log line below.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  get-worktree-path --plan-id {plan_id}
```

Extract the `worktree_path` field from the TOON output. Use that value as `{worktree_path}` in the dispatch's `WORKTREE:` header below.

Emit the standardized post-resolve dispatch log line — see [`ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract for the field semantics and placement rule:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[DISPATCH] (plan-marshall:plan-marshall) target={target} level={level} role=phase-2-refine workflow=plan-marshall:phase-2-refine/SKILL.md plan_id={plan_id}"
```

Dispatch:

```
Task: plan-marshall:{target}
  prompt: |
    name: phase-2-refine
    plan_id: {plan_id}
    skills[1]:
    - plan-marshall:phase-2-refine
    workflow: plan-marshall:phase-2-refine/SKILL.md
    WORKTREE: {worktree_path}
```

The agent returns confidence + track + scope_estimate + qgate_pending_count in its TOON. The 12-step confidence loop (Steps 3b/3c/8/9/10/11/12) iterates *inside* this single envelope; `AskUserQuestion` in Step 11 propagates to the host UI directly from the subagent (no main-context routing required).

**Post-dispatch contract assertion**: phase-2-refine's contract restricts writes to `.plan/local/plans/{plan_id}/**` and `.plan/local/worktrees/{plan_id}/**` (see `plan-marshall:phase-2-refine` § Enforcement → Allowed write paths). Refine reaching for `Edit` / `Write` against the main checkout is a recurring failure mode (lesson `2026-05-16-14-001`, `feedback_phase2_refine_never_implements`) that silently advances the orchestrator into phase-3-outline with main-checkout drift. Assert structurally that the main checkout is clean before advancing:

```bash
git -C . status --porcelain
```

**Success branch** — empty output (main checkout clean):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (plan-marshall:plan-marshall) Post-refine main-checkout assertion passed (clean)"
```

Continue to the Metrics fused-call below.

**Violation branch** — non-empty output (refine wrote to the main checkout). The orchestrator MUST emit a `[CRITICAL]` work-log entry naming each modified file, return the structured error TOON, and refuse to advance to phase-3-outline:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR \
  --message "[CRITICAL] (plan-marshall:plan-marshall) Refine contract violation — main checkout dirty after phase-2-refine dispatch: {file_list}"
```

Return:

```toon
status: error
error_type: refine_contract_violation
display_detail: "refine dispatched edits to main checkout"
plan_id: {plan_id}
dirty_files: {file_list}
```

Do NOT call `manage-status transition` to 3-outline. Do NOT proceed with the metrics fused-call. The orchestrator stops here; recovery requires the user to inspect the offending files and either revert them or move them into `.plan/local/plans/{plan_id}/**`.

**Cross-references**:
- `plan-marshall:phase-2-refine` § Enforcement → Allowed write paths — the prohibition this assertion enforces (Deliverable 3)
- Lesson `2026-05-16-14-001` (consolidated recurrence) — driving failure history
- `pm-plugin-development:plugin-doctor` analyzer `REFINE_CONTRACT_VIOLATION` (Deliverable 5) — edit-time complement to this runtime assertion

**Metrics**: After refine completes, record the `2-refine → 3-outline` boundary in a single fused call (forwarding the aggregated `<usage>` data from every dispatch that fired inside this phase — the `phase-2-refine` envelope itself plus any q-gate-validation sub-dispatch at Step 13.5 for lesson-derived plans). Sum `total_tokens`, `tool_uses`, and `duration_ms` across each dispatch's `<usage>` tag:
```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics phase-boundary \
  --plan-id {plan_id} --prev-phase 2-refine --next-phase 3-outline \
  --total-tokens {sum of total_tokens from all agent <usage> tags} \
  --tool-uses {sum of tool_uses from all agent <usage> tags} \
  --duration-ms {sum of duration_ms from all agent <usage> tags}
```

**Phase handshake**: Capture invariants for the just-completed phase:

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake capture \
  --plan-id {plan_id} --phase 2-refine
```

The fused call already recorded the start of `3-outline`; the **Action: outline**
section below MUST NOT call `start-phase 3-outline` again. Continue to
**Action: outline** with the same plan_id.

---

## Action: outline (3-Outline + 4-Plan Phases)

See [`workflow/planning-outline.md`](planning-outline.md) for the full workflow. The outline action runs the 3-outline phase (loaded directly in main context with Q-Gate auto-loop and a user review gate guarded by `plan_without_asking`) and then the 4-plan phase (dispatched via `plan-marshall:execution-context-{level}` with workflow `plan-marshall:phase-4-plan/SKILL.md` under role `phase-4-plan`). Both phases record metrics via fused `phase-boundary` calls and capture phase handshake invariants on completion. After tasks are created, the action either auto-continues to execute or stops based on `execute_without_asking` config.

---

## Action: cleanup

Two-pass user-facing maintenance: remove completed plans, then prune redundant superseded-lesson stubs. Both passes confirm with the user before deleting.

---

### Step 1: Plan archive cleanup

List completed plans (filter `complete`). For each entry, present a numbered selection via `AskUserQuestion` and call `manage-status archive` for confirmed entries.

**1a — List completed plans:**

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status list --filter complete
```

Parse the result. If the list is empty, log and continue to Step 2:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO \
  --message "(plan-marshall:plan-marshall:cleanup) No completed plans to archive — skipping plan archive pass"
```

**1b — Confirm and archive:** When the list is non-empty, present the entries via `AskUserQuestion` (multiSelect: true) and for each selected plan_id call:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status archive \
  --plan-id {plan_id}
```

Log each archive:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO \
  --message "(plan-marshall:plan-marshall:cleanup) Archived plan {plan_id}"
```

---

### Step 2: Superseded-lesson stub cleanup

Prune redirect stubs (`.md` files with `status: superseded` frontmatter and a matching tombstone). Retention is hardcoded to `0` days so a freshly superseded lesson is pruned on the very next cleanup invocation. Tombstones at `.tombstones/{id}.json` are preserved so id resolution survives.

**2a — Dry-run to enumerate candidates:**

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons \
  cleanup-superseded --retention-days 0 --dry-run
```

Parse `removed[]` from the TOON output. If the list is empty, log and finish:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO \
  --message "(plan-marshall:plan-marshall:cleanup) No superseded stubs to prune — skipping stub cleanup pass"
```

**2b — Confirm and prune:** When `removed[]` is non-empty, display the count and the list of candidate ids, then ask:

```
AskUserQuestion:
  question: "Prune {count} superseded lesson stub(s)? (Tombstones will be preserved.)"
  header: "Cleanup"
  options:
    - label: "Yes, prune"
      description: "Delete the .md redirect stubs; tombstones at .tombstones/{id}.json remain"
    - label: "No, keep"
      description: "Leave the stubs in place"
  multiSelect: false
```

**On "Yes, prune"**, run the actual deletion (no `--dry-run`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons \
  cleanup-superseded --retention-days 0
```

Log the outcome via `manage-logging decision`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO \
  --message "(plan-marshall:plan-marshall:cleanup) Pruned {removed_count} superseded stub(s); tombstones preserved"
```

**On "No, keep"**, log the decline:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO \
  --message "(plan-marshall:plan-marshall:cleanup) Stub cleanup declined by user — {count} candidates left in place"
```

---

### Step 3: Orphan-dir cleanup

Prune orphan plan directories — entries under `.plan/plans/` that have no readable `status.json`. These typically result from interrupted plan creation, aborted `phase-1-init` dispatches, or stale worktree-only artifacts. The archived-plans directory is excluded by `manage-status list-orphans`.

**3a — Enumerate orphan directories:**

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status list-orphans
```

Parse `orphans[]` from the TOON output. Each entry exposes `id`, `path`, and `contents` (top-level entries inside the orphan directory). If the list is empty, log and finish the cleanup action:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO \
  --message "(plan-marshall:plan-marshall:cleanup) No orphan plan directories to prune — skipping orphan-dir cleanup pass"
```

**3b — Per-orphan triage (mirrors Step 1 / Step 2 empty-vs-non-empty split):**

For each orphan entry:

- **Empty (`contents` is `[]`)**: Log the silent removal decision and delete without prompting (mirrors Step 1's empty-log-and-skip shape — no user-visible noise for clearly disposable directories):

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id global --level INFO \
    --message "(plan-marshall:plan-marshall:cleanup) Removing empty orphan directory {id} ({path})"
  ```

  Then remove the directory:

  ```bash
  rm -rf {path}
  ```

- **Non-empty**: Defer the deletion decision to the user. Collect all non-empty orphans, then present a single multi-select `AskUserQuestion` so the user can pick which directories to delete in one pass:

  ```
  AskUserQuestion:
    question: "Select orphan plan directories to delete. Each lists the top-level entries it contains so you can decide whether the contents are recoverable."
    header: "Orphans"
    options:
      # For each non-empty orphan:
      - label: "{id}"
        description: "{path} — contains: {comma-separated contents}"
    multiSelect: true
  ```

  For each confirmed orphan, log the decision and remove the directory:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id global --level INFO \
    --message "(plan-marshall:plan-marshall:cleanup) Removed non-empty orphan directory {id} ({path}) at user confirmation — contents: {contents}"
  ```

  ```bash
  rm -rf {path}
  ```

  For each non-empty orphan the user declined, log the decline:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id global --level INFO \
    --message "(plan-marshall:plan-marshall:cleanup) Orphan directory {id} ({path}) left in place by user — contents: {contents}"
  ```

---

## Action: lessons

List lessons learned with options to convert to plan or analyze all.

### Menu

**Step 1**: List all lessons:
```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list
```

**Step 2**: Present options using `AskUserQuestion`:

```
AskUserQuestion:
  questions:
    - question: "What would you like to do with lessons?"
      header: "Lessons"
      options:
        # For each lesson from list (dynamic):
        - label: "[{category}] {title}"
          description: "Component: {component} — Convert to plan"
        # Always include:
        - label: "Analyze all lessons"
          description: "Review validity, find done/combinable lessons, cleanup"
        - label: "Aggregate aggressively"
          description: "Cross-lesson grouping + supersede + prune in one batch — routes to Action: lessons-aggregate"
        - label: "Back to main menu"
          description: "Return to plan list"
      multiSelect: false
```

If the user selects "Aggregate aggressively", route to `Action: lessons-aggregate` (the new section below).

### Convert lesson to plan

When a specific lesson is selected, convert it to a plan via a `lesson_id` reference. Compute the dispatch target via the role resolver, then dispatch:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --role phase-1-init
```

Extract the `target` field from the TOON output. Use that value as `{target}` in the dispatch and the post-resolve log line below.

Emit the standardized post-resolve dispatch log line — see [`ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id none --level INFO \
  --message "[DISPATCH] (plan-marshall:plan-marshall) target={target} level={level} role=phase-1-init workflow=plan-marshall:phase-1-init/SKILL.md plan_id=none"
```

```
Task: plan-marshall:{target}
  prompt: |
    name: phase-1-init
    plan_id: none
    skills[1]:
    - plan-marshall:phase-1-init
    workflow: plan-marshall:phase-1-init/SKILL.md
    WORKTREE: .

    lesson_id: {lesson_id}
```

The agent returns `plan_id` and `domain` in its TOON. Passing `lesson_id` triggers `phase-1-init` Step 4 ("From Lesson") to resolve the lesson body from `lessons-learned/` and Step 5b ("Move Lesson File Into Plan Directory") to relocate the lesson file into the new plan directory via `manage-lessons convert-to-plan`. Both side effects are automatic — the caller only supplies `lesson_id`.

**Anti-pattern (prohibited):** Never dispatch the lesson conversion with `source=lesson, content={verbatim lesson text}` in the prompt body. Inline `content` is the `description` source path and causes `phase-1-init` to treat the input as a free-form description — Step 5b is skipped and the original lesson file is orphaned in `lessons-learned/` instead of being archived inside the plan directory. Always reference the lesson by `lesson_id`; never paste its body.

### Analyze all lessons

When "Analyze all lessons" is selected, run the analyze workflow. This is an interactive LLM workflow — no plan is created.

**Step 1**: List lessons with full body content:
```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list --full
```

**Step 2**: Classify each lesson per `plan-marshall:manage-lessons:references/dedup-analysis.md` — the authoritative Close / Merge / Keep-open (i.e. `already_closed` / `merge_into` / `new`) classification rule shared with the `plan-retrospective` lessons-proposal caller. Verify each lesson's validity against the current codebase as part of that classification.

**Step 3**: Present a single batch summary via `AskUserQuestion` (cleanup-side caller contract from `dedup-analysis.md` — one confirmation per batch, not per candidate):

```
AskUserQuestion:
  questions:
    - question: |
        ## Lessons Analysis

        ### Close (already done):
        {for each close candidate:}
        - {id}: {title} — {reasoning}

        ### Merge:
        {for each merge group:}
        - {source_id} → {target_id}: {reasoning}

        ### Keep open:
        {for each open lesson:}
        - {id}: {title}

        Proceed with these actions?
      options:
        - label: "Proceed"
          description: "Execute all proposed close and merge actions"
        - label: "Cancel"
          description: "Make no changes"
      multiSelect: false
```

**Step 4**: If user selects "Proceed", execute close and merge actions per `dedup-analysis.md` (delete stale files for `already_closed`, Edit target lesson with `## Recurrence — YYYY-MM-DD (context)` section for `merge_into`). Log each action:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO --message "(plan-marshall:lessons-analyze) Closed lesson {id}: {title} — {reasoning}"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO --message "(plan-marshall:lessons-analyze) Merged lesson {source_id} into {target_id}: {reasoning}"
```

**Step 5**: Display summary of actions taken.

---

## Action: lessons-aggregate

See [`workflow/planning-lessons-aggregate.md`](planning-lessons-aggregate.md) for the full workflow. Aggressive cross-lesson aggregation in a single command: classify the active lessons corpus, ask the user once for confirmation, then for each multi-lesson group rewrite the primary lesson's body and title, supersede the absorbed lessons, and optionally prune the resulting `.md` stubs. The orchestrator counterpart to the read-only `manage-lessons aggregate` verb.

---

## Script API Reference

Script: `plan-marshall:manage-status:manage_status`

| Command | Parameters | Description |
|---------|------------|-------------|
| `read` | `--plan-id` | Read plan status |
| `create` | `--plan-id --title --phases [--force]` | Initialize status.json |
| `set-phase` | `--plan-id --phase` | Set current phase |
| `update-phase` | `--plan-id --phase --status` | Update phase status |
| `progress` | `--plan-id` | Calculate plan progress |
| `list` | `[--filter]` | Discover all plans |
| `list-orphans` | _(none)_ | Discover orphan plan directories (no readable status.json); archived-plans excluded |
| `transition` | `--plan-id --completed` | Transition to next phase |
| `archive` | `--plan-id [--dry-run]` | Archive completed plan |
| `route` | `--phase` | Get skill for phase |
| `get-routing-context` | `--plan-id` | Get combined routing context |

---

## Storage

Status is stored in the plan directory:

```
.plan/plans/{plan_id}/status.json
```

Archived plans:

```
.plan/archived-plans/{yyyy-mm-dd}-{plan-name}/
```

---

## Status File Format

TOON format with phases table:

```toon
title: Implement JWT Authentication
current_phase: 5-execute

phases[6]{name,status}:
1-init,done
2-refine,done
3-outline,done
4-plan,done
5-execute,in_progress
6-finalize,pending

created: 2025-12-02T10:00:00Z
updated: 2025-12-02T14:30:00Z
```

### Phase Statuses

| Status | Meaning |
|--------|---------|
| `pending` | Not started |
| `in_progress` | Currently active |
| `done` | Completed |

---

## Phase Routing

The `route` command returns skill names for each phase:

| Phase | Skill | Description |
|-------|-------|-------------|
| 1-init | `plan-init` | Initialize plan structure |
| 2-refine | `request-refine` | Clarify request until confident |
| 3-outline | `solution-outline` | Create solution outline with deliverables |
| 4-plan | `task-plan` | Create tasks from deliverables |
| 5-execute | `plan-execute` | Execute implementation tasks + verification |
| 6-finalize | `plan-finalize` | Finalize with commit/PR |

## Output

Top-level orchestrator workflow — entered from the `/plan-marshall` slash command, not dispatched as a unit. The workflow drives multiple phase agents to completion; its terminal return is a user-visible status display rather than a TOON consumed by a parent. Conformance to the ext-point output contract is degenerate:

```toon
status: success | error
display_detail: "<plan {plan_id} reached {phase}>"
```

The orchestrator emits this shape only when wrapped in a `Task: execution-context-{level}` dispatch (e.g., from automated tooling). When entered interactively, the workflow surfaces its progress via `manage-logging` + `mark-step-done` records on each phase boundary; the terminal user-facing message replaces the TOON.
