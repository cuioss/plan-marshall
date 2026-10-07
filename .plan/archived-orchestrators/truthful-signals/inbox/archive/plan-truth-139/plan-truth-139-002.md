envelope_version=1
sender_type=plan
sender_id=plan-truth-139
epic=truthful-signals
kind=candidate-lesson
created=2026-09-13T14:20:14Z

# A fix that flips a claim's truth conditions must assert both directions

component: plan-marshall:plan-marshall
category: anti-pattern
confidence: high
suggested_epic: truthful-signals
source_plan: plan-truth-139
source_pr: 1479

## Context

Two of this run's own fixes introduced the inverse of the defect they closed, and
both were caught by the reviewer rather than by the fix task or any gate.

**Case 1 — `574fd5` (Major), the same function twice.** Triage round 1 allocated
TASK-021 to fix a false REFUSAL at `manage_build_server.py:1428`:
`_write_cap_unguarded` stats and chmods *after* the atomic replace, so a
post-replace `OSError` reported "Neither file was changed" over an already-migrated
machine config. TASK-021 added an `OSError` arm. Triage round 3 then received
CodeRabbit Major `574fd5` against that arm: `write_max_slots_if_unset` releases its
`O_EXCL` guard in the `finally` at `_machine_config.py:651` *before* the exception
reaches the handler, so a concurrent same-value write between the raise and the
re-read makes the post-state match — and the report now claims
`machine_config_modified: true` for a migration this invocation never committed.
A false refusal was traded for a possible false success.

**Case 2 — `9c441d`, a guard the operator specifically requested.** The operator's
re-grounding note identified a genuine gap: `test_default_cap_is_five` pins the cap's
VALUE, which cannot see how many modules carry it, so re-duplication would pass. An
AST-derived single-definition guard was added (commit `331b9a2ce`). CodeRabbit then
found that `_default_cap_carriers` admits on target-name-ends-`MAX_SLOTS` AND an
int-literal `Constant`, so the historical `DEFAULT_BUILD_QUEUE` dict carrier — the
shape that actually seeded `build.queue.max_slots` into every project's
`marshal.json` — fails BOTH conjuncts. The module's own docstring called that the
shape all three historical carriers had, and its sibling docstring named the dict
carrier as the third. The module contradicted itself.

## Root cause

A fix task is specified against the observation that produced it, so its
verification asserts that the previously-wrong claim is now right. Nothing requires
it to assert that the previously-right claim is still right. When the fix changes
the *truth conditions* of a report rather than its wording — an added error arm, a
new guard predicate — the untested direction is exactly where the inverse defect
lands, and it lands in the same function.

Case 2 adds a second edge: when a guard is derived from a predicate, the
predicate's conjuncts must be checked against the population the guard claims to
cover, not against the population that motivated it. Today's `DEFAULT_BUILD_QUEUE`
is `{max_retries: 10}`, so the dict-carrier blindness was *latent* — a value-pinning
test and a shape-blind AST guard both pass on the current tree while the invariant
claims to forbid re-duplication generally.

## Proposed action

In the triage FIX action, when a disposition changes what a report *claims* (not
only how it words it), require the fix task to carry a matched control pair: one
assertion that the previously-false claim is now false, and one that the
previously-true claim is still true. Where the claim is about a concurrent or
failure path, the control must be constructible — TASK-023's eventual remedy is the
model: a writer-provided post-replace marker, so the partial arm is gated on
evidence the write committed and every unmarked non-default post-state reports
`undetermined`.

Both of this run's fixes were eventually correct, and both were made correct by a
reviewer. The remedy is to make the second direction a fix-task obligation rather
than a review finding.

## Evidence

- aspect: log_analysis — decision `939568` (triage round 3): "This is the INVERSE of
  the false refusal our own TASK-021 fixed, in the same function"
- aspect: log_analysis — decision `939568` on `9c441d`: "its own docstring calls
  that the shape all three historical carriers had and the sibling docstring names
  the dict carrier as the third. Module contradicts itself."
- aspect: log_analysis — decision `3acbe2`: "GENUINE GAP FOUND AND CLOSED: F5 item 4
  did not exist - test_default_cap_is_five pins the VALUE, which cannot see how many
  modules carry it, so re-duplication would have passed"
- review-retrospective.md § Comparative Verdict — "A false-success claim introduced
  by one of this plan's own fix tasks, and then the *inverse* false claim its remedy
  created — the same recurrence archetype the plan was written to remove, caught in
  both directions"
