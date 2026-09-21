# Landing Analysis: PLAN-111 — Self-ingested reply is a non-terminating barrier loop

epic: truthful-signals
workstream: WS-01
pr: 1047 — merged as `978afd182`, 2026-07-29 09:52:20 +0000

## Deliverable Fidelity vs Spec

| Deliverable | Verdict | Evidence |
|---|---|---|
| D1 — exclude the self-authored transmission shape | shipped-as-specified | start-anchored `_is_self_authored_response` pre-filter **as a distinct stage with its own counter**, subtracted from `expected_stored` |
| D2 — barrier regression: loop terminates, exhaustion reported | shipped-as-specified | bounded loop guard files a **Q-Gate finding** rather than passing silently |

⭐ **D1 followed the spec's binding constraint exactly.** The spec ruled out author identity as the
filter key (the repo owner is also the human-review identity) and required the *transmission shape*.
The implementation is start-anchored on that shape — **the constraint held under implementation**,
which is the outcome the verify-first labelling existed to protect.

⭐ **D3's termination guarantee was carried too**, via `_current_cycle_self_response_count` as a
**trailing-run** counter — because the provider returns comments grouped **by kind, not by time**.
That is a non-obvious correctness detail the spec did not anticipate and the implementation caught.

## ⭐ The defect reproduced itself during its own finalize — the strongest possible evidence

The main-checkout executor still resolved the **cached pre-fix** `github_pr.py` and re-ingested this
plan's own `## Triage dispositions` reply as pending finding `40a533`. The **identical fetch through
the worktree executor** returned `count_skipped_self_response: 1, count_stored: 0`.

⇒ **A controlled side-by-side, pre-fix vs post-fix, on the same input, in the same run.** That is
better evidence than the regression test alone, and it was recorded in the decision log rather than
merely asserted.

⚠ It also re-confirms the **stale-plugin-cache-as-evidence** hazard: the main checkout was executing
pre-fix code while the worktree had the fix. Any verification run from the wrong checkout would have
"confirmed" the defect still existed.

## Routing and Merge Behavior

- ⛔ **Merged with ZERO bot review**, at the loop-back ceiling, by operator decision. CodeRabbit
  re-attempted against the new HEAD and **refused again** (vendor rate limit); Sourcery hit its
  **weekly quota**; **pr-agent never saw `3a4d11282`**.
- ⭐ **Round 1 of this fix was itself defective, and pr-agent caught it** — the guard compared a
  **lifetime** counter against the bound. ⚠ **Without that single review, a false-positive generator
  would have shipped into the merge barrier.** The plan that fixes the barrier nearly broke the
  barrier, and one reviewer was the entire margin.
- **Cost**: 3.2M tokens / 4h24m wall against a `single_module + bug_fix` anchor of 1.3M / 90m —
  **~2.5× over**. The driver was **3 loop-back iterations, two of them pure re-review attempts
  against bots that were never going to answer.** ⇒ Direct evidence for the pending
  accepted-coverage-gap decision: **retrying a refusing bot is now a measurable cost centre**, not a
  free safety margin.

### Post-merge PR revisit — clean

Merged 09:52:20Z, latest comment 09:18:19Z. **No post-merge arrivals on this PR.**

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` = 1047; `landing`; `plan_marshall_plan_id` — all four stamped
- [x] cost overrun recorded as evidence for the coverage-gap decision
- [x] retrospective's four self-findings routed (below)

## Follow-Ups

- **The retrospective found four defects in the retrospective itself**, all one archetype:
  `affected_files_recall` reports a confident `Recall 0%` for a footprint it **structurally cannot
  resolve** (fires for every plan); `shape_violation` is **vacuous** because the verb it keys on takes
  no `--plan-id`; `dispatch_coverage_violation` **false-fires** on `architecture-refresh`; and
  `extract-chat-signal` **dropped 804 of 806 turns while reporting success**.
  ⇒ **All four route to `code-intelligence-substrate`** per the inbound routing rule — they are
  measurement-surface defects, and three already have owners there (PLAN-106, PLAN-104, PLAN-78).
- **13 messages** queued for the next drain.
