---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Planning Workflow — Action: outline

Workflow for the `outline` action (3-Outline + 4-Plan phases).

> **cwd for `.plan/execute-script.py` calls**: `manage-*` scripts resolve `.plan/` via the uniform cwd walk-up (ADR-002) — the nearest ancestor of cwd containing `.plan/local`. The orchestrator runs on the main checkout in phases 1-4 (resolving main's `.plan/`) and pins cwd to the worktree in phase-5+ (resolving the moved-in worktree copy); do **NOT** pass routing flags to `manage-*`, and never use `env -C`. Build / CI / Sonar scripts accept `--plan-id {plan_id}` (preferred — auto-resolves the worktree itself) or `--project-dir {worktree_path}` (escape hatch / explicit override); the two flags are mutually exclusive. See `plan-marshall:tools-script-executor/standards/cwd-policy.md`.

## Action: outline (3-Outline + 4-Plan Phases)

**CRITICAL**: This action has 4 steps. Step 3 is a user review gate controlled by `plan_without_asking` config. If false (default): MANDATORY user review — do NOT skip. If true: Auto-proceed to Step 4.

### Inline early-phase path (Tier 1 recipe-match-routed shortcut)

When the Tier 1 recipe-match path short-circuited the plan onto a known recipe transformation (see [`planning.md`](planning.md) § Action: init → **Inline early-phase path (Tier 1 recipe-match-routed shortcut)** for the routed-shortcut detection — `auto_route_recipe == true` AND a non-empty `status.metadata.recipe_key`), this outline action honors the routed shortcut: the orchestrator runs the outline **inline in its own context** rather than dispatching a separate phase-3-outline execution-context envelope, and reserves an execution-context dispatch for phase-5-execute only. There is NO separate outline dispatch (and no q-gate-validation sibling dispatch) when the recipe path short-circuits — the recipe's own outline shape is already determined by the matched transformation.

To honor the shortcut, read whether a routed recipe was persisted at init:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} --get --field recipe_key
```

When `recipe_key` is non-empty AND `auto_route_recipe == true` (the same gate read in `planning.md`), follow the recipe outline path inline (no Step-2 phase-3-outline dispatch); otherwise run the standard Step-2 dispatch chain below. The routed shortcut changes only the dispatch topology (inline vs per-phase execution-context dispatch); the Q-Gate auto-loop, user review gate, and phase transitions still apply to the inline outline.

---

**Step 1**: Read domains from references:
```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get \
  --plan-id {plan_id} --field domains
```

---

**Step 2**: Dispatch the outline phase under role key `phase-3-outline` (single-workflow phase with `track={simple|complex}` runtime input — see [`call-graph.md`](../../ref-workflow-architecture/standards/call-graph.md) § 2.3).

**Planning-lane branch (light skips this Step-2 dispatch entirely).** Read `status.metadata.planning_lane`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} --get --field planning_lane
```

- **`planning_lane == light`** → the [light-lane envelope](../../phase-3-outline/workflow/light-lane.md) dispatched from `planning.md` ALREADY self-derived the outline (it folds Simple-outline + deliverable-derivation in one envelope and wrote `solution_outline.md` + transitioned `3-outline`). The light lane sets `qgate_validation_required: false` — there is NO Complex-Track outline dispatch and NO q-gate-validation sibling dispatch on the light lane. Skip the entire Step-2 phase-3-outline dispatch + the **Post-return q-gate-validation dispatch** block below; proceed directly to **Step 3 (USER REVIEW GATE)** to display the light-lane-derived outline. (On a light-lane `escalate_to_deep` return, `planning.md` already flipped the lane to `deep` and re-entered the deep pipeline, so this read sees `deep`.)
- **`planning_lane == deep`** (or absent) → run today's full Complex-Track dispatch below, guarded by `plan.phase-3-outline.qgate` (the q-gate-validation sibling dispatch is suppressed when that gate resolves to `never`).

