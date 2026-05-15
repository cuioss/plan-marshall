---
name: default:sonar-roundtrip
description: Sonar analysis roundtrip
order: 40
requires: [ci-complete]
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Sonar Roundtrip

Pure executor for the `sonar-roundtrip` finalize step. Drives the consumer-side dispatch for `sonar-issue` findings as defined in [`findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md) — this document owns the step list (producer fetch+store, per-finding decision loop, intra-finalize re-capture, mark-step-done). Refer to [`findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md) for the architecture-level synthesis (producers, store schema, invariant gate, extension contract).

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `sonar-roundtrip` in `manifest.phase_6.steps`. When the dispatcher runs this step, the document executes top to bottom — there is no skip-conditional branching at this layer.

## Timeout Contract

This step runs as inline orchestration (producer fetch + finding enumeration in main context) plus a single `verification-feedback` Task dispatch (`plan-marshall:execution-context-{level}` resolved via `manage-config effort resolve-target --phase phase-6-finalize --role verification-feedback`) under a **15-minute (900 s) per-agent timeout budget** enforced by the SKILL.md Step 3 dispatch loop. The budget covers the full roundtrip: producer fetch+store, the per-finding triage dispatch with `producer=sonar` (one envelope, smart grouping inside — see `plan-marshall:plan-marshall/workflow/verification-feedback.md`), optional fix-task creation, and (on loop-back) the `manage-status set-phase --phase 5-execute` handoff.

**Graceful degradation**: When the wrapper expires:

1. The dispatcher logs an ERROR entry at `[ERROR] (plan-marshall:phase-6-finalize) Step default:sonar-roundtrip timed out after 900s — marking failed and continuing`.
2. The dispatcher marks this step `failed` via `manage-status mark-step-done … --outcome failed --display-detail "timed out after 900s"`.
3. The dispatcher continues with the next manifest step. Sonar timeouts MUST NOT block the rest of finalize — knowledge/lessons capture, branch cleanup, archive, and metrics still run.
4. On the next Phase 6 entry, the resumable re-entry check sees `outcome=failed` and retries this step from scratch (one fresh attempt per invocation).

There is no internal soft-timeout, polling cap, or partial-progress checkpoint inside this document — the wrapper is the only timeout authority.

## Inputs

- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). All `sonar`, `ci`, and build script invocations below MUST identify the worktree via either `--plan-id {plan_id}` (preferred — auto-resolves through `manage-status get-worktree-path`) or `--project-dir {worktree_path}` (escape hatch / explicit override) for Bucket B notations; the two flags are mutually exclusive. Bucket A `manage-*` scripts (including `manage-findings`) remain cwd-agnostic and do NOT take routing flags. Examples below use the literal `--project-dir {worktree_path}` form; substitute `--plan-id {plan_id}` to use auto-resolution.

## Execution

### Producer: stage Sonar issues as findings (entry-point)

Call the producer-side fetch-and-store subcommand once. It pulls Sonar issues for the project (optionally scoped to the active PR), applies pre-filters (severity floor, file scope, dismissed-status filter), and writes one `sonar-issue` finding per surviving issue into the per-plan findings store.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-sonar:sonar \
  --project-dir {worktree_path} fetch-and-store --plan-id {plan_id}
```

The producer is the ONLY surface that fetches and stores `sonar-issue` findings. This document does not classify, decide, or act on issues inline — every consumer-side action below reads from the findings store via `manage-findings query`.

If the producer reports `status: error` because Sonar is not configured for the project (no SonarQube/SonarCloud credentials, no project key), proceed directly to "Mark Step Complete" Branch C with `Sonar not configured`.

### Consumer: enumerate pending sonar-issue findings

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings query \
  --plan-id {plan_id} --type sonar-issue --resolution pending
```

If the result's `findings` list is empty, the gate is clean — proceed directly to "Handle findings (loop-back)" with `loop_back_needed = false`, then "Mark Step Complete" Branch A (`quality gate passed`).

### Dispatch the per-finding triage core

