envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-24T15:38:01Z

# Candidate lesson: CodeRabbit reviewed-at-HEAD is read from the wrong signals; the barrier fails open (plan-marshall:automatic-review)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-23-cookie-forwarding-policy-r2 (PR cuioss/API-Sheriff#515, merge bd730f5a), inbox message(s) plan-v02-23-cookie-forwarding-policy-r2-004 and -005.

Two linked findings. (1) After fix pushes, a manual "@coderabbitai review" is refused inside CodeRabbit's hourly window ("only applicable when automatic reviews are paused"). (2) CodeRabbit's replies on existing threads, stamped at the new HEAD, were counted as bot participation for that HEAD, so the pre-merge barrier reported the review current while the new commits were not reviewed.

The reliable signal is the coveredCommitId marker in CodeRabbit's summary (walkthrough) comment: the review covers HEAD only when it equals the HEAD SHA. Suggested direction: derive participation from a review whose commit_id is HEAD (for CodeRabbit, the marker), never from thread replies or issue comments; do not send the manual trigger while automatic reviews are active; add a regression case where thread replies at HEAD carry an older coveredCommitId and must yield "not reviewed at HEAD".

Related earlier item: lessons-archive sweep 2026-10-13, message 188 (re-review precedence and participation).
