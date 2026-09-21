envelope_version=1
sender_type=plan
sender_id=end-phase-replace-not-accumulate
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-29T16:36:17Z

component=workflow-integration-git
category=bug
created=2026-07-29

# detect-artifacts safe-to-delete set includes live in-flight state, contradicting its own gitignore-exclusion contract

`detect-artifacts` is documented as excluding gitignored files from its safe-to-delete classification. In this plan's own finalize run it instead returned 111,433 "safe-to-delete" entries totaling 19.9MB that included `.plan/local/plans/{plan_id}/logs/work.log` (the plan's own in-flight audit trail) and the whole `.mypy_cache/` tree — both gitignored, both live at scan time.

A caller that follows the documented instruction "for safe artifacts, delete them" would destroy the plan's own in-flight audit trail during finalize, before the run that produced it has even finished. This was caught during this plan's own self-review (finding `d8fa4a`) and triaged `accepted` — out of scope for this plan's diff — rather than fixed in-run.

## Impact

Any finalize or cleanup pass that trusts `detect-artifacts`' safe-to-delete set at face value risks deleting a running plan's own logs and language-server caches that are actively in use, not stale. The documented "gitignored files are excluded" contract is not honored by the current implementation.

## Suggested corrective action

Fix `detect-artifacts` at the tool layer: either honor the documented gitignore-exclusion contract for real (exclude gitignored paths from the safe-to-delete classification), or narrow the documented contract to describe the actual behavior and add an explicit liveness/staleness check (mtime-based or lock-aware) before any gitignored path — especially anything under an active plan's own `logs/` — is offered as safe-to-delete.
