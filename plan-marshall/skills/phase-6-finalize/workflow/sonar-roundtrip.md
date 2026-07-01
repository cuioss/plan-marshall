---
lane:
  class: prunable
  prunable_when: no_code_delta
  cost_size: L
name: default:sonar-roundtrip
description: Sonar analysis roundtrip — fetch new-code issues, triage, then fix or suppress (requires: [ci-complete], so CI must finish before this step runs)
order: 40
requires: [ci-complete]
mutates_source: true
default_on: true
presets:
  - full
implements:
  - plan-marshall:extension-api/standards/ext-point-execution-context-workflow
  - plan-marshall:extension-api/standards/ext-point-finalize-step
configurable:
  - key: touched_file_cleanup
    default: new_code_only
    description: Which surface the Sonar roundtrip success criterion covers — new_code_only anchors on new-code issues == 0; touched_files_zero also sweeps pre-existing issues on the files the plan touched.
  - key: do_transition
    default: false
    description: Gate the server-side SonarCloud dismissal path — false routes FALSE-POSITIVE / WON'T-FIX dispositions through in-code suppression; true re-enables the server-side transition dismissal.
  - key: ce_wait_timeout_seconds
    default: 600
    description: Budget (seconds) for the synchronous in-Python CE-readiness wait performed before enumerating new-code issues.
---

# Sonar Roundtrip

Pure executor for the `sonar-roundtrip` finalize step. Drives the consumer-side dispatch for `sonar-issue` findings as defined in [`findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md) — this document owns the step list (producer fetch+store, per-finding decision loop, intra-finalize re-capture, mark-step-done). Refer to [`findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md) for the architecture-level synthesis (producers, store schema, invariant gate, extension contract).

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `sonar-roundtrip` in `manifest.phase_6.steps`. When the dispatcher runs this step, the document executes top to bottom — there is no skip-conditional branching at this layer.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

## Timeout Contract

This step runs as inline orchestration (producer fetch + finding enumeration in main context) plus a single `verification-feedback` Task dispatch (`plan-marshall:execution-context-{level}` resolved via `manage-config effort resolve-target --phase phase-6-finalize --role verification-feedback`) under a **15-minute (900 s) per-agent timeout budget** enforced by the SKILL.md Step 3 dispatch loop. The budget covers the full roundtrip: producer fetch+store, the per-finding triage dispatch with `producer=sonar` (one envelope, smart grouping inside — see `plan-marshall:plan-marshall/workflow/verification-feedback.md`), optional fix-task creation, and (on loop-back) the `manage-status set-phase --phase 5-execute` handoff.

**Graceful degradation**: When the wrapper expires:

1. The dispatcher logs an ERROR entry at `[ERROR] (plan-marshall:phase-6-finalize) Step default:sonar-roundtrip timed out after 900s — marking failed and continuing`.
2. The dispatcher marks this step `failed` via `manage-status mark-step-done … --outcome failed --display-detail "timed out after 900s"`.
3. The dispatcher continues with the next manifest step. Sonar timeouts MUST NOT block the rest of finalize — knowledge/lessons capture, branch cleanup, archive, and metrics still run.
4. On the next Phase 6 entry, the resumable re-entry check sees `outcome=failed` and retries this step from scratch (one fresh attempt per invocation).

There is no internal soft-timeout, polling cap, or partial-progress checkpoint inside this document — the wrapper is the only timeout authority.

## Inputs

- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). All `sonar`, `ci`, and build script invocations below MUST identify the worktree via either `--plan-id {plan_id}` (preferred — auto-resolves through `manage-status get-worktree-path`) or `--project-dir {worktree_path}` (escape hatch / explicit override) for Bucket B notations; the two flags are mutually exclusive. Bucket A `manage-*` scripts (including `manage-findings`) remain cwd-agnostic and do NOT take routing flags. The `sonar fetch-and-store` producer below takes only `--plan-id {plan_id}` (it does not accept `--project-dir`); examples use the `--plan-id {plan_id}` auto-resolution form throughout.

## Execution

### Producer: stage Sonar issues as findings (entry-point)

**Resolve the active PR number first.** The producer fetch MUST be PR-decoration-scoped so its `new_code_issue_count` is a confirmed PR-scoped new-code total (see `workflow-integration-sonar/SKILL.md` § "sonar.py fetch-and-store" — `--pr` is what makes the enumeration the single authority on PR-scoped new-code issues). Resolve the PR for the worktree branch via the same `ci pr view` surface the rest of finalize uses:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci \
  --plan-id {plan_id} pr view
