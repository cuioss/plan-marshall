envelope_version=1
sender_type=plan
sender_id=generic-charter-language-specific-defect
epic=review-apparatus
kind=landing
created=2026-08-09T18:38:03Z

# PLAN-PR-022 fully shipped — all four foreign PRs MERGED

Closes the residue tracked in `generic-charter-language-specific-defect-012.md`, which recorded
the four foreign PRs as *open, not merged*. All four have now landed, each verified from PR state
(`ci pr view` → `state: merged`) rather than from a landing message.

| PR | Deliverable | Landing evidence |
|---|---|---|
| `cuioss/pr-agent-settings#14` | D7 — central `[pr_code_suggestions]` block | direct squash, `state=MERGED, merged_at=2026-08-09T18:19:32Z` |
| `cuioss/cuioss-organization#237` | D6 — `pr-agent-improve` label gate | direct squash, `state=MERGED, merged_at=2026-08-09T18:19:58Z` |
| `cuioss/API-Sheriff#202` | D8 — Java pack + missing `AGENTS.md` | merge queue, verified `state: merged` |
| `cuioss/TokenSheriff#643` | D8 — Java pack + `AGENTS.md` case rename | merge queue, verified `state: merged` |

Together with `cuioss/plan-marshall#1130` (D1–D5), **all eight deliverables are shipped.**

## The dependency order held

D7 landed 26 seconds before D6, which is the order that matters: the label gate now gates a tool
whose `[pr_code_suggestions]` config block exists. Had they landed the other way round, `/improve`
would have been reachable while falling back to upstream defaults on the one path that writes into
the diff.

## Two mechanisms that did real work during the merge

- **The merge-queue guard refused two direct merges.** Both Java repositories have required merge
  queues on `main`, and `ci pr merge` refused rather than performing an immediate merge that would
  have closed each PR *unmerged*. That is the `#866` failure mode being caught prospectively, in
  two more repositories than it was originally found in.
- **Both direct merges returned real corroboration** (`state=MERGED, merged_at=…`) rather than a
  bare `merged: true`. Given that this verb once reported success while deleting a branch without
  merging (plan-marshall#1081), the corroborated shape is the thing that makes the report
  trustworthy — and it is what the queue-routed pair were verified against separately.

## What is now true that was not before

The two Java repositories have a reviewer with Java vocabulary for the first time, and
`API-Sheriff` has an `AGENTS.md` at all (it was configured in `repo_context_files` and absent —
the run log said `Repo context file is empty or missing: AGENTS.md`). `TokenSheriff` had one all
along under a lowercase name the case-sensitive container could never open.

**This is not yet evidence that the blind spot is closed.** The plan's own falsifiable check
remains unrun: re-review a closed Java pull request that CodeRabbit found in-charter defects on —
`API-Sheriff#185` (26 inline items) or `#154` (47) — with the pack installed, and compare against
this reviewer's recorded empty result. Until that runs, the 0-of-19 result has a plausible cause
addressed, not a demonstrated fix.

## Queue action

`PLAN-PR-022` may be stamped **shipped**. The residue item is closed.
