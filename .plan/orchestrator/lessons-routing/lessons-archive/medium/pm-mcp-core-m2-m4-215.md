envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T11:06:03Z

# Candidate lesson: whole-tree pre-commit verify after the finalize rebase failed on stale test-class fixtures

Source: dispatcher-reported script-level friction (not tallied as a script-failure cluster)

## What happened

The first whole-tree `verify -Ppre-commit` after the finalize rebase onto main failed because `target/test-classes`
still held fixtures that upstream #48 had removed from the sources. The build passed only after `clean` was added
to the command.

## Candidate rule

After a rebase that pulls in upstream deletions of test resources or fixtures, run the quality gate with `clean`
(or the finalize rebase step should do so by default for Maven), since incremental builds keep deleted resources
in `target/`.

Likely owner: plan-marshall:phase-6-finalize (post-rebase verification) or plan-marshall:build-maven.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `scenario-replay-harness-006.md` from plan scenario-replay-harness (PLAN-22, #50; Claude Code)