**Metrics**: The start of `3-outline` was already recorded by the
`2-refine → 3-outline` fused boundary call above (or by the
`1-init → 3-outline` boundary when refine was skipped because the action was
entered directly via `outline`). Skip any explicit `start-phase 3-outline`
invocation here — calling it again would clobber the fused timestamp.

When entering this action directly (no preceding refine/init phase in the
same orchestration cycle), use a fused call to close the previous active
phase and start `3-outline`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics phase-boundary \
  --plan-id {plan_id} --prev-phase {prev_phase} --next-phase 3-outline
```

**Resume entry shape (already transitioned, boundary never stamped)**: a third
recognized entry — distinct from entry-via-refine and direct-entry — is a
cross-session resume where the prior session's phase skill already
self-transitioned the status into `3-outline`, so the fused boundary call above
would be the first to *also* stamp metrics, but a no-op transition path may have
skipped it. Before relying on the fused call, reconcile via `boundary-status`;
when it returns `missing`, stamp the boundary explicitly rather than skipping it
because the status was already advanced:

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics boundary-status \
  --plan-id {plan_id} --prev-phase {prev_phase} --next-phase 3-outline
```

(See `manage-metrics` Canonical invocations → `boundary-status`.) On
`classification: missing`, issue the `phase-boundary --prev-phase {prev_phase}
--next-phase 3-outline` call above and log a `[STATUS]` reconciliation decision;
on `stamped` / `not_applicable`, proceed unchanged.

**Phase handshake** (direct-entry variant): capture the just-closed phase:

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake capture \
  --plan-id {plan_id} --phase {prev_phase}
```

**Phase handshake (verify)**: Before entering 3-outline, verify the captured invariants for the previous phase still match the live state. Stop on `status: drift`. Use `2-refine` when entering from the refine path, otherwise the same `{prev_phase}` value used in the fused boundary call above.

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake verify \
  --plan-id {plan_id} --phase {prev_phase} --strict
```

Compute the dispatch target via the role resolver. Phases 2-4 always run on the main checkout (the worktree is not materialized until phase-5 Step 2.5), so the dispatch's `WORKTREE:` header is the static main-checkout marker `.`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --role phase-3-outline
```

Extract the `target` field from the TOON output. Use that value as `{target}` in the dispatch and the post-resolve log line below.

Emit the standardized post-resolve dispatch log line — see [`ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[DISPATCH] (plan-marshall:plan-marshall) target={target} level={level} role=phase-3-outline workflow=plan-marshall:phase-3-outline/SKILL.md plan_id={plan_id}"
```

Dispatch:

```text
Task: plan-marshall:{target}
  prompt: |
    name: phase-3-outline
    plan_id: {plan_id}
    skills[1]:
    - plan-marshall:phase-3-outline
    workflow: plan-marshall:phase-3-outline/SKILL.md
    WORKTREE: .
```

The agent returns the outline summary (`track`, `deliverable_count`, `qgate_pending_count`, `qgate_validation_required`, etc.) in its TOON. The Complex-Track per-deliverable loop (Steps 9c + 10 + 10b) iterates *inside* this envelope; the per-deliverable loop never spawns per-iteration subagents.

**Post-return q-gate-validation dispatch (conditional, deep lane only)**: Read `qgate_validation_required` from the phase return TOON captured above. When `true` (the surgical-bypass predicate did NOT fire in Step 11) AND `plan.phase-3-outline.qgate != never` (read via `manage-config plan phase-3-outline get --field qgate`), dispatch q-gate-validation as a sibling top-level Task at the orchestrator layer — the phase body cannot spawn it because the `Task` tool is unavailable inside an `execution-context-{level}` subagent. When `false` (bypass fired or recipe path short-circuited), when the plan ran the light lane (which sets `qgate_validation_required: false`), or when the `plan.phase-3-outline.qgate` gate resolves to `never` (the operator opted out at config-set time), skip this block and continue directly to "Log solution outline creation" below.

Resolve the dispatch target via the same role used for phase-3-outline (q-gate-validation tracks the calling phase's default):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --role phase-3-outline
```

