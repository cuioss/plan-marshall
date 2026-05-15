---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Planning Workflow — Action: outline

Workflow for the `outline` action (3-Outline + 4-Plan phases).

> **cwd for `.plan/execute-script.py` calls**: `manage-*` scripts (Bucket A) resolve `.plan/` via `git rev-parse --git-common-dir` and work from any cwd — do **NOT** pin cwd, do **NOT** pass routing flags, and never use `env -C`. Build / CI / Sonar scripts (Bucket B) accept `--plan-id {plan_id}` (preferred — auto-resolves the worktree via `manage-status get-worktree-path`) or `--project-dir {worktree_path}` (escape hatch / explicit override); the two flags are mutually exclusive. See `plan-marshall:tools-script-executor/standards/cwd-policy.md`.

## Action: outline (3-Outline + 4-Plan Phases)

**CRITICAL**: This action has 4 steps. Step 3 is a user review gate controlled by `plan_without_asking` config. If false (default): MANDATORY user review — do NOT skip. If true: Auto-proceed to Step 4.

---

**Step 1**: Read domains from references:
```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get \
  --plan-id {plan_id} --field domains
```

---

**Step 2**: Dispatch the outline phase under role key `phase-3-outline` (single-workflow phase with `track={simple|complex}` runtime input — see [`call-graph.md`](../../ref-workflow-architecture/standards/call-graph.md) § 2.3).

**Metrics**: The start of `3-outline` was already recorded by the
`2-refine → 3-outline` fused boundary call above (or by the
`1-init → 3-outline` boundary when refine was skipped because the action was
entered directly via `outline`). Skip any explicit `start-phase 3-outline`
invocation here — calling it again would clobber the fused timestamp.

When entering this action directly (no preceding refine/init phase in the
same orchestration cycle), use a fused call to close the previous active
phase and start `3-outline`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics phase-boundary \
  --plan-id {plan_id} --prev-phase {prev_phase} --next-phase 3-outline
```

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

Compute the dispatch target via the role resolver and resolve the active worktree path so the Worktree Header can be populated explicitly (when `metadata.use_worktree==false`, `get-worktree-path` returns the main checkout, so the same call covers both flows):

```bash
target=$(python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --role phase-3-outline)

worktree_path=$(python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  get-worktree-path --plan-id {plan_id})
```

Emit the standardized post-resolve dispatch log line — see [`ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[DISPATCH] (plan-marshall:plan-marshall) target={target} level={level} role=phase-3-outline workflow=plan-marshall:phase-3-outline/SKILL.md plan_id={plan_id}"
```

Dispatch:

```
Task: plan-marshall:{target}
  prompt: |
    name: phase-3-outline
    plan_id: {plan_id}
    skills[1]:
    - plan-marshall:phase-3-outline
    workflow: plan-marshall:phase-3-outline/SKILL.md
    WORKTREE: {worktree_path}
```

The agent returns the outline summary (`track`, `deliverable_count`, `qgate_pending_count`, etc.) in its TOON. The Complex-Track per-deliverable loop (Steps 9c + 10 + 10b) iterates *inside* this envelope; the per-deliverable loop never spawns per-iteration subagents.

Log solution outline creation:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[ARTIFACT] (plan-marshall:plan-marshall) Created solution_outline.md - pending user review"
```

**Step 2b**: Q-Gate auto-loop (max 3 iterations)

Check if the phase returned Q-Gate findings. If so, auto-loop without user intervention.

```
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
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status transition \
  --plan-id {plan_id} --completed 3-outline
```

**Metrics**: After outline completes, record the `3-outline → 4-plan` boundary
in a single fused call (forwarding the aggregated `<usage>` data from the
dispatches spawned during this phase — the `phase-3-outline` outline envelope plus
any q-gate-validation dispatch, and any LLM fallback dispatched from
`manage-status:change-type-heuristic` when its heuristic returned
`ambiguous`). Sum `total_tokens`, `tool_uses`, and `duration_ms` across each
dispatch's `<usage>` tag:
```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics phase-boundary \
  --plan-id {plan_id} --prev-phase 3-outline --next-phase 4-plan \
  --total-tokens {sum of total_tokens from all agent <usage> tags} \
  --tool-uses {sum of tool_uses from all agent <usage> tags} \
  --duration-ms {sum of duration_ms from all agent <usage> tags}
```

**Phase handshake**: Capture invariants for the just-completed phase:

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake capture \
  --plan-id {plan_id} --phase 3-outline
```

The fused call already recorded the start of `4-plan`; Step 4 below MUST NOT
call `start-phase 4-plan` again.

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
```
## Solution Outline Created

**Review your solution outline**: .plan/plans/{plan_id}/solution_outline.md

Please review the deliverables and architecture before proceeding.
```

### 3b. Ask the user to confirm or request changes:
```
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
target=$(python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --role phase-4-plan)
```

Emit the standardized post-resolve dispatch log line — see [`ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[DISPATCH] (plan-marshall:plan-marshall) target={target} level={level} role=phase-4-plan workflow=plan-marshall:phase-4-plan/SKILL.md plan_id={plan_id}"
```

Dispatch:

```
Task: plan-marshall:{target}
  prompt: |
    name: phase-4-plan
    plan_id: {plan_id}
    skills[1]:
    - plan-marshall:phase-4-plan
    workflow: plan-marshall:phase-4-plan/SKILL.md
    WORKTREE: {worktree_path}
```

The agent returns the task creation summary (`tasks` array with `domain`, `profile`, `skills`) in its TOON.

**Metrics**: After the plan agent completes, record the `4-plan → 5-execute`
boundary in a single fused call (forwarding the agent's `<usage>` data to
the closing phase):
```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics phase-boundary \
  --plan-id {plan_id} --prev-phase 4-plan --next-phase 5-execute \
  --total-tokens {total_tokens from <usage>} \
  --duration-ms {duration_ms from <usage>} \
  --tool-uses {tool_uses from <usage>}
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
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status transition \
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
