# PR Review Operations

Operations for interacting with pull request reviews: comments, replies, thread resolution, approval state.

---

## Workflow: Reply to PR

**Pattern**: Provider-Agnostic Router

Post a comment on a pull request using the three-step path-allocate pattern.
The script owns path allocation — callers never invent scratch paths. Markdown
bodies are written directly by the main context with its native Write tool, and
the `pr reply` subcommand consumes the prepared file. No multi-line markdown
crosses the shell boundary, so the host platform's shell-heading heuristic never
fires.

### Step 1: Allocate Scratch Body Path

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr prepare-comment \
    --plan-id {plan_id} --for reply --slot {unique_slot}
```

Read the `path` field from the returned TOON. It is the canonical, script-owned
location for the reply body, bound to this plan and slot. Pick a `--slot` value
that is unique for each concurrent reply so their bodies do not collide.

### Step 2: Write the Reply Body

```text
Write({path from prepare-comment}) with reply body markdown content
```

### Step 3: Post the Reply

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr reply \
    --pr-number 123 --plan-id {plan_id} --slot {unique_slot}
```

The subcommand reads the body from the prepared scratch file, posts the
comment, and deletes the scratch on success.

### Step 4: Process Result

```toon
status: success
operation: pr_reply
pr_number: 123
```

---

## Workflow: Resolve Review Thread

**Pattern**: Provider-Agnostic Router

Resolve (mark as resolved) a review thread on a PR.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr resolve-thread \
    --pr-number 123 --thread-id PRRT_abc123
```

### Step 2: Process Result

```toon
status: success
operation: pr_resolve_thread
thread_id: PRRT_abc123
```

---

## Workflow: Reply to Review Thread

**Pattern**: Provider-Agnostic Router

Reply to a specific review thread (inline code comment), not a top-level PR
comment, using the three-step path-allocate pattern. The script owns path
allocation — callers never invent scratch paths. Markdown bodies are written
directly by the main context with its native Write tool, and the `pr
thread-reply` subcommand consumes the prepared file. No multi-line markdown
crosses the shell boundary, so the host platform's shell-heading heuristic never
fires.

### Step 1: Allocate Scratch Body Path

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr prepare-comment \
    --plan-id {plan_id} --for thread-reply --slot {unique_slot}
```

Read the `path` field from the returned TOON. It is the canonical, script-owned
location for the thread-reply body, bound to this plan and slot. Pick a
`--slot` value that is unique for each concurrent thread-reply so their bodies
do not collide.

### Step 2: Write the Thread-Reply Body

```text
Write({path from prepare-comment}) with thread-reply body markdown content
```

### Step 3: Post the Thread-Reply

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr thread-reply \
    --pr-number 123 --thread-id PRRT_abc123 --plan-id {plan_id} --slot {unique_slot}
```

The subcommand reads the body from the prepared scratch file, posts the
thread-reply, and deletes the scratch on success.

### Step 4: Process Result

```toon
status: success
operation: pr_thread_reply
pr_number: 123
thread_id: PRRT_abc123
```

---

## Workflow: Get PR Reviews

**Pattern**: Provider-Agnostic Router

Get reviews for a pull request.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr reviews \
    --pr-number 123
```

### Step 2: Process Result

```toon
status: success
operation: pr_reviews
pr_number: 123

reviews[2]{user,state,submitted_at}:
alice	APPROVED	2025-01-15T10:30:00Z
bob	CHANGES_REQUESTED	2025-01-15T11:00:00Z
```

---

## Workflow: Get PR Comments

**Pattern**: Provider-Agnostic Router

Get inline review comments on a PR.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr comments \
    --pr-number 123
```

### Step 2: Process Result

```toon
status: success
operation: pr_comments
provider: github
pr_number: 123
total: 3
unresolved: 2

comments[3]{id,thread_id,author,body,path,line,resolved,created_at}:
IC_abc123	PRRT_thread1	alice	Fix this null check	src/Main.java	42	false	2025-01-15T10:30:00Z
IC_abc124	PRRT_thread1	bob	Done	src/Main.java	42	false	2025-01-15T11:00:00Z
IC_abc125	PRRT_thread2	alice	Typo here	README.md	10	true	2025-01-15T09:00:00Z
```

See [api-contract.md](api-contract.md) for provider-specific field mappings.

---

## Workflow: Wait for New Review Comments

See [blocking-wait-pattern.md](blocking-wait-pattern.md) for the general pattern, timeout/interval guidance, and the full wait-for-* subcommand catalog.

**Pattern**: Provider-Agnostic Router (polling, replaces blocking shell sleep)

Block until review activity is observed on the PR or the timeout elapses. On entry it snapshots both the unresolved-comment count and a wait-start timestamp, then polls on the standard CI interval and exits as soon as EITHER arm of a two-armed completion predicate fires: the count grows (for a bot that appends a new comment per review, `participation_requires_update: false`), OR a `participation_requires_update: true` bot's existing comment moves — the LATER of its `updated_at` / `created_at` passing the wait-start — which is how a bot that re-reviews by EDITING one persistent comment in place is detected without any count growth. Used by `workflow-pr-doctor`'s Automated Review Lifecycle (Step 2) in place of a bash `sleep`, which the harness blocks for long leading durations.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr wait-for-comments \
    --pr-number 123 --timeout 180
```

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--pr-number` | yes | — | PR number |
| `--timeout` | no | 300 (caller usually passes `review_bot_buffer_seconds`, sourced from the `plan-marshall:automatic-review` step's params in the manifest step-params snapshot) | Max wait time in seconds |
| `--interval` | no | 30 | Poll interval in seconds |

### Step 2: Process Result

```toon
status: success
operation: pr_wait_for_comments
pr_number: 123
timed_out: false
duration_sec: 47
polls: 2
baseline_count: 1
final_count: 2
new_count: 1
detector_answerable: true
unanswerable_reason: ""