Extract the `target` field. Emit the standardized post-resolve dispatch log line:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[DISPATCH] (plan-marshall:plan-marshall) target={target} level={level} role=phase-3-outline workflow=plan-marshall:plan-marshall/workflow/q-gate-validation.md plan_id={plan_id}"
```

Dispatch:

```text
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

    activation_context: 3-outline
```

The agent returns `qgate_pending_count` in its TOON. ADD that value to the `qgate_pending_count` already returned by phase-3-outline so the combined aggregate drives the Step 2b auto-loop predicate uniformly. Fold the q-gate-validation `<usage>` data into the per-phase running totals so it lands in the fused `phase-boundary` metrics call below.

Log solution outline creation:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[ARTIFACT] (plan-marshall:plan-marshall) Created solution_outline.md - pending user review"
```

**Step 2b**: Q-Gate auto-loop (max 3 iterations)

Check if the phase returned Q-Gate findings. If so, auto-loop without user intervention.

```text
qgate_iteration = 0
MAX_QGATE_ITERATIONS = 3

WHILE qgate_pending_count > 0 AND qgate_iteration < MAX_QGATE_ITERATIONS:
  qgate_iteration += 1
  1. Log: "(plan-marshall:plan-marshall:qgate) Auto-fix iteration {qgate_iteration}/{MAX_QGATE_ITERATIONS}: {count} findings — re-dispatching phase-3-outline"
  2. Re-dispatch phase-3-outline via the same Task: plan-marshall:{target} envelope used in Step 2 (phase reads findings at Step 1 and addresses them)
  3. Check qgate_pending_count from phase return

IF qgate_pending_count > 0 AND qgate_iteration >= MAX_QGATE_ITERATIONS:
  → STOP: Escalate to user — "Q-Gate auto-loop exhausted after {MAX_QGATE_ITERATIONS} iterations. {count} findings remain unresolved."
  → Present remaining findings and ask user how to proceed
```

This loop runs automatically — do NOT prompt the user for Q-Gate findings unless the max iteration limit is reached. Q-Gate findings are objective quality failures that the phase must self-correct. Only proceed to Step 2c when `qgate_pending_count == 0`.

**Step 2c**: Transition phase after outline completes AND Q-Gate is clean:
```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status transition \
  --plan-id {plan_id} --completed 3-outline
```

**Metrics**: After outline completes, record the `3-outline → 4-plan` boundary
in a single fused call (forwarding the aggregated `<usage>` data from every
dispatch spawned during this phase — the `phase-3-outline` outline envelope,
the sibling orchestrator-level q-gate-validation dispatch above when
`qgate_validation_required` was `true`, and any LLM fallback dispatched from
`manage-status:change-type-heuristic` when its heuristic returned
`ambiguous`). Sum `total_tokens`, `tool_uses`, and `duration_ms` across each
dispatch's `<usage>` tag:
```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics phase-boundary \
  --plan-id {plan_id} --prev-phase 3-outline --next-phase 4-plan \
  --total-tokens {sum of total_tokens from all agent <usage> tags} \
  --tool-uses {sum of tool_uses from all agent <usage> tags} \
  --duration-ms {sum of duration_ms from all agent <usage> tags}
```

**Resume-reconciliation guard at this boundary**: when the orchestrator reaches
this `3-outline → 4-plan` transition on a cross-session resume where the
transition was already advanced by the prior session (so the fused call above is
the first to *also* stamp metrics), reconcile via `boundary-status --prev-phase
3-outline --next-phase 4-plan` before relying on the fused call. On
`classification: missing`, issue the `phase-boundary --prev-phase 3-outline
--next-phase 4-plan` call above (omitting the `<usage>` flags when no in-cycle
dispatch totals are available) and log a `[STATUS]` reconciliation decision; on
`stamped` / `not_applicable`, the in-cycle fused call already covers the
boundary — proceed unchanged. See `manage-metrics` Canonical invocations →
`boundary-status`.

