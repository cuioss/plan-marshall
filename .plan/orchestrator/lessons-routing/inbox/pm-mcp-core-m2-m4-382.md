envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T18:47:07Z

component=plan-marshall:build-maven
category=anti-pattern

# build_server invoked as a verb of the maven notation instead of plan-marshall:build-server-client:build_server

Source: script-failure cluster (notation plan-marshall:build-maven:maven, `build_server` rejected as an unknown verb), plan plan-70-plan-instance-alignment.

The caller treated `build_server` as a subcommand of `plan-marshall:build-maven:maven`. It is not one: build-server consumption lives in its own notation, `plan-marshall:build-server-client:build_server`. The call failed in argparse with exit 2.

## Rule

Build-server submission and polling go through `plan-marshall:build-server-client:build_server`; the build-maven notation exposes only its own verbs (e.g. `run`). Docs that mention the build server next to a maven build should name the full client notation so it is not read as a maven verb.
