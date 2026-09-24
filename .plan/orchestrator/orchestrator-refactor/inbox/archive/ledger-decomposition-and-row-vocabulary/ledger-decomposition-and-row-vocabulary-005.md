envelope_version=1
sender_type=plan
sender_id=ledger-decomposition-and-row-vocabulary
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-24T09:04:53Z

# Surface closed-set doc claims against the code's returned token set

component: pm-plugin-development:ext-self-review-plan-marshall
category: improvement

## Context

Pre-submission self-review on ledger-decomposition-and-row-vocabulary did not converge. Its four rounds found 10, then 2, then 6, then 6 findings, and the operator closed the fourth round out of budget with 6 fixes unreviewed. 21 of the 24 findings were `contract_drift`. Most were closed-set over-claims in docs: "written only by regenerate-view and compact" when migrate-layout also writes; refusal lists that omit `ledger_unreadable`; a "closed vocabulary" naming 1 of 8 `ROUTING_REASONS`; "exactly two paths write the file". Round 2's findings were produced by round 1's own fix.

## Root cause

The plan added a new set of refusal tokens and writers across about 10 docs and 3 scripts. Each doc stated the set by hand instead of deriving it from the code. The deterministic surface has no candidate class for "doc enumerates a subset with only/every/exactly language while the code returns more", so the LLM reviewer finds these one round at a time.

## Proposed action

Add a closed-set-claim candidate to the self_review surface. Extract each changed verb's returned error/refusal tokens (AST over return dicts that carry an `error` key) and each writer of a named file. Then list the doc passages in the diff that enumerate those sets with exclusive quantifiers. Seeding round 1 with the complete set would end the round-over-round drip.

## Evidence

- aspect: chat_history_analysis — self-review loop-backs 10 -> 2 -> 6 -> 6, closed out of budget
- aspect: llm_to_script_opportunities — 21 of 24 qgate-6-finalize findings are contract_drift
- aspect: plan_efficiency — 6-finalize took 56% of dispatched tokens (5.74M floor), versus 2.35M for 5-execute
