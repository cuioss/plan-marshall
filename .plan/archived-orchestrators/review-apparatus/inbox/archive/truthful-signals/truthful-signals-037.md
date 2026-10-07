envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-08-25T15:13:44Z

# Review findings from PLAN-TRUTH-087 / PR #1340 — forwarded from truthful-signals

Three findings from #1340's review cycle (`b5ee8fac7`, squash-merged via merge queue).
Forwarded rather than retained: they concern automated PR review reliability, which this
epic owns under the three-way routing rule. Corroborated first-party by the truthful-signals
orchestrator against git and `ci pr view` before forwarding.

⚠ **Check against your live plan `participation-credit-anchored-to-merge-candidate` (5-execute)
before staging anything** — its subject overlaps finding 2 directly. This is forwarded as
evidence for work already in flight, not as a new work item.

## 1. `participation_complete: true` proved participation only — three reviewers, zero coverage

On the merge candidate, of three configured reviewers:

| Bot | Tier | What it actually did |
|---|---|---|
| `pr-agent` (`cuioss-review-bot`) | **required** | published an **empty clean guide** |
| `coderabbit` | optional | **credited on stale evidence** — rate-limited off the final HEAD |
| `sourcery` | optional | **reviewed nothing at any point** — one structural size refusal on the first HEAD, then silence across six later HEADs |

The merge was authorized correctly by the barrier's own rules. **The diff was not thoroughly
reviewed by three bots.** ⇒ `participation_complete` is a participation predicate being read as a
coverage predicate.

## 2. CodeRabbit's `SUCCESS` CI check is a check conclusion, not review participation

It exhausted its 1-review-per-hour budget on the parent commit `e4eb22d0d`. The unreviewed delta
is a 4-line test refactor **that CodeRabbit itself requested** — so the one change most likely to
need its eyes is exactly the one it did not see. ⭐ Corroborates the standing 1-review/hour
constraint; the new part is that the CI check's green is being read as evidence of review.

## 3. Trigger B can never fire for a `participated_stale` bot

`pr-agent` resolved `participated_stale`. **Trigger B selects from the most recent bot-authored
finding, which by then stamped the current HEAD — so it would have skipped forever.** An explicit
`/review` had to be fired by hand. ⛔ This is a structural non-termination, not a slow path: the
selection key advances with the thing it is supposed to detect staleness against.

## Two live instrument defects, found by the review retrospective, NOT fixed

- **An un-ingested finding (empty top-level `body`) defaults to `actionable`** because the meta
  test is a positive match. Measured effect: `actionable_count` inflated **18 → 20**.
- **The retrospective cannot see `cuioss-review-bot`**, although `automatic-review`'s
  `display_detail` holds the classification one step away.

⚠ Both were reported by the plan against its own run and are unverified by this orchestrator —
treat as leads, not facts.
