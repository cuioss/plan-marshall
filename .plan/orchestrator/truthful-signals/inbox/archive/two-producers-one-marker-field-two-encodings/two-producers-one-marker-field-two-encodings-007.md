envelope_version=1
sender_type=plan
sender_id=two-producers-one-marker-field-two-encodings
epic=truthful-signals
kind=finding
created=2026-08-09T04:59:03Z

component=plan-marshall:plan-retrospective
severity=warning
source_plan=two-producers-one-marker-field-two-encodings
source_pr=1125
relates_to=lesson-2026-08-08-20-001
kind_note=finding, not candidate-lesson — this reports a filed lesson reproducing unchanged, not a new rule

# Lesson 2026-08-08-20-001 reproduced three of its four instances verbatim, one plan later

## What happened

Lesson `2026-08-08-20-001` ("Four retrospective cross-checks hard-code a population
that drifted from its authoritative source") was filed from the retrospective of
`absent-names-two-states-with-opposite-remedies` on 2026-08-08. This retrospective,
run against the very next plan, reproduced **three of its four instances** — not as
similar defects, but as the same code paths emitting the same wrong output.

| Lesson instance | Reproduced here | Evidence |
|---|---|---|
| Instance 1 — `check-routing-decisions` `posture_cutoff` regex does not match the emitter's line shape, so `mis_prune` falls through to predicate re-evaluation and emits a false positive | YES | `mis_prune:sonar-roundtrip` = `fail`, `removal_cause: predicate_evaluated`, against a decision log that records the drop as `lane_resolution — dropped sonar-roundtrip ... (execution_profile=standard): effective tier full exceeds the standard posture cutoff` |
| Instance 3 — `check-manifest-consistency` rule M3 gates on `['module-tests']` while the canonical form is `['verify:module-tests']`, so the rule is dead and reports `skip` | YES | `tests_only_diff` = `skip`, message `rule M3 not applicable — verification_steps != ["module-tests"]`, against a manifest carrying `verification_steps: ['verify:module-tests']` and a decision log line reading `Rule tests_only fired`. Re-confirmed at `check-manifest-consistency.py:324` and against `manage-config list-verify-steps`, which returns only prefixed ids |
| Instance 4 — `extract-chat-signal` reduction keyed on a denylist of synthetic shapes, so `no_signal: false` is carried by synthetic content | YES | `raw_turn_count: 1128`, `reduced_turn_count: 3` (was 5 of 1090); one of the three retained turns is a `<task-notification>` envelope |
| Instance 2 — `_PRUNABLE_PREDICATES` under-enumerated | not re-tested | this plan did not exercise a mis-prune of `plan-retrospective` itself |

## Why this is worth a finding rather than a new lesson

Nothing new was learned. The lesson is accurate, its root-cause analysis is correct,
and its Proposed action names the right remedy for each instance. What the second
observation adds is only this: **the remedy has not been applied, and the defects are
still producing wrong output in the tooling that audits every plan.** Instance 1 is
emitting a false `fail` and Instance 3 is emitting a `skip` indistinguishable from a
legitimate non-applicable skip — both in the retrospective's own cross-checks, so
every plan audited between the filing and the fix carries the same two wrong verdicts.

The lesson's own closing line observed that the plan it audited "had this exact
archetype as its subject and hit it four more times during its own execution". This
retrospective extends that: the archetype now recurs across the plan boundary, in the
same component, with the lesson already on file.

## Requested disposition

Do not refile. Either schedule the three named remedies (they are concrete and
localised — one shared constants module, one import of the canonical verify-step keys
plus a one-line doc fix at `manifest-crosscheck.md:37`, and one positive-predicate
reduction), or record explicitly that they are deferred so the next retrospective
does not report them a third time as if they were news.

## Evidence

- lesson `2026-08-08-20-001`, Instances 1, 3 and 4, with their Proposed action bullets
- aspect: routing_decisions (this plan) — `mis_prune:sonar-roundtrip` `fail`
- aspect: manifest_decisions (this plan) — `tests_only_diff` `skip`
- aspect: chat_history_analysis (this plan) — 3 of 1128 turns retained
- first-party: `manage-config list-verify-steps` returns `default:verify:quality-gate`,
  `default:verify:module-tests`, `default:verify:coverage` — no bare form exists, so
  M3's guard can never be false
- source: `check-manifest-consistency.py:324`
