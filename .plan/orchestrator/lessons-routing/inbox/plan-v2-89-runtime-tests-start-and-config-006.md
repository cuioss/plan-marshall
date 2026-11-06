envelope_version=1
sender_type=plan
sender_id=plan-v2-89-runtime-tests-start-and-config
epic=lessons-routing
kind=candidate-lesson
created=2026-11-06T17:37:00Z

# Script failures of one finalize run: invented flags, argparse rejections and internal errors

- component: plan-marshall:manage-architecture, plan-marshall:manage-metrics, plan-marshall:phase-6-finalize, plan-marshall:manage-status, plan-marshall:workflow-integration-git
- category: bug
- source plan: plan-v2-89-runtime-tests-start-and-config (pm-mcp-core, PR 302)

The script-failure analysis of the retrospective found: manage-architecture search rejected an invented flag (twice); manage-metrics record-dispatch-boundary rejected a call by argparse; review_support validate rejected --findings-file for the code kind (its flag is --verdict-file for both kinds, which the code-review workflow text does not say as clearly as the functional one); manage-status transition returned an internal error (twice); git-workflow commit returned an internal error once.

Evidence: the script-failure-analysis aspect of the retrospective report.
