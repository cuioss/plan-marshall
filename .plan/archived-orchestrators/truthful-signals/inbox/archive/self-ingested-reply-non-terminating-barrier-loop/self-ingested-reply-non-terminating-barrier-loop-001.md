envelope_version=1
sender_type=plan
sender_id=self-ingested-reply-non-terminating-barrier-loop
epic=truthful-signals
kind=landing
created=2026-07-29T09:44:08Z

## What landed

**PR #1047** — `fix(github-pr): exclude self-authored replies, add loop guard` (PLAN-111).

The pre-merge comment barrier could re-ingest its own triage reply as a new "unresolved" comment, looping without terminating. The fix adds a start-anchored `_is_self_authored_response` pre-filter as a 5th stage in `cmd_fetch_findings`, with its own counter, plus a bounded self-response-loop guard that files a Q-Gate finding at the bound.

## Root-cause reframe (the epic's own theme, reproduced inside its own fix)

**Round 1 of the fix was itself defective, and `pr-agent` caught it in review.** The loop guard compared a **lifetime** counter — `fetch_findings` runs with `unresolved_only=False`, so it counts every historical `## Triage dispositions` comment ever posted on the PR — against the fixed bound. Any PR that legitimately completed 3+ triage cycles would falsely trip the guard. Fixed in TASK-004 by adding `_current_cycle_self_response_count`, a trailing-run count that relies on the provider returning comments grouped by kind (not strict chronological order) to isolate the current cycle. This is a confident signal ("loop detected") hiding a caveat ("counting history, not convergence") — the exact epic theme, recurring inside the plan built to fix a different instance of it.

## Resolved at outline

Two spec hypotheses were confirmed before implementation: `## Triage dispositions` is a reliable dedup key **only** when start-anchored (not a substring match), and `fail_into_loopback` does exist as the `branch-cleanup.pre_merge_comment_barrier` step-param value.

## Merged unreviewed at the loop-back ceiling

The fix commit (TASK-004, which corrected the round-1 defect) was itself never reviewed by any bot: `coderabbit` hard-rate-limited (vendor-side, ~57 min, re-attempted and refused against the new HEAD), `sourcery` was over its weekly quota, and `pr-agent` did not run against the fix commit at all (it had already reviewed and caught the round-1 defect on an earlier HEAD). The operator merged anyway at the ceiling.

## Residue the epic should track

1. **Tool defect, second independent occurrence** — `manage-solution-outline get-module-context` failed with `worktree_resolution_failed` at phase-3 in this run too (it reads architecture hints and needs no worktree, but phase-3 runs pre-worktree). Corroborates `dispatched-leaf-has-no-search-primitive-004.md` already in this inbox/archive.
2. **Process defect (structural, not yet fixed)** — the plan's success criteria required each new test to be "observed FAILING pre-fix", but the plan's own `depends_on` ordering placed the fix task before the test tasks, making that observation impossible by construction.
3. **Zero-bot-review of a corrective fix commit** at the loop-back ceiling — see above; this is a sharper instance of the epic's headline theme than a merely-absent reviewer, because the un-reviewed diff is the one that fixed a bug an earlier review had just caught.

Each of items 1-3, plus the round-1 counter defect and the outline verification-quality note, rides as its own `candidate-lesson` message alongside this landing.
