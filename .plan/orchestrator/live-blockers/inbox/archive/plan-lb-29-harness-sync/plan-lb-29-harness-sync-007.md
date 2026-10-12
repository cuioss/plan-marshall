envelope_version=1
sender_type=plan
sender_id=plan-lb-29-harness-sync
epic=live-blockers
kind=candidate-lesson
created=2026-10-09T14:12:33Z

component=plan-marshall:workflow-integration-github
category=bug
created=2026-10-09

# Exclude the coderabbitai full review command as an own trigger

## Context

While PR #1724 of plan `plan-lb-29-harness-sync` waited on CodeRabbit's quota, two comments reading only `@coderabbitai full review` were posted from the owner account, as the bot's own refusal text recommends. On the next fetch, `fetch_findings` filed both comments as `pr-comment` findings (c25cf4, 6d6a00), plus the bot's "Full review finished" acknowledgement (afad18). A later firing filed the bot's "Already reviewed the last commit" acknowledgement (5dc1a8) as well. All four carry no review content and all four had to be closed by triage or by the main session. The earlier comment reading exactly `@coderabbitai review` was excluded correctly.

## Root cause

The own-trigger exclusion compares a comment body against the registered trigger text by exact match. `@coderabbitai full review` is a different string, so it is treated as review feedback. The bot's replies to a trigger are not recognised as trigger acknowledgements either.

## Proposed action

- Register every command form of each bot as an own trigger (for CodeRabbit at least `review` and `full review`), matched on the normalised whole body.
- Classify a bot's direct reply to a trigger ("Action performed", "Action not completed", "Already reviewed") as noise unless it carries a refusal the recovery path needs.
- Add tests with the two request bodies and the two acknowledgement bodies quoted above, each asserting zero stored findings.

## Evidence

- aspect: chat_history_analysis — fetch report: "`@coderabbitai full review` is not an exact match for the registered trigger `@coderabbitai review`, so the own-trigger exclusion did not catch the two request comments (it did exclude the 07:26Z one)"; fetch counts 20 fetched, 5 stored, of which 3 noise.
- decision log — 0684b6: c25cf4, 6d6a00 and afad18 resolved `taken_into_account` with no reply; 0a689a: 5dc1a8 resolved by the main session without a triage dispatch, as the same class.
- aspect: log_analysis — `github_re_review` is the third slowest script call of the plan (624,230 ms).
