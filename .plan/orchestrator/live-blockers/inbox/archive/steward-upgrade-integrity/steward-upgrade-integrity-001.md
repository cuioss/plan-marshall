envelope_version=1
sender_type=plan
sender_id=steward-upgrade-integrity
epic=live-blockers
kind=candidate-lesson
created=2026-10-15T15:48:22Z

category: insight
component: plan-marshall:phase-6-finalize
title: Owed architecture hint (preference-emitter): ci-timeout taken_into_account recurrence

Owed `architecture enrich` call (post-merge follow-up record — do NOT apply
here; the enrich write belongs to a pre-merge band):

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture enrich insight --module plan-marshall --insight "Treat ci-verify timeout findings (CI still running at the wait deadline with no failing check) as a standing re-poll signal in plan-marshall:phase-6-finalize: re-issue the consume-failures precondition resolve instead of routing an empty set to triage"
```

Provenance: within-plan recurrence (plan steward-upgrade-integrity) of
(module=plan-marshall:phase-6-finalize via component fallback,
finding-class triage ci_timeout, disposition=taken_into_account) ×2,
clearing preference_min_recurrence=2. Generalized per the shared
disposition-to-hint contract (taken_into_account → insight); routed to
module plan-marshall (bundle owning the component). Suppressed (0) and
accepted (1, unattributed default bucket) yielded no promotable pattern.
