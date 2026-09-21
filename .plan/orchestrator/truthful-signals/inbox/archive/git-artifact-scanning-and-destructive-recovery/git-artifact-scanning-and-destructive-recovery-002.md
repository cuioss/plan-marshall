envelope_version=1
sender_type=plan
sender_id=git-artifact-scanning-and-destructive-recovery
epic=truthful-signals
kind=candidate-lesson
created=2026-08-31T08:03:14Z

component=plan-marshall:plan-marshall
category=bug
created=2026-08-31
bundle=plan-marshall
confidence=high
source_plan=git-artifact-scanning-and-destructive-recovery
related_finding=ecbbef

# A skipped enrichment step must fail closed, not let a matcher run against an empty field

## Context

After the round-2 `github_pr fetch_findings` on PR 1371, `manage-findings ingest` was never invoked. Every round-2 finding (`cc04b7`, `669221`, `541cac`, `5cc518`) therefore carried a populated `raw_input.body` and **no top-level `body`**. Nothing errored anywhere.

Two consequences followed from that one skipped step, in opposite directions and both silent:

1. **A wrong measurement.** The `review_body_summary_patterns` meta test matched an EMPTY STRING, so `cc04b7` ("Actionable comments posted: 1") was bucketed ACTIONABLE while its structurally identical round-1 twin `53b0c4` ("...posted: 7") was correctly bucketed meta. That inflated CodeRabbit's actionable count from 8 to 9 and depressed its resolved-as-fixed rate from a true 62.5% (5/8) to a published 55.6% (5/9).
2. **An unperformed action.** The same skipped tail left all four round-2 findings with no `responded` marker, so the rationale for the Major fix `5cc518` never reached the PR. A reader of PR 1371 sees CodeRabbit's Major finding and CodeRabbit's own auto-generated "Addressed in commit b9506f8" marker, but no explanation from this run of what changed or why — the one thread where the run's reasoning mattered most is the one it never posted to.

Neither was caught by a gate. The operator caught the measurement half by challenging a published figure, and the unposted half only surfaced when the operator asked a second question ("SO all not-refuted pr-comments are fixed, and the refuted one are commented accordingly?"). A corroborating signal existed and did not escalate: the retrospective's own delta pass independently flagged exactly those two records as "unpartitioned", reaching the same rows by a different route.

## Root cause

A classifier keyed on a text field returned a confident bucket over an empty field instead of refusing. And a RESPOND stage completed without comparing the count it transmitted against the count it was handed. Both are the vacuous-guard archetype: a check that cannot fail because its input is absent reports the same green as a check that passed.

## Proposed action

Two changes, both in the FIND → ingest → triage → RESPOND chain owned by `verification-feedback.md` and the automatic-review producer contract:

1. **Refuse, do not default.** Any classifier keyed on a record's text field must treat an empty/absent field as `indeterminate` and report it, never as a match or a non-match. A bucket assigned over an empty body is not a classification.
2. **Publish the transmission ratio.** `post_responses` must report `transmitted` against `handed`, so a zero-transmission pass over a non-empty finding set is visible in the payload rather than inferable only from the absence of a marker.

Note before re-implementing: this merge landed a sibling plan's work across `automatic-review/` (`bot_registry.py`, `review_completeness.py`, `coderabbit.md` +48) in the same merge commit — check `main` first.

## Evidence

- aspect: logging_gap_analysis — `FIND_INGEST_RESPOND_CHAIN` gap, error severity
- aspect: chat_history_analysis — turn 15 (operator caught the metric), turn 16 (operator caught the silence)
- Finding `ecbbef`, qgate `6-finalize`, severity error, resolved `taken_into_account`
- Corrected figures now on record: CodeRabbit 8 actionable / 5 meta / 62.5% fixed
