---
lane:
  class: adversarial
  cost_size: L
name: default:sonar-roundtrip
description: Sonar analysis roundtrip — FIND-only producer that fetches PR-scoped new-code issues and files sonar-issue findings; the dispatcher-owned unified wait-region triage consumes them. Gated on the sonar barrier arm (requires: [ci-complete] resolved with --signal-arm sonar), so a red Sonar arm STILL FINDs — a red Sonar gate is exactly when its new-code findings exist (the TokenSheriff-572 deadlock fix)
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

Pure **FIND-only** executor for the `sonar-roundtrip` finalize step — one of the two wait-region producers. It drives the producer-side FIND for `sonar-issue` findings as defined in [`findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md) — this document owns the step list (producer FIND via `fetch_findings`, verified-scan marker gate, mark-step-done). It files `sonar-issue` findings to the store and stops there; it dispatches NO triage of its own. The per-finding LLM triage runs ONCE at the dispatcher level as the **Wait-region unified triage** (`producer=finalize-feedback`, over the union of `pr-comment` ∪ `sonar-issue` findings) — see [`../SKILL.md`](../SKILL.md) Step 3 item 7c and [`../../plan-marshall/workflow/verification-feedback.md`](../../plan-marshall/workflow/verification-feedback.md) § "Producer modes". Refer to [`findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md) for the architecture-level synthesis (producers, store schema, invariant gate, extension contract).

**Per-signal sonar-arm gate (the TokenSheriff-572 fix).** The wait-region precondition (`requires: [ci-complete]`) is resolved by the dispatcher on the **sonar arm** (`--signal-arm sonar`), NOT global CI colour. The gate proceeds to FIND once the sonar arm reaches a **terminal** state — including a `failed` (red) arm: a red Sonar gate is exactly when its new-code findings exist, so the old global-CI gate that skipped the FIND on a Sonar-only red CI silently blocked the very signal it should have consumed. Only a `pending` arm (CI not yet terminal) defers the step, and the resumable re-entry check re-fires it. See [`../SKILL.md`](../SKILL.md) Step 3 § "Precondition resolution" (the per-consumer resolution map keys `default:sonar-roundtrip` to the sonar arm).

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `sonar-roundtrip` in `manifest.phase_6.steps`. When the dispatcher runs this step, the document executes top to bottom — there is no skip-conditional branching at this layer.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

## Timeout Contract

This step runs as inline orchestration (producer FIND + verified-scan marker read in main context) under a **FIND-only 15-minute (900 s) per-agent timeout budget** enforced by the SKILL.md Step 3 dispatch loop. The budget covers the producer `fetch_findings` FIND (including its synchronous bounded CE-readiness wait) and the marker read — it does NOT cover triage or RESPOND. The per-finding triage (batched ingest, smart-grouped LLM decision, `sonar post_responses` server-side dismissals, optional fix-task creation, and the loop-back handoff) runs once at the dispatcher level as the unified wait-region triage (`producer=finalize-feedback`), under that dispatch's own budget.

**Graceful degradation**: When the wrapper expires:

1. The dispatcher logs an ERROR entry at `[ERROR] (plan-marshall:phase-6-finalize) Step default:sonar-roundtrip timed out after 900s — marking failed and continuing`.
2. The dispatcher marks this step `failed` via `manage-status mark-step-done … --outcome failed --display-detail "timed out after 900s"`.
3. The dispatcher continues with the next manifest step. Sonar timeouts MUST NOT block the rest of finalize — knowledge/lessons capture, branch cleanup, archive, and metrics still run.
4. On the next Phase 6 entry, the resumable re-entry check sees `outcome=failed` and retries this step from scratch (one fresh attempt per invocation).

There is no internal soft-timeout, polling cap, or partial-progress checkpoint inside this document — the wrapper is the only timeout authority.

## Inputs

- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). All `sonar`, `ci`, and build script invocations below MUST identify the worktree via either `--plan-id {plan_id}` (preferred — auto-resolves through `manage-status get-worktree-path`) or `--project-dir {worktree_path}` (escape hatch / explicit override) for Bucket B notations; the two flags are mutually exclusive. Bucket A `manage-*` scripts (including `manage-findings`) remain cwd-agnostic and do NOT take routing flags. The `sonar fetch_findings` producer below takes only `--plan-id {plan_id}` (it does not accept `--project-dir`); examples use the `--plan-id {plan_id}` auto-resolution form throughout.

