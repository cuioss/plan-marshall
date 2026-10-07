envelope_version=1
sender_type=plan
sender_id=merge-queue-enqueue-does-not-take
epic=review-apparatus
kind=candidate-lesson
created=2026-08-03T21:04:05Z

component=plan-marshall:tools-integration-ci
category=anti-pattern
title=A routing table written in prose is not an enforcement boundary — only the callee can refuse an off-routing dispatch
confidence=high
source_plan=merge-queue-enqueue-does-not-take
source_pr=1087
severity=root-cause-unestablished

# A routing table written in prose is not an enforcement boundary — only the callee can refuse an off-routing dispatch

## Context

`branch-cleanup`'s merge routing is a two-branch decision expressed in workflow prose: with
`use_merge_queue: true` dispatch `ci pr merge-queue`, otherwise dispatch the direct-merge path. Both
branches are documented, both are reachable, and the plumbing that feeds the decision was verified
correct — `use_merge_queue: true` was present in the step-params payload.

The verb that was actually dispatched in the #1081 incident was **`ci pr merge`** — a verb named on
**neither** branch of that routing. The dispatch did not take the wrong branch; it left the routing
entirely, and landed on the single merge-shaped verb that had no preflight, no readiness poll, and no
post-merge corroboration. That verb then returned `merged: true` for a PR that closed **unmerged**.

## Root cause

Only the *destination* of the departure is established. **Why the executor left the routing is not
established** — no artifact recorded the decision, and the plan explicitly declines to claim one.

What *is* established is the structural reason the departure was survivable: the routing lived only in
prose read by the caller, and the callee accepted any invocation that arrived. A prose routing table
constrains a compliant caller and constrains nothing else. Every verb reachable outside the routing is a
silent alternative entry point, and the least-defended verb is the one an off-routing dispatch is most
likely to reach — precisely because it is the one with the fewest arguments and the fewest checks.

Note the asymmetry that made this expensive: the off-routing target was not merely *un-preflighted*, it
was the *only* merge-shaped verb with no post-merge check. The departure and the false green are the same
event only because containment was absent at exactly the point the routing did not cover.

## Proposed action

1. **Treat "the caller is documented to route correctly" as an unverified assumption, never a guarantee.**
   For any verb set where one member is destructive and the members are mutually exclusive by policy, the
   refusal must live at the **callee**, which is the only party present on every path. This plan shipped
   exactly that containment for the merge-shaped verbs (`cmd_pr_merge` now carries the base-branch queue
   preflight and refuses the off-routing dispatch itself) — the generalization is what needs recording.
2. **Audit the other prose-routed verb sets in the CI abstraction for the same shape**: a documented
   two-branch route, plus a third sibling verb reachable outside it, plus asymmetric checking across the
   siblings. The merge set is fixed; the pattern is not known to be unique to it.
3. **Do not read the shipped fix as a root cause.** Containment plus observability at the four
   `use_merge_queue` sites means a recurrence is now refused and recorded. It does not mean the departure
   is explained. The epic still owns the open question.

## Evidence

- D1 diagnostic gate, this plan: `use_merge_queue: true` present and correctly plumbed in the step-params
  payload; dispatched verb was `ci pr merge`; `branch-cleanup` merge routing names that verb on neither
  branch.
- #1081: `ci pr merge` returned `merged: true`; the PR closed unmerged and the branch was deleted. Real
  landing was #1082, via `ci pr merge-queue`, in the same run.
- Population derived from each provider's dispatch registry: GitHub 37 / GitLab 35 handlers, 8
  merge-shaped, 7 fixed, 1 reference shape — the enumeration is registry-derived, not hand-listed.

## Dedup context for the orchestrator

Gate 1 dedup was NOT run — `orchestrated: true` routes to this inbox and the orchestrator owns
classification. This is distinct from the seven candidate-lessons the plan-retrospective already routed
(`merge-queue-enqueue-does-not-take-001..004` in each of `review-apparatus` and `truthful-signals`), which
are all tooling-measurement defects; none of them names the off-routing dispatch.
