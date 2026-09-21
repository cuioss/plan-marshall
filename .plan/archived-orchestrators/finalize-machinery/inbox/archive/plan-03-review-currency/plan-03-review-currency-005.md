envelope_version=1
sender_type=plan
sender_id=plan-03-review-currency
epic=finalize-machinery
kind=candidate-lesson
created=2026-09-17T18:06:24Z

component=plan-marshall:automatic-review
category=improvement
created=2026-09-17

# Review-currency helpers without production wiring slipped past authoring, caught by review bots

Plan plan-03-review-currency remediated five review-bot findings in-run (PR 1510, all resolution fixed): one cuioss-review-bot inline on _github_ci.py:88 (unconstrained SHA substring match with dead re.findall loop) and four coderabbitai inline findings on review_completeness.py:386 (Trigger-B target selection bypassing select_stale_bot_for_trigger), review_gate_delta.py:189 (await flag with no production caller), _github_checks.py:290 (currency verdict mapper with no production caller), and test_review_currency_holes_regression.py:34 (regression tests supplying downstream state directly).

## Pattern

Each helper computed a verdict but had no production caller between the helper and the emitted check state, await decision, or trigger target, so unit tests passed while production wiring was absent.

## Candidate rule for orchestrator judgement

Wire every verdict helper into its production emission path before landing, and drive regression tests through the production entry point with only the external GitHub boundary mocked. Assert the resulting state or selected target, not the helper return in isolation.

## Evidence

signal_automated_review_count=1; manage-findings list --type pr-comment --resolution fixed filtered_count=5 (hashes bbd56b, 9605d7, 4dc74d, e8fbbb, fe3dcd); tasks TASK-4 through TASK-8.