## Execution

### Producer: stage Sonar issues as findings (entry-point)

**Resolve the active PR number first.** The producer fetch MUST be PR-decoration-scoped so its `new_code_issue_count` is a confirmed PR-scoped new-code total (see `workflow-integration-sonar/SKILL.md` § "sonar.py fetch_findings" — `--pr` is what makes the enumeration the single authority on PR-scoped new-code issues). Resolve the PR for the worktree branch via the same `ci pr view` surface the rest of finalize uses:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci \
  --plan-id {plan_id} pr view
```

Read `pr_number` from the TOON output. If `ci pr view` returns `status: error` (no PR exists for the branch yet), there is no PR-scoped new-code surface to attest — proceed directly to "Mark Step Complete" Branch C with `Sonar not configured` (no PR scope, nothing to gate).

Then call the producer-side `fetch_findings` verb once (FIND stage). It performs a synchronous bounded CE-readiness wait, fetches the PR-scoped new-code issues, applies pre-filters (severity floor, file scope, dismissed-status filter), files one `sonar-issue` finding per surviving issue into the per-plan findings store with the untrusted Sonar `message` quarantined under `raw_input.{message}`, and writes one attestation row to the `sonar-scan-summary.jsonl` marker — see `workflow-integration-sonar/SKILL.md` § "Workflow 1: Fetch & Store Issues (Producer-Side)" for the producer contract (CE-wait, verified count, marker artifact); do not inline-copy its decision tables here.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-sonar:sonar \
  fetch_findings --plan-id {plan_id} --project {sonar_project_key} --pr {pr_number}
```

`--project {sonar_project_key}` is required by the `fetch_findings` argparse surface — it is the SonarQube/SonarCloud project key (e.g. `com.example:project`). Resolve `{sonar_project_key}` from the Sonar provider configuration via the `workflow-integration-sonar` skill (the project key stored alongside the Sonar credentials/host for this repository). `--pr {pr_number}` threads the resolved PR into the producer's CE-status lookup and new-code enumeration, so a reported `0` is a confirmed PR-scoped zero rather than an unscoped total. The `sonar` notation auto-resolves the worktree via `--plan-id {plan_id}` and does NOT accept a `--project-dir` routing flag; `{plan_id}` is the only worktree-binding flag this producer takes. A `status: unconfigured` return means Sonar is not configured — fail loud (Branch C below), never a silent zero.

This is the FIND stage of the consolidated FIND → INGEST → TRIAGE → RESPOND flow. The producer is the ONLY surface that fetches and files `sonar-issue` findings; the downstream INGEST (batched `manage-findings ingest`), TRIAGE (top-level-only), and RESPOND (`sonar post_responses` server-side dismissals) all run inside the dispatcher-owned unified wait-region triage (`producer=finalize-feedback`), NOT in this step. This document does not classify, decide, respond to, or act on issues inline — it only FINDs and files.

If the producer reports `status: error` because Sonar is not configured for the project (no SonarQube/SonarCloud credentials, no project key), proceed directly to "Mark Step Complete" Branch C with `Sonar not configured`.

### Consumer count (for display only)

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list \
  --plan-id {plan_id} --type sonar-issue --resolution pending
