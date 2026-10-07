envelope_version=1
sender_type=plan
sender_id=module-budget-campaign-run-2-slice-040
epic=test-quality
kind=candidate-lesson
created=2026-09-18T11:23:52Z

# Candidate lesson — router-scoped --plan-id belongs before the verb on ci

Source plan: module-budget-campaign-run-2-slice-040 (epic test-quality).

Observation: repeated exit-2 argparse rejections from placing `--plan-id` after
the verb on `ci` read verbs (checks/pr view) whose subparsers declare no
`--plan-id`; the router consumes the flag only ahead of the first verb token.
Same class: invented manage-* subcommands (manage-logging read, manage-findings
assessment) and misplaced flags on architecture search.

Candidate rule: consult each script's canonical-invocation block for flag
position per verb; never append --plan-id by rote. Already guarded by the
ARGUMENT_NAMING rule cluster and the fix-argparse-rejection recipe — merge
into existing coverage rather than filing standalone.

Signal provenance: script-failure-analysis (32 failures, 14 unique; ci cluster
x4, manage-logging x11).