When the query above returns one or more pending `sonar-issue` findings, dispatch the unified feedback workflow [`verification-feedback.md`](../../plan-marshall/workflow/verification-feedback.md) with `producer=sonar`. That workflow's Step 1 (sonar branch) verifies the store-only query, then delegates the per-finding LLM-judgement core to [`triage.md`](../../plan-marshall/workflow/triage.md) Steps 1-6 — single source of truth for the smart-grouping algorithm, the per-outcome action bodies (FIX / SUPPRESS / ACCEPT / AskUserQuestion), the overflow / timeout handling, and the Scope-Deviation Escalation guard.

The dispatch is **by reference** — the prompt carries `producer=sonar` only; the subagent issues its own `manage-findings query` against the same store as its first workflow step.

Compute the target variant via the role resolver, then dispatch:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --phase phase-6-finalize --role verification-feedback
```

Extract the `target` field from the TOON output. Use that value as `{target}` in the dispatch and the post-resolve log line below.

Emit the standardized post-resolve dispatch log line — see [`../../ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[DISPATCH] (plan-marshall:phase-6-finalize) target={target} level={level} role=verification-feedback workflow=plan-marshall:plan-marshall/workflow/verification-feedback.md plan_id={plan_id}"
```

```
Task: plan-marshall:{target}
  prompt: |
    name: verification-feedback
    plan_id: {plan_id}
    skills[5]:
    - plan-marshall:manage-findings
    - plan-marshall:manage-tasks
    - plan-marshall:manage-architecture
    - plan-marshall:manage-config
    - plan-marshall:workflow-integration-sonar
    workflow: plan-marshall:plan-marshall/workflow/verification-feedback.md

    producer: sonar
    caller_phase: phase-6-finalize

    WORKTREE: {worktree_path}
```

For Sonar findings, the loaded `ext-triage-{domain}` skill's `severity.md` and `suppression.md` documents are the load-bearing inputs to the per-finding decision (the `pr-comment-disposition.md` table is PR-comment-specific). The triage workflow's "ACCEPT" action body for `sonar-issue` dispatches Sonar dismissal via `workflow-integration-sonar` (per the skill's standards) rather than a PR thread reply.

When the subagent returns `status: loop_back` it has created fix tasks (FIX outcomes), filed an overflow envelope, or both — proceed to "Handle findings (loop-back)" with `loop_back_needed = true`. When it returns `status: success` every finding resolved as SUPPRESS / ACCEPT / `taken_into_account` (no FIX, no overflow) — proceed with `loop_back_needed = false`.

### Handle findings (loop-back)

**On `loop_back` return from the triage dispatch** (one or more `sonar-issue` findings closed with `--resolution fixed` and a fix-task reference, an overflow envelope was filed, OR all findings were inline-fixable but the calling step needs replay), `loop_back_needed = true`. Read `loop_back_target` from the triage dispatch's return TOON (REQUIRED on every `status: loop_back` return per [`triage.md`](../../plan-marshall/workflow/triage.md) § Step 7):

1. The triage dispatch already allocated the fix tasks (see [`triage.md`](triage.md) § Step 3c FIX action). No further task allocation here.

2. **Conditional `set-phase`** — only call `manage-status set-phase --phase 5-execute` when `loop_back_target == "5-execute"` (full-phase rollback for fix-task-required dispositions). When `loop_back_target == "6-finalize"` (inline replay for inline-fixable dispositions), the persisted `current_phase` stays at `6-finalize` and NO `set-phase` call is issued.

   **Loopback target invariant**: the `set-phase` call below fires ONLY for `loop_back_target == "5-execute"`; the `6-finalize` target leaves `current_phase` untouched. See [SKILL.md § Loop-back Target Contract](../SKILL.md#loop-back-target-contract) for the granularity invariant.

   ```bash
   # IF loop_back_target == "5-execute":
   python3 .plan/execute-script.py plan-marshall:manage-status:manage_status set-phase \
     --plan-id {plan_id} --phase 5-execute
   # IF loop_back_target == "6-finalize": skip the set-phase call entirely.
   ```

3. The intermediate-iteration `mark-step-done --outcome loop_back` call (Branch D in the "Mark Step Complete" section below) MUST forward the same `loop_back_target` value via `--loop-back-target {value}` — this is REQUIRED per the manage-status validation contract (omitting it returns `error: missing_loop_back_target`).

4. Continue until clean or max iterations (3). The dispatcher's Step 3 § 7b loop-back continuation hook reads the persisted `loop_back_target` and routes between full-phase rollback (`5-execute`) and inline replay (`6-finalize`) deterministically.

When the triage dispatch returns `status: success` (every finding closed as SUPPRESS / ACCEPT / `taken_into_account`, or the query returned empty), `loop_back_needed = false` — proceed directly to "Phase Boundary Re-Capture" below.

## Phase Boundary Re-Capture (intra-finalize gate)

Before marking the step complete, re-issue the `phase_handshake capture` against the `6-finalize` phase. The orchestrator's `_BLOCKING_BOUNDARIES` set guards `6-finalize` — re-issuing capture here trips `BlockingFindingsPresent` if any pending blocking-type finding (notably any unresolved `sonar-issue`) remains in the store, which guards the documented `sonar-roundtrip → next` boundary in [`plan-marshall/references/phase-handshake.md`](../../plan-marshall/references/phase-handshake.md#guarded-boundaries).

Run the capture:

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake capture \
  --plan-id {plan_id} --phase 6-finalize
```

