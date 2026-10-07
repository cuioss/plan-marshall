envelope_version=1
sender_type=plan
sender_id=plan-06-dispatch-roster
epic=process-compliance
kind=candidate-lesson
created=2026-09-24T10:23:37Z

# Candidate lesson: CI-deadline-exceeded timeout findings accepted without fix in plan-marshall finalize

plan: plan-06-dispatch-roster (epic process-compliance, PLAN-06)
kind: candidate-lesson
source-step: default:finalize-step-preference-emitter

## Owed architecture hint (reconstructible enrich call)

- Target `--module`: plan-marshall
- Enrich verb: insight (disposition `accepted` per the shared disposition-to-hint contract)
- Generalized hint text: the project tolerates CI-deadline-exceeded timeout findings accepted without fix tasks in plan-marshall finalize runs — CI wall-clock routinely exceeds the precondition wait budget, so a timeout names a still-running pipeline, not a code failure

## Evidence (populations, not raw dispositions)

- Within-plan recurrence: 2 accepted findings of the same triage class in this plan (preference_min_recurrence=2 met); 0 suppressed, 2 taken_into_account in other classes (no recurrence)
- Suppressed count 0; taken_into_account classes distinct (no recurrence)
- No per-finding hash IDs, titles, or raw rows persisted per the privacy invariant