```

Read `pr_number` from the TOON output. If `ci pr view` returns `status: error` (no PR exists for the branch yet), there is no PR-scoped new-code surface to attest — proceed directly to "Mark Step Complete" Branch C with `Sonar not configured` (no PR scope, nothing to gate).

Then call the producer-side fetch-and-store subcommand once. It performs a synchronous bounded CE-readiness wait, fetches the PR-scoped new-code issues, applies pre-filters (severity floor, file scope, dismissed-status filter), writes one `sonar-issue` finding per surviving issue into the per-plan findings store, and writes one attestation row to the `sonar-scan-summary.jsonl` marker — see `workflow-integration-sonar/SKILL.md` § "Workflow 1: Fetch & Store Issues (Producer-Side)" for the producer contract (CE-wait, verified count, marker artifact); do not inline-copy its decision tables here.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-sonar:sonar \
  fetch-and-store --plan-id {plan_id} --project {sonar_project_key} --pr {pr_number}
```

`--project {sonar_project_key}` is required by the `fetch-and-store` argparse surface — it is the SonarQube/SonarCloud project key (e.g. `com.example:project`). Resolve `{sonar_project_key}` from the Sonar provider configuration via the `workflow-integration-sonar` skill (the project key stored alongside the Sonar credentials/host for this repository). `--pr {pr_number}` threads the resolved PR into the producer's CE-status lookup and new-code enumeration, so a reported `0` is a confirmed PR-scoped zero rather than an unscoped total. The `sonar` notation auto-resolves the worktree via `--plan-id {plan_id}` and does NOT accept a `--project-dir` routing flag; `{plan_id}` is the only worktree-binding flag this producer takes.

The producer is the ONLY surface that fetches and stores `sonar-issue` findings. This document does not classify, decide, or act on issues inline — every consumer-side action below reads from the findings store via `manage-findings list`.

If the producer reports `status: error` because Sonar is not configured for the project (no SonarQube/SonarCloud credentials, no project key), proceed directly to "Mark Step Complete" Branch C with `Sonar not configured`.

### Consumer: enumerate pending sonar-issue findings

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list \
  --plan-id {plan_id} --type sonar-issue --resolution pending
```

If the result's `findings` list is empty, there is nothing to triage — proceed directly to "Handle findings (loop-back)" with `loop_back_needed = false`, then to the "Verified-Scan Marker Gate" below. An empty findings store does NOT by itself prove a clean pass: the terminal success criterion is still the confirmed PR-scoped new-code zero read from the marker (the producer may have stored zero findings because it could not confirm the count — `count_status == undecidable`), so the marker gate is what decides Branch A vs the fail-closed path.

### Dispatch the per-finding triage core

When the query above returns one or more pending `sonar-issue` findings, dispatch the unified feedback workflow [`verification-feedback.md`](../../plan-marshall/workflow/verification-feedback.md) with `producer=sonar`. That workflow's Step 1 (sonar branch) verifies the store-only query, then delegates the per-finding LLM-judgement core to [`triage.md`](../../plan-marshall/workflow/triage.md) Steps 1-6 — single source of truth for the smart-grouping algorithm, the per-outcome action bodies (FIX / SUPPRESS / ACCEPT / AskUserQuestion), the overflow / timeout handling, and the Scope-Deviation Escalation guard.

The dispatch is **by reference** — the prompt carries `producer=sonar` only; the subagent issues its own `manage-findings list` against the same store as its first workflow step.

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

```text
Task: plan-marshall:{target}
  prompt: |
    name: verification-feedback
    plan_id: {plan_id}
    skills[6]:
    - plan-marshall:manage-findings
    - plan-marshall:manage-tasks
    - plan-marshall:manage-architecture
    - plan-marshall:manage-config
    - plan-marshall:manage-execution-manifest
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

1. The triage dispatch already allocated the fix tasks (see [`triage.md`](../../plan-marshall/workflow/triage.md) § Step 3c FIX action). No further task allocation here.

