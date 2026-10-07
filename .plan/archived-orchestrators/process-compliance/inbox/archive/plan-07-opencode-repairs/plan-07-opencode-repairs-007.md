envelope_version=1
sender_type=plan
sender_id=plan-07-opencode-repairs
epic=process-compliance
kind=candidate-lesson
created=2026-09-21T01:24:36Z

id=pending-orchestrator-pickup
component=plan-marshall:plan-retrospective
category=bug
created=2026-09-21

# Retrospective fragment pipeline fails on missing fragment files

Plan-retrospective finalize-step run emitted three script_failure markers: check-artifact-consistency exit 2 argparse_rejection (--output-file not declared, accepted archved-plan-path mode plan-id), collect-fragments exit 1 missing fragment-artifact-consistency.toon under doubled .plan/local/plans path, compile-report exit 1 missing work/retro-fragments.toon. Step still completed done with 20 findings across 16 aspects after warning for dropped Permission Prompt Analysis section.

## Solution

No in-run fix; step outcome done covered the advisory output. Underlying defects are stale --output-file call shape and doubled plan-dir resolution plus missing fragments file guard.

## Impact

Retrospective callers must query --help accepted flags before passing --output-file, resolve plan-dir once without doubling, and treat missing fragments as a structured skip rather than an exit 1 chain.

## Source

work-log script_failure lines for notations plan-marshall:plan-retrospective:check-artifact-consistency, collect-fragments, compile-report on 2026-09-21T01:17-01:20Z. Candidate for orchestrator-side classification.
