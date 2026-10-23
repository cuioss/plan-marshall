envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:56:32Z

component=plan-marshall:manage-architecture
category=anti-pattern
source=script-failure cluster, work log 8e49fa (2026-10-17T19:51:59Z, phase-5) and 17ca0d (2026-10-18T08:12:56Z, finalize review)

# Two misuses of `architecture search`: an invented `--path`, and `--plan-id` placed before the verb

## Observation

1. In phase-5, `architecture search --path ...` was rejected: unknown flag. The path glob lives on `architecture find --pattern P`, and file content on `search --content --pattern P`.
2. In the finalize review, `architecture.py --plan-id plan-74-credential-store-choice search --content --pattern 'Outcome\.FAILED|CredentialStoreCheck'` was rejected: argparse_rejection. `--plan-id` was placed as a router flag before `search`, which does not declare it there.

## Rule

`search` matches content and `find` matches paths. Never put `--plan-id` before an architecture verb (or append it at all) unless that verb's canonical block declares it. The execution-context envelope's prompt names the `ci` router as the pre-verb exception, and agents generalise that exception to other routers. A one-line counter-example for `architecture` in the persona's recurrence-signature list would help.