**Phase handshake**: Capture invariants for the just-completed phase:

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake capture \
  --plan-id {plan_id} --phase 3-outline
```

The fused call already recorded the start of `4-plan`; Step 4 below MUST NOT
call `start-phase 4-plan` again.

**Issue-documentation mode — milestone (b): mirror the outline**: After the 3-outline phase has completed and `solution_outline.md` exists, if the plan originated from a GitHub issue, post the outline's `## Summary` and `## Overview` sections (NOT the Deliverables) to the originating issue as one comment, so the issue thread reflects the proposed solution shape before implementation begins. The hook is a clean no-op when the plan did not originate from an issue.

1. Read `source` and `source_id` from `request.md`:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \
     --plan-id {plan_id}
   ```

   When `source != issue`, skip the entire hook — no comment is posted.

2. Derive the issue number from `source_id` by splitting the issue URL on `/issues/` and taking the first path segment of the tail.

3. Read the outline's `## Summary` and `## Overview` sections only (exclude Deliverables) via `manage-solution-outline read`, then post them as a single comment via the path-allocate flow documented in [`tools-integration-ci/standards/issue-operations.md`](../../tools-integration-ci/standards/issue-operations.md) § "Workflow: Comment on Issue" (`ci issue prepare-comment` → Write the body → `ci issue comment --issue {issue_number} --plan-id {plan_id}`). The canonical call shape is the `### issue` block in [`tools-integration-ci/SKILL.md`](../../tools-integration-ci/SKILL.md) § Canonical invocations — do not inline-copy it here.

**Forbidden**: direct `gh` / `glab`. All issue interactions route through `plan-marshall:tools-integration-ci:ci`.

**Step 2d**: Auto-open solution outline in IDE for user review:

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files open-in-ide \
  --plan-id {plan_id} --document solution_outline
```

The verb resolves the solution outline path internally, detects the active IDE from `__CFBundleIdentifier` / `TERM_PROGRAM` + host platform, and dispatches the appropriate launcher (no `TERM_PROGRAM` parsing in this workflow, no per-platform forks, no `open` / `xdg-open` fallback). On unknown IDE the verb exits non-zero with `reason: ide_not_detected` rather than silently routing through the OS file-association handler. The verb is gated by `plan.open_in_ide.enabled` in `.plan/marshal.json` (default `true`); when disabled it returns `status: success, action: skipped` and does nothing. See the `plan-marshall:manage-files` skill (Operations → open-in-ide) for the supported IDE matrix and TOON return shapes.

---

## Step 3: USER REVIEW GATE

The outline presented here has already passed Q-Gate verification. The user reviews the quality-verified outline.

**Config check** — Read `plan_without_asking` to determine gate behavior:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-3-outline get --field plan_without_asking --audit-plan-id {plan_id}
```

**IF `plan_without_asking == true`**:
- Log: `"(plan-marshall:plan-marshall) Config: plan_without_asking=true — auto-proceeding to task creation"`
- Skip Steps 3a-3c, continue directly to Step 4

**ELSE (default)**: **STOP HERE. Do NOT proceed to Step 4 without user approval.**

### 3a. Read and display the solution outline for review:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline read \
  --plan-id {plan_id}
```

Then display:
```text
## Solution Outline Created

**Review your solution outline**: .plan/plans/{plan_id}/solution_outline.md

Please review the deliverables and architecture before proceeding.
```

### 3b. Ask the user to confirm or request changes:
```text
AskUserQuestion:
  questions:
    - question: "Have you reviewed the solution outline? How would you like to proceed?"
      header: "Review"
      options:
        - label: "Proceed to create tasks"
          description: "Solution outline looks good, continue to task planning"
        - label: "Request changes"
          description: "I have feedback to improve the solution outline"
      multiSelect: false
