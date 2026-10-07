envelope_version=1
sender_type=plan
sender_id=barrier-override-not-head-bound
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T11:41:22Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
title=A fix for "credential not bound to X" must bind on every discriminating dimension, not just the one in the title

# A fix for "credential not bound to X" must bind on every discriminating dimension, not just the one in the title

## What happened

Plan `barrier-override-not-head-bound` exists to remove one fail-open shape: a merge-gate
override recorded as free text and bound to nothing, so it could be recalled at a later HEAD
to merge a tree the operator never saw.

Its own pre-submission self-review (round 1, commit `9e1caf`) found that the **new
authorization check reintroduced the exact fail-open shape the plan exists to remove.** The
new `merge-authorization check` was correctly HEAD-bound — and **kind-agnostic**. So a
`pre-merge-consent` granted seconds earlier at the *same* HEAD, over a *different* gap,
satisfied the review barrier. The credential was bound on the dimension named in the plan
title (HEAD) and left unbound on the dimension the plan never named (which gap the
authorization was granted over).

Three further self-review rounds found three more defects in the same guard (see the sibling
candidate-lessons). Four blocking defects, all in a guard whose entire purpose is to fail
closed, all caught by the plan's own pre-submission review rather than by review bots.

## Why it recurs

The defect title names ONE dimension ("not bound to the HEAD"). That title becomes the
implementation's mental model, and the fix binds that one dimension. But an authorization is
a credential, and a credential is safe only when it is bound on **every dimension that
discriminates one authorization from another**: *who* granted it, *when* (HEAD), and **what
it was granted over**. Binding a strict subset produces a credential that is narrower than
before and still forgeable.

This is the same family as the recurring "vacuous guard" archetype — a predicate that fires
but does not discriminate — and the same family as "a reviewer's list of call sites is a
SAMPLE, not an enumeration". The plan's own spec even said it, in D1's root-cause note 3:
*"The override is a SAMPLE, not the population."* It said that about the roster and then
under-applied it to the check's own matching key.

## Rule

When the defect is "credential C is not bound to dimension D":

1. **Enumerate every dimension on which two instances of C can differ** BEFORE implementing.
   For a merge authorization that is at minimum `{granting HEAD, kind/gap it was granted
   over}`; it is not just the one in the ticket title.
2. **State explicitly, in the artifact, which dimensions the check keys on and which it
   deliberately does not** — a silently-omitted dimension reads identical to a
   deliberately-excluded one.
3. **Write the negative test on the dimension you did NOT name in the title**: "a valid
   authorization of a DIFFERENT kind, at the SAME HEAD, does not satisfy this gate". A test
   suite that only varies HEAD passes on a kind-agnostic check.
4. Treat "my fix reproduced my own target defect" as a first-class hypothesis during
   self-review of any fail-closed guard, not as an unlikely irony.

## Scope note for the orchestrator

The concrete instance is plan-marshall-specific (`merge-authorization check` in
`phase-6-finalize/standards/branch-cleanup.md`), but the rule is domain-invariant and is a
candidate for the global corpus rather than the epic-local one. Classification deferred to
the orchestrator per the write-boundary contract.
