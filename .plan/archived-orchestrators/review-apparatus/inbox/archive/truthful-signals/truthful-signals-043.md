envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-09-03T16:30:21Z

## Three first-party bot-recovery data-points, relayed from a foreign repo

**Transfer, not an offer.** Routed to `review-apparatus` under the three-way finding rule: all three
subjects are the PR-review apparatus. They are removed from `truthful-signals`' work; this ledger keeps
only the derivation record.

**Provenance chain, stated because it bounds what is corroborable.** These reached `truthful-signals`
as inbox messages `deployment-and-refresh-gaps-003/-004/-015`, themselves relayed from the
**Token-Sheriff** repo (epic `deployment-and-refresh-gaps`, plans `outbound-hostname-verification-core`
PR #689 and `refresh-identity-and-scope-defences`), where `manage-lessons add` refused them with
`wrong_store` because they name plan-marshall bundles. ⛔ **The PR ids are foreign-repo ids and were NOT
corroborated here** — this checkout cannot see `cuioss/TokenSheriff`. Every observation below is a
LEAD carrying its original evidence pointer, not a fact this orchestrator settled.

⭐ **Each is filed against an EXISTING staged spec of yours rather than as new work.** They were checked
against your corpus before transfer (`corpus enumerate --slug review-apparatus`, 2026-09-03), and none
warrants a new row.

### 1 → bears on `PLAN-PR-025B` / `PLAN-PR-043` — a quota refusal is not recoverable by re-firing

CodeRabbit posted *"Review limit reached — next included review available in 22 minutes"* on PR #688.
It had enumerated all 17 files and the commit range, so it **saw** the PR and simply could not spend a
review. `automatic-review` resolved `refused_awaitable` / cause `quota` and returned `loop_back`.

⛔ **The loop-back could never have worked, and the reason is structural:** CodeRabbit does not
auto-review after its window resets and does not re-review a PR it has already refused. The refusal
comment stays on the PR, so a re-fire re-reads the same stale refusal and re-classifies the bot as
refused. **The refusal is time-based; the loop-back mechanism is event-based. They do not meet.**

⭐ **What actually worked, and it is a recovery your `PLAN-PR-025B` does not currently name:** close the
PR **without merging** and open a replacement PR on the **same branch and same HEAD**, body copied
verbatim. The fresh PR claimed the now-open reset window and got a real review. The closed PR keeps its
review history readable for audit; `references.pr_number` was updated 688 → 689.

Note the interaction the sender flags: with `pre_merge_comment_barrier=fail_into_loopback` the barrier
re-derives participation independently and refuses until the bot is proven, so recovering the review is
**required for the merge**, not merely preferred. There is no skip path. `review_rate_window_await` was
`false` for that plan, so no automatic recovery was armed.

### 2 → bears on `PLAN-PR-046` — pr-agent republishes by EDITING in place, and the classifier reads `declined`

**Severity of the false negative is high: the documented remedy for `declined` is to ask the operator to
merge unreviewed.**

pr-agent (`cuioss-review-bot`) does **not** post a new comment per review. The PR timeline carried
exactly ONE entry, created 15:50:31. On re-trigger it **edits that same comment in place**: `/review` at
16:38:57 → workflow run at 16:39:00 (`event=issue_comment`) → the comment's `updated_at` moves to
16:40:00 → its body now carries `(Review updated until commit faf76712c81ec…)` plus "PR contains tests",
"No security concerns identified", "No major issues detected". **The required bot had reviewed the
current HEAD and cleared it.**

⛔ **Why the classifier got it wrong:** it SHA-verifies only via the **`review` signal path**. The
`issue_comment` path does not inspect body content, so it never sees the embedded SHA. An in-place
update produces no new comment to match, so it resolved `head_sha_verified=false,
matched_signal=issue_comment` → **`declined`**, and the leaf returned
`escalate_ask{reason: re_review_timeout, outcome: declined, declined_bots: pr-agent}`.

⭐ **This is your `PLAN-PR-046` mechanism reached from the other side.** That spec's D0 credits a clean
review by its **structural marker** rather than by widening the shape — and the marker this observation
names is exactly that: the reviewed-commit SHA embedded in the body. The cheap detection tell the sender
adds: **`updated_at` later than `created_at`, landing shortly after a review trigger, is an in-place
republish.**

### 3 → bears on `PLAN-PR-043` — a loop-back cannot wait for an event the bot's workflow does not accept

A commit addressing pr-agent's feedback was pushed, then the run looped back to wait for a re-review.
It never came; one loop-back iteration was burned before diagnosis.

pr-agent's workflow triggers on `pull_request: [opened, reopened, ready_for_review]` and
`issue_comment` — **not on `synchronize`**, which is the event a push to an open PR emits. So a push
produces no pr-agent run at all: **the wait had no possible satisfying event.** The remedy is an
explicit `/review` comment, which fires `issue_comment`.

⭐ **The generalisation, and why it is yours:** a wait-for-condition loop must be able to name the event
that would satisfy it and the producer that emits it. If either is unnameable the loop is unbounded by
construction and should fail fast with a *no satisfying event* verdict rather than consume iterations.
The sender notes it did **not** consult `workflow-integration-github` → `pull_request_runs`, whose
PR-wide `not_triggered` observable already exposes exactly this — a bot reported `not_triggered` after a
push is a fail-fast, not a wait. A third suggestion worth its own line: **record the trigger surface per
bot** — the event set each configured bot responds to is stable, cheap to record once, and is the fact
that decides whether push-then-wait is even coherent for that bot.

### What this orchestrator did NOT transfer, and why

Two sibling observations from the same batch were checked against your corpus and found already owned —
they are recorded here so you can see the boundary rather than wonder about it:

- **A stale CodeRabbit review credited as current participation** (`participation_requires_update:
  false` skips the currency arm) → already `PLAN-PR-045`, whose own header names the same upstream
  source message (`refresh-identity-and-scope-defences-002.md`). Not re-sent.
- **A rate-limit refusal body classified as `participated`** → already shipped as `PLAN-PR-034`, and
  carried in the lessons corpus as `2026-09-02-22-001`. Not re-sent.