```

### 3c. Handle user response:
- **If "Proceed to create tasks"**: Continue to Step 4
- **If "Request changes"** or user provides custom feedback:
  - Capture the user's feedback
  - Write each feedback point as a Q-Gate finding:
    ```bash
    python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
      qgate add --plan-id {plan_id} --phase 3-outline --source user_review \
      --type triage --title "User: {feedback summary}" \
      --detail "{full feedback text}"
    ```
  - Log feedback capture:
    ```bash
    python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
      decision --plan-id {plan_id} --level INFO --message "(plan-marshall:plan-marshall) User review: {count} change requests recorded to artifacts/qgate-3-outline.jsonl"
    ```
  - Re-dispatch phase-3-outline via the same Task: plan-marshall:{target} envelope used in Step 2 (phase reads Q-Gate findings at Step 1)
  - **Loop back to Step 3a**

---

**Step 4**: Create tasks from deliverables

Only execute this step AFTER user approves in Step 3.

**Metrics**: The start of `4-plan` was already recorded by the
`3-outline → 4-plan` fused boundary call above — do NOT call
`start-phase 4-plan` here.

**Phase handshake (verify)**: Before entering 4-plan, verify the captured invariants for the previous phase still match the live state. Stop on `status: drift`.

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake verify \
  --plan-id {plan_id} --phase 3-outline --strict
```

Compute the dispatch target via the role resolver:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --role phase-4-plan
```

Extract the `target` field from the TOON output. Use that value as `{target}` in the dispatch and the post-resolve log line below.

Emit the standardized post-resolve dispatch log line — see [`ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[DISPATCH] (plan-marshall:plan-marshall) target={target} level={level} role=phase-4-plan workflow=plan-marshall:phase-4-plan/SKILL.md plan_id={plan_id}"
```

Dispatch:

```text
Task: plan-marshall:{target}
  prompt: |
    name: phase-4-plan
    plan_id: {plan_id}
    skills[1]:
    - plan-marshall:phase-4-plan
    workflow: plan-marshall:phase-4-plan/SKILL.md
    WORKTREE: .
```

The agent returns the task creation summary (`tasks` array with `domain`, `profile`, `skills`) plus `qgate_pending_count` and `qgate_validation_required` in its TOON.

**Dispatch-boundary recording (phase-4-plan dispatch)**: Immediately after the phase-4-plan execution-context Task dispatch returns and BEFORE the conditional q-gate-validation block below, record the termination boundary of the phase-4-plan dispatch itself. The call captures the phase-4-plan agent's return outcome — NOT the combined phase-4+qgate outcome (q-gate-validation, when dispatched, is a sibling orchestrator-level dispatch that records its own boundary independently if instrumented). This call mirrors the existing phase-5-execute dispatch-boundary contract documented in `workflow/execution.md` § "After execution-context returns".

Classify the phase-4-plan return into exactly one of:

| Cause | Detection rule |
|-------|----------------|
| `task_batch_complete` | The agent returned `status: success` with the `tasks` array populated (clean exit — the task creation summary is complete). |
| `voluntary_checkpoint` | The agent returned a non-error payload with `qgate_pending_count > 0` findings still pending, OR emitted a "Returning control to orchestrator" / "progress checkpoint" / "partial-completion handoff" marker. |
| `harness_cancellation` | The dispatch ended with a host-platform cancellation marker (timeout, context-window limit, etc.). |
| `error` | The agent returned a structured error payload via the skill's Error Handling section. |

Issue the call BEFORE any subsequent dispatch (q-gate-validation, phase-boundary, phase_handshake) so the audit trail captures the actual termination order:

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics record-dispatch-boundary \
  --plan-id {plan_id} --phase 4-plan --termination-cause {task_batch_complete|voluntary_checkpoint|harness_cancellation|error} \
  --total-tokens {n} --tool-uses {n} --duration-ms {n}
```

