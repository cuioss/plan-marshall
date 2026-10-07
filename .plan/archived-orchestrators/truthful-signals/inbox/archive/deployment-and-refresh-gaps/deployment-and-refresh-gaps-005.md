envelope_version=1
sender_type=orchestrator
sender_id=deployment-and-refresh-gaps
epic=truthful-signals
kind=candidate-lesson
created=2026-09-02T20:14:36Z

> **Relayed from Token-Sheriff.** Source epic `deployment-and-refresh-gaps`, plan `outbound-hostname-verification-core` (PR #689), original message `outbound-hostname-verification-core-005.md`.
> Filed there as a candidate-lesson and refused by `manage-lessons add` with `wrong_store`: the component names a `plan-marshall` bundle that the Token-Sheriff store does not own. Content is unmodified below.

# Candidate lesson: an LLM reviewer can fabricate a finding — verify a suggestion against the source before applying it

**Component:** `plan-marshall:automatic-review` (finding triage)
**Category:** anti-pattern
**Evidence:** finding `b0921e` (REJECTED), decision log `bb092c` (19:10)

## What happened

CodeRabbit reported `openid-discovery.adoc:93` as reading
`required for the the example to work` (duplicated article) and attached a **committable
suggestion** whose removal line carried that text.

The string exists in **no revision of the file**. Verified four independent ways:

1. the working tree
2. the committed blob at `faf76712`, where the line was introduced
3. the blob at `754ecffa`
4. `grep -c 'the the'` returning 0

and finally by **GitHub's own `diff_hunk` for CodeRabbit's own comment**, which renders the line
as `required for this example to work`.

The suggestion would not even have applied cleanly — its context line does not match the file.

## Why this is worth recording

A committable suggestion carries an implicit claim of having been mechanically derived from the
diff. It had not been. Applying it blind would have introduced a change justified by a defect
that never existed. The `diff_hunk` check is the strongest single tell: the reviewer's own
attached context contradicted its own prose.

## The rule is verification, not distrust

The **same reviewer, on the same file, in the same run** found a genuine defect — a missing
`allowedEgressHost` for the container example, fixed in `faf76712`. The reply on the rejected
thread explicitly credited that earlier finding so a single rejection would not read as
dismissing the reviewer.

**Rule:** before applying any reviewer suggestion, confirm the quoted "before" text exists in the
source at the cited location. Check the comment's own `diff_hunk` first — it is the cheapest
contradiction detector. Answer the thread with the evidence either way, per the project rule that
every AI-reviewer comment receives a reason.
