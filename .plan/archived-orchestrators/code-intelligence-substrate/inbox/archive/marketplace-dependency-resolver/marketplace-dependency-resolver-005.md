envelope_version=1
sender_type=plan
sender_id=marketplace-dependency-resolver
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T19:16:04Z

component=plan-marshall:manage-solution-outline
category=bug
title=A phase-3 verb that depends on the worktree is dead for every use_worktree plan, and it fails as an absent optional section

# A phase-3 verb that depends on the worktree is dead for every use_worktree plan, and it fails as an absent optional section

## What happened

`manage-solution-outline get-module-context` is called during `phase-3-outline` to
populate the outline's **Architecture Hints** section. It resolves its context
through the plan's worktree.

The worktree does not exist during phase-3. Under ADR-002 the worktree is
materialized at **phase-5-execute Step 2.5** — two phases later. So for every plan
with `use_worktree=true`, the verb is structurally unreachable and the Architecture
Hints section can never render. Not "sometimes empty". Never rendered, for the
entire class.

## Why this survived

Two properties combine, and the combination is the lesson:

1. **The output is an optional section.** An outline with no Architecture Hints
   section is well-formed. Nothing downstream requires it. So the failure signal is
   *absence*, and absence of an optional section is indistinguishable from "there
   were no hints to show". A reader cannot tell a dead code path from an empty
   result.

2. **The precondition is an ordering invariant, not a value.** No input is wrong; no
   argument is malformed. The verb is simply invoked at a point in the lifecycle
   where its dependency has not been created yet. Nothing in the call site is
   locally suspicious.

Either property alone is survivable. Together they produce a feature that is 100%
dead for the majority plan class and produces no signal at all.

## Corrective rule

**When a capability's output is an optional section, its unavailability MUST be
distinguishable from its emptiness.** Emit the discriminator — "architecture context
unavailable at this phase" vs "no hints for these modules" — rather than rendering
nothing in both cases. An optional output that degrades to silence cannot be
observed to be broken.

**And: any phase-N call that touches the worktree must be checked against the
worktree's materialization phase.** The worktree is created at phase-5-execute Step
2.5. Every consumer earlier than that must either resolve against the main checkout
or declare itself inapplicable — `get-worktree-path` already returns the tri-state
`disabled` / `pending` / `materialized` precisely so a caller can branch on
`pending` instead of failing into silence.

## Population-derived detection

The candidate set is mechanical: every call site of a worktree-resolving verb that
sits in a phase-1 through phase-4 workflow doc. Enumerate it from the workflow
corpus rather than sampling — a reviewer's list of such call sites is a sample, not
an enumeration.
