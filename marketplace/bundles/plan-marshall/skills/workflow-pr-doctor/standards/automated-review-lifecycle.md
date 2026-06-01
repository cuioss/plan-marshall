# Automated Review Lifecycle Reference

Detailed reference for the Automated Review Lifecycle mode used by phase-6-finalize when `decisions.automated_review: true`.

> **Architectural context**: This document owns the lifecycle step list (review-bot buffer, producer call, consumer dispatch, thread replies, overflow handling). CI completion is a dispatcher-resolved precondition declared via the `requires: [ci-complete]` frontmatter field on the consumer step — the phase-6-finalize dispatcher invokes its precondition resolver (see [`phase-6-finalize/SKILL.md`](../../phase-6-finalize/SKILL.md) Step 3 § "Precondition resolution") before this lifecycle executes and guarantees CI is green. On `wait_failed`, the dispatcher skips this lifecycle entirely and marks the consumer step `failed` with `display_detail "ci_failure (precondition)"`. For the architecture-level synthesis (producer→store→consumer→gate), see [`ref-workflow-architecture/standards/findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md). The pipeline narrative is not restated here.

## Input Parameters

- `plan_id` — for logging, finding storage, and Q-Gate findings
- `pr_number` — PR number (from phase-6-finalize Step 4 or pr-view)
- `review_bot_buffer_seconds` — max-wait ceiling (in seconds) passed to `pr wait-for-comments` as `--timeout`. The polling subcommand exits as soon as a new review-bot comment is posted, so this is a cap, not a fixed delay. Sourced from phase-6-finalize config (default: 180).

## Step-by-Step Reference

CI completion is guaranteed by the dispatcher's precondition resolver before this lifecycle runs (see the architectural-context note above). The body therefore starts at the review-bot wait — there is no inline CI-readiness probe and no `ci-wait` outcome record to consult.

### Step 1: Wait for Review Bot Comments

Poll for new review-bot comments using the dedicated CI subcommand. It exits as soon as a new comment arrives instead of sleeping the full window.

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr wait-for-comments \
  --pr-number {pr_number} --timeout {review_bot_buffer_seconds}
```

| Script Output | Action |
|--------------|--------|
| `status: success`, `timed_out: false` | New comment(s) detected — proceed to Step 2 |
| `status: success`, `timed_out: true` | No new comment within timeout — proceed to Step 2 anyway (the producer at Step 2 surfaces whatever is on the PR; if nothing, the lifecycle returns `comments_total: 0`) |
| `status: error` | Treat as warning, log, proceed to Step 2 best-effort |

### Step 2: Producer-stage PR comments as findings

Call the producer-side comments-stage subcommand once. It fetches PR review comments, applies pre-filters, and writes one `pr-comment` finding per surviving comment into the per-plan findings store. The producer is the ONLY surface that fetches and stores `pr-comment` findings — this lifecycle does NOT classify or decide on comments inline.

Pre-filters applied by `comments-stage` (in order):

1. **Already-resolved threads** — comments on threads where `isResolved=true` are dropped silently. The thread owner already addressed them; storing them as findings would produce spurious `ACCEPT` work.
2. **Obvious text noise** — automated/acknowledgment patterns (e.g., "lgtm", bot signatures) matched via the `comment-patterns.json` ignore list.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr \
  comments-stage --pr-number {pr_number} --plan-id {plan_id}
```

For GitLab projects use `plan-marshall:workflow-integration-gitlab:gitlab_pr comments-stage` instead. Provider selection follows `manage-providers` for the plan's host.

### Step 3: Enumerate pending pr-comment findings

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list \
  --plan-id {plan_id} --type pr-comment --resolution pending
```

If the result's `findings` list is empty, return success with `comments_total: 0` and `loop_back_needed: false`.

### Step 4: Per-finding dispatch through ext-triage-{domain}

For each pending finding, perform the following sequence sequentially. Every per-finding decision goes through the loaded `ext-triage-{domain}` skill's standards — there is no batch keyword classifier.

1. **Detect domain** via `architecture which-module --path {finding.file_path}`.
2. **Resolve the triage extension** via `manage-config resolve-workflow-skill-extension --domain {domain} --type triage`.
3. **Load the resolved extension** with `Skill: {bundle}:ext-triage-{domain}`. The extension brings its `severity.md`, `suppression.md`, and `pr-comment-disposition.md` into context.
4. **Decide** per the loaded `pr-comment-disposition.md` table:

   | Decision | Action |
   |----------|--------|
   | **FIX** | Create a fix task (prepare-add → commit-add) and loop back to phase-5-execute |
   | **SUPPRESS** | Apply domain-specific annotation (per loaded `suppression.md`); reply on the thread acknowledging the suppression; resolve the thread |
   | **ACCEPT** | Reply on the thread with rationale; resolve the thread. See **Affirmative acceptance policy** below. |
   | **AskUserQuestion** | Ask the user (one question per finding, never batched) when the loaded standards leave the call genuinely ambiguous |

   **Affirmative acceptance policy.** `ACCEPT` is a first-class disposition — not a fallback for comments that cannot be classified. It applies when the reviewer's comment reflects a valid perspective but the current implementation is already correct and intentional. Three conditions must all hold before issuing `ACCEPT`:

   1. **Substantive engagement**: the reply must explain the design decision or trade-off that makes the current code correct, not merely acknowledge the comment.
   2. **No suppression annotation needed**: the concern is not a false-positive warning that needs to be silenced at the tool level — it is a deliberate choice that warrants explanation.
   3. **Unambiguous call**: if there is genuine uncertainty about whether the code is correct as-is, escalate via `AskUserQuestion` rather than assuming `ACCEPT`.

   When all three hold, reply on the thread with the rationale, then resolve the thread. `ACCEPT` resolves the finding with `resolution: accepted`.

5. **Resolve the finding** via `manage-findings resolve --hash-id {hash_id} --resolution {fixed|suppressed|accepted|taken_into_account} --detail "{rationale}"`.

The PR thread reply / resolve calls use `plan-marshall:tools-integration-ci:ci pr prepare-comment` → `pr thread-reply` → `pr resolve-thread` (see the canonical phase-6-finalize `automated-review.md` standard for the exact command sequences).

### Step 5: Return Summary

```toon
status: success
pr_number: {pr_number}
ci_status: success
comments_total: {N}
comments_unresolved: {N}
processed:
  fixed: {N}
  suppressed: {N}
  accepted: {N}
  taken_into_account: {N}
threads_resolved: {N}
loop_back_needed: {true|false}
```

`loop_back_needed` is `true` under either of two conditions:

1. **FIX disposition fired** — at least one `pr-comment` finding resolved to `fixed` during this iteration's per-finding loop, allocating a fix task. When this is the trigger, phase-6-finalize creates the fix tasks and loops back to phase-5-execute.
2. **Overflow capture fired** — the per-iteration triage budget (900 s) was nearly exhausted before all `pr-comment` findings could be processed. The Step 5 loop captures the unprocessed comment IDs as a single `pr-comment-overflow` finding (see [`manage-findings/standards/jsonl-format.md`](../../manage-findings/standards/jsonl-format.md) § `pr-comment-overflow`) and breaks early. The next phase-6-finalize entry's `automated-review` invocation reads the pending `pr-comment-overflow` finding to know which comments are outstanding.

The two paths are not mutually exclusive — a single iteration can both allocate fix tasks for some comments AND defer others to overflow. In that case, `loop_back_needed: true` covers both, and the overflow finding is filed alongside the fix-task allocations. The 3-iteration loop-back ceiling applies uniformly regardless of which trigger fired.

## Error Handling

| Failure | Action |
|---------|--------|
| `comments-stage` returns empty | Report "No unresolved comments" via the Step 3 query (which will also return empty) and return success |
| `manage-findings list` fails | Log error, return error to caller |
| Per-finding triage step (resolve, reply, thread-resolve) fails | Log warning, continue with the next finding — best-effort processing; the failed finding remains `pending` and is retried on the next finalize entry |

CI-readiness failures are handled by the dispatcher's `ci-complete` precondition resolver before this lifecycle runs — see the architectural-context note at the top of this document.
