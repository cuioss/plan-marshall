envelope_version=1
sender_type=plan
sender_id=arm-the-refusal-recovery-that-has-never-run
epic=review-apparatus
kind=landing
created=2026-09-07T14:32:48Z

## What landed

arm-the-refusal-recovery-that-has-never-run shipped as #1433 (merged, `29a3dad1c`) — the CodeRabbit rate-window refusal recovery, armed and exercised on itself.

```landing-facts
schema=landing-facts/1
plan_id=arm-the-refusal-recovery-that-has-never-run
epic=review-apparatus
pr=#1433
merge_state=merged
deliverables_total=5
deliverables_done=5
total_tokens=19482607
total_wall_seconds=162168.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:skipped,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:n/a,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.create-pr.pr_number=1431
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.merge_state=merged
step.record-metrics.any_phase_missing_end_time=false
```

## Residue

**The `pr` fact and the `create-pr` step record disagree, and the disagreement is the point.**
`create-pr` recorded `pr_number=1431`. #1431 is **closed unmerged**: the plan's own close-and-reopen
recovery — deliverable 10, running on the plan that was shipping it — replaced it with **#1433**, which
is what merged as `29a3dad1c`. No step re-recorded the substitution, so the step-level fact is stale
rather than wrong. `pr=#1433` above is stamped from PR state, and both numbers are carried so the epic
can see the replacement instead of inferring it. A step that creates a PR and a recovery that replaces
it need a write-back seam; there is none.

**The run reported a review that never happened.** The orchestrator stated "CodeRabbit round 4 came back
clean" for commit `1af15958`. CodeRabbit's last completed review covered only `d75ded9e`; the account-scoped
quota refused the rest. A `count_stored: 0` finding-fetch was read as *reviewed and clean* when it meant
*not reviewed*, and a fresh `cause=quota` refusal was dismissed as a known stale comment. Caught only by
`project:finalize-step-review-retrospective`, after the merge. This is the epic's own
confident-signal-hides-a-caveat archetype, reproduced inside the plan that was shipping guards against it.

**Remedy, completed post-merge.** A scaffolding PR (#1440) between two throwaway branches at the endpoints
of the unreviewed delta obtained the missing review. It found a **Major** — `parse_toon` deleting the first
character of a shallow-indented block-scalar payload, character-level corruption of the shared TOON
transport, reported by nothing — plus a Minor. Both fixed in **#1441**, merged as `05ca6fe7b`, with
CodeRabbit clean at HEAD (`coveredCommitId` matching), Sourcery approved, CI green. #1440 closed unmerged,
both scaffolding branches deleted.

**Post-hoc review recipe (reusable).** `@coderabbitai review` on a merged PR is refused
(*"Pull request is closed"*). A PR between throwaway branches at the delta endpoints works, but the
`@coderabbitai review` comment is **mandatory** — auto-review does not fire on a non-default base branch.
That same base-branch filter is why the technique sidesteps the heavy `verify` workflow: `python-verify.yml`'s
`pull_request:` trigger filters on the base being `main`.

**Reviewer yield.** CodeRabbit found **four Majors across three rounds** that five self-review rounds, a
clean 37-rule plugin-doctor gate, and six whole-tree verifies all missed: cap bypass across PRs; an
`escalate_exhausted` arm with no correct reachable path, discarding a paid-for claim; `.strip()` corrupting
bodies in the close-and-reopen path; and the `parse_toon` truncation above.

**Live defect on `main`, filed as `c27d28` (Q-Gate store, phase 6-finalize).** The always-on skip gate in
`test/conftest.py` fails every macOS verify: `test_read_process_argv_reads_this_process_from_proc` skips
with *"no /proc on this platform"* and is not in `_SKIP_EXCEPTIONS`. Pre-existing, unrelated to this plan,
and deliberately **not** silently appended to the exception list.

**Two findings already transferred to the `truthful-signals` epic inbox**: `f94f11`, `d66348`.

**Measurement gap.** Three channels went dark over `6-finalize` — the phase that did the most work: no
accumulator file, no dispatch-boundary file, and `check-dispatch-audit` classified 16/16 finalize steps
`no_evidence`. The `total_tokens` above is a floor, not a settled figure, despite
`any_phase_missing_end_time=false`.

**A producer defect the retrospective found in its own substrate.** `extract-chat-signal` still emits a raw
multi-line quoted scalar whose `operator-decision:` and `user:` lines sit at column zero, which `parse_toon`
reads as phantom top-level keys — the exact class this plan fixed for `ci pr view` / `ci issue view` using
the `BlockScalar` marker the plan itself added. The sibling producer was never swept, and its payload is
operator-authored free text, so the forgery surface is wider than the two that were fixed.

**The participation ledger conflates observation currency with review provenance.** The plan's own artifact
shows `reviewed_commit_sha` re-stamped at fetch time: comment `IC_kwDOQ3xasM8AAAABS4ng4A` appears under three
different shas, `PRRC_kwDOQ3xasM7rTFi6` under two. Every consumer reads that field as *which commit this
review covered*. That producer-side conflation is the substrate under the false-clean call above; fixing only
the consumer leaves it live.
