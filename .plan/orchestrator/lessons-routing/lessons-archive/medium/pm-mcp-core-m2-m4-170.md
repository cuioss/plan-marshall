envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T07:34:08Z

# Candidate lesson: stale target/test-classes fixture after rebase broke verify -Ppre-commit

Source: run event in plan verify-not-resolve (PR #43), pm-workflow module.

## What happened

After a rebase onto main, a test fixture compiled before the rebase was still in `pm-workflow/target/test-classes`. `verify -Ppre-commit` failed in pm-workflow on that stale class until a clean build removed it.

## Why it matters

The failure came from leftover build output, not from the change. Time went into investigating a failure the source did not cause.

## Suggested correction

After a rebase or branch sync that removes or renames test sources or fixtures, run the quality gate with `clean` first (for example `clean verify -Ppre-commit` through the canonical build command). Or have the finalize/verify flow clean when the branch was rebased since the last build. Possible homes: `plan-marshall:build-maven` or the phase-5/phase-6 verify step after branch sync.

Classification is left to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `verify-not-resolve-002.md` from plan verify-not-resolve (PLAN-18, #43; Claude Code)
