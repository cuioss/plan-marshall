envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-22T05:50:11Z

# Candidate lesson: Argparse rejections from paraphrased flags and verbs (manage-architecture, manage-solution-outline, build-maven)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-45-request-body-and-h2-buffer-bounds (PR cuioss/API-Sheriff#506), source message 016, 017, 018.

Three rejected calls in PLAN-V02-45, each corrected at once:

- 016: `architecture search ... --plan-id P` -> `misplaced_router_flag` (router-scoped flag must precede the verb). RECURRENCE of api-sheriff-api-sheriff-0-2-0-006.
- 017: `manage-solution-outline get-deliverable --number 3` -> `unknown_flag` (declared: `--deliverable-number`). RECURRENCE of api-sheriff-api-sheriff-0-2-0-016.
- 018: `maven resolve-test-scope` -> `unknown_verb`; the verb was a paraphrase of the step's intent (work out which tests to run). Registered verbs: check-warnings, coverage-report, discover, parse, rewrite-log, run, run-config-key.

Common cause: flags and verbs derived from prose or intent rather than the canonical invocation. The 016/017 shapes keep recurring across plans despite earlier routing.
