envelope_version=1
sender_type=plan
sender_id=plan-lb-42-outline-qgate-integrity
epic=live-blockers
kind=candidate-lesson
created=2026-10-15T11:28:43Z

component: plan-marshall:phase-6-finalize
category: insight
title: CI verify-wait timeouts are waited out, not triaged as failures

Owed architecture hint (post-merge step — do NOT apply here):

- module: plan-marshall
- enrich verb: insight
- hint: the project treats CI verify-wait timeouts as a standing consideration in plan-marshall — a bounded CI wait that lapses with checks still running evidences no defect; re-poll the wait rather than filing fix tasks.

Evidence: 4 taken_into_account [ci_timeout] triage findings in this plan (heads 2910ddf6 x2, b150b7fa, 2248478b), each resolved with "re-poll, no code change"; every lapse was followed by a green CI on re-poll.
