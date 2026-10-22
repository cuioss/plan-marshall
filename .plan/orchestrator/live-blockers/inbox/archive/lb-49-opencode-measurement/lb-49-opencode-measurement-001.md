envelope_version=1
sender_type=plan
sender_id=lb-49-opencode-measurement
epic=live-blockers
kind=candidate-lesson
created=2026-10-22T11:17:06Z

title: Owed architecture hint: a bounded CI-wait expiry is not a CI failure
component: plan-marshall:phase-6-finalize
category: improvement

# Owed architecture hint

- module: plan-marshall
- enrich verb: best-practice
- hint: A failed bounded CI wait (`ci_timeout`) records a wait expiry, not a failing check. Reconcile the head against a completed green run before treating the finding as a CI failure, and record the superseding evidence on the finding when it holds.
