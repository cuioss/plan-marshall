envelope_version=1
sender_type=plan
sender_id=merge-queue-enqueue-does-not-take
epic=review-apparatus
kind=candidate-lesson
created=2026-08-03T21:04:32Z

component=plan-marshall:marshall-orchestrator
category=anti-pattern
title=A plan spec titled after its hypothesised cause mis-frames every artifact the plan produces
confidence=high
source_plan=merge-queue-enqueue-does-not-take
source_pr=1087

# A plan spec titled after its hypothesised cause mis-frames every artifact the plan produces

## Context

`PLAN-PR-009-merge-queue-enqueue-does-not-take.md` was named after a **hypothesised cause**: that an
enqueue was issued and failed to take. The spec carried two candidate explanations, both built on that
premise — (i) a fallback from the queue to a direct merge, and (ii) the enqueue itself not taking.

The plan's D1 diagnostic gate refuted **both**, and refuted the title's premise along with them: no
enqueue was ever issued, and the queue was never the failing component. The actual cause was an
off-routing dispatch to `ci pr merge`, a verb outside the documented routing entirely. The queue worked —
the same run recovered through `ci pr merge-queue` and #1082 landed normally.

## Root cause

The plan id is not a label; it is load-bearing. It becomes the branch name, the plan directory, the PR
title stem, the inbox `sender_id`, and the phrase every later reader uses to recall the work. When it
encodes a hypothesis rather than an observation, a refuted hypothesis cannot be corrected without
renaming a launched plan — which is prohibited, and rightly so, because the id is referenced from the
epic ledger, the inbox envelopes, and the landed PR.

The result is a permanent inversion: the artifact set for this work is filed under a symptom that was
demonstrated not to exist. Anyone searching the epic for "merge queue enqueue" reaches a plan whose
finding is "the merge queue was never reached", and anyone reasoning from the title alone will re-derive
the refuted hypothesis.

## Proposed action

1. **Name plan specs after the OBSERVATION, not the hypothesised cause.** The observable fact here was
   "`ci pr merge` reported merged on a PR that closed unmerged" (#1081) — that phrasing survives any
   diagnostic outcome, because it states what was seen rather than what was guessed. A hypothesis belongs
   in the spec body, where it can be refuted in place.
2. **State hypotheses in a spec as inputs to a diagnostic gate, never as its conclusions.** This spec did
   this well in one respect — it carried its hypotheses explicitly and enumerated, which is exactly what
   let the D1 gate refute them cleanly and settle a third cause. Preserve that practice; move only the
   naming.
3. **Retire the "the enqueue does not take" framing at the epic level.** It is refuted, and it will
   otherwise propagate into sibling plan specs that cite this one.

## Evidence

- Request spec hypotheses (i) fallback and (ii) enqueue-does-not-take: both REFUTED by the D1 gate.
- `use_merge_queue: true` was correctly plumbed and present in the step-params payload — the configuration
  the title implicates was never at fault.
- Recovery in the same run via `ci pr merge-queue`; #1082 landed through the queue.

## Dedup context for the orchestrator

Gate 1 dedup was NOT run — `orchestrated: true` routes to this inbox and the orchestrator owns
classification. Not covered by the seven candidate-lessons already routed by the plan-retrospective
(`merge-queue-enqueue-does-not-take-001..004` in each of `review-apparatus` and `truthful-signals`). The
sibling residue message on off-routing dispatch (`-006`) names the technical defect; this one names the
spec-authoring practice that made it hard to see.