**On `status: success`** (no pending blocking-type findings): proceed to "Mark Step Complete" below.

**On `status: error` with `error: blocking_findings_present`** (the structured envelope mirrors the TOON shape in [`phase-handshake.md` § Capture-time behavior](../../plan-marshall/references/phase-handshake.md#pending_findings_blocking_count-resolution)):

```toon
status: error
error: blocking_findings_present
plan_id: {plan_id}
phase: 6-finalize
blocking_count: {N}
blocking_types[K]:
  - sonar-issue
  - …
per_type{sonar-issue,…}:
  {N},…
message: "pending_findings_blocking_count failed for phase '6-finalize': …"
```

The capture is the structural enforcer of "no unresolved sonar-issue findings at the next finalize boundary". Loop-back guidance:

1. Read the offending findings via `manage-findings query --type sonar-issue --resolution pending` (or whichever type the `per_type` map names).
2. For each pending finding, run the per-finding consumer dispatch defined above (load `ext-triage-{domain}`, decide FIX / SUPPRESS / ACCEPT / `AskUserQuestion`, act with the Sonar-specific outcomes — NOSONAR annotation for SUPPRESS, sonar dismiss / comment for ACCEPT — then `manage-findings resolve`). FIX outcomes set `loop_back_needed = true` and re-enter phase-5-execute via the loop-back block in this document; SUPPRESS / ACCEPT / `taken_into_account` resolve in-place without loop-back.
3. After every pending finding is resolved, **re-issue the same `phase_handshake capture --phase 6-finalize`** call. The boundary is satisfied only when capture returns `status: success`.
4. Bound the iterations by the existing `sonar-roundtrip` iteration cap (3); on cap exhaustion mark the step `failed` per the dispatcher contract — the boundary remains gated and downstream finalize steps do not run.

**No `_BLOCKING_BOUNDARIES` change required**: re-issuing capture under the `6-finalize` phase value reuses the existing single-phase guard from [`_invariants.py`](../../plan-marshall/scripts/_invariants.py).

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time. Mark done only on the terminal pass that returns clean (or on a skip); loop-back iterations do not terminate the step.

`sonar-roundtrip` is one of the three HEAD-dependent steps (alongside `pre-push-quality-gate` and `automated-review`) — see [`phase-6-finalize/SKILL.md`](../SKILL.md) Step 3 "Special case — HEAD-dependent steps". Every `--outcome done` branch below MUST capture the worktree HEAD SHA immediately before the `mark-step-done` call and forward it via `--head-at-completion {sha}`, so the dispatcher's HEAD-dependent resumability check can detect a stale `done` record after a future loop-back commit advances HEAD. Loop-back iterations (recorded via `--outcome loop_back` from the "Handle findings (loop-back)" block above) do NOT need to persist the SHA — the dispatcher's general resumability handling for `loop_back` treats it as no-record on re-entry regardless of HEAD.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the Sonar quality gate result. The payload differs by branch:

**Branch A — quality gate passed** (terminal Sonar pass returns clean — every finding closed as SUPPRESS / ACCEPT, or the query was empty from the start). Resolve the worktree HEAD before marking done:

```bash
git -C {worktree_path} rev-parse HEAD
```

Capture stdout as `{sha}` and forward via `--head-at-completion`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step sonar-roundtrip --outcome done \
  --display-detail "quality gate passed" \
  --head-at-completion {sha}
```

**Branch B — quality gate failed** (gate stayed red after max loop-back iterations; the step still marks `done` because the handshake records that the workflow executed — remediation is deferred to human follow-up). Resolve the worktree HEAD before marking done:

```bash
git -C {worktree_path} rev-parse HEAD
```

Capture stdout as `{sha}` and forward via `--head-at-completion`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step sonar-roundtrip --outcome done \
  --display-detail "quality gate failed" \
  --head-at-completion {sha}
```

**Branch C — Sonar not configured for project** (the dispatcher ran this step but the producer determined Sonar is not configured — e.g., no SonarQube/SonarCloud credentials, no project key). Resolve the worktree HEAD before marking done:

```bash
git -C {worktree_path} rev-parse HEAD
```

Capture stdout as `{sha}` and forward via `--head-at-completion`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step sonar-roundtrip --outcome done \
  --display-detail "Sonar not configured" \
  --head-at-completion {sha}
```

**Branch D — loop-back recorded** (intermediate pass; used when `loop_back_needed = true` after the "Handle findings (loop-back)" block above). `{iteration}` is the current loop-back iteration number (1..3); `{loop_back_target}` is the granularity classification from the triage dispatch's return TOON (`5-execute` for fix-task-required dispositions, `6-finalize` for inline-fixable). This branch records `--outcome loop_back --loop-back-target {value}` so the Step 3 dispatcher table re-fires the step as a fresh dispatch on next entry AND the continuation hook (§ 7b) routes deterministically. Never record `--outcome done` for an intermediate iteration — `done` is terminal and will cause the dispatcher to skip the step on re-entry. The `loop_back` branch does NOT need `--head-at-completion` but DOES require `--loop-back-target` (per the manage-status validation contract — omitting it returns `error: missing_loop_back_target`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step sonar-roundtrip --outcome loop_back \
  --loop-back-target {5-execute|6-finalize} \
  --display-detail "loop-back iteration {iteration} (target={5-execute|6-finalize})"
```

Note: there is no "config disabled" branch — when the manifest excludes `sonar-roundtrip`, the dispatcher does not run this document at all, so no step record is written.

## Resumability

`sonar-roundtrip` is one of the three HEAD-dependent steps in `HEAD_DEPENDENT_STEPS` (`pre-push-quality-gate`, `automated-review`, `sonar-roundtrip`) — see [`phase-6-finalize/SKILL.md`](../SKILL.md) Step 3 "Special case — HEAD-dependent steps". The HEAD comparison guards against false-clean re-entry after a downstream loop-back commit (typically produced by `automated-review` opening a fix task that produces a new commit, or by an earlier `sonar-roundtrip` iteration's own FIX dispositions) advances HEAD past the validated tree:

| Persisted state | Live worktree HEAD | Action |
|-----------------|--------------------|--------|
| `outcome == done` AND `head_at_completion == HEAD` | matches | SKIP (steady-state — Sonar already cleared this exact tree) |
| `outcome == done` AND `head_at_completion != HEAD` | differs | RE-FIRE (treat as no record — HEAD has advanced past the validated SHA; re-fetch Sonar issues and re-triage against the new tree) |
| `outcome == done` AND `head_at_completion` absent | n/a | RE-FIRE (record is incomplete without a SHA; safe default is to re-run) |
| `outcome == failed` | n/a | RETRY (unchanged — same as the general rule) |
| `outcome == loop_back` | n/a | RE-FIRE (treat as no record — same as the general rule for loop_back) |
| no record | n/a | DISPATCH (unchanged — same as the general rule) |

## Output

```toon
status: success | error | loop_back
display_detail: "<{N} issues, {fixed} fixed, {suppressed} suppressed, {accepted} accepted>"
issues_fetched: {N}
issues_fixed: {N}
issues_suppressed: {N}
issues_accepted: {N}
```

Orchestrator workflow — the LLM core is delegated to `verification-feedback` (`producer=sonar`) via the internal sub-dispatch. The `display_detail` value (≤80 chars, ASCII, no trailing period) is forwarded via `mark-step-done --display-detail`. On `loop_back`, the calling step re-fires on the next phase entry per the HEAD-dependent resumability rules above.
