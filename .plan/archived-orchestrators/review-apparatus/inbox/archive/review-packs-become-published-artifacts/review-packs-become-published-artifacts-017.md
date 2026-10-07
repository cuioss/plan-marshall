envelope_version=1
sender_type=plan
sender_id=review-packs-become-published-artifacts
epic=review-apparatus
kind=landing
created=2026-09-03T22:48:37Z

## What landed

review-packs-become-published-artifacts shipped as #1388 (merged) — the pr-agent target now emits an orthogonal artifact set (one per derived domain plus one spine carrying the charter exactly once) published to cuioss/pr-agent-settings, replacing the per-repository assembled `.pr_agent.toml` blob.

```landing-facts
schema=landing-facts/1
plan_id=review-packs-become-published-artifacts
epic=review-apparatus
pr=#1388
merge_state=merged
deliverables_total=5
deliverables_done=5
total_tokens=4063723
total_wall_seconds=193346.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,finalize-step-security-audit:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,sonar-roundtrip:done,adr-propose:skipped,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.action=merged
step.record-metrics.any_phase_missing_end_time=false
step.create-pr.pr_number=1388
```

## Residue

**The merge cleared its review barrier by authorization, not by completed bot participation.** `participation_complete` was `false` with `unproven_bots=[pr-agent, sourcery]`. A HEAD-bound `barrier-ask-override` over gap-class `review-barrier-gap` was granted at `0a6fa35f7`. The gap it covers is a **detector** gap, not a review gap — finding `e8bde7` records why: `head_sha_verified` is derived from the signal TYPE (a review object verifies, an issue_comment does not), and pr-agent re-reviews by editing one issue comment in place, so it can **never** yield `head_sha_verified: true`. A plan with pr-agent in `required_bots` therefore cannot clear a `participated_stale` block by the remedy the contract prescribes for that state. pr-agent did in fact review this exact HEAD and reported no major issues; the probe's own matched-comment body names the commit. **This is squarely this epic's subject matter.**

**Sourcery refused structurally** — a declared diff-size ceiling (cap 150000 against 2963 changed lines). Not clearable by waiting or re-triggering.

**CodeRabbit's included review budget was spent on both rounds** (1 review/hour; `0 remain` after the second).

**Eight findings filed during finalize are pending in a store that dies with the plan directory.** `e8bde7`, `5a5761`, `18f362`, `79a483`, `1d5140`, plus `c8e4a9`, `1f0c43`, `d4501c`. Inbox message 016 is the candidate-lesson for the missing carry-out route; the findings themselves have no route out. `79a483` additionally holds two ADR proposals still awaiting per-proposal operator confirmation before `manage-adr create` — `adr-propose` is recorded `skipped` for exactly that reason.

**Scope drift the coverage metrics structurally cannot show.** All 5 deliverables report 100% coverage of their *declared* paths, yet 12 of 23 landed files (52%) sit outside every deliverable's declared surface — tasks 8 and 10 landed build-server `--timeout` protocol work attributed to deliverable 1, whose declared surface is `marketplace/targets/pr_agent`. Because recall is computed over the declared set, out-of-surface work cannot lower any figure: a PR titled "publish review packs to pr-agent-settings" landed a build-server change with every metric green.

**Budget: 4.06M tokens against the `multi_module + feature` error anchor of 2.5M — 1.63×.** 6-finalize alone is 48% (1,944,394) versus 620,880 for execute. One errored dispatch returned nothing for 344,716 tokens. Billing-weighted total 86.2M. Build time is **unavailable, not zero** — the change ledger holds no build rows despite 68 `pyproject_build` calls totalling 80.3% of plan script time.

**Two retrospective-machinery defects found in-run**, both recorded as candidate-lessons rather than fixed here: `extract-chat-signal.py` silently truncates its payload (9 turns / 2382 bytes in, 4 turns / ~765 bytes out) while forwarding complete-looking counts, losing 6 of 8 operator turns; and every tier of the footprint resolver is worktree-bound, so it cannot serve a retrospective ordered after `branch-cleanup` removes the worktree.

**Two terminal-step outcomes are as-of-emission**: `emit-landing` is executing as this message is written, and `archive-plan` has not yet run.

**Operator debt outside the plan**: the host plugin registry pin is stale again (registry `0.1.1585`, cache now `0.1.1591`) — repair is `python3 .plan/temp/repair-plugin-pin.py --target 0.1.1591`. The build-daemon reconcile was deferred (owed ×1) because a build was in flight.
