envelope_version=1
sender_type=plan
sender_id=review-packs-become-published-artifacts
epic=review-apparatus
kind=candidate-lesson
created=2026-09-03T22:42:52Z

# A diff-scoped self-review cannot see a claim that is false only against absent behaviour

component: pm-plugin-development:ext-self-review-plan-marshall
category: improvement
confidence: high

## Context

Pre-submission-self-review fired three recorded times after two failures and converged 3 -> 4 -> 3 -> 1 -> 0 findings across five rounds. It filed 13 Q-Gate findings in 6-finalize, 11 of them doc/contract-claim defects, and 9 of those were resolved by DELETING the over-claim rather than implementing it. The surfacer is demonstrably strong on this class.

Two Major CodeRabbit findings on the same PR were the same class, and the self-review had passed over both across all five rounds:

- 26e602 — the generated pr-agent domain header states the spine artifact is applied alongside the domain artifact and is not optional. Nothing enforces it: `generate()` writes separate files and the consuming half does not exist yet.
- 166827 / a525f1 — `target.py` forwarded `--bundles` into `discover_domains` while the module docstring claimed a whole-derived-set contract.

The run's own reply on 26e602 named the reason: "the claim is internally consistent with the rest of the diff and fails only against behaviour the diff does not contain, which is exactly the boundary our surfacer publishes as its structural limit."

## Root cause

The surfacer's candidate classes are diff-scoped PAIRS — contract sources, doc-claim vs body, symmetric-pair functions, near-identical hunks, description-vs-body frontmatter. Every one compares two things that are both present in the change. A claim whose falsifier is the ABSENCE of a mechanism has no second site to compare against, so no candidate class can reach it. The class is not merely missed; it is structurally out of reach.

The 9 delete-resolved findings confirm the shape from the other side: the surfacer is excellent at "two present sites disagree" and blind to "one present site describes something that does not exist".

## Proposed action

Add a candidate class keyed on ENFORCEMENT VERBS in claims — "is enforced", "cannot be omitted", "is not optional", "is rejected", "rather than" — that requires the reviewer to name the mechanism in the changed source making the claim true, and files a finding when no mechanism can be named. This inverts the comparison: instead of hunting a second site, it demands a mechanism.

CodeRabbit reached both instances through a path-instruction rule of exactly that shape ("a claimed non-optional behavior requires an implementation mechanism, not generated prose"), which is evidence the class is detectable this way.

## Evidence

- 6-finalize Q-Gate: 13 findings, 11 doc/contract-claim, 9 resolved by deletion (5ecb9d, 4cf25e, a145de, fc5157, 7d49d0, c4e309, 30d9f0 across 3 sites, 5835d8)
- pr-comment 26e602 (Major, routed to TASK-11) and 166827 / a525f1 (Major, routed to TASK-7) — both this class, both missed by five self-review rounds
- 26e602's disposition text names the structural limit verbatim
- The detecting rule on the CodeRabbit side is a path instruction demanding a mechanism, not a second site
