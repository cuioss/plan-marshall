envelope_version=1
sender_type=plan
sender_id=plan-01-script-surface-validation
epic=tooling-truthfulness
kind=candidate-lesson
created=2026-09-11T19:21:56Z

# Candidate lesson — Review-bot caught weak claim-index verdict assertion fixed in-run
key=value envelope:
component=plan-marshall:automatic-review
category=bug
title=Review-bot caught weak claim-index verdict assertion fixed in-run
plan_id=plan-01-script-surface-validation

CodeRabbit inline (pr-comment 2d7191, PR 1466, test_orchestrator_status_regression.py:205) flagged weak assertion passing when _CLAIM_A stamped because _CLAIM_B still existed. Fixed via TASK-005 with nested verdict under _CLAIM_B plus no-verdict guard under _CLAIM_A. Two re-review polls declined with head_sha_verified=false (no reviewed-commit SHA, bot_kind=coderabbit) and one operational issue_comment pair accepted with no action. Remediated-in-run review finding fires the automated-review signal even at outcome=done.
