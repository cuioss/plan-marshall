# Automated Review Lifecycle Reference

Detailed reference for the Automated Review Lifecycle mode used by phase-6-finalize when `decisions.automated_review: true`.

> **Architectural context**: This document owns the lifecycle step list for the consolidated FIND → INGEST → TRIAGE → RESPOND flow (review-bot buffer, `fetch_findings` FIND, batched `ingest`, per-finding TRIAGE reading top-level only, `post_responses` RESPOND, overflow handling). CI completion is a dispatcher-resolved precondition declared via the `requires: [ci-complete]` frontmatter field on the consumer step — the phase-6-finalize dispatcher invokes its precondition resolver (see [`phase-6-finalize/SKILL.md`](../../phase-6-finalize/SKILL.md) Step 3 § "Precondition resolution") before this lifecycle executes and guarantees CI is green. On `wait_failed`, the dispatcher skips this lifecycle entirely and marks the consumer step `failed` with `display_detail "ci_failure (precondition)"`. For the architecture-level synthesis (producer→store→consumer→gate), see [`ref-workflow-architecture/standards/findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md). The pipeline narrative is not restated here.

## Input Parameters

- `plan_id` — for logging, finding storage, and Q-Gate findings
- `pr_number` — PR number (from phase-6-finalize Step 4 or pr-view)
- `review_bot_buffer_seconds` — max-wait ceiling (in seconds) passed to `pr wait-for-comments` as `--timeout`. The polling subcommand exits as soon as a new review-bot comment is posted, so this is a cap, not a fixed delay. Sourced from the `plan-marshall:automatic-review` step's params in the plan-local execution-manifest step-params snapshot — read via `manage-execution-manifest step-params get --plan-id {plan_id} --phase 6-finalize --step-id plan-marshall:automatic-review` (default: 180), NOT from a flat phase-6-finalize config field.

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

> **Rate-window await (cross-reference).** The `pr wait-for-comments` return also carries a `rate_limited` discriminator: `rate_limited: true` signals the wait ended because the review bot's rate window was exhausted rather than because a review landed. The `plan-marshall:automatic-review` finalize step exposes an opt-in `review_rate_window_await` knob (with `review_rate_window_timeout_seconds`) that, when enabled, re-polls in a bounded await loop on `rate_limited: true` and escalates via `escalate_ask{reason: rate_window_timeout}` on budget exhaustion. This lifecycle reference does NOT duplicate that behaviour — see [`automatic-review/SKILL.md`](../../automatic-review/SKILL.md) § "Rate-window await (opt-in)" for the authoritative await loop and escalation contract.

### Step 2: FIND — file PR comments to the ledger

Call the producer-side `fetch_findings` verb once. It fetches PR review comments, applies pre-filters, and files one `pr-comment` finding per surviving comment into the per-plan findings store, quarantining the untrusted comment body under `raw_input.{body}` (the trusted structured metadata — `thread_id`, `comment_id`, `kind`, `author`, `path`, `line` — goes in the finding's `detail`). The producer is the ONLY surface that fetches and files `pr-comment` findings — this lifecycle does NOT classify or decide on comments inline.

Pre-filters applied by `fetch_findings` (in order):

1. **Already-resolved threads** — comments on threads where `isResolved=true` are dropped silently. The thread owner already addressed them; storing them as findings would produce spurious `ACCEPT` work.
2. **Obvious text noise** — automated/acknowledgment patterns (e.g., "lgtm", bot signatures) matched via the `comment-patterns.json` ignore list.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr \
  fetch_findings --pr-number {pr_number} --plan-id {plan_id}
```

For GitLab projects use `plan-marshall:workflow-integration-gitlab:gitlab_pr fetch_findings` instead. Provider selection follows `manage-providers` for the plan's host. A `status: unconfigured` return means the provider is not authenticated — fail loud, never a silent zero-findings success.

### Step 2.5: INGEST — promote quarantined bodies to top-level

Run the single batched ingestion pass once, after FIND and before triage reads any finding. It runs `validate_struct` over every `raw_input.{field}` (schema + length-cap + domain-allowlist) and promotes only the validated value to the clean top-level field; triage then reads TOP-LEVEL fields only, never `raw_input.*`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings ingest \
  --plan-id {plan_id}
```

This one deterministic batched boundary supersedes the retired per-finding reader-dispatch + `validate_struct` hop.

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
4. **Security-claim classification gate (pre-disposition).** Before applying the disposition table, classify whether the finding is a **security-claim edit**. The classification is **intent-based** — NOT keyword-based and NOT limited to polarity flips. A finding is a security-claim edit when the suggestion modifies a statement describing what a tool, API, command, or boundary *can or cannot do* from a **trust, access, or scope** perspective — for example, a reword that changes the asserted reach of a file-read tool, the privilege a command runs with, or the boundary a path resolver enforces. The classification is independent of the originating bot's own label: a comment a bot files as a "docs nit", "typo", or style suggestion still qualifies when its edit alters a trust / access / scope assertion. This gate is cross-cutting — it lives here in the shared lifecycle and applies to every finding regardless of domain, NOT in any per-domain `pr-comment-disposition.md` table.

   When a finding IS a security-claim edit, the triage MUST route it to the security-expert persona for verification BEFORE any disposition:

   ```text
   Skill: plan-marshall:persona-security-expert
   ```

   The security-expert verifies whether the rewritten claim is *true* against the actual code / boundary behaviour. The accept path MUST NOT resolve a security-claim finding as `fixed` or `accepted` without explicit security-expert sign-off. A security-claim edit the persona finds false is closed as `rejected` with a `resolution_detail` explaining why the suggested rewrite is incorrect (the RESPOND loop in Step 4.5 posts that rationale on the thread and resolves it) — never silently accepted and never routed to `SUPPRESS` or `AskUserQuestion`. Only after sign-off does the finding fall through to the disposition table below. When the finding is NOT a security-claim edit, proceed directly to the disposition table below.

   **Canonical case (PR #784).** A review bot rewrote an unrestricted-`Read` statement into the false assertion *"Read is WORKTREE-path-scoped"*, inverting the plan's deliberate unrestricted-Read thesis. With no security-claim gate the comment was applied straight through as `fixed`. Under this gate the same comment is classified as a security-claim edit (it changes what the `Read` tool is asserted to be able to access), routed to the security-expert, found false against the actual unrestricted-Read behaviour, and refused acceptance.

5. **Decide** per the loaded `pr-comment-disposition.md` table. Triage RECORDS the disposition (and applies the in-code source change); the reviewer-facing thread reply / resolve is transmitted later by the single RESPOND loop (Step 4.5), NOT inline here:

   | Decision | Action (triage records; RESPOND transmits) |
   |----------|--------|
   | **FIX** | Create a fix task (prepare-add → commit-add) and loop back to phase-5-execute; record the finding `fixed` with a reviewer-ready `resolution_detail` naming the task |
   | **SUPPRESS** | Apply domain-specific annotation (per loaded `suppression.md`); record the finding `suppressed` with the rationale |
   | **ACCEPT** | Record the finding `accepted` with the rationale. See **Affirmative acceptance policy** below. |
   | **AskUserQuestion** | Ask the user (one question per finding, never batched) when the loaded standards leave the call genuinely ambiguous |

   **Affirmative acceptance policy.** `ACCEPT` is a first-class disposition — not a fallback for comments that cannot be classified. It applies when the reviewer's comment reflects a valid perspective but the current implementation is already correct and intentional. Three conditions must all hold before issuing `ACCEPT`:

   1. **Substantive engagement**: the `resolution_detail` must explain the design decision or trade-off that makes the current code correct, not merely acknowledge the comment (it becomes the thread reply the RESPOND loop posts).
   2. **No suppression annotation needed**: the concern is not a false-positive warning that needs to be silenced at the tool level — it is a deliberate choice that warrants explanation.
   3. **Unambiguous call**: if there is genuine uncertainty about whether the code is correct as-is, escalate via `AskUserQuestion` rather than assuming `ACCEPT`.

   When all three hold, record the rationale as `resolution_detail`. `ACCEPT` resolves the finding with `resolution: accepted`.

6. **Resolve the finding** via `manage-findings resolve --hash-id {hash_id} --resolution {fixed|suppressed|accepted|taken_into_account|rejected} --detail "{reviewer-ready rationale}"`. The `--detail` is exactly the text the RESPOND loop posts back to the thread.

### Step 4.5: RESPOND — transmit dispositions to the PR

After every pending finding has been dispositioned in Step 4, transmit the recorded dispositions back to the PR in ONE respond loop via the pure `post_responses` verb, keyed by each finding's own `hash_id` (never a positional pairing). For each terminal-disposition finding carrying a `thread_id` and `resolution_detail`, `post_responses` posts the stored `resolution_detail` as a thread-reply then resolves the thread; findings without a `thread_id` or `resolution_detail` are skipped, never guessed at:

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr \
  post_responses --pr-number {pr_number} --plan-id {plan_id}
```

For GitLab projects use `plan-marshall:workflow-integration-gitlab:gitlab_pr post_responses` instead.

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
2. **Overflow capture fired** — the per-iteration triage budget (900 s) was nearly exhausted before all `pr-comment` findings could be processed. The Step 5 loop captures the unprocessed comment IDs as a single `pr-comment-overflow` finding (see [`manage-findings/standards/jsonl-format.md`](../../manage-findings/standards/jsonl-format.md) § `pr-comment-overflow`) and breaks early. The next phase-6-finalize entry's `plan-marshall:automatic-review` invocation reads the pending `pr-comment-overflow` finding to know which comments are outstanding.

The two paths are not mutually exclusive — a single iteration can both allocate fix tasks for some comments AND defer others to overflow. In that case, `loop_back_needed: true` covers both, and the overflow finding is filed alongside the fix-task allocations. The 3-iteration loop-back ceiling applies uniformly regardless of which trigger fired.

## Error Handling

| Failure | Action |
|---------|--------|
| `fetch_findings` returns empty | Report "No unresolved comments" via the Step 3 query (which will also return empty) and return success |
| `manage-findings list` fails | Log error, return error to caller |
| Per-finding triage step (resolve) fails | Log warning, continue with the next finding — best-effort processing; the failed finding remains `pending` and is retried on the next finalize entry |
| `post_responses` RESPOND transmit fails | Log warning, continue — the disposition is already recorded in the ledger; the reply is re-transmitted on the next finalize entry (`post_responses` is idempotent) |

CI-readiness failures are handled by the dispatcher's `ci-complete` precondition resolver before this lifecycle runs — see the architectural-context note at the top of this document.
