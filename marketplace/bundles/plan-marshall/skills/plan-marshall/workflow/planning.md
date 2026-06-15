---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Planning Workflows (Phases 1-4)

Workflows for plan creation and setup phases: init, refine, outline, and plan.

> **cwd for `.plan/execute-script.py` calls**: `manage-*` scripts resolve `.plan/` via the uniform cwd walk-up (ADR-002) — the nearest ancestor of cwd containing `.plan/local`. The orchestrator runs on the main checkout in phases 1-4 (resolving main's `.plan/`) and pins cwd to the worktree in phase-5+ (resolving the moved-in worktree copy); do **NOT** pass routing flags to `manage-*`, and never use `env -C`. Build / CI / Sonar scripts accept `--plan-id {plan_id}` (preferred — auto-resolves the worktree itself) or `--project-dir {worktree_path}` (escape hatch / explicit override); the two flags are mutually exclusive. See `plan-marshall:tools-script-executor/standards/cwd-policy.md`.

**CRITICAL CONSTRAINT**: These workflows create and manage **plans only**. NEVER implement tasks directly. All task descriptions MUST result in plans - not actual implementation. After completing 1-init through 4-plan phases, check `execute_without_asking` config. If false (default): STOP and wait for execute action. If true: Auto-continue to execute phase.

## Action Routing

| Action | Workflow |
|--------|----------|
| `list` (default — no inputs) | List all plans |
| `init` | Create new plan, auto-continue |
| `refine` | Clarify request until confident |
| `outline` | Run 3-outline and 4-plan phases |
| `cleanup` | Remove completed plans |
| `lessons` | List and convert lessons to plans |
| `lessons-aggregate` | Aggressive cross-lesson aggregation + superseded-stub prune in a single command |
| `recipe` | Create plan from recipe (routes to `workflow/recipe.md`) |

When `action=` is omitted, infer the action from the supplied source/target parameters per the [Action Resolution rules in SKILL.md](../SKILL.md#action-resolution):

| Supplied parameter (no explicit `action=`) | Inferred action |
|--------------------------------------------|-----------------|
| `task=` or `issue=` | `init` (parameter becomes the plan source) |
| `lesson=` | `lessons` (seeds the lessons workflow with the given lesson) |
| `recipe=` | `recipe` (seeds the recipe workflow with the given recipe key) |
| `plan=` | auto-detected from plan's current phase (see SKILL.md) |
| (none) | `list` |

If two or more of `{task, issue, lesson, recipe, plan}` are supplied together without an explicit `action=`, return `status: error` naming the conflict.

---

## Action: list (default)

Display all plans with numbered selection, recipe option, and conditional lessons.

**Step 1**: Get existing plans:
```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status list
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

Emit the standardized pre-dispatch attempt log line and the post-resolve dispatch log line — see [`ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id none --level INFO \
  --message "[ATTEMPT] (plan-marshall:plan-marshall) dispatching target={target} role=phase-1-init"
```

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

**Post-init contract assertion**: phase-1-init's contract is plan-structure creation only — it writes `request.md`, `references.json`, and `status.json` under `.plan/local/plans/{plan_id}/**` and returns `plan_id` + `domains` (+ `next_phase`) and nothing else of substance (see `plan-marshall:phase-1-init` § Enforcement). When the `content` it receives reads like a ready-to-apply implementation spec, the agent treats it as a work order — editing source files, switching the checkout onto a `fix/`/`feature/` branch, and returning a payload that omits `plan_id` and carries a `pr_url` instead. This is the same failure class as the post-refine violation one phase later (see `feedback_phase2_refine_never_implements`), and it silently advances the orchestrator into phase-2-refine with main-checkout drift. Assert structurally that the init was contract-clean before advancing.

**Return-shape check**: assert the phase-1-init return TOON carries a non-empty `plan_id` AND does NOT carry a `pr_url`, a `branch`, or a "patched N files" / files-patched `display_detail`. Any of those is a rogue-implementation signal — phase-1-init never opens a PR, never reports a branch, and never reports files patched.

**Main-checkout cleanliness check**: assert the main checkout is clean and was not switched onto a feature branch. Keep the two checks as separate single-command Bash blocks (one command per call):

```bash
git -C . status --porcelain
```

```bash
git -C . branch --show-current
```

Assert the first command's output is empty and the second command's output equals the base branch (the checkout was not switched onto a `fix/`/`feature/` branch).

**Success branch** — the return-shape check passes (non-empty `plan_id`, no rogue payload field), the porcelain output is empty, and the current branch equals the base branch:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (plan-marshall:plan-marshall) Post-init main-checkout assertion passed (clean, plan_id present)"
```

Continue to the **Metrics** fused-call below.

**Violation branch** — any of the checks fails: the return TOON omits `plan_id` or carries a `pr_url` / `branch` / patched-files `display_detail`, OR the porcelain output is non-empty, OR the current branch differs from the base branch. The orchestrator MUST emit a `[CRITICAL]` work-log entry naming the offending signal (dirty files / switched branch / missing plan_id / rogue payload field), return the structured error TOON, and refuse to advance to phase-2-refine.

`{offending_signal}` names the specific violation: the joined non-empty lines of the `git -C . status --porcelain` output for a dirty tree, the resolved branch name for a switched checkout, `missing plan_id` when the return omits `plan_id`, or the rogue field name (`pr_url` / `branch` / files-patched `display_detail`) when the return shape is wrong.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id:-none} --level ERROR \
  --message "[CRITICAL] (plan-marshall:plan-marshall) Init contract violation — phase-1-init dispatched edits to the main checkout: {offending_signal}"
```

Return:

```toon
status: error
error: init_contract_violation
display_detail: "init dispatched edits to main checkout"
plan_id: {plan_id}
offending_signal: {offending_signal}
```

Do NOT call the **Metrics** fused-call. Do NOT capture the phase handshake. Do NOT continue to 2-refine. The orchestrator stops here; recovery requires the user to inspect the offending files, revert them or move them into `.plan/local/plans/{plan_id}/**`, and run `git -C . checkout {base_branch}` if the checkout was switched onto a `fix/`/`feature/` branch.

**Cross-references**:
- `plan-marshall:phase-1-init` § Enforcement — the prohibition this assertion enforces
- `feedback_phase2_refine_never_implements` — driving failure history for the symmetric post-refine guard

**Metrics**: After the init agent completes and `plan_id` is known, record the
`1-init → 2-refine` boundary in a single fused call (forwarding the agent's
`<usage>` data to the closing phase). The fused command persists the same
state as the prior `end-phase` + `start-phase` + `generate` sequence:
```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics phase-boundary \
  --plan-id {plan_id} --prev-phase 1-init --next-phase 2-refine \
  --total-tokens {total_tokens from <usage>} \
  --duration-ms {duration_ms from <usage>} \
  --tool-uses {tool_uses from <usage>}
```

phase-1-init Step 3a records `1-init.start_time` via `manage-metrics
start-phase` as soon as the plan directory exists, so the fused
`phase-boundary` call above closes 1-init using a real agent-side timestamp
and computes `duration_seconds = end_time - start_time` against it. The
`_read_status_created` backfill in `manage-metrics.py` is retained only as a
safety net for plans materialised under older orchestrator versions; current
plans never exercise that path.

**Phase handshake**: Capture invariants for the just-completed phase so drift is detected at the next phase entry:

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake capture \
  --plan-id {plan_id} --phase 1-init
```

**Automatic Continuation** — read `plan.phase-1-init.init_without_asking` from `marshal.json`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-1-init get --field init_without_asking --audit-plan-id {plan_id}
```

- If `false` → STOP and display the plan summary.
- Otherwise (`true` or unset → default `true`) → continue through 2-refine, 3-outline, and 4-plan phases with the new plan_id.

This mirrors the existing `plan_without_asking` (phase-3-outline) and `execute_without_asking` (phase-4-plan) gate-resolution pattern.

**2-Refine Phase**: Dispatch the refine phase under role key `phase-2-refine` (single-workflow phase per [`call-graph.md`](../../ref-workflow-architecture/standards/call-graph.md) § 2.2 and [`dispatch-walkthrough.md`](../../ref-workflow-architecture/standards/dispatch-walkthrough.md) § Example A).

The `phase-boundary` call above already recorded the start of `2-refine` — do
not call `start-phase 2-refine` again.

#### Planning-lane dispatch (light vs deep)

The **planning lane** — `status.metadata.planning_lane`, resolved by the phase-1-init lane router (`manage-status planning-lane route`) — is the structural selector for the whole phases-2-4 pipeline. The orchestrator branches on it deterministically: a `light` plan runs ONE collapsed light-lane envelope (refine-no-loop + Simple-outline + deliverable-derivation folded together); a `deep` plan runs today's full refine-loop → outline → plan pipeline. The orchestrator remains LLM-driven; this lane read is the only deterministic branch in the planning path.

Read the lane (single call) before the **Phase handshake (verify)** below:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} --get --field planning_lane
```

Extract `value` (`light` or `deep`). When the field is absent or unresolved, treat it as `deep` (the conservative, full-pipeline default).

**Light-lane branch** — when `planning_lane == light`:

1. Log the lane decision (decision-level, exact wording for grep-ability):

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     decision --plan-id {plan_id} --level INFO \
     --message "(plan-marshall:planning) planning-lane=light — dispatching ONE collapsed light-lane envelope (refine+outline+derive), skipping the deep refine-loop and Complex-Track outline"
   ```

2. Resolve the dispatch target and dispatch ONE light-lane envelope. The envelope LOADS `plan-marshall:phase-3-outline/workflow/light-lane.md` as its workflow (the doc folds refine-no-loop + Simple-outline + deliverable-derivation, bounds discovery per DQ2, and evaluates the DQ3 escalation ratchet in-context). Resolve the level via the `phase-3-outline` role:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
     effort resolve-target --role phase-3-outline
   ```

   ```
   Task: plan-marshall:{target}
     name: phase-3-outline-light-lane
     plan_id: {plan_id}
     skills[]:
       - plan-marshall:phase-3-outline
     workflow: plan-marshall:phase-3-outline/workflow/light-lane.md
     WORKTREE: .
   ```

3. **Inspect the light-lane return** for the escalation signal:
   - **`outcome: escalate_to_deep`** (the DQ3 ratchet fired — the envelope already set `planning_lane=deep` + `lane_escalated=true` via `manage-status planning-lane escalate`): the orchestrator OWNS the deep-lane re-dispatch (the leaf cannot self-dispatch). Log the re-dispatch decision, then **fall through to the deep-lane branch below** — run the full refine-loop → outline → plan pipeline fresh from the escalation point:

     ```bash
     python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
       decision --plan-id {plan_id} --level INFO \
       --message "(plan-marshall:planning) light-lane returned escalate_to_deep (trigger={escalation_trigger}) — orchestrator re-dispatching the deep refine→outline→plan pipeline"
     ```

   - **`status: success`** (deliverables derived, no escalation): the light lane has already written `solution_outline.md`, derived the deliverables, and transitioned `3-outline`. Record the `2-refine → 3-outline → 4-plan` boundary metrics from the envelope's `<usage>`, then proceed to **Action: outline** Step 4-plan (task derivation) — the light lane self-derived the outline, so the Complex-Track + q-gate-validation sibling dispatch is skipped (see `planning-outline.md` § lane branch).

**Deep-lane branch** — when `planning_lane == deep` (or the light-lane envelope returned `escalate_to_deep`): run the full phases-2-4 pipeline documented below without modification (the standard refine→outline→plan dispatch chain).

**Phase handshake (verify)**: Before entering 2-refine, verify the captured invariants for the previous phase still match the live state. Stop on `status: drift`.

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake verify \
  --plan-id {plan_id} --phase 1-init --strict
```

Compute the dispatch target via the role resolver. Phases 2-4 always run on the main checkout (the worktree is not materialized until phase-5 Step 2.5), so the dispatch's `WORKTREE:` header is the static main-checkout marker `.`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --role phase-2-refine
```

Extract the `target` field from the TOON output. Use that value as `{target}` in the dispatch and the post-resolve log line below.

Emit the standardized pre-dispatch attempt log line and the post-resolve dispatch log line — see [`ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract for the field semantics and placement rule:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[ATTEMPT] (plan-marshall:plan-marshall) dispatching target={target} role=phase-2-refine plan_id={plan_id}"
```

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
    WORKTREE: .
```

The agent returns confidence + track + scope_estimate + qgate_pending_count + qgate_validation_required in its TOON. The 12-step confidence loop (Steps 3b/3c/8/9/10/11/12) iterates *inside* this single envelope; `AskUserQuestion` in Step 11 propagates to the host UI directly from the subagent (no main-context routing required).

**Post-return q-gate-validation dispatch (conditional)**: Read `qgate_validation_required` from the phase return TOON captured above. When `true` (lesson-derived plan activated Step 13.5's `narrative-vs-code-validator`), dispatch q-gate-validation as a sibling top-level Task at the orchestrator layer — the phase body cannot spawn it because the `Task` tool is unavailable inside an `execution-context-{level}` subagent. When `false` or absent, skip this block and continue to the Post-dispatch contract assertion below.

Resolve the dispatch target via the same role used for phase-2-refine (q-gate-validation tracks the calling phase's default per the manage-config effort contract):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --role phase-2-refine
```

Extract the `target` field. Emit the standardized pre-dispatch attempt log line and the post-resolve dispatch log line:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[ATTEMPT] (plan-marshall:plan-marshall) dispatching target={target} role=q-gate-validation plan_id={plan_id}"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[DISPATCH] (plan-marshall:plan-marshall) target={target} level={level} role=q-gate-validation workflow=plan-marshall:plan-marshall/workflow/q-gate-validation.md plan_id={plan_id}"
```

Dispatch:

```
Task: plan-marshall:{target}
  prompt: |
    name: q-gate-validation
    plan_id: {plan_id}
    skills[6]:
    - plan-marshall:manage-solution-outline
    - plan-marshall:manage-findings
    - plan-marshall:manage-plan-documents
    - plan-marshall:manage-status
    - plan-marshall:manage-architecture
    - plan-marshall:manage-logging
    workflow: plan-marshall:plan-marshall/workflow/q-gate-validation.md
    WORKTREE: .

    activation_context: 2-refine
    validators: [narrative-vs-code-validator]
```

The agent returns `qgate_pending_count` in its TOON. ADD that value to the `qgate_pending_count` already returned by phase-2-refine so the combined aggregate drives the existing 3-iteration auto-loop predicate uniformly. Fold the q-gate-validation `<usage>` data into the per-phase running totals so it lands in the fused `phase-boundary` metrics call below.

**Post-dispatch contract assertion**: phase-2-refine's contract restricts writes to `.plan/local/plans/{plan_id}/**` and `.plan/local/worktrees/{plan_id}/**` (see `plan-marshall:phase-2-refine` § Enforcement → Allowed write paths). Refine reaching for `Edit` / `Write` against the main checkout is a recurring failure mode (see `feedback_phase2_refine_never_implements`) that silently advances the orchestrator into phase-3-outline with main-checkout drift. Assert structurally that the main checkout is clean before advancing:

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

**Violation branch** — non-empty output (refine wrote to the main checkout). The orchestrator MUST emit a `[CRITICAL]` work-log entry naming each modified file, return the structured error TOON, and refuse to advance to phase-3-outline.

`{file_list}` is assembled from the `git -C . status --porcelain` output captured in the "Check main checkout" call above — join the non-empty lines of that output (the porcelain lines already carry the `XY path` status-and-path encoding) into a single space- or comma-separated string and substitute it into both the log message and the error TOON below:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR \
  --message "[CRITICAL] (plan-marshall:plan-marshall) Refine contract violation — main checkout dirty after phase-2-refine dispatch: {file_list}"
```

Return:

```toon
status: error
error: refine_contract_violation
display_detail: "refine dispatched edits to main checkout"
plan_id: {plan_id}
dirty_files: {file_list}
```

Do NOT call `manage-status transition` to 3-outline. Do NOT proceed with the metrics fused-call. The orchestrator stops here; recovery requires the user to inspect the offending files and either revert them or move them into `.plan/local/plans/{plan_id}/**`.

**Named recovery case — `.plan/marshal.json`**: When `dirty_files` contains `.plan/marshal.json`, output an additional recovery line alongside the generic instruction:

```
Recovery: git checkout -- .plan/marshal.json
```

`marshal.json` holds only project-level configuration read by phases; it is never a refine-phase output artifact. Restoring it from HEAD is always safe — refine MUST NOT have touched it (the manage-config mutation prohibition in `plan-marshall:phase-2-refine` § Enforcement → Prohibited actions forbids `set`, `init`, `sync-defaults`, and `sync-plan-defaults` during refine). A dirty `marshal.json` after refine is therefore always a spurious write that safe to revert without losing any refine-phase work.

**Cross-references**:
- `plan-marshall:phase-2-refine` § Enforcement → Allowed write paths — the prohibition this assertion enforces
- `plan-marshall:phase-2-refine` § Enforcement → Prohibited actions — the manage-config mutation prohibition that makes marshal.json restoration always safe
- `feedback_phase2_refine_never_implements` — driving failure history
- `pm-plugin-development:plugin-doctor` analyzer `REFINE_CONTRACT_VIOLATION` (Deliverable 5) — edit-time complement to this runtime assertion

**Metrics**: After refine completes, record the `2-refine → 3-outline` boundary in a single fused call (forwarding the aggregated `<usage>` data from every dispatch that fired inside this phase — the `phase-2-refine` envelope itself plus any q-gate-validation sub-dispatch at Step 13.5 for lesson-derived plans). Sum `total_tokens`, `tool_uses`, and `duration_ms` across each dispatch's `<usage>` tag:
```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics phase-boundary \
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

**Issue-documentation mode — milestone (a): mirror clarification answers**: After refine completes, if the plan originated from a GitHub issue, post each clarification-round answer captured this run back to the originating issue as a comment. This keeps the issue thread synchronized with the refinement dialogue. The hook is a clean no-op when the plan did not originate from an issue.

1. Read the plan's `source` and `source_id` from `request.md`:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \
     --plan-id {plan_id}
   ```

   When `source != issue`, skip the entire hook — no comment is posted.

2. Derive the issue number from `source_id`: split the `source_id` issue URL on `/issues/` and take the first path segment of the tail (the same split the CI providers use, e.g. `https://github.com/org/repo/issues/789` → `789`).

3. For each clarification-round answer captured this run, post it via the path-allocate flow documented in [`tools-integration-ci/standards/issue-operations.md`](../../tools-integration-ci/standards/issue-operations.md) § "Workflow: Comment on Issue" (`ci issue prepare-comment` → Write the body → `ci issue comment --issue {issue_number} --plan-id {plan_id}`). The canonical call shape is the `### issue` block in [`tools-integration-ci/SKILL.md`](../../tools-integration-ci/SKILL.md) § Canonical invocations — do not inline-copy it here.

**Forbidden**: direct `gh` / `glab`. All issue interactions route through `plan-marshall:tools-integration-ci:ci`.

The fused call already recorded the start of `3-outline`; the **Action: outline**
section below MUST NOT call `start-phase 3-outline` again. Continue to
**Action: outline** with the same plan_id.

---

## Action: outline (3-Outline + 4-Plan Phases)

See [`workflow/planning-outline.md`](planning-outline.md) for the full workflow. The outline action runs the 3-outline phase (loaded directly in main context with Q-Gate auto-loop and a user review gate guarded by `plan_without_asking`) and then the 4-plan phase (dispatched via `plan-marshall:execution-context-{level}` with workflow `plan-marshall:phase-4-plan/SKILL.md` under role `phase-4-plan`). Both phases record metrics via fused `phase-boundary` calls and capture phase handshake invariants on completion. After tasks are created, the action either auto-continues to execute or stops based on `execute_without_asking` config.

---

## Action: cleanup

Multi-pass user-facing maintenance: remove completed plans, prune redundant superseded-lesson stubs, prune orphan plan directories, and restore lessons trapped inside stalled lesson-sourced plans. Each destructive or restorative pass confirms with the user before acting.

---

### Step 1: Plan archive cleanup

List completed plans (filter `complete`). For each entry, present a numbered selection via `AskUserQuestion` and call `manage-status archive` for confirmed entries.

**1a — List completed plans:**

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status list --filter complete
```

Parse the result. If the list is empty, log and continue to Step 2:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO \
  --message "(plan-marshall:plan-marshall:cleanup) No completed plans to archive — skipping plan archive pass"
```

**1b — Confirm and archive:** When the list is non-empty, present the entries via `AskUserQuestion` (multiSelect: true) and for each selected plan_id call:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status archive \
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
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status list-orphans
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

  Then remove the directory through the managed API:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-status:manage-status delete-plan \
    --plan-id {id}
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

  For each confirmed orphan, log the decision and remove the directory through the managed API:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id global --level INFO \
    --message "(plan-marshall:plan-marshall:cleanup) Removed non-empty orphan directory {id} ({path}) at user confirmation — contents: {contents}"
  ```

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-status:manage-status delete-plan \
    --plan-id {id}
  ```

  For each non-empty orphan the user declined, log the decline:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id global --level INFO \
    --message "(plan-marshall:plan-marshall:cleanup) Orphan directory {id} ({path}) left in place by user — contents: {contents}"
  ```

---

### Step 4: Stalled-lesson-sourced-plan restore

Restore lessons trapped inside stalled lesson-sourced plans. A lesson-sourced plan relocates its lesson into the plan directory via `convert-to-plan` (`plans/{plan_id}/lesson-{id}.md`), taking it out of the active corpus. If the plan stalls or is abandoned in `5-execute`/`6-finalize` without running `restore-from-plan`, the lesson stays stranded and is silently lost. This pass detects every such plan and restores its lesson(s) to the active corpus. Running `Action: cleanup` over the current corpus therefore doubles as the one-time scan-and-restore over all presently-stalled lesson-sourced plans.

**`restore-from-plan` is the mandatory inverse**: it MUST run before a stalled lesson-sourced plan is dormated or deleted, so its lesson is never stranded.

**4a — Enumerate stalled lesson-sourced plans:**

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list-stalled
```

Parse `stalled_plans[]` from the TOON output. Each entry exposes `plan_id`, `plan_source`, `current_phase`, `phase_status`, `lesson_ids[]`, and `restore_command` (the exact `restore-from-plan --plan-id {plan_id}` invocation). If `stalled_count` is `0`, log and finish the cleanup action:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO \
  --message "(plan-marshall:plan-marshall:cleanup) No stalled lesson-sourced plans to restore — skipping stalled-lesson restore pass"
```

**4b — Confirm and restore:** When `stalled_plans[]` is non-empty, present the entries via `AskUserQuestion` (multiSelect) so the user can pick which stalled plans to restore in one pass:

```
AskUserQuestion:
  question: "Select stalled lesson-sourced plans whose lesson(s) should be restored to the active corpus."
  header: "Restore"
  options:
    # For each stalled plan:
    - label: "{plan_id}"
      description: "stalled in {current_phase} ({phase_status}) — lesson(s): {comma-separated lesson_ids}"
  multiSelect: true
```

For each confirmed plan, invoke `restore-from-plan` to return its lesson(s) to `.plan/local/lessons-learned/`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons restore-from-plan \
  --plan-id {plan_id}
```

Log each restore:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO \
  --message "(plan-marshall:plan-marshall:cleanup) Restored stalled lesson(s) {lesson_ids} from plan {plan_id} to the active corpus"
```

For each stalled plan the user declines, log the decline:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO \
  --message "(plan-marshall:plan-marshall:cleanup) Stalled plan {plan_id} left unrestored by user — lesson(s) {lesson_ids} remain trapped"
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

Emit the standardized pre-dispatch attempt log line and the post-resolve dispatch log line — see [`ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id none --level INFO \
  --message "[ATTEMPT] (plan-marshall:plan-marshall) dispatching target={target} role=phase-1-init (lesson conversion)"
```

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

#### Post-init contract assertion (lesson-sourced)

phase-1-init's generic post-init assertion (see **Action: init** § Post-init contract assertion) is a necessary-but-insufficient gate for a lesson-sourced dispatch: it asserts only that `plan_id` is non-empty and no rogue `pr_url` / `branch` / files-patched payload is present. It does NOT verify that the lesson-source path actually ran. The failure class this guard catches: the dispatch silently ignores `lesson_id`, falls back to its **own agent id** as the `plan_id` (Step 2a's slug derivation never ran), records `source: description` instead of `source: lesson`, and runs `convert-to-plan` (removing the lesson from the corpus) WITHOUT placing the Step 5b plan-dir copy — yet returns a plausible `status: success` TOON that passes the generic assertion. Net effect: a phantom plan whose `request.md` holds the plan_id instead of the lesson body, and a lesson silently gone from the corpus with no plan-dir copy.

Because this dispatch always carries `lesson_id`, the orchestrator MUST run the three additional lesson-source assertions below — after the dispatch returns and BEFORE the auto-continued pipeline advances to phase-2-refine. Capture the dispatched agent's id as `{agent_id}` (the `Task` tool surfaces it on the dispatch) for assertion (b).

**Assertion (a) — `source == lesson`**: read the new plan's `request.md` and assert the recorded `source` is `lesson` (not `description`). A `description` source is the structural tell that the lesson-source path was skipped:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id}
```

Parse the `source` field from the returned `content`. Assertion (a) fails when `source != lesson`.

**Assertion (b) — `plan_id` is not an agent-id pattern**: a real lesson plan_id is a title-derived kebab slug; an agent-id-shaped value (hex-only, no hyphens or word segments — matching `^[0-9a-f]{12,}$`) means Step 2a's slug derivation fell through and the agent mis-registered its own id as the plan. Assertion (b) fails when `plan_id` matches `^[0-9a-f]{12,}$` OR `plan_id == {agent_id}`.

**Assertion (c) — Step 5b post-condition file exists**: the lesson file MUST have been relocated into the plan directory by `convert-to-plan`. Assert it exists on disk via the managed API:

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files exists \
  --plan-id {plan_id} --file lesson-{lesson_id}.md
```

Parse `exists` from the output. Assertion (c) fails when `exists: false` — the lesson was removed from the corpus but no plan-dir copy was placed (the orphaning failure mode).

**Success branch** — all three assertions pass (`source == lesson`, `plan_id` is a non-agent-id slug, the plan-dir lesson file exists):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (plan-marshall:plan-marshall) Post-init lesson-source assertion passed (source=lesson, slug plan_id, plan-dir lesson file present)"
```

Continue to the auto-continued planning pipeline (2-refine etc.).

**Violation branch** — any of the three assertions fails. The orchestrator MUST emit a `[CRITICAL]` work-log entry naming the violated condition, return the structured error TOON, and refuse to advance to phase-2-refine.

`{offending_signal}` names the specific violation: `source=description (expected lesson)` for assertion (a), `agent-id-shaped plan_id: {plan_id}` for assertion (b), or `missing plan-dir lesson file: lesson-{lesson_id}.md` for assertion (c).

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id:-none} --level ERROR \
  --message "[CRITICAL] (plan-marshall:plan-marshall) Lesson-conversion contract violation — phase-1-init silently ignored lesson_id: {offending_signal}"
```

Return:

```toon
status: error
error: init_contract_violation
display_detail: "lesson conversion silently ignored lesson_id"
plan_id: {plan_id}
offending_signal: {offending_signal}
```

Do NOT continue to phase-2-refine. The orchestrator stops here; recovery requires restoring the lesson body to the corpus under a fresh id (`manage-lessons add` + `set-body --file`), deleting the phantom plan (`manage-status delete-plan`), and re-dispatching the conversion with explicit `plan_id` (title slug) and `domain` overrides.

**Cross-references**:
- `plan-marshall:phase-1-init` § Enforcement / Step 2a (plan-id derivation guard) and Step 5b (convert-to-plan post-condition abort) — the skill-level complements to this orchestrator-boundary assertion
- **Action: init** § Post-init contract assertion — the generic post-init guard this lesson-source guard layers on top of

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

Script: `plan-marshall:manage-status:manage-status`

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
