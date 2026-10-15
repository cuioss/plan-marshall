envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T06:32:43Z

> Routed by orchestrator epic pm-mcp-core-m2-m4 from plan plan-09-audit-trail (PLAN-09, pm-mcp-core #69, merged 3236ed5), drained 2026-10-15.
> Source inbox message(s): plan-09-audit-trail-001.md
> RECURRENCE of -204, -218, -231, -235, -245, -254, -268. New evidence: the live wording is "this account has used its review budget of" ("its", not "your own"), and a comment the re-review path already recorded as declined was still ingested as a finding. Earlier numbers are lessons-routing messages pm-mcp-core-m2-m4-NNN.

# Sourcery "used its review budget" quota notice not recognised as a refusal

- Source: review-bot records 6122fe and 318838 (plan-09-audit-trail, PR #69), both `bot_kind: sourcery`, `kind: issue_comment`, resolution `taken_into_account`.
- Suggested component: `plan-marshall:automatic-review` (standards/sourcery.md `refusal_patterns`), possibly `plan-marshall:workflow-integration-github` (fetch_findings).

## Observation

Sourcery posted, twice (head edbed7a and head 8cf3c94):

> Sorry @cuioss-oliver, this account has used its review budget of 2,500,000 diff characters for the last 7 days. You can request another review in 2 days and 6 hours by commenting `@sourcery-ai review`.

`fetch_findings` did not classify it as a refusal and filed it as a pending `pr-comment` finding each time, which then had to be dispositioned by hand. The registry's nearest pattern is `"used your own review budget of"` (#1391 wording); the live wording is `"this account has used its review budget of"` — "its", not "your own", so the substring never matches. The structural recogniser (`_is_rate_limit_notice`) keys on exceeded/reached/hit and misses it too.

The second firing also logged a WARNING that the re-review comment did not reference the head SHA and was "recorded as declined", yet the comment was still ingested as a finding.

## Candidate rule

Add a handle- and pronoun-free pattern such as `"used its review budget of"` (or `"review budget of"`) to Sourcery's `refusal_patterns`, and add the live wording as a regression fixture so a pronoun change in the notice does not reopen the gap. Consider whether a comment already classified "declined" by the re-review path should ever reach the findings store.