Substitute the `--termination-cause` value with the canonical cause from the table above and `{n}` with the integer parsed from the phase-4-plan agent's `<usage>...</usage>` block (use `0` when the field is absent).

**Post-return q-gate-validation dispatch (conditional)**: Read `qgate_validation_required` from the phase return TOON captured above. When `true` (the default — phase-4-plan signals unconditionally on successful completion per Step 9b), dispatch q-gate-validation as a sibling top-level Task at the orchestrator layer — the phase body cannot spawn it because the `Task` tool is unavailable inside an `execution-context-{level}` subagent. When `false` or absent (unrecoverable error path), skip this block and continue directly to the Metrics fused-call below.

Resolve the dispatch target via the same role used for phase-4-plan (q-gate-validation tracks the calling phase's default):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --role phase-4-plan
```

Extract the `target` field. Emit the standardized post-resolve dispatch log line:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[DISPATCH] (plan-marshall:plan-marshall) target={target} level={level} role=q-gate-validation workflow=plan-marshall:plan-marshall/workflow/q-gate-validation.md plan_id={plan_id}"
```

Dispatch:

```text
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

    activation_context: 4-plan
    validators: [module-mapping-validator, scope-criterion-validator]
```

The agent returns `qgate_pending_count` in its TOON. ADD that value to the `qgate_pending_count` already returned by phase-4-plan so the combined aggregate drives the existing 3-iteration auto-loop predicate uniformly (re-dispatch phase-4-plan via the same envelope used in Step 4 when the combined count is non-zero, up to `max_iterations`). Fold the q-gate-validation `<usage>` data into the per-phase running totals so it lands in the fused `phase-boundary` metrics call below.

**Metrics**: After the plan agent completes, record the `4-plan → 5-execute`
boundary in a single fused call (forwarding the aggregated `<usage>` data
from every dispatch spawned during this phase — the `phase-4-plan` envelope
itself plus the sibling orchestrator-level q-gate-validation dispatch above
when `qgate_validation_required` was `true`):
```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics phase-boundary \
  --plan-id {plan_id} --prev-phase 4-plan --next-phase 5-execute \
  --total-tokens {sum of total_tokens from all agent <usage> tags} \
  --duration-ms {sum of duration_ms from all agent <usage> tags} \
  --tool-uses {sum of tool_uses from all agent <usage> tags}
```

**Phase handshake**: Capture invariants for the just-completed phase. The `5-execute` entry verifies this row before the task loop runs (see `workflow/execution.md`):

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake capture \
  --plan-id {plan_id} --phase 4-plan
```

Log task plan agent invocation:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:plan-marshall) Invoked execution-context for phase-4-plan"
```

**Step 4b**: Transition phase after tasks created:
```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status transition \
  --plan-id {plan_id} --completed 4-plan
```

**Step 4c**: Check `execute_without_asking` config to determine next action:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-4-plan get --field execute_without_asking --audit-plan-id {plan_id}
```

**IF `execute_without_asking == true`**:
- Log: `"(plan-marshall:plan-marshall) Config: execute_without_asking=true — auto-continuing to execute"`
- Load `workflow/execution.md` and follow **Action: execute** with `plan_id`

**ELSE (default)**:
- Display: `"Tasks created. Ready to execute."`
- Display: `"Run '/plan-marshall action=execute plan={plan_id}' when ready."`
- **STOP** (current behavior)

## Output

Top-level orchestrator workflow. Conformance to the ext-point output contract:

```toon
status: success | error
display_detail: "<plan {plan_id} reached {terminal_phase}>"
```

The orchestrator emits this shape when wrapped in a `Task: execution-context-{level}` dispatch.
