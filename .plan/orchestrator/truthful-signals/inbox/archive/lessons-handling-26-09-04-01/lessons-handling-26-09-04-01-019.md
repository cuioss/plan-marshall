envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-08T05:58:27Z

component=plan-marshall:workflow-integration-github
category=bug

Relayed from Token-Sheriff PLAN-07 (PR #715 / `8f3b8aee`), finding `fcafa2`. ⚠ Predicted as self-amplifying, then **reproduced exactly at the final barrier pass** — the prediction and its confirmation are both in the body.

# Candidate lesson: a self-response filter keyed on body shape rather than author is self-amplifying

Source finding: `fcafa2` (improvement, severity info) in plan `test-signal-and-assertion-integrity`.
Component: `plan-marshall:workflow-integration-github` (`github_pr fetch_findings`).

## Cross-repo routing note

plan-marshall-bundle component — carry to that repo's lessons store rather than filing
locally with `--allow-foreign-store`.

## Observation

At the pre-merge review-completeness barrier on PR #715, `fetch_findings` returned
`count_skipped_self_response: 1` while storing THREE further comments authored by the same
operator account (`cuioss-oliver`) as pending `pr-comment` findings — hash_ids `90819a`,
`7289f1`, `c145ab`: this run's own triage-disposition replies and its `@coderabbitai`
review triggers. One of the four WAS caught, so the mechanism works and the predicate is
too narrow.

The behaviour was predicted from the first observation and then reproduced exactly at the
final barrier pass.

## Proposed rule

A pending `pr-comment` is an actionable type and gates the pre-merge barrier, so an
unfiltered self-authored comment blocks a merge on feedback no reviewer gave. Worse, the
loop is self-amplifying: each reply written to ANSWER a reviewer becomes a new blocker at
the next barrier re-fetch, so a plan that answers its reviewers thoroughly accrues more
blockers than one that ignores them — the incentive runs backwards.

Filter self-authored content by AUTHOR IDENTITY, never by body shape or marker. A
shape-keyed filter silently stops discriminating the moment the pipeline writes a comment
in a shape its author did not anticipate, and the failure presents as a merge blocker
rather than as a filter defect.

## Suggested fix

Widen the predicate to skip every comment whose author is the PR-authoring account,
independent of body shape or marker.

## Negative control any fix must pass

Post two operator comments of different shapes (a plain reply and one containing an
`@`-mention trigger) and require `fetch_findings` to report
`count_skipped_self_response: 2` with `count_stored` unchanged.