```

Read the `findings` count for the mark-step-done display. This FIND-only step does NOT triage the findings — they remain `pending` in the store for the dispatcher-owned unified wait-region triage (`producer=finalize-feedback`), which consumes the union of pending `pr-comment` ∪ `sonar-issue` findings once both wait-region producers have filed (see [`../SKILL.md`](../SKILL.md) Step 3 item 7c). An empty findings store does NOT by itself prove a clean pass: the terminal success criterion is still the confirmed PR-scoped new-code zero read from the marker (the producer may have stored zero findings because it could not confirm the count — `count_status == undecidable`), so the marker gate below is what decides Branch A vs the fail-closed path.

### Findings await the unified triage (no inline triage, no loop-back, no RESPOND here)

This FIND-only step performs NO triage. The filed `sonar-issue` findings remain `pending` in the store; the dispatcher-owned unified wait-region triage (`producer=finalize-feedback`) consumes them once both wait-region producers have filed — it owns the per-finding LLM decision (FIX / SUPPRESS / ACCEPT / AskUserQuestion), the loop-back on FIX dispositions, the `sonar post_responses` server-side dismissals (gated by `do_transition`), and the pending-findings phase-boundary gate. See [`../SKILL.md`](../SKILL.md) Step 3 item 7c and [`../../plan-marshall/workflow/verification-feedback.md`](../../plan-marshall/workflow/verification-feedback.md) § "Producer modes" (`finalize-feedback`). Because triage is dispatcher-owned, this step never emits a `loop_back` outcome — a fix commit from the unified triage advances HEAD and the resumable re-entry check (HEAD-dependent) re-fires this FIND step against the new tree.

## Verified-Scan Marker Gate (success criterion)

The success condition for this FIND-only step is **a confirmed PR-scoped new-code issue count of zero** — NOT "the Sonar quality gate reported passed." The gate verdict can report green while new-code issues remain (CE lag, PR-scoping gaps), so the terminal clean pass is anchored on the producer's verified count, read from the `sonar-scan-summary.jsonl` marker the producer wrote during the fetch above. Because triage is dispatcher-owned, this gate attests only the producer's FOUND count; a confirmed non-zero count means findings were filed for the unified triage to resolve, not that this step failed.

After the producer fetch, read the **latest** attestation row from the verified-scan marker. The marker lives in the archive-surviving findings directory; its row schema (`count_status`, `new_code_issue_count`, `count_status_reason`, `pr`, `project`, `scanned_sha`, `ts`) is owned by `workflow-integration-sonar/SKILL.md` § "Scan-Summary Marker (sonar-scan-summary.jsonl)" — do not restate it here.

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files read \
  --plan-id {plan_id} --file artifacts/findings/sonar-scan-summary.jsonl
```

Take the last (most recent) JSONL row as the verified-scan attestation for this run. Evaluate the success criterion:

- **Clean pass (Branch A)** — the row exists AND `count_status == confirmed` AND `new_code_issue_count == 0`. Only this combination satisfies the new-code-zero success criterion. Proceed to "Mark Step Complete" Branch A.

