envelope_version=1
sender_type=plan
sender_id=absent-names-two-states-with-opposite-remedies
epic=review-apparatus
kind=candidate-lesson
created=2026-08-08T20:43:45Z

# Candidate lesson: five hard-coded set-guarding populations in one PR, three of them inside the guards protecting the new taxonomy

**Source records:** Q-Gate `92dd7c` (self-review pass 3, fixed), Q-Gate `7bf2b7` (6-finalize, fixed), `pr-comment` `d66c05` (CodeRabbit Major, fixed as TASK-14), `pr-comment` `308d72` (CodeRabbit Major, fixed as TASK-15), `pr-comment` `7b5c4c` (CodeRabbit Minor, fixed as TASK-16). Plus one fixed pre-review in `a10c7253`.

## The observation

The project already carries a standing rule that every set-guarding detector derives its population from its authoritative source. This PR — whose entire subject is widening a set from five members to seven — introduced or left standing **five** violations of that rule, and one earlier one was fixed during the run itself.

| Record | Site | Population that was a literal |
|---|---|---|
| `a10c7253` (pre-review) | self-review detector | fixed during the run |
| `92dd7c` | blocking-count guard `_CONSUMER_DOCS` | hard-coded 2-tuple; replaced by a marketplace tree walk |
| `d66c05` | `test_bot_participation_contract.py:111` `_NON_PARTICIPATION_MEMBERS` | 7-element literal mirroring `rc.STATE_*` |
| `308d72` | `test_review_completeness.py:500` parametrize | `rc.bot_registry.bot_kinds()` with no non-vacuity guard |
| `7b5c4c` | `test_ci_base.py:1178` | 4-element partial mirror of `checks_sub.choices`, omitting `rerun` and `logs` |
| `7bf2b7` | `test_not_triggered_detection.py:212` | 3-name literal over the detection path, missing the two new PR-boundary helpers |

## Why each is worse than "a list that could drift"

- **`d66c05` — the literal is the shared pivot of both guards.** `test_every_documented_member_is_one_the_classifier_can_produce` compares the documented set against the tuple, and `test_the_contracts_closure_count_agrees_with_the_derived_member_count` compares the prose count against `len()` of the *same* tuple. A member added to the classifier and omitted from the tuple moves **both sides of the comparison together**. Every check stays green over a set missing it. The taxonomy parametrize never exercises it either. So the new member reaches no check at all.
- **`308d72` — an empty parametrize is a SKIP, not a failure.** `rc.bot_registry.bot_kinds()` is evaluated at collection time; an empty return generates zero cases and pytest reports skipped. The property silently retired would have been the refusal-outranks-stale precedence — the exact precedence edge this PR introduced.
- **`7b5c4c` — the assertion runs in the subset direction.** A verb added later is not merely uncovered, it is invisible. The test named `is_a_sibling_of_the_other_checks_verbs` neither enumerates the siblings nor detects a new one, and its docstring claims it does both.
- **`7bf2b7` — the newly widened detection path is unguarded exactly where a future edit would reach for the forbidden signal.** The two new PR-boundary helpers were not in the `mergeable_state` prohibition's population.

## The generalisable shape

Each of these files **declares the derive-your-population rule in its own docstring** and then violates it in one place. The rule is understood; it is applied unevenly within a single file. `308d72` is the clearest case — line 499 parametrizes an underived population while lines 600-601 of the same file guard the same population with an assertion.

Two second-order notes worth carrying:

- **A count check is not a membership check.** Three of the six sites compare counts. A count comparison whose two sides share a pivot proves nothing.
- **The fix must not reproduce the defect one member later.** `7b5c4c`'s remediation explicitly ruled out adding `rerun` and `logs` to the literal, for this reason. And `d66c05` took the *fallback* rather than the primary suggestion — the ordering and length of the literal were deliberate, so the literal stayed and gained an equality assertion against the derived set plus a non-vacuity guard, which preserves the ordering semantics while making a classifier-only member fail at import.

## Why it is routed here

Three of the six sites are the guards over the participation taxonomy itself, so the epic's own regression net was the thing most affected. Whether the transferable rule belongs wider than `review-apparatus` is the orchestrator's call.
