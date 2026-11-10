envelope_version=1
sender_type=plan
sender_id=plan-v2-89-runtime-tests-start-and-config
epic=lessons-routing
kind=candidate-lesson
created=2026-11-06T17:36:59Z

# Execute leaves broke the commit and file-operation rules because Grep and Glob were not available to them

- component: plan-marshall:execute-task
- category: anti-pattern
- source plan: plan-v2-89-runtime-tests-start-and-config (pm-mcp-core, PR 302)

The TASK-3 leaf committed with plain git add and git commit instead of the gated commit verb, and appended its ledger entry by hand. Other leaves used Bash sed -i, python3 -c, ls, unzip and javap for work the file tools should do, because Grep and Glob were not available inside the dispatched envelope. The rules forbid both, but the envelope gave the leaves no tool that would have complied.

Evidence: the behavioural-observations aspect of the retrospective report.
