envelope_version=1
sender_type=plan
sender_id=review-packs-become-published-artifacts
epic=review-apparatus
kind=candidate-lesson
created=2026-09-03T22:43:10Z

# A control that passes under both readings of a contract adjudicates neither

component: plan-marshall:persona-module-tester
category: anti-pattern
confidence: high

## Context

Two independent instances on this PR, found by two different reviewers.

**(1) Q-Gate 30d9f0** — a three-site cohort each stating that a `--timeout` request below the daemon default "changes nothing". The resolver is `max(requested + 30s margin, default)`, so 1790 against an 1800s default resolves to 1820: below the default, yet raising the bound. The false claim survived three rounds of review because the only test cited as pinning the resolver, `test_a_request_below_the_default_does_not_lower_the_outer_bound`, uses `BELOW_DEFAULT_TIMEOUT=120` — far outside the 30-second margin window. That value passes under BOTH the true and the false reading, so the test contradicted none of the three claims while appearing to pin them.

**(2) pr-comment 1411f0 (CodeRabbit, Minor)** — five of seven negative controls in `test_charter_invariants.py` assert stdlib behaviour (`str.replace`, membership, `{}` falsiness) rather than the invariant they are named for; the injection control never inspects `DOMAIN_ARTIFACTS` at all while the guard it covers iterates it. In the reviewer's words: "A changed predicate can therefore leave both the positive guards and these controls green."

## Root cause

Both are one failure: a check whose input or subject cannot distinguish the correct implementation from the defective one. In (1) the fixture VALUE sits outside the disputed region; in (2) the control's SUBJECT is not the predicate under guard. Neither is visible from the test name, and both read as coverage.

The distinguishing property is checkable in both cases: a control is only a control if the mutated input FAILS it. Instance (2)'s remedy is exactly that — one helper per check, the positive asserting the real input passes, the negative asserting the mutated input fails, and the positive guard calling the same helper so control and guard cannot diverge. Instance (1)'s remedy is the same property applied to a boundary: choose the fixture value inside the disputed window.

## Proposed action

Require the matched positive/negative control shape for any test cited as pinning a contract, and require that a test invoked as EVIDENCE for a documentation claim be exercised at the claim's BOUNDARY rather than at a value comfortably inside the uncontested region.

Add a review-time obligation: when a disposition cites a test as pinning a claim, verify that the cited test would fail under the claim's negation before accepting it as evidence. This run cited `test_a_request_below_the_default_...` both in a Q-Gate resolution and in a CodeRabbit reply before discovering it pinned nothing at the margin.

## Evidence

- Q-Gate 30d9f0 — three doc sites, three review rounds; resolved by deleting the false clause at all three and adding `test_a_request_inside_the_margin_window_still_raises_the_bound` to pin the distinguishing case
- pr-comment 1411f0 — five of seven controls vacuous, routed to TASK-9
- `persona-module-tester` already documents the matched positive/negative control shape and the fixture-level neutralization contract; both instances shipped anyway, so the standard exists and is not being applied at review time
