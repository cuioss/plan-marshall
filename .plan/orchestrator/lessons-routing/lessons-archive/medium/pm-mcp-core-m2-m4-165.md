envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T06:54:54Z

# Candidate lesson: triage fixes the flagged site only, so the bot finds the sibling next round

- Component: plan-marshall:plan-marshall (workflow/verification-feedback.md, finalize-feedback triage)
- Suggested category: improvement
- Signal: plan-retrospective (plan-efficiency, chat-history-analysis, logging-gap-analysis)
- Related: workflow-engine-005 (parity tests from the start). This one is about the triage response, not the original authoring.

## Context

Finalize ran four review rounds on PR #45. Rounds 1-3 each fixed one CodeRabbit finding of the same
class, a hard-coded list in the code that mirrors a set defined in the specification:
32bd50 (codec MEMBERS / retry_counters enum), then 174dc2 (WorkflowStatus.PHASES used `orchestrator`
where the schema says `epic`), then 7c6014 (WorkflowEngine.PHASES has no parity check). Each triage leaf
fixed only the site the bot named; the next bot pass found the sibling. Round 4 was clean.

## Root cause

verification-feedback triages finding by finding. Nothing asks the leaf to look for other instances of
the defect class a finding names before it commits, so each sibling costs a full round.

## Proposed action

When triage fixes a finding whose message names a reusable defect class (here: a closed list that mirrors
a specification set), the leaf sweeps the plan's footprint for other instances of that class and fixes or
explicitly dispositions them in the same round, and lists them in its hand-back.

## Evidence

- plan-efficiency: 6-finalize 3,435,919 tokens (floor, phase open) = 48% of 7.15M; plan exceeds the
  multi_module+feature error anchor (2.5M) by 2.9x.
- status.json: pre-push-quality-gate firing_count 5, ci-verify 4, automatic-review 4, sonar-roundtrip 4;
  loop_back_budgets wait-region-unified-triage spent 3.
- Leaf hand-backs (session transcript): round 2 triage notes 174dc2 is "the same kind of
  hardcoded-list-versus-schema point as the earlier parity finding"; round 3 notes 495a20 and 7c6014
  are "both about hard-coded lists that mirror a set defined elsewhere".
- work.log: wait-region rounds complete at 20:09 (verification-feedback), 20:58, 21:35; each followed by a
  clean verify -Ppre-commit of about 5 minutes and a CI wait of about 7 minutes.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-engine-015.md` from plan workflow-engine (PLAN-13, #45; Claude Code)