- **Fail closed (undecidable or absent marker)** — `count_status == undecidable` (the producer's CE wait timed out or an auth/REST failure blocked confirmation), OR the marker file is absent / carries no row (`manage-files read` returns a not-found / empty result). An undecidable result MUST NOT be treated as a clean pass — an absent marker means "not checked," not "checked, zero issues." Fail closed: mark the step `failed` (`mark-step-done … --outcome failed --display-detail "sonar new-code count {undecidable|marker absent}"`). The `--outcome failed` record does NOT take `--head-at-completion`; on the next Phase 6 entry the resumability check sees `outcome=failed` and retries this step from scratch. The dispatcher halts the pipeline; the operator re-runs finalize once CE has settled.

- **Confirmed non-zero (Branch B)** — `count_status == confirmed` AND `new_code_issue_count > 0`: the producer FOUND new-code issues and filed one `sonar-issue` finding per issue for the unified triage to resolve. Proceed to "Mark Step Complete" Branch B — the FIND succeeded; remediation is owned by the dispatcher-level unified triage.

**`touched_file_cleanup` knob** — the success criterion's scope is governed by the `default:sonar-roundtrip` step's `touched_file_cleanup` param, read from the plan-local execution-manifest step-params snapshot in a single one-stop call: `manage-execution-manifest step-params get --plan-id {plan_id} --phase 6-finalize --step-id sonar-roundtrip` (then read `touched_file_cleanup` off the returned `params` object). Under the default `new_code_only` the criterion is the confirmed PR-scoped new-code zero described above. Under `touched_files_zero` the criterion extends to pre-existing issues on touched files — the producer's enumeration (D2) widens accordingly and the same `count_status == confirmed AND new_code_issue_count == 0` predicate then attests the wider set; the marker-read logic here is unchanged. The same one-stop `step-params get` call also yields the step's `do_transition` and `ce_wait_timeout_seconds` params, so no flat `plan.phase-6-finalize.sonar_*` reads remain.

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time. This FIND-only step marks done on the terminal FIND pass (or fails closed on an undecidable marker); it emits no `loop_back` of its own.

`sonar-roundtrip` is one of the three HEAD-dependent steps (alongside `pre-push-quality-gate` and `plan-marshall:automatic-review`) — see [`phase-6-finalize/SKILL.md`](../SKILL.md) Step 3 "Special case — HEAD-dependent steps". Every `--outcome done` branch below MUST capture the worktree HEAD SHA immediately before the `mark-step-done` call and forward it via `--head-at-completion {sha}`, so the dispatcher's HEAD-dependent resumability check can detect a stale `done` record after a unified-triage fix commit advances HEAD (re-firing this FIND against the new tree).

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the Sonar quality gate result. The payload differs by branch:

**Branch A — new-code count confirmed zero** (terminal FIND pass returns clean — the verified-scan marker gate above reported `count_status == confirmed AND new_code_issue_count == 0`; the producer found no new-code issues). Resolve the worktree HEAD before marking done:

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

**Branch B — new-code count confirmed non-zero** (the verified-scan marker gate reported `count_status == confirmed AND new_code_issue_count > 0`; the producer FILED one `sonar-issue` finding per issue for the unified triage. The FIND succeeded, so the step marks `done` — remediation is owned by the dispatcher-level unified triage). Resolve the worktree HEAD before marking done:

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

There is no `loop_back` branch — this FIND-only step never emits a loop-back outcome. A unified-triage FIX disposition advances HEAD via its own fix commit; the dispatcher's HEAD-dependent resumability check (below) then re-fires this FIND step against the new tree as a fresh dispatch, so no `--outcome loop_back` record is written here.

Note: there is no "config disabled" branch — when the manifest excludes `sonar-roundtrip`, the dispatcher does not run this document at all, so no step record is written.

## Resumability

`sonar-roundtrip` is one of the three HEAD-dependent steps in `HEAD_DEPENDENT_STEPS` (`pre-push-quality-gate`, `plan-marshall:automatic-review`, `sonar-roundtrip`) — see [`phase-6-finalize/SKILL.md`](../SKILL.md) Step 3 "Special case — HEAD-dependent steps". The HEAD comparison guards against false-clean re-entry after a downstream loop-back commit (typically produced by the unified wait-region triage opening a fix task that produces a new commit) advances HEAD past the validated tree:

| Persisted state | Live worktree HEAD | Action |
|-----------------|--------------------|--------|
| `outcome == done` AND `head_at_completion == HEAD` | matches | SKIP (steady-state — Sonar already cleared this exact tree) |
| `outcome == done` AND `head_at_completion != HEAD` | differs | RE-FIRE (treat as no record — HEAD has advanced past the validated SHA; re-fetch Sonar issues and re-file them for the unified triage against the new tree) |
| `outcome == done` AND `head_at_completion` absent | n/a | RE-FIRE (record is incomplete without a SHA; safe default is to re-run) |
| `outcome == failed` | n/a | RETRY (unchanged — same as the general rule) |
| `outcome == loop_back` | n/a | RE-FIRE (treat as no record — same as the general rule for loop_back) |
| no record | n/a | DISPATCH (unchanged — same as the general rule) |

## Output

```toon
status: success | error
display_detail: "<new-code issues: {new_code_issue_count} ({count_status}); {issues_fetched} filed for unified triage>"
new_code_issue_count: {N | null}
count_status: confirmed | undecidable
issues_fetched: {N}
```

`new_code_issue_count` and `count_status` are read from the latest `sonar-scan-summary.jsonl` marker row (the verified-scan attestation written by the producer); they are the source of the FIND verdict — `status: success` requires `count_status == confirmed` (whether the count is zero or non-zero — a confirmed non-zero count means findings were filed for the unified triage), and a `count_status == undecidable` (or absent marker) yields `status: error` (fail closed). `issues_fetched` is the count of `sonar-issue` findings this step FILED to the store.

FIND-only producer — this step fetches and files `sonar-issue` findings; the per-finding LLM triage (and the `sonar post_responses` server-side dismissals) is delegated to the dispatcher-owned unified wait-region triage (`producer=finalize-feedback`), not dispatched here. The `display_detail` value (≤80 chars, ASCII, no trailing period) is forwarded via `mark-step-done --display-detail`. This step emits no `loop_back`; a unified-triage fix commit advances HEAD and re-fires this FIND per the HEAD-dependent resumability rules above.
