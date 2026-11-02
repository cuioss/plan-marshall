envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-24T15:38:03Z

# Recurrence: invented verbs and flags after an argparse rejection (manage-solution-outline, manage-change-ledger, build-maven, manage-execution-manifest)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-23-cookie-forwarding-policy-r2 (PR cuioss/API-Sheriff#515, merge bd730f5a), inbox message(s) plan-v02-23-cookie-forwarding-policy-r2-012, -013, -014 and -015.

Recurrence of the lessons-archive rows "Invented verbs and flags" (sweeps 2026-10-09, 2026-10-13, 2026-10-15). Seven rejections in one run:
- manage-solution-outline get-deliverable --number N, four times in one run (canonical flag is --deliverable-number); the rejection did not stick across dispatches.
- manage-change-ledger list (the read verb is query), then a router-level --plan-id (it belongs after the verb).
- build-maven resolve-test-scope (not a verb; the verbs are check-warnings, coverage-report, discover, parse, rewrite-log, run, run-config-key).
- manage-execution-manifest loop-back (not a verb; loop-back is a phase-transition concern).

Suggested direction: where the paraphrase is natural and recurs (--number, list), accept an alias or name the canonical form in the rejection ("did you mean --deliverable-number"). Workflow steps that describe loop-back and test-scope derivation should name the exact sanctioned calls.