rate_limited_bots[1]{bot_kind,rate_limit_class,eta}:
coderabbit	awaitable_window	18 minutes

movement_matched_bots[0]:
```

`status: success` is returned even when `timed_out: true` — the caller should still proceed to fetch comments (`pr comments --unresolved-only`) and triage whatever did arrive. `status: error` is reserved for fetch/auth failures.

`movement_matched_bots[]`, `detector_answerable`, and `unanswerable_reason` are specified per-field in [api-contract.md](api-contract.md) § "Provider Field Mapping" → `pr wait-for-comments`, which this section does not restate. The one consequence a caller must act on: a `timed_out: false` return carrying `new_count: 0` and a non-empty `movement_matched_bots[]` is the normal shape for an in-place re-review — not an anomaly — so a caller MUST NOT read `new_count == 0` as "no review arrived".

⚠ **`detector_answerable` / `unanswerable_reason` are REPORTED, not yet consumed.** No caller currently branches on `detector_answerable`: the consumer tables in [`automated-review-lifecycle.md`](../../workflow-pr-doctor/standards/automated-review-lifecycle.md) and [`automatic-review/SKILL.md`](../../automatic-review/SKILL.md) route on `timed_out` alone, so an `escalate_ask` re-wait offer can still be presented for a wait that could never have succeeded. Wiring a consumer branch is deliberately outside this contract's scope — the fields exist so the distinction is LEGIBLE in the return and the logs, which is the precondition for acting on it, not the acting itself. A caller that does branch should treat `detector_answerable: false` as "re-waiting cannot help" and skip straight to escalation.

`rate_limited_bots[]` (bot-agnostic, default empty) carries one `{bot_kind, rate_limit_class, eta}` record per REGISTERED reviewer bot whose newest comment on the PR is a rate-limit / service notice posted in place of a review, rather than an actual review. An empty list means no registered bot is rate-limited. It is an additive discriminator — the poll behaviour and every other field are unchanged; a caller that ignores it sees identical semantics. See [api-contract.md](api-contract.md) § "Provider Field Mapping" → `pr wait-for-comments` for the authoritative per-field contract, which this section does not restate.

When the list is non-empty, the just-observed comment growth is a status notice from those bots, not reviewable feedback, so the caller should not triage the notice as a finding. Whether to WAIT for the limit to lift is decided per record by `rate_limit_class`, never uniformly: `awaitable_window` reopens on its own so awaiting the reset is productive, `hard_quota` does not reopen on a useful timescale so awaiting only burns budget, and `unknown` is the fail-closed value for a bot whose refusal shape has never been observed and MUST NOT be awaited. The example row above is illustrative of the shape — the bot set and every per-bot value are registry data, not literals in this contract.

---

## The widened participation taxonomy

Every review operation on this surface feeds ONE downstream classification: the closed
non-participation taxonomy owned by
[`automatic-review/standards/bot-participation-contract.md`](../../automatic-review/standards/bot-participation-contract.md).
That taxonomy has **seven** members, and this section records only which observation on this surface
feeds which member — the semantics, the severity rules, and the closure statement live in the contract
and are not restated here.

| Member | Fed by |
|--------|--------|
| `participated` / `participated_but_empty` | `github_pr fetch_findings` → `participated_bots[]` (evidence-typed publish shapes) |
| `participated_stale` | `github_pr fetch_findings` → `stale_participation_bots[]` (publish shape matched, `participation_requires_update` currency test failed) |
| `refused_awaitable` / `refused_hard` | `github_pr fetch_findings` → `refused_bots[]`, unioned with `pr wait-for-comments` → `rate_limited_bots[]`; the split comes from each bot's registry `rate_limit_class` |
| `in_progress` | `github_pr bot_completion` → the non-terminal check state at the poll bound |
| `not_triggered` | `checks pull-request-runs` → `not_triggered` (PR-wide: no `pull_request`-event run exists at all) |
| `absent` | no observation of any kind — the fail-closed fall-through |

Two of those members are **refinements of `absent` whose remedies are its opposite**, which is why a
consumer must not flatten them back together:

- `participated_stale` — the bot DID publish; the review merely predates this HEAD. Remedy:
  **re-trigger** the review.
- `not_triggered` — nothing ran on account of the PR, so no bot was ever asked. Remedy: **trigger** the
  review at all.

`absent`, by contrast, means a reviewer was asked and did not answer — remedy: **escalate** the
non-participation. A consumer that renders all three as "the bot did not review" prescribes escalation
in two cases where a trigger was the correct and cheaper answer.

**Provider coverage is not uniform, and the gap is explicit.** `stale_participation_bots[]` and the
`not_triggered` observable are both GitHub-only today: `checks pull-request-runs` returns a structured
unsupported error on GitLab (see [api-contract.md](api-contract.md#checks-pull-request-runs) for the
refusal and its rationale), and `gitlab_pr fetch_findings` declares neither `--required-bots` nor
`--optional-bots`, so the whole participation-classification arm is a GitHub capability there. On a
GitLab host the taxonomy is therefore reachable only as far as the provider's own reads allow — a
capability gap surfaced at the point of use, never a silently narrower verdict.
