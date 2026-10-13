envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T06:54:48Z

# Candidate lesson: pre-push quality gate after a rebase must build clean

- Component: plan-marshall:phase-6-finalize (pre-push-quality-gate) / plan-marshall:build-maven
- Suggested category: bug
- Signal: build failure in phase 6-finalize

## Observation

After the finalize rebase onto main, an incremental `verify -Ppre-commit` failed: upstream had deleted
the test fixture `question-class-unregistered.pmwf`, but the stale copy in `target/test-classes`
was still read by the tests. A clean rerun was green. The orchestrator reports that 13 build and
test findings from the failed run had to be cleared afterwards.

## Evidence

- work.log 2026-10-12T19:29:33Z [WARNING] (plan-marshall:pre-push-quality-gate): "First non-clean run
  failed on a stale target/test-classes fixture deleted upstream (question-class-unregistered.pmwf);
  clean rerun green."
- The count of 13 cleared findings is the orchestrator's observation, not re-read from the stores.

## Suggested correction

When the branch was rebased (or HEAD moved relative to the last build), the pre-push quality gate
runs `clean verify` instead of an incremental build. Findings filed from a run later classified as
stale-output are cleared together with it.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-engine-002.md` from plan workflow-engine (PLAN-13, #45; Claude Code)
