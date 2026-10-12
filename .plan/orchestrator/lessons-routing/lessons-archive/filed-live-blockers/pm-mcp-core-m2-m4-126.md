envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=finding
created=2026-10-12T12:40:44Z

# [HIGH][Antigravity] The agent ran a build plugin the project does not have (Spotless from Maven Central) and committed its output

- Component: plan-marshall:build-maven (maven run guard), plan-marshall:phase-5-execute / phase-6-finalize (formatting step), Antigravity agent rules
- Category: bug

## What happened

- Build log `maven-2026-10-12-090117.log`: `No plugin found for prefix 'spotless' in the current project`.
- The next run, `maven-2026-10-12-090124.log`, downloaded `com.diffplug.spotless:spotless-maven-plugin` 3.10.x from Maven Central and ran it.
- Three commits followed: 62b133e, d6a6a19 and 24f745d, "style(workflow): format … with spotless". They are small: whitespace, an import and a `default -> {}` reshape.

The project's `CLAUDE.md` forbids adding a plugin without asking, and names `verify -Ppre-commit` (OpenRewrite, licence headers, import order) as the formatting authority.

## Why it matters

- The wrapper `plan-marshall:build-maven:maven run --command-args "…"` accepted an arbitrary fully-qualified plugin goal, so the canonical-command rule did not protect the project.
- A foreign formatter can fight the project's own recipes.
- An ad-hoc plugin resolved from Central bypasses the project's repository filter (`.mvn/rrf`) intent.

## Suggested direction

- `maven run` refuses goals whose plugin is not declared in the effective POM, unless the operator explicitly allows it.
- The formatting step resolves to the project's declared quality-gate profile only.

- Priority: **HIGH** (operator decision 2026-10-12: Antigravity issues are filed directly as high priority)
- Platform: Antigravity — first plan of epic pm-mcp-core-m2-m4 run under it
- Plan: `plan-41-static-verifier-remaining-rules` (PLAN-41), pm-mcp-core PR #34, merge commit ebe82b3
- Evidence location: pm-mcp-core `.plan/local/archived-plans/2026-10-12-plan-41-static-verifier-remaining-rules/` (logs/, metrics.md, execution.toon, build-results/)
- Origin: filed by the orchestrator of epic pm-mcp-core-m2-m4 from its landing analysis, verified against the archived plan and the PR
