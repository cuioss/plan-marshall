envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T18:29:09Z

# ADRs backfilled from PR bodies overclaim; check every factual claim against the code

## What happened

Plan 39 wrote ADRs after the fact for decisions already merged, mostly using the PR descriptions as the source. Over several review rounds, coderabbit found about 16 factual overclaims in those ADRs: field lists that did not match the records, scopes wider than what was implemented, and claims about wiring that the code did not do. Each one took another fix-and-re-review cycle.

## Rule

- A PR body is a description of intent, not evidence. Before writing a backfilled ADR, check each concrete claim (field or record lists, which modules or verbs a decision covers, what is wired to what) against the source at HEAD, and cite the type or file it was checked against.
- Prefer narrow, verifiable statements over complete-sounding summaries. Leave out details that cannot be confirmed in the code instead of copying them from the PR.
- Add a self-review step to the ADR backfill task: list every concrete claim in the draft ADR and confirm each one in the code before submitting.

## Evidence

About 16 coderabbit findings on PR #53 across several rounds, all factual corrections to backfilled ADRs.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-39-module-readmes-and-adrs-002.md` from plan plan-39-module-readmes-and-adrs (PLAN-39, #53; Claude Code)
