envelope_version=1
sender_type=plan
sender_id=wait-for-comments-counts-rows
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T17:44:54Z

# Pre-merge review barrier must fail closed when its own producer call fails

component: plan-marshall:phase-6-finalize
category: bug
confidence: high
source_plan: wait-for-comments-counts-rows
source_pr: 1071

## Context

`branch-cleanup`'s **Pre-Merge Review-Completeness Barrier** is documented as fail-closed: it
re-fetches bot comments from the provider against the current HEAD and refuses to merge unless BOTH
(a) zero `pr-comment` findings are pending and (b) every REQUIRED bot's participation against this
HEAD is proven.

On PR #1071 the barrier's own producer call died:

```
2026-08-01T17:11:52Z [ERROR] (plan-marshall:execute-script:2) script_failure
  notation=plan-marshall:workflow-integration-github:github_pr exit_code=2
  failure_kind=argparse_rejection
  detail=github_pr.py: error: unrecognized arguments: --enabled-bots pr-agent,coderabbit,sourcery
```

The PR merged at `2026-08-01T17:22:59Z`. `branch-cleanup` recorded
`outcome: done, display_detail: "merged PR #1071 via queue, main pulled, worktree removed"`.

Both predicates were therefore unevaluated at merge time. Predicate 1 fell back to whatever the
findings *store* already held (the barrier's whole purpose is to re-read the *provider*, precisely
because the store cannot see a comment that was never fetched). Predicate 2 never ran at all — the
stale cached doc the step executed has no Predicate 2 section, and its input
(`participated_bots` / `refused_bots`) comes from the return of the call that just died.

`branch-cleanup.md` states its own contract explicitly, and this run violated it verbatim:

> `exit_code != 0`: STOP and return an error TOON to the orchestrator carrying the script's stderr
> verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of
> `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally
> forbidden.

## Root cause

Two independent contributors, both required for the failure:

1. **Stale runtime plugin-cache pin** (see sibling candidate-lesson 1) supplied a pre-#1041 barrier
   doc whose invocation shape no longer parses against the live script.
2. **No structural fail-closed enforcement.** The fail-closed property lives only in prose. Nothing
   in the executing path converts "the barrier's producer returned non-zero" into "do not merge".
   A gate whose evidence-gathering step fails is indistinguishable, downstream, from a gate that
   gathered evidence and found nothing wrong.

Contributor 2 is the one worth fixing here: contributor 1 will recur in some other form, and the
barrier must survive it.

## Proposed action

- Bind the barrier's verdict to an explicit tri-state — `clean` / `blocked` / **`indeterminate`** —
  and make `indeterminate` take the same path as `blocked` (`fail_into_loopback` / `ask`), never the
  clean path. A non-zero exit from `fetch_findings`, an `unconfigured` status, or an absent
  `participated_bots` field all resolve to `indeterminate`.
- Add a `mark-step-done` guard: `branch-cleanup` may not record `outcome: done` with a merge in its
  `display_detail` unless a barrier verdict was recorded in the same run.
- Cross-check the finalize step docs' fenced invocations against the live scripts' argparse surfaces
  at dispatch time, not only at edit time (see sibling candidate-lesson on dispatch-time validation).

## Evidence

- aspect: script_failure_analysis — `invented_flag` finding, `plan-marshall:workflow-integration-github:github_pr fetch_findings`, exit 2, `2026-08-01T17:11:52Z`.
- aspect: logging_gap_analysis — no `decision.log` entry from `branch-cleanup` between the 17:11:52Z error and the 17:22:59Z merge; the barrier emits no verdict line on its clean path, so "passed" and "never ran" are byte-identical in the log.
- aspect: chat_history_analysis — 894 transcript turns, zero operator interventions; `final_merge_without_asking=true` meant no human checkpoint existed between the failed barrier and the merge.
- `status.metadata.phase_steps["6-finalize"]["branch-cleanup"] = {outcome: done, display_detail: "merged PR #1071 via queue, main pulled, worktree removed"}`.

## Note on framing

This plan's own deliverable 3 was *"A detector that cannot answer says so — an await that ends because
its observable can never change must report THAT, not a timeout."* The same plan's finalize ran a
detector that could not answer, and it did not say so. It merged.
