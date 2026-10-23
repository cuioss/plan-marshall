envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T17:28:51Z

# Candidate lesson: invented verb `resolve-test-scope` on build-maven

- Source: script-failure cluster (work-log failure marker)
- Plan: plan-37-ported-primitive-tests (pm-mcp-core)
- Failing notation: plan-marshall:build-maven:maven
- Candidate component: plan-marshall:build-maven

## Observation

An agent called `maven resolve-test-scope ...`. The build-maven script has no such verb. The documented surface is `run --command-args "..."`, with the module-scoped test command taken from the project's canonical commands (CLAUDE.md: `test -pl {path} -am`) or from `architecture resolve`. argparse rejected the call with exit 2. This is the verb-paraphrase signature: a plausible name made up from the workflow's wording ("resolve the test scope") instead of quoted from the script's `--help`.

## Possible rule (for orchestrator judgement)

Resolve a module's test command through `manage-architecture architecture resolve` (or the project's canonical build commands), then run it through `maven run --command-args`. Never call a scope-resolving verb on the build script. If the phase-5 / module_testing workflow wording ("resolve test scope") invites this paraphrase, that wording could name the real resolve seam explicitly.