2. **Conditional `set-phase`** — only call `manage-status set-phase --phase 5-execute` when `loop_back_target == "5-execute"` (full-phase rollback for fix-task-required dispositions). When `loop_back_target == "6-finalize"` (inline replay for inline-fixable dispositions), the persisted `current_phase` stays at `6-finalize` and NO `set-phase` call is issued.

   **Loopback target invariant**: the `set-phase` call below fires ONLY for `loop_back_target == "5-execute"`; the `6-finalize` target leaves `current_phase` untouched. See [SKILL.md § Loop-back Target Contract](../SKILL.md#loop-back-target-contract) for the granularity invariant.

   ```bash
   # IF loop_back_target == "5-execute":
   python3 .plan/execute-script.py plan-marshall:manage-status:manage-status set-phase \
     --plan-id {plan_id} --phase 5-execute
   # IF loop_back_target == "6-finalize": skip the set-phase call entirely.
   ```

3. The intermediate-iteration `mark-step-done --outcome loop_back` call (Branch D in the "Mark Step Complete" section below) MUST forward the same `loop_back_target` value via `--loop-back-target {value}` — this is REQUIRED per the manage-status validation contract (omitting it returns `error: missing_loop_back_target`).

4. Continue until clean or max iterations (3). The dispatcher's Step 3 § 7b loop-back continuation hook reads the persisted `loop_back_target` and routes between full-phase rollback (`5-execute`) and inline replay (`6-finalize`) deterministically.

When the triage dispatch returns `status: success` (every finding closed as SUPPRESS / ACCEPT / `taken_into_account`, or the query returned empty), `loop_back_needed = false` — proceed directly to "Phase Boundary Re-Capture" below.

## Phase Boundary Re-Capture (intra-finalize gate)

Before marking the step complete, run the read-only `phase_handshake findings-check` against the `6-finalize` phase. `findings-check` evaluates ONLY the `pending_findings_blocking_count` invariant — it trips `blocking_findings_present` if any pending blocking-type finding (notably any unresolved `sonar-issue`) remains in the store, which guards the documented `sonar-roundtrip → next` boundary in [`plan-marshall/references/phase-handshake.md`](../../plan-marshall/references/phase-handshake.md#guarded-boundaries). Because it is the single-invariant verb it never runs `phase_steps_complete`, so it cannot short-circuit on `phase_steps_incomplete` at this mid-pipeline checkpoint where downstream finalize steps have not run yet — the failure mode that made the composite `capture` gate inoperative here.

Run the check:

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake findings-check \
  --plan-id {plan_id} --phase 6-finalize
```

**On `status: success`** (no pending blocking-type findings): proceed to "Mark Step Complete" below.

**On `status: error` with `error: query_failed`** (the blocking-findings invariant could not be evaluated — a per-type query failed, typically because the executor was unreachable): the gate fails CLOSED. The boundary is NOT satisfied, so do NOT proceed to the next step. This is an environmental failure with no findings to triage — there is nothing to loop back over. Mark the step `failed` (`mark-step-done … --outcome failed --display-detail "findings-check query_failed (gate unevaluable)"`) so the dispatcher halts the pipeline; the operator re-runs finalize once the environment is healthy and the read-only check re-evaluates on re-entry. Do NOT treat `query_failed` as a clean pass — that would reintroduce the fail-open the single-invariant gate exists to prevent.

**On `status: error` with `error: blocking_findings_present`** (the structured envelope is field-for-field identical to the composite `capture` blocking-findings payload — see [`phase-handshake.md` § Capture-time behavior](../../plan-marshall/references/phase-handshake.md#pending_findings_blocking_count-resolution)):

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

The check is the structural enforcer of "no unresolved sonar-issue findings at the next finalize boundary". Loop-back guidance:

1. Read the offending findings via `manage-findings list --type sonar-issue --resolution pending` (or whichever type the `per_type` map names).
2. For each pending finding, run the per-finding consumer dispatch defined above (load `ext-triage-{domain}`, decide FIX / SUPPRESS / ACCEPT / `AskUserQuestion`, act with the Sonar-specific outcomes — NOSONAR annotation for SUPPRESS, sonar dismiss / comment for ACCEPT — then `manage-findings resolve`). FIX outcomes set `loop_back_needed = true` and re-enter phase-5-execute via the loop-back block in this document; SUPPRESS / ACCEPT / `taken_into_account` resolve in-place without loop-back.
3. After every pending finding is resolved, **re-issue the same `phase_handshake findings-check --phase 6-finalize`** call. The boundary is satisfied only when the check returns `status: success`.
4. Bound the iterations by the existing `sonar-roundtrip` iteration cap (3); on cap exhaustion mark the step `failed` per the dispatcher contract — the boundary remains gated and downstream finalize steps do not run.

**Single-invariant verb, not the composite `capture`**: `findings-check` evaluates the blocking-findings invariant in isolation via [`_handshake_commands.cmd_findings_check`](../../plan-marshall/scripts/_handshake_commands.py), reusing the `pending_findings_blocking_count` capture and its `BlockingFindingsPresent` → structured-error translation. It writes no handshake row and never evaluates `phase_steps_complete`, so the mid-pipeline gate works where the composite `capture` would short-circuit on `phase_steps_incomplete`.

## Verified-Scan Marker Gate (success criterion)

The success condition for this step is **a confirmed PR-scoped new-code issue count of zero after triage** — NOT "the Sonar quality gate reported passed." The gate verdict can report green while new-code issues remain (CE lag, PR-scoping gaps), so the terminal clean pass is anchored on the producer's verified count, read from the `sonar-scan-summary.jsonl` marker the producer wrote during the fetch above.

After the producer fetch and the triage dispatch have resolved all pending `sonar-issue` findings (and the Phase Boundary Re-Capture gate above returned `status: success`), read the **latest** attestation row from the verified-scan marker. The marker lives in the archive-surviving findings directory; its row schema (`count_status`, `new_code_issue_count`, `count_status_reason`, `pr`, `project`, `scanned_sha`, `ts`) is owned by `workflow-integration-sonar/SKILL.md` § "Scan-Summary Marker (sonar-scan-summary.jsonl)" — do not restate it here.

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files read \
  --plan-id {plan_id} --file artifacts/findings/sonar-scan-summary.jsonl
```

Take the last (most recent) JSONL row as the verified-scan attestation for this run. Evaluate the success criterion:

- **Clean pass (Branch A)** — the row exists AND `count_status == confirmed` AND `new_code_issue_count == 0`. Only this combination satisfies the new-code-zero success criterion. Proceed to "Mark Step Complete" Branch A.

- **Fail closed (undecidable or absent marker)** — `count_status == undecidable` (the producer's CE wait timed out or an auth/REST failure blocked confirmation), OR the marker file is absent / carries no row (`manage-files read` returns a not-found / empty result). An undecidable result MUST NOT be treated as a clean pass — an absent marker means "not checked," not "checked, zero issues." Fail closed: mark the step `failed` (`mark-step-done … --outcome failed --display-detail "sonar new-code count {undecidable|marker absent}"`), mirroring the `findings-check` `query_failed` fail-closed handling above. The `--outcome failed` record does NOT take `--head-at-completion`; on the next Phase 6 entry the resumability check sees `outcome=failed` and retries this step from scratch. The dispatcher halts the pipeline; the operator re-runs finalize once CE has settled, and the read-only check re-evaluates on re-entry.

- **Confirmed non-zero after triage (Branch B)** — `count_status == confirmed` AND `new_code_issue_count > 0` after the triage dispatch and any loop-back iterations have run (gate stayed red after max loop-back iterations). Proceed to "Mark Step Complete" Branch B.

**`touched_file_cleanup` knob** — the success criterion's scope is governed by the `default:sonar-roundtrip` step's `touched_file_cleanup` param, read from the plan-local execution-manifest step-params snapshot in a single one-stop call: `manage-execution-manifest step-params get --plan-id {plan_id} --phase 6-finalize --step-id sonar-roundtrip` (then read `touched_file_cleanup` off the returned `params` object). Under the default `new_code_only` the criterion is the confirmed PR-scoped new-code zero described above. Under `touched_files_zero` the criterion extends to pre-existing issues on touched files — the producer's enumeration (D2) widens accordingly and the same `count_status == confirmed AND new_code_issue_count == 0` predicate then attests the wider set; the marker-read logic here is unchanged. The same one-stop `step-params get` call also yields the step's `do_transition` and `ce_wait_timeout_seconds` params, so no flat `plan.phase-6-finalize.sonar_*` reads remain.

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time. Mark done only on the terminal pass that returns clean (or on a skip); loop-back iterations do not terminate the step.

`sonar-roundtrip` is one of the three HEAD-dependent steps (alongside `pre-push-quality-gate` and `automated-review`) — see [`phase-6-finalize/SKILL.md`](../SKILL.md) Step 3 "Special case — HEAD-dependent steps". Every `--outcome done` branch below MUST capture the worktree HEAD SHA immediately before the `mark-step-done` call and forward it via `--head-at-completion {sha}`, so the dispatcher's HEAD-dependent resumability check can detect a stale `done` record after a future loop-back commit advances HEAD. Loop-back iterations (recorded via `--outcome loop_back` from the "Handle findings (loop-back)" block above) do NOT need to persist the SHA — the dispatcher's general resumability handling for `loop_back` treats it as no-record on re-entry regardless of HEAD.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the Sonar quality gate result. The payload differs by branch:

**Branch A — new-code count confirmed zero** (terminal Sonar pass returns clean — the verified-scan marker gate above reported `count_status == confirmed AND new_code_issue_count == 0` after every finding was closed as SUPPRESS / ACCEPT or the query was empty from the start). Resolve the worktree HEAD before marking done:

```bash
git -C {worktree_path} rev-parse HEAD
```

Capture stdout as `{sha}` and forward via `--head-at-completion`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step sonar-roundtrip --outcome done \
  --display-detail "new-code issues: 0 (confirmed)" \
  --head-at-completion {sha}
```

**Branch B — new-code count confirmed non-zero** (the verified-scan marker gate reported `count_status == confirmed AND new_code_issue_count > 0` after max loop-back iterations; the step still marks `done` because the handshake records that the workflow executed — remediation is deferred to human follow-up). Resolve the worktree HEAD before marking done:

```bash
git -C {worktree_path} rev-parse HEAD
```

Capture stdout as `{sha}` and forward via `--head-at-completion`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step sonar-roundtrip --outcome done \
  --display-detail "new-code issues remain (confirmed)" \
  --head-at-completion {sha}
```

**Branch C — Sonar not configured for project** (the dispatcher ran this step but the producer determined Sonar is not configured — e.g., no SonarQube/SonarCloud credentials, no project key). Resolve the worktree HEAD before marking done:

```bash
git -C {worktree_path} rev-parse HEAD
```

Capture stdout as `{sha}` and forward via `--head-at-completion`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step sonar-roundtrip --outcome done \
  --display-detail "Sonar not configured" \
  --head-at-completion {sha}
```

**Branch D — loop-back recorded** (intermediate pass; used when `loop_back_needed = true` after the "Handle findings (loop-back)" block above). `{iteration}` is the current loop-back iteration number (1..3); `{loop_back_target}` is the granularity classification from the triage dispatch's return TOON (`5-execute` for fix-task-required dispositions, `6-finalize` for inline-fixable). This branch records `--outcome loop_back --loop-back-target {value}` so the Step 3 dispatcher table re-fires the step as a fresh dispatch on next entry AND the continuation hook (§ 7b) routes deterministically. Never record `--outcome done` for an intermediate iteration — `done` is terminal and will cause the dispatcher to skip the step on re-entry. The `loop_back` branch does NOT need `--head-at-completion` but DOES require `--loop-back-target` (per the manage-status validation contract — omitting it returns `error: missing_loop_back_target`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step sonar-roundtrip --outcome loop_back \
  --loop-back-target {5-execute|6-finalize} \
  --display-detail "loop-back iteration {iteration} (target={5-execute|6-finalize})"
```

Note: there is no "config disabled" branch — when the manifest excludes `sonar-roundtrip`, the dispatcher does not run this document at all, so no step record is written.

## Resumability

`sonar-roundtrip` is one of the three HEAD-dependent steps in `HEAD_DEPENDENT_STEPS` (`pre-push-quality-gate`, `automated-review`, `sonar-roundtrip`) — see [`phase-6-finalize/SKILL.md`](../SKILL.md) Step 3 "Special case — HEAD-dependent steps". The HEAD comparison guards against false-clean re-entry after a downstream loop-back commit (typically produced by `automated-review` opening a fix task that produces a new commit, or by a `sonar-roundtrip` iteration's own FIX dispositions on a previous pass) advances HEAD past the validated tree:

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
display_detail: "<new-code issues: {new_code_issue_count} ({count_status}); {fixed} fixed, {suppressed} suppressed, {accepted} accepted>"
new_code_issue_count: {N | null}
count_status: confirmed | undecidable
issues_fetched: {N}
issues_fixed: {N}
issues_suppressed: {N}
issues_accepted: {N}
```

`new_code_issue_count` and `count_status` are read from the latest `sonar-scan-summary.jsonl` marker row (the verified-scan attestation written by the producer); they are the source of the success verdict — `status: success` requires `count_status == confirmed AND new_code_issue_count == 0`, and a `count_status == undecidable` (or absent marker) yields `status: error` (fail closed). The disposition counters (`issues_fixed` / `issues_suppressed` / `issues_accepted`) report how the fetched findings were triaged on the way to that verdict.

Orchestrator workflow — the LLM core is delegated to `verification-feedback` (`producer=sonar`) via the internal sub-dispatch. The `display_detail` value (≤80 chars, ASCII, no trailing period) is forwarded via `mark-step-done --display-detail`. On `loop_back`, the calling step re-fires on the next phase entry per the HEAD-dependent resumability rules above.
