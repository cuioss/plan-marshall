---
name: workflow-integration-github
description: GitHub provider for PR review workflows — four pure verbs (fetch_findings files comments to the ledger, post_responses transmits triaged dispositions, bot_completion reports a review bot's completion state, pull_request_runs reports the PR-wide not_triggered observable) via gh CLI
user-invocable: false
mode: workflow
---

# GitHub CI Integration Workflow Skill

GitHub provider for the findings-pipeline `pr-comment` producer. The provider surface is exactly FOUR pure, zero-LLM verbs — no triage judgment lives here:

- **`fetch_findings`** — fetch PR review comments, apply the pre-filter (`comment-patterns.json`), exclude the batched response body `post_responses` itself posted, and file one `pr-comment` finding per surviving comment via `manage-findings add`. The untrusted comment body is quarantined under `raw_input.{body}` (never embedded raw in the top-level `detail`); the batched `manage-findings ingest` pass promotes it to top-level only after `validate_struct`. A bounded guard reports a non-converging respond → re-fetch cycle as a `(self-response-loop)` Q-Gate finding.
- **`post_responses`** — apply already-decided triage dispositions back to the PR, keyed by each finding's own `hash_id`, via a three-way transmit keyed on the finding's `kind`: thread-reply-then-resolve for a thread-bearing finding (untransmitted, never batched, when its thread is missing), ONE batched PR-level comment for the genuinely threadless kinds, and `skipped` only when there is genuinely nothing to say.
- **`bot_completion`** — report a review bot's registry `completion_check_name` check-run state (`{status, in_progress, completed}`) for the PR HEAD, so the `automatic-review` completion-aware poll can wait for a slow bot to finish before fetching; a bot with no completion check-run reports `no_check_name` and the caller falls back to the `review_bot_buffer_seconds` wait.
- **`pull_request_runs`** — report whether ANY `pull_request`-event workflow run exists for the requested PR. The head branch is how the runs are FETCHED, not what the answer is scoped to: a run is excluded only when its `pull_requests` association reliably names a DIFFERENT PR. This is the PR-WIDE observable behind the `not_triggered` participation state: when no such run exists, nothing ever ran on account of the PR, so no bot could have published and a required bot's silence says nothing about that bot. A run that EXISTS and concluded `skipped` keeps the observable false — the workflow *was* triggered. Never reads `mergeable_state`.

All four verbs FAIL LOUD when GitHub is not configured (a typed `unconfigured` status, never a silent no-op). Uses the `gh` CLI for all GitHub operations.

> **Architectural context**: This SKILL.md owns the producer-side CLI surface. For the producer→store→consumer→gate flow that connects this producer to the unified store, the per-domain `ext-triage` consumer dispatch, and the invariant gate, see [`ref-workflow-architecture/standards/findings-pipeline.md`](../ref-workflow-architecture/standards/findings-pipeline.md).

## Enforcement

**Execution mode**: Four pure provider verbs — `fetch_findings` files PR review comments to the ledger (untrusted body quarantined under `raw_input`); `post_responses` transmits already-decided triage dispositions back to the PR; `bot_completion` reports a review bot's completion-check state for the completion-aware poll; `pull_request_runs` reports the PR-wide `pull_request`-run observable behind `not_triggered`. Triage judgment lives in the consolidated triage pass, NOT in this provider.

**Prohibited actions:**
- Never call `gh` directly from LLM context; all operations go through script API
- Never make a triage decision inside the provider verbs — they only fetch and transmit already-decided dispositions
- Never read a finding's `raw_input.*` from a triage/response surface — read the top-level fields promoted by `manage-findings ingest`
- Never resolve review comments without addressing the reviewer's concern
- Never dismiss reviews without documented justification

**Constraints:**
- Review comment responses must explain the fix or provide rationale for disagreement
- CI wait timeout must be respected with user prompt on expiry

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `pr` | int | no | auto-detect | PR number (auto-detects current branch's PR if omitted) |
| `unresolved-only` | bool | no | false | Only return unresolved comments (`pr comments`) |

## Architecture

```text
workflow-integration-github (GitHub PR comment workflow)
  ├─> github_ops.py (GitHub operations via gh CLI — PR, CI, issue)
  ├─> github_pr.py (PR comment triage — delegates to github_ops for fetch)
  ├─> github_re_review.py (bot_kind-keyed re-review strategy registry)
  └─> triage_helpers (ref-toon-format) — shared triage, error handling
```

This skill is the GitHub provider in the CI provider model. The central dispatcher (`tools-integration-ci:ci`) routes to this skill's `github_ops.py` for all GitHub operations.

## Usage Examples

```bash
# FIND: fetch + pre-filter + file one pr-comment finding per surviving comment (body quarantined under raw_input)
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr fetch_findings --pr-number 123 --plan-id EXAMPLE-PLAN

# RESPOND: apply already-decided dispositions (thread-reply + resolve-thread) back to the PR, keyed by hash_id
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr post_responses --pr-number 123 --plan-id EXAMPLE-PLAN

# Raw fetch (no filtering, no storage) — for ad-hoc inspection
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr fetch-comments --pr 123

# LLM consumer reads stored findings via manage-findings
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list --plan-id EXAMPLE-PLAN --type pr-comment
```

## Scripts

| Script | Notation | Purpose |
|--------|----------|---------|
| github_ops | `plan-marshall:workflow-integration-github:github_ops` | GitHub PR, CI, and issue operations via gh CLI |
| github_pr | `plan-marshall:workflow-integration-github:github_pr` | Producer-side PR review comment fetcher (fetch + pre-filter + store) |
| github_re_review | `plan-marshall:workflow-integration-github:github_re_review` | `bot_kind`-keyed re-review strategy registry (request + await a fresh bot review for the current HEAD) |

## Consumers

This skill is consumed by:
- `tools-integration-ci` — CI dispatcher routes GitHub operations here
- `workflow-pr-doctor` — PR diagnosis workflows
- `phase-6-finalize` — plan finalization with PR creation

## Workflows

### Workflow 1: Fetch Comments

**Purpose:** Fetch all review comments for a PR.

**Steps:**

1. **Get PR Comments**

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr comments [--pr-number {number}] [--unresolved-only]
   ```

2. **Return Comment List**

### Workflow 2: Find → Ingest → Triage → Respond (two-verb provider contract)

**Purpose:** File PR review comments into the per-type finding store with the untrusted body quarantined, then let the consolidated triage pass drive dispositions, then transmit those dispositions back to the PR — all through the two pure provider verbs.

**Provider contract:** the provider surface is exactly `fetch_findings` (FIND) and `post_responses` (RESPOND). Neither makes a triage decision — triage judgment lives in the consolidated triage pass, not in the provider. `fetch_findings` fetches review comments, applies the `comment-patterns.json` keyword pre-filter, and files one `pr-comment` finding per surviving comment with the untrusted body quarantined under `raw_input.{body}`. The trusted structured metadata (`pr_number`, `thread_id`, `comment_id`, `kind`, `author`, `path`, `line`) goes in the finding's `detail`. `pr_number` records the PR the comment came from and is load-bearing on the RESPOND side: the findings store is plan-scoped, not PR-scoped, so it is the only thing that tells `post_responses` which rows belong to the PR it is transmitting to.

**Containment:** the untrusted comment body is quarantined at file time under `raw_input.{body}` and promoted to the top level only by the single batched `manage-findings ingest` pass, which runs `validate_struct` over every `raw_input.{field}` (schema + length-cap + domain-allowlist). Triage then reads the clean top-level fields **only, never `raw_input.*`**. Containment is one deterministic batched boundary.

**GitHub GraphQL ID Format Rules:**

| Operation | Parameter | ID Field | Format Example |
|-----------|-----------|----------|----------------|
| `thread-reply --thread-id` | Comment's `thread_id` field | GraphQL node ID | `PRRT_kwDO...` |
| `resolve-thread --thread-id` | Comment's `thread_id` field | GraphQL node ID | `PRRT_kwDO...` |

Both operations take the same `PRRT_` thread ID — pass the comment's `thread_id` field for either. The comment's `id` field (format `PRRC_...`) is never valid for `thread-reply` or `resolve-thread`. `post_responses` reads each finding's `thread_id` from its own `detail` block, keyed by `hash_id` — never a positional pairing. Which path a finding takes is decided by its `kind`, not by whether a `thread_id` was extractable: a genuinely threadless kind (`review_body`, `issue_comment`) goes out on the batched PR-comment path, while a thread-bearing kind with no usable `thread_id` is reported as untransmitted rather than batched (see Workflow 2 step 4).

**NEVER use numeric IDs** — GitHub GraphQL requires global node IDs.

**Steps:**

1. **FIND — file findings** (untrusted body quarantined under `raw_input`):
   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr fetch_findings --pr-number {pr} --plan-id {plan_id}
   ```
   Output reports `count_fetched`, `count_skipped_noise`, `count_skipped_duplicate`, `count_skipped_refusal`, `count_skipped_self_response`, `count_self_response_current_cycle`, `self_response_loop_detected`, `self_response_loop_hash_id`, `count_stored`, `participated_bots[]`, `stale_participation_bots[]`, `refused_bots[]`, `unclassified_bots[]`, and `producer_mismatch_hash_id` (set when count_stored ≠ count_fetched − count_skipped_noise − count_skipped_duplicate − count_skipped_refusal − count_skipped_self_response; the mismatch is also persisted as a Q-Gate finding under phase `5-execute` with title prefix `(producer-mismatch)`). An unclassified bot's comments are stored like any other, so they are NOT subtracted from the expected count. When that mismatch finding's own persist is REJECTED, `producer_mismatch_hash_id` stays `null` and the output carries `qgate_persist_failed: true` plus `qgate_persist_failure{title, detail, message}` — the mismatch content that never reached the store, with the primitive's rejection message. Both fields are absent when the mismatch finding landed (or when there was no mismatch). Read `qgate_persist_failed`, not a `null` hash id, to tell a lost mismatch finding from no mismatch at all; `status` stays `success` because the fetch itself succeeded. A `status: unconfigured` return means GitHub is not authenticated — never a silent zero-findings success.

   **A failed currency test is a branch, never a discard.** `participated_bots[]` credits a bot only when an observed comment's `kind` matches a declared `participation_evidence` publish shape AND — for a bot declaring `participation_requires_update` — the comment is first-present or its `updated_at` has moved. When the *kind* matched but the *currency test* failed, the bot is named in **`stale_participation_bots[]`** rather than dropped:

   ```toon
   stale_participation_bots[N]{bot_kind,evidence_kind}:
   ```

   Same record shape as `participated_bots[]`, and the proven set is **subtracted before emitting** — a bot with one stale comment and one fresh one appears only in `participated_bots[]`, never in both. Forward the list to `review_completeness check --stale-participation-bots` so the quorum layer classifies the bot `participated_stale` instead of `absent`. The two are not interchangeable and their remedies are opposite: a stale publish is **re-triggered** (the review exists, it merely predates this HEAD), while a true absence is **escalated** (there is no review to refresh). Discarding the failed currency test is what collapsed the two.

   **A refusal is a branch, never a noise drop.** A comment recognized as a bot DECLINING to review (its registry `refusal_patterns`, or the structural `_is_rate_limit_notice` recognizer for an unregistered bot) files no `pr-comment` finding — it is a signal *about* the review, not feedback about the code, so the operator is never asked to triage it — but it is counted in `count_skipped_refusal` and its bot is named in `refused_bots[]`, and it is excluded from `participated_bots[]`. Forward `refused_bots[]` to `review_completeness check --refused-bots` so the quorum layer classifies the bot as `refused_awaitable` / `refused_hard`. Folding a refusal into `count_skipped_noise` instead is what let a PR whose every required reviewer refused report a clean, complete review; `count_skipped_noise` and `count_skipped_refusal` are deliberately separate counters for that reason.

   **A self-authored response is excluded start-anchored, and the loop is bounded.** `post_responses` transmits thread-less dispositions as a NEW PR-level comment (step 4 below) authored by the repo-owner account. On the next fetch that comment is unresolved, is not a refusal, matches no `ignore` regex, and carries a NEW `comment_id` the `(bot_kind, comment_id)` dedup cannot know — so without a dedicated stage it is filed as a fresh pending finding, the pre-merge comment barrier blocks on it, triage responds again, and the cycle never terminates. `fetch_findings` therefore drops any comment whose whitespace-stripped body **starts with** the batched-response heading, counting it in `count_skipped_self_response` (never `count_skipped_noise` — our own output is not acknowledgment noise) and subtracting it from the expected count. The match is **start-anchored, never a substring test**: a human comment that quotes or blockquotes the heading is real reviewer feedback and is still filed.

   The filter cannot be complete — a thread-bearing disposition whose resolve-thread failed leaves an unresolved reply carrying arbitrary `resolution_detail` text and no transmission shape at all — so a bound backs it. Every turn of the cycle leaves one permanent response comment on the PR, so the PR's own comment list IS the iteration counter: no new state store and no new config key. When one fetch observes `count_self_response_current_cycle` at or above the bound, the verb returns `self_response_loop_detected: true` and files a `(self-response-loop)` Q-Gate finding under phase `5-execute` through the same checked-persist primitive the mismatch finding uses — a rejected persist surfaces as `self_response_loop_persist_failed: true` plus `self_response_loop_persist_failure{title, detail, message}`. Exhaustion is a REPORTED coverage gap requiring an operator decision, never a silent pass; `status` stays `success` because the fetch itself succeeded.

   **The bound counts the CURRENT cycle, not the PR's history.** `fetch_findings` fetches with `unresolved_only=False`, so every fetch sees the PR's entire comment history. `count_skipped_self_response` is therefore a LIFETIME total — it includes every already-converged triage round — and reading it as the loop predicate reported a loop on any PR that merely completed three ordinary cycles, typically at pre-merge validation long after every finding was resolved. The predicate is `count_self_response_current_cycle`: the TRAILING run of self-responses, ordered by `created_at` (the provider returns comments grouped by kind, not chronologically, and self-responses are always `issue_comment` — so the raw list order would put every historical response in the tail). A non-converging cycle posts response after response with nobody else speaking, which is what makes the run the right measure; fresh reviewer activity breaks it, because a cycle somebody replied to has converged. A registered re-review trigger comment is transparent — it neither counts nor breaks the run, since letting this pipeline's own output reset its own guard would mask the loop class the bound exists to terminate. Both counts are reported: the lifetime total is the honest record of what the filter dropped, the current-cycle figure is the guard.

2. **INGEST — promote validated free-text to top-level** (one batched deterministic pass over the whole ledger):
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings ingest --plan-id {plan_id}
   ```

3. **TRIAGE — one consolidated pass** reads the clean top-level fields (never `raw_input.*`) and records a disposition per finding via `manage-findings resolve --hash-id {hash} --resolution {fixed|suppressed|accepted|taken_into_account|rejected} --detail "{rationale}"`. The rationale becomes the `resolution_detail` that `post_responses` transmits.

4. **RESPOND — apply dispositions back to the PR** (keyed by hash_id):
   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr post_responses --pr-number {pr} --plan-id {plan_id}
   ```
   `post_responses` transmits every terminal-disposition finding through a three-way branch — no decision is lost and none is guessed at. **The routing predicate is the finding's `kind` — its thread-BEARING-ness — never the presence of an extractable `thread_id`:**

   | Finding shape | Transmit | Recorded as |
   |---------------|----------|-------------|
   | `pr_number` names a DIFFERENT PR | nothing — the row belongs to another PR | `skipped[]`, reason `belongs_to_pr_<n>` |
   | `pr_number` absent from `detail` | nothing — the row cannot be shown to belong here (fail closed) | `skipped[]`, reason `pr_number_unrecorded` |
   | no `resolution_detail` | nothing — there is genuinely nothing to say | `skipped[]`, reason `no_resolution_detail` |
   | genuinely threadless `kind` (`review_body`, `issue_comment`) | ONE batched PR-level comment for ALL such findings in the run, each section anchored on its source `comment_id` | `responded[]`, `transmit_mode: batched_issue_comment`, `resolved_on_provider: false` |
   | thread-bearing `kind` (`inline`, and any unrecognised kind) | thread-reply carrying the `resolution_detail`, then resolve-thread | `responded[]`, `transmit_mode: thread_reply`, `resolved_on_provider: true` |

   Batching is deliberate: `review_body` findings from every bot are thread-less, so a per-finding comment would spam the PR. `resolved_on_provider: false` on that path is truthful — an issue comment has no resolvable thread, and reporting `true` would be a false signal.

   **The `pr_number` gate runs FIRST, before the kind routing, and applies to thread-bearing rows too.** A plan that gathered findings across several PRs (a review-debt sweep, a multi-PR triage) holds rows the current PR does not own. Without the gate every threadless foreign row lands in this PR's batched comment while the run still reports `count_untransmitted: 0` — a confidently green report for a partly-misdelivered action. Thread-bearing rows are gated as well: a `thread_id` is a global GraphQL node id that would reach its own PR regardless, but the caller loops once per PR, so an ungated pass would re-reply to and re-resolve every other PR's threads on every iteration. A row whose `pr_number` was never recorded fails closed into `skipped[]` rather than defaulting onto the current PR — visibly deferred, never silently dropped and never misdelivered. Both gate outcomes are `skipped[]`, not `untransmitted[]`: nothing was undeliverable, the rows simply were not this PR's to send.

   **An undeliverable in-thread reply is untransmitted, never silently batched.** A thread-bearing finding whose `thread_id` is empty or unextractable is *undeliverable*, not threadless: it lands in `untransmitted[]` with a reason naming the missing thread and the run reports `status: partial`. It is NEVER re-routed into the batch — a silent downgrade would report the disposition as delivered while the reviewer's own thread stays unanswered and unresolved. Only genuinely threadless kinds enter the batch, so the batch membership is decided by the kind alone and cannot be reached by losing a `thread_id`.

   Any disposition that had something to say but could not be delivered — a missing thread on a thread-bearing finding, a failed thread-reply, a failed resolve-thread, or a failed batched post (which untransmits the WHOLE batch) — lands in `untransmitted[]` with a reason, drives `count_untransmitted`, and sets the envelope `status` to `partial`. The envelope reports `success` only when `count_untransmitted` is 0; it is never unconditionally `success`.

### Workflow 3: Re-Review After a HEAD-Advancing Branch Operation

**Purpose:** Close the post-merge re-review gap. When a HEAD-advancing branch operation in phase-6-finalize (branch-cleanup rebase/force-push, or a phase-5 loop-back fix commit) advances HEAD past the `reviewed_commit_sha` of the staged `pr-comment` findings, the new commits are unreviewed by automated bots. The `re-review` subcommand requests a fresh bot review for the new HEAD and polls until a review lands for it.

**Strategy registry:** `github_re_review.py` is a `bot_kind`-keyed registry with a strict two-method contract per strategy (`request_fresh_review`, `await_fresh_review`) and **no speculative extensibility**. The registry is **GitHub-only** — a sibling GitLab registry would be added separately without changing the consumer-side workflow docs. The canonical `bot_kind` list is imported from `manage-findings/_findings_core.BOT_KINDS`; the registry does **not** inline-copy the enum. Downstream consumers that need the enforcement-critical `bot_kind` list MUST reference that canonical source (or query a finding's `bot_kind` field) rather than hard-coding the values.

The strategies differ **only** in the trigger comment `request_fresh_review` posts — each posts an explicit trigger and uses the comment-post time as the trigger time:

| `bot_kind` | `request_fresh_review` | Trigger time |
|------------|------------------------|--------------|
| `coderabbit` | Posts `@coderabbitai review`. CodeRabbit's incremental auto-review on push is not a reliable trigger for the new HEAD (it can be debounced or skipped on a force-push), so the explicit comment is the trigger that guarantees a fresh review lands. | The comment-post time. |
| `sourcery` | Posts `@sourcery-ai review`. | The comment-post time. |
| `pr-agent` | Posts `/review` (PR-Agent does **not** auto-review on push). | The comment-post time. |

`await_fresh_review` is **identical** for every bot and is satisfied by **either** of two completion signals, checked in order of evidential strength:

| Signal | Match condition | Envelope |
|--------|-----------------|----------|
| **review** (preferred) | a review whose reviewed commit SHA equals `--head-sha` AND whose `submittedAt` strictly post-dates the trigger time, and which is not a refusal notice | `matched_signal: review`, `matched_review: {…}`, `head_sha_verified: true` |
| **issue comment** (fallback) | a comment whose author resolves to the awaited `bot_kind`, whose later of `updated_at` / `created_at` strictly post-dates the trigger time, and which is not a refusal notice | `matched_signal: issue_comment`, `matched_comment: {…}`, `head_sha_verified: false` |

**Both** signals additionally reject a **refusal notice** — a bot declining to review (rate-limit, diff-size, quota). The rejection is two-layer and identical on both paths: the awaited bot's registry `refusal_patterns` (its OBSERVED refusal strings — a DEDICATED field, never `ignore_patterns`, which lists the routine sections a bot emits on a *successful* review and would therefore over-match) are checked first, with the author-independent structural `_is_rate_limit_notice` as the last-resort fallback for an unknown or renamed bot. A refusal carries no review, so counting it as a completion signal would assert review coverage that never happened. This applies to the review path as much as the comment path: a bot may submit its refusal as a **review object** rather than an issue comment, and the review path resolves first — so without the check the strongest signal (`head_sha_verified: true`) would be the one most likely to be false.

`head_sha_verified: false` on the comment path is load-bearing: an issue comment carries no reviewed-commit SHA, so the match proves the bot **responded**, not that it reviewed the new HEAD. The caller learns the strength of the evidence, not just the fact of a match. The comment path uses the LATER of `updated_at` / `created_at` so a bot that edits ONE persistent comment in place still registers as fresh activity. No bot is named in code — both matchers are generic across the registry.

**Steps:**

1. **Invoke the registry** for the new HEAD:

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_re_review re-review --pr-number {pr} --bot-kind {coderabbit|sourcery|pr-agent} --head-sha {new HEAD} --push-time {ISO8601 push time} [--timeout {seconds}] --plan-id {plan_id}
   ```

   The subcommand resolves the strategy by `bot_kind`, runs `request_fresh_review` (posts each bot's registry `trigger_comment` — `@coderabbitai review`, `@sourcery-ai review`, `/review` — each using the comment-post time as the trigger time), then awaits either completion signal. The await budget is configurable via `--timeout` (default `DEFAULT_CI_TIMEOUT`); the phase-6-finalize trigger sites pass their `re_review_await_timeout_seconds` step-param value. It emits a TOON envelope with `matched: true|false`, `timed_out: true|false`, `matched_signal` (`review` | `issue_comment`, empty when unmatched), the matched `matched_review` / `matched_comment` record, and `head_sha_verified`.

2. **Consume the match outcome.** On `matched: true`, re-run `fetch_findings` to file the fresh review's comments, then re-run the consolidated ingest → triage → respond pass (Workflow 2). On `matched: false` / `timed_out: true`, the await budget expired with no fresh review — the consumer decides how to handle the timeout. This registry surfaces `timed_out` and does NOT decide policy itself; the timeout-handling responsibility (the `re_review_on_timeout` ask/defer/proceed branches) lives in the two trigger docs: trigger A in [`phase-6-finalize/standards/branch-cleanup.md`](../phase-6-finalize/standards/branch-cleanup.md) § "On re-review timeout (trigger A)" and trigger B in [`automatic-review`](../automatic-review/SKILL.md) § "On re-review timeout (trigger B)".

**Registry extension pattern:** to support a new `bot_kind`, add its `automatic-review/standards/{bot_kind}.md` registry doc and nothing else. `_findings_core.BOT_KINDS`, the login→`bot_kind` map, the `--bot-kind` `choices=` surface, and the strategy instance all DERIVE from that data. There is exactly ONE generic strategy class parameterized by the doc's `trigger_comment` — no per-bot subclass, and neither `request_fresh_review` nor `await_fresh_review` is re-implemented per bot.

## Comment Classification

`standards/comment-patterns.json` is a **pre-filter only** — it drops obvious noise (bot signatures, "lgtm", "thanks!") before findings are written. It is the shared *acknowledgment-noise* layer and nothing else: the refusal recognizer and the self-authored-response recognizer are deliberately NOT in it, because neither a bot declining to review nor this workflow's own transmitted output is noise. Each is its own stage with its own counter. Classification of surviving comments belongs to the consolidated triage pass, which reads the validated top-level body (promoted from `raw_input.{body}` by the batched `manage-findings ingest` pass) — never the raw un-ingested `raw_input.*`.

## Merge-queue bypass-actor configuration

The `repo merge-queue enable` path reads two optional, org-agnostic `marshal.json` keys under the top-level `merge_queue` block to weave a bypass actor into the `plan-marshall-merge-queue` ruleset — letting an org release-automation app (tag + version-bump push straight to the protected branch) proceed without a GH013 push-protection rejection. Both are absent by default; when neither is set the ruleset is created with no `bypass_actors` (the bypass-less behavior).

| Key | Type | Purpose |
|-----|------|---------|
| `merge_queue.bypass_app_id` | int | Static numeric GitHub App id — the config-only preferred path. When set, its id is used directly as an `Integration` bypass actor (`bypass_mode: always`) with **no** `gh api` call, so it works on both org-owned and personal-account repos. |
| `merge_queue.bypass_app_slugs` | list[str] | App slugs for the best-effort org-list fallback, used only when `bypass_app_id` is unset. Each slug is matched against `gh api /orgs/{owner}/installations` and the matched installation's app id is used. This path requires `admin:org` scope on an org-owned repo; it no-ops gracefully (no bypass actor, no error) when that precondition is unmet. |

On the idempotent already-configured path, `enable` self-heals the ruleset's `bypass_actors`: when a resolved id is not already present as an `Integration`/`bypass_mode: always` actor — either wholly absent, or present but carrying the wrong `actor_type`/`bypass_mode` — the wrong-shaped entry (if any) is dropped and the id is PATCHed back in with the correct `Integration`/`always` shape, so the merged set carries exactly one bypass actor per resolved id.

## Canonical invocations

The canonical argparse surface for the three CLI scripts owned by this skill,
`github_ops.py`, `github_pr.py`, and `github_re_review.py`. The plugin-doctor analyzer
(`_analyze_manage_invocation.py`) reads this section as source-of-truth for markdown
notation occurrences across the marketplace. Consuming skills xref this section by
name (e.g., "see `workflow-integration-github` Canonical invocations →
`pr create`") instead of restating the command inline. The sibling
`github_provider.py` module exposes provider declarations and shared helpers — it
has no CLI surface and is not invoked directly.

Both `github_ops` and `github_pr` accept the top-level `--plan-id PLAN_ID` /
`--project-dir DIR` routing pair (mutually exclusive) consumed before argparse runs.
`github_re_review` accepts the same `--project-dir DIR` routing flag; its
`re-review` subcommand declares its own `--plan-id` (accepted for routing uniformity).

**`--plan-id NO_PLAN`** is accepted wherever `--plan-id` is — both as the top-level
routing flag (it binds to the main checkout, never to a worktree) and as the
verb-scoped body-store binding on the ten body-bearing verbs below (`pr prepare-body`,
`pr prepare-comment`, `pr create`, `pr edit`, `pr reply`, `pr thread-reply`,
`issue prepare-body`, `issue prepare-comment`, `issue create`, `issue comment`).
The sentinel is the one plan-less
convention on this surface: there is no `--body-file` and no per-verb escape hatch,
and it is correct only for a caller that genuinely has no plan — a `--plan-id` that
failed to resolve must be corrected instead. The semantics are stated once in
[`tools-integration-ci/SKILL.md`](../tools-integration-ci/SKILL.md) § "The `NO_PLAN`
sentinel — one plan-less convention for every `--plan-id` verb" and are not repeated
per verb below.

### github_ops pr view

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr view \
  [--pr-number N] [--head BRANCH]
```

At most one of `--pr-number` / `--head`; supplying both is a structured error and
supplying neither views the PR for the current cwd HEAD. A landing poll MUST use
`--pr-number` — the platform auto-deletes the head branch as the merge queue
merges, so a `--head`-keyed lookup stops resolving exactly when the terminal
`state: merged` becomes observable.

### github_ops pr list

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr list \
  [--head BRANCH] [--state {open|closed|all}]
```

### github_ops pr create

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr create \
  --plan-id PLAN_ID --title TEXT \
  [--slot SLOT] [--base BRANCH] [--draft] [--head BRANCH]
```

The PR body is supplied via the path-allocate pattern — call `pr prepare-body`
first, write the body to the returned path, then run `pr create`.

### github_ops pr edit

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr edit \
  --plan-id PLAN_ID --pr-number N \
  [--slot SLOT] [--title TEXT]
```

### github_ops pr reply

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr reply \
  --plan-id PLAN_ID --pr-number N [--slot SLOT]
```

### github_ops pr resolve-thread

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr resolve-thread \
  --thread-id ID [--pr-number N]
```

### github_ops pr thread-reply

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr thread-reply \
  --plan-id PLAN_ID --pr-number N --thread-id ID [--slot SLOT]
```

### github_ops pr reviews

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr reviews \
  --pr-number N
```

### github_ops pr comments

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr comments \
  --pr-number N [--unresolved-only]
```

### github_ops pr wait-for-comments

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr wait-for-comments \
  --pr-number N [--timeout SECS] [--interval SECS]
```

The poll ends as soon as EITHER arm of a two-arm completion predicate fires:

- **count-growth arm** — the unresolved-comment count grows past the baseline. This is the only arm
  consulted for a bot whose registry record declares `participation_requires_update: false`, because
  such a bot appends a NEW comment per review and the count growth IS its movement signal.
- **movement arm** — a bot declaring `participation_requires_update: true` EDITED its persistent
  comment after the wait started: a comment authored by that bot (resolved through the registry
  login map), not a refusal notice, whose later of `updated_at` / `created_at` strictly post-dates
  the wait-start time. Such a bot re-reviews in place, so the count never grows and the count arm
  alone could only ever run to the full timeout.

Both arms are registry-derived — no bot is named in the predicate path. The movement arm fails closed:
a non-`dict` element in the fetched comment list is filtered, and an unparseable or absent timestamp is
a NON-match, never a match-anything wildcard.

Alongside the poll fields (`timed_out`, `duration_sec`, `polls`, `baseline_count`, `final_count`,
`new_count`) the return carries **`movement_matched_bots[]`**, **`detector_answerable`**,
**`unanswerable_reason`**, and **`rate_limited_bots[]`**.

**`movement_matched_bots[]`** names one record per bot the movement arm matched, so the caller learns
WHICH bot's edit ended the wait rather than inferring it. Empty when the count arm fired alone, or on a
timeout:

```toon
movement_matched_bots[N]{bot_kind}:
```

A match proves a re-review **ARRIVED** — it says nothing about whether the diff was reviewed well, and
must never be read or rendered as evidence of review quality.

**`detector_answerable`** / **`unanswerable_reason`** distinguish a timeout whose observable could
never have moved from one where the bots were simply silent — without them both return an identical
bare `timed_out: true`. The signal is computed from the REGISTRY ALONE and is independent of the
observed comment set: it is `false` in exactly two states, which `unanswerable_reason` names — no bot
kinds are registered at all, or every registered bot declares an empty `participation_evidence` (the
fail-closed never-provable state). `unanswerable_reason` is `""` when answerable. An await that merely
starts with zero comments, or whose bots stay silent, is `detector_answerable: true` — a genuine
timeout, NOT an unanswerable one.

**`rate_limited_bots[]`** names one record per REGISTERED bot whose newest
comment on the PR is a rate-limit / service notice posted in place of a review:

```toon
rate_limited_bots[N]{bot_kind,rate_limit_class,eta}:
```

- `bot_kind` — the registry key of the refusing bot. The bot set, and each bot's login, are derived
  from `automatic-review/standards/{bot_kind}.md`; no bot is named in the detection path.
- `rate_limit_class` — that bot's registry `rate_limit_class`: `awaitable_window` (a rolling window
  that reopens, so awaiting the reset is productive), `hard_quota` (a budget that does not reopen on
  a useful timescale, so awaiting it only burns budget), or `unknown` (no refusal observed for this
  bot). `unknown` is the fail-closed default — a caller MUST NOT await a bot whose refusal shape has
  never been observed.
- `eta` — the reset time the notice itself stated, extracted via that bot's registry
  `rate_limit_eta_patterns`, or `""` when the notice stated none. An empty `eta` means *unknown*,
  never *reopens now*.

An **empty list means no registered bot is rate-limited**. The list is per-bot by design: a single
boolean cannot say WHICH bot refused, and — because the classes differ per bot — cannot say whether
awaiting is worth anything. Detection is best-effort and never alters poll behaviour: a failed
post-poll fetch leaves the list empty.

### github_ops pr merge

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr merge \
  (--pr-number N | --head BRANCH) \
  [--strategy {merge|squash|rebase}] [--delete-branch]
```

Exactly one of `--pr-number` or `--head` is required (validated by handler).

### github_ops pr auto-merge

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr auto-merge \
  (--pr-number N | --head BRANCH) \
  [--strategy {merge|squash|rebase}]
```

### github_ops pr safe-merge

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr safe-merge \
  (--pr-number N | --head BRANCH) \
  [--strategy {merge|squash|rebase}] [--delete-branch] [--admin-merge-on-stuck-state] \
  [--poll-timeout SECS] [--poll-interval SECS]
```

### github_ops pr merge-queue

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr merge-queue \
  (--pr-number N | --head BRANCH)
```

Takes no `--strategy` / `--delete-branch` — the queue's own configuration decides
the merge method and the platform deletes the head branch after the queue merge.

### github_ops pr update-branch

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr update-branch \
  (--pr-number N | --head BRANCH)
```

### github_ops pr close

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr close \
  --pr-number N
```

### github_ops pr ready

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr ready \
  --pr-number N
```

### github_ops pr submit-review

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr submit-review \
  --review-id PRR_ID \
  [--event {COMMENT|APPROVE|REQUEST_CHANGES}]
```

### github_ops pr prepare-body

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr prepare-body \
  --plan-id PLAN_ID [--for {create|edit}] [--slot SLOT]
```

### github_ops pr prepare-comment

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr prepare-comment \
  --plan-id PLAN_ID [--for {reply|thread-reply}] [--slot SLOT]
```

### github_ops checks status

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops checks status \
  (--pr-number N | --head BRANCH)
```

### github_ops checks wait

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops checks wait \
  --pr-number N [--timeout SECS] [--interval SECS]
```

### github_ops checks wait-for-status-flip

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops checks wait-for-status-flip \
  --pr-number N [--timeout SECS] [--interval SECS] \
  [--expected {success|failure|any}]
```

### github_ops checks pull-request-runs

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops checks pull-request-runs \
  --pr-number N
```

The provider-level entry point for the PR-wide `pull_request`-run observable behind `not_triggered`.
Its body is shared verbatim with `github_pr pull_request_runs` — see that block below for the return
contract and the caller obligations, which are not restated here.

### github_ops checks rerun

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops checks rerun \
  --run-id ID
```

### github_ops checks logs

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops checks logs \
  --run-id ID
```

### github_ops issue create

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops issue create \
  --plan-id PLAN_ID --title TEXT \
  [--slot SLOT] [--labels CSV]
```

### github_ops issue prepare-body

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops issue prepare-body \
  --plan-id PLAN_ID [--slot SLOT]
```

### github_ops issue prepare-comment

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops issue prepare-comment \
  --plan-id PLAN_ID [--slot SLOT]
```

### github_ops issue comment

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops issue comment \
  --issue REF --plan-id PLAN_ID [--slot SLOT]
```

The comment body is supplied via the path-allocate pattern — call
`issue prepare-comment` first, write the body to the returned path, then run
`issue comment`.

### github_ops issue view

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops issue view \
  --issue REF
```

### github_ops issue close

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops issue close \
  --issue REF
```

### github_ops issue wait-for-close

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops issue wait-for-close \
  --issue-number N [--timeout SECS] [--interval SECS]
```

### github_ops issue wait-for-label

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops issue wait-for-label \
  --issue-number N --label TEXT \
  [--mode {present|absent}] [--timeout SECS] [--interval SECS]
```

### github_ops branch delete

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops branch delete \
  --remote-only --branch BRANCH
```

`--remote-only` is a required, explicit flag.

### github_ops repo merge-queue probe

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops repo merge-queue probe
```

### github_ops repo merge-queue enable

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops repo merge-queue enable
```

### github_ops repo label ensure

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops repo label ensure \
  --label TEXT [--color HEX] [--description TEXT]
```

### github_pr fetch-comments

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr fetch-comments \
  [--pr N] [--unresolved-only]
```

### github_pr fetch_findings

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr fetch_findings \
  --pr-number N --plan-id PLAN_ID \
  [--required-bots [CSV]] [--optional-bots [CSV]]
```

`--required-bots` / `--optional-bots` carry the review-bot participation CLASSIFICATION, not an
admission filter. A comment whose derived `bot_kind` is in NEITHER list is **still ingested**, and
the bot is reported in the return's `unclassified_bots[]` so the caller can surface the configuration
gap (the warn-but-ingest rule). A required bot's silence is a failure that gates the completeness
quorum; an optional bot's silence never gates. See
[`automatic-review/standards/bot-participation-contract.md`](../automatic-review/standards/bot-participation-contract.md).

Both list flags take an OPTIONAL value: each may be supplied bare (the flag with no value at all),
which reads as the empty list — identical to omitting it. Because both lists carry classification and
never admission, an empty list changes nothing about what is ingested; it only leaves every observed
bot unclassified, and the warn-but-ingest prose above holds unchanged. Callers interpolating a
possibly-empty variable MUST still double-quote the placeholder; the bare form is the parser-side
backstop, not a licence to leave the interpolation unquoted.

### github_pr post_responses

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr post_responses \
  --pr-number N --plan-id PLAN_ID
```

### github_pr bot_completion

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr bot_completion \
  --pr-number N --bot-kind {coderabbit|sourcery|pr-agent}
```

Pure provider read — reports the bot's registry `completion_check_name` check-run state as `{status, in_progress, completed}` for the PR HEAD. A bot with an empty `completion_check_name` reports status `no_check_name` (the caller falls back to the `review_bot_buffer_seconds` wait); the `automatic-review` completion-aware poll consumes this verb.

### github_pr pull_request_runs

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr pull_request_runs \
  --pr-number N
```

Pure provider read — files no finding and triages nothing. It answers the PR-WIDE question behind the
`not_triggered` participation state: does any `pull_request`-event workflow run exist **for this PR**?
The head branch is how the runs are FETCHED, not what the answer is scoped to — see the PR-boundary
contract point below. Return contract:

```toon
status: success
operation: pull_request_runs
provider: github
pr_number: {N}
head_branch: "{the PR's head branch}"
run_count: {every workflow run recorded for the branch}
pull_request_run_count: {the subset triggered by the pull_request event AND not excluded as another PR's}
has_pull_request_run: true | false
not_triggered: true | false
```

`has_pull_request_run` and `not_triggered` are exact complements — the pair is carried because callers
read the question in both polarities, and the predicate's own name is worth stating positively. The
predicate is **existence only**: no timestamp comparison, and no `conclusion` check.

Four contract points a caller MUST honour:

- **The observable is bounded to the REQUESTED PR, not to its head branch.** A branch is not a PR
  boundary: a branch a closed PR already used, and two open PRs sharing one head branch against
  different bases, both carry `pull_request` runs that belong to another PR. Counting those would
  suppress `not_triggered` for a PR that genuinely never triggered anything — and suppressing it
  removes the "trigger the review" remedy this observable exists to enable. A run is therefore excluded
  when its `pull_requests` association **reliably names a different PR**.

  The exclusion **fails safe, and that asymmetry is required**: GitHub's `pull_requests` array is
  unreliable — routinely empty for fork-originated runs and not guaranteed for same-repo runs — so an
  absent, non-list, empty, or number-less array KEEPS the run and the branch-scoped answer stands. Only
  a populated, usable association that omits the requested PR excludes. An unreliable association
  signal must never by itself produce `not_triggered: true`: that would manufacture spurious "the
  reviewers were never asked" verdicts and block merges, a false positive in a more damaging direction
  than the narrower false negative it would fix.
- **A `skipped` run still counts as triggered.** A `pull_request` run that exists and concluded
  `skipped` yields `not_triggered: false` — the workflow *was* triggered and declined to do work,
  which is a different fact from nothing having run at all. Only the absence of any `pull_request`-event
  run for this PR yields `not_triggered: true`.
- **`mergeable_state` is never read, returned, or branched on.** GitHub computes mergeability
  asynchronously and reports `UNKNOWN` while it is still computing, so a participation state keyed on
  it would depend on *when* the question happened to be asked rather than on what happened.
- **An unconfigured provider fails loud.** A `status: unconfigured` return is never collapsed into
  `not_triggered: true` — an unauthenticated `gh` would otherwise report every PR as never having
  triggered a review. A failed run-list fetch is likewise a structured error, not an empty list: "the
  list was never read" and "the list is empty" are distinct, and conflating them would claim the
  review bots were never triggered on evidence nobody gathered.

The verb shares ONE body with the `ci checks pull-request-runs` abstraction verb
(`github_ops.pull_request_runs_result`), so the two entry points cannot drift into different answers to
the same question. See [`tools-integration-ci/SKILL.md`](../tools-integration-ci/SKILL.md) § Canonical
invocations → `ci checks pull-request-runs` for the abstraction-layer entry point, which is the one
`automatic-review` and the pre-merge barrier call.

### github_re_review re-review

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_re_review re-review \
  --pr-number N --bot-kind {coderabbit|sourcery|pr-agent} --head-sha SHA --push-time ISO8601 \
  [--timeout SECONDS] [--plan-id PLAN_ID]
```

`--timeout SECONDS` bounds the `await_fresh_review` poll (default `DEFAULT_CI_TIMEOUT`); consumers (the trigger-A / trigger-B re-review sites in phase-6-finalize) supply their `re_review_await_timeout_seconds` step-param value here.

## Error Handling

| Failure | Action |
|---------|--------|
| `pr comments` failure | Report error to caller with stderr details |
| triage failure | Log warning, skip comment, continue |
| CI router failure | Log warning, continue — best-effort |

## Related

- `plan-marshall:tools-integration-ci` — Central CI dispatcher
- `plan-marshall:workflow-integration-gitlab` — GitLab provider counterpart
- `plan-marshall:workflow-pr-doctor` — PR diagnosis workflows
