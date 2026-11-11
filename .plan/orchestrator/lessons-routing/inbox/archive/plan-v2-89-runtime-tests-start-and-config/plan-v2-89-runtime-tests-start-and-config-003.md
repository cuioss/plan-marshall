envelope_version=1
sender_type=plan
sender_id=plan-v2-89-runtime-tests-start-and-config
epic=lessons-routing
kind=candidate-lesson
created=2026-11-06T17:36:58Z

# The execution log has no record-step row for the verify steps until the exit leaf adds them as unmeasured

- component: plan-marshall:phase-5-execute
- category: bug
- source plan: plan-v2-89-runtime-tests-start-and-config (pm-mcp-core, PR 302)

The execution log carried no record-step row for verify:quality-gate or verify:module-tests while those builds ran. The exit leaf added both afterwards as unmeasured, so the log shows the builds as never measured although they ran and passed.

Evidence: the metrics aspect of the retrospective report.
