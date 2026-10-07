envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-29T13:44:01Z

# review-retrospective miscounts bot status replies as false positives; create-pr record names the replaced PR

**Observed (plan-12-tool-triage, finalize review-retrospective, 2026-09-29):**

1. `fetch_findings` stores CodeRabbit's trigger acknowledgments ("Action performed — Review finished", findings `7447e1`, `63896b`) as `pr-comment` findings. They carry no code observation, so triage can only resolve them `rejected` — and the review-retrospective script then counts every `rejected` bot finding as a false positive. CodeRabbit is charged 2 false positives for two status replies it posted in answer to our own triggers.
2. A triage row recorded `resolution: taken_into_account` with a detail beginning "False positive: …" (`63a935`, cuioss-review-bot). Nothing cross-checks the resolution against its own detail, so the bot's false-positive count read 0 instead of 1 until corrected by hand post-merge.
3. The `create-pr` step record still names PR `#1653`, but the PR that merged is `#1654` (the close-and-reopen CodeRabbit recovery replaced it). Downstream readers of the step record see the retired PR id.

**The defects:** (1) status/acknowledgment comments are filed as reviewable findings instead of being classified as noise alongside `own_trigger`/`refusal`; (2) the false-positive metric keys on the resolution enum alone; (3) close-and-reopen does not re-stamp the `create-pr` record's PR id.

**Suggested fixes:** classify bot acknowledgment replies to our own trigger as noise in `fetch_findings`; have the retrospective exclude findings whose body makes no code claim, or require a `rejected` resolution for a detail that asserts a false positive; re-stamp the PR id when a PR is replaced.
