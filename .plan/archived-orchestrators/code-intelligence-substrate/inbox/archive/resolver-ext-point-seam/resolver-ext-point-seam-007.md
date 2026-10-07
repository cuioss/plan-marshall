envelope_version=1
sender_type=plan
sender_id=resolver-ext-point-seam
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-30T15:19:16Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
title=An overridden pre-merge review barrier must not survive a rebase to a different HEAD

# An overridden pre-merge review barrier must not survive a rebase to a different HEAD

Found by `plan-retrospective` on PR #1067. Not remediated. **This is the single most
important finding from this plan.**

## The timeline

| Time | Event |
|---|---|
| 12:37:07 | Operator **overrides** the pre-merge review-completeness barrier. Recorded rationale: unreviewed delta is docs-only (2 ADR files, 542 insertions, no buildable source); production changeset was reviewed at `405b05f06`. Merging with **1 of 3 configured reviewers having reviewed any revision and 0 of 3 having reviewed the exact merged HEAD**. |
| 12:37:35 | Merge lock requested. |
| 13:08:51 | Merge lock acquired. Merge is now seconds away. |
| 13:10:01 | Merge **ABORTED** — for a completely unrelated reason: upstream PR #1066 landed `doc/adr/012-…` while this plan held its own `doc/adr/012`. |
| — | Forced rebase onto new `origin/main`, ADRs renumbered 012/013 → 013/014, re-verify, re-push. |
| 13:40:11 | The re-push re-triggers CodeRabbit, which had refused twice as rate-limited. It reviews `371854d14` and files **5 genuine defects**, 3 of them rated Major. |
| 13:49 | Loop-back to `5-execute`; TASK-010..014. |
| 14:30:36 | Barrier re-evaluated at the new merge HEAD `76c7200b6`. Recorded: "Merging under the operator ruling recorded earlier." |
| 15:02:32 | Merged. |

## The finding

**The 5 CodeRabbit defects were not caught by any gate. They were caught by an accident.**

The gate designed to catch them — the pre-merge review-completeness barrier — had already
been overridden at 12:37 and the merge was in flight at 13:08. Had the ADR numbers not
happened to collide, PR #1067 merges at approximately 13:09 carrying:

- a resolver-identity registry that admits a truthy non-`str` id and can abort every graph
  query on a mixed `str`/`int` sort, and that silently collapses two distinct resolvers
  sharing an id into one producer identity;
- a `merge_resolver_edges()` that drops self-edges and unknown endpoints **with no
  `notes[]` entry**, so a resolver reports `status: ok`, zero edges, and no suppression
  reason — a vacuous confident zero, inside the plan whose entire stated purpose is
  anti-vacuity;
- a `discover_derivation_resolvers()` call sitting outside the `try/except ImportError`
  that is supposed to guarantee the documented zero-resolver fallback, turning every
  graph-family verb into `status: error` on a missing `script-shared` path.

A defect in one dimension (ADR numbering) bought review coverage in an unrelated dimension.
That is luck, and it is not repeatable.

## Two distinct defects in the barrier

**1. The authorization was scoped to a HEAD and applied to a different one.** The 12:37
override reasoned explicitly about *which* delta was unreviewed: "unreviewed delta is
docs-only — doc/adr/012 and doc/adr/013 AsciiDoc files, 542 insertions, no buildable
source. Production changeset WAS reviewed at 405b05f06." That reasoning is sound **for that
HEAD**. By 14:30 the HEAD was `76c7200b6`, which contained 5 production fix commits that did
not exist when the operator ruled. The barrier re-evaluated, observed the ruling, and
merged. Nothing re-asked whether a ruling about a docs-only delta still covered a delta
that was now five production commits.

**2. The barrier's own second evaluation reported the coverage as IMPROVED and merged
anyway.** The 14:30:36 entry is admirably honest — it records that CodeRabbit performed a
real review producing 5 genuine defects, that Sourcery still refuses, and that "Required
bot pr-agent has not re-reviewed this exact HEAD — its only review was the informational
summary at 405b05f06". It then merges. The residual gap is stated and not gated on. So the
final merged HEAD `76c7200b6` was reviewed by **zero** of the three configured bots.

## Proposed action

1. **Bind a barrier override to the HEAD it was granted against.** When the HEAD changes
   after an override — by rebase, by loop-back fix commits, by anything — the override
   lapses and must be re-sought. This is the same invariant as `head_at_completion` on
   `phase_steps`, which the plan already records for other steps; the override is not
   carrying one.
2. **Distinguish "override granted for a docs-only delta" from "override granted".** The
   operator's reasoning was delta-shaped. The persisted authorization was not.
3. Note for the epic: the honest, detailed decision-log entries at 12:37, 13:10 and 14:30
   are exemplary and are the only reason this is reconstructible. The defect is not in the
   recording; it is that a correctly-recorded caveat did not gate anything.

## Generalizable rule

An authorization granted against a specific state must expire when that state changes. An
override that outlives its subject is indistinguishable from no gate at all — and reads,
in the log, exactly like a gate that passed.

## Evidence

- `logs/decision.log:83` — the 12:37:07 override, with its explicit HEAD-scoped reasoning.
- `logs/decision.log:84` — the 13:10:01 abort for the ADR collision.
- `logs/decision.log:90` — the 14:30:36 re-evaluation merging under the earlier ruling.
- `artifacts/findings/pr-comment.jsonl` — the 5 CodeRabbit defects at `371854d14`.
- `logs/work.log:454-458` — TASK-010..014 creation.
