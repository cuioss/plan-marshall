envelope_version=1
sender_type=plan
sender_id=lb-25-phase-and-merge-gates
epic=live-blockers
kind=candidate-lesson
created=2026-10-11T16:01:11Z

component=plan-marshall:phase-6-finalize
category=bug
bundle=plan-marshall
source_plan=lb-25-phase-and-merge-gates

# Attribute ci-verify findings to the run that produced each failing check

## Context

PR #1751 had two CI runs failing at the same HEAD (38120928178 and 38120821440). ci_verify filed all four findings with `file_path` under `artifacts/ci-runs/38120928178/...`, although two of them belonged to run 38120821440. In the same pass `ci checks status` returned empty `log_file` / `filtered_log_file` for every failing check, so the triage leaf had to fall back to `ci checks logs --job "verify / verify" --match ...`.

## Root cause

The ci-verify finding writer keys artifact paths on the first run id it saw instead of on the run each failing check belongs to, and the `ci checks status` producer does not populate the log-file fields for failing checks (the fields the finding is meant to point at).

## Proposed action

Key each ci-verify finding's `file_path` on the run id of its own check, and make `ci checks status` (tools-integration-ci) populate `log_file` / `filtered_log_file` for failing checks, or report why it could not. Add a two-run fixture test.

## Evidence

- aspect: chat_history_analysis - verification-feedback leaf: "all four findings point their file_path at artifacts/ci-runs/38120928178/..., but two of them belong to run 38120821440. Also, ci checks status returned empty log_file / filtered_log_file for every failing check"
