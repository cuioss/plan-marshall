envelope_version=1
sender_type=plan
sender_id=lb-33-leaf-test-scope-and-executor
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T19:59:00Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
confidence=high
source_aspects=chat_history_analysis,execution_context_dispatch_audit

# Stop asking the self-review author leaf to record mark-step-done

## Context

Across lb-33's 7 pre-submission-self-review firings, every author leaf returned without `mark-step-done`. Step 3b's verifier must be dispatched from the inline orchestrator context, and Step 4 (Branch A or B) needs the verifier's answer. In later rounds the orchestrator's dispatch brief still told the author to "record before return". The leaves had to refuse that explicitly, saying a `verifier_unavailable` record would force an unfixable loop-back and inventing an acceptance would undo the author/verifier split. The same session also dispatched the step once with the wrong notation `plan-marshall:phase-6-finalize/standards/pre-submission-self-review.md` (the doc lives under `workflow/`), and that dispatch returned `workflow_not_found` and was wasted.

## Root cause

The finalize dispatcher treats pre-submission-self-review like a self-recording step. Its brief template carries the generic record-before-return clause, and the workflow notation is composed by hand rather than read from the step registry.

## Proposed action

In phase-6-finalize, mark pre-submission-self-review as orchestrator-recorded: drop the record-before-return clause from its author brief, state that the orchestrator runs Step 3b then Step 4, and take the workflow notation from the manifest/registry entry instead of composing it, so a `standards/` vs `workflow/` slip cannot occur.

## Evidence

- aspect: chat_history_analysis — round-6 author leaf: "Your brief asked me to record before returning. The workflow forbids that here"; one leaf returned `error: workflow_not_found` for the `standards/` notation
- aspect: execution_context_dispatch_audit — pre-submission-self-review shows 5 execution-log firings with no paired boundary row
