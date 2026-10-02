envelope_version=1
sender_type=plan
sender_id=truth-168-sync-defaults-reverting-remove
epic=truthful-signals
kind=candidate-lesson
created=2026-10-02T15:45:28Z

component=plan-marshall:manage-config
category=bug
created=2026-10-02

# Review-bot merge-membership defects: seed absent maps, preserve curated membership, canonicalize removals

CodeRabbit review on PR 1674 caught three merge-membership defects in `_cmd_sync_defaults.py` that unit tests missed, all fixed in-run (6 pr-comment findings with resolution fixed): (1) when `qgate` is `never`/`always` and `phase-6-finalize.steps` is absent, seeding created a single-owner map and the later merge held every other default instead of seeding; (2) legacy `qgate` migration materialized a missing owner step before the membership check, hiding `held_for_ask`/`re_added`; (3) `removed_steps` entries recorded under retired step IDs (e.g. `default:automated-review`) missed comparison against the canonical ID (`plan-marshall:automatic-review`) and surfaced as held instead of re-added.

## Solution

Preserve the absent-map seeding path while applying migrated lanes; retain the legacy `qgate` value until the operator accepts the owner step (defer, do not materialize); canonicalize removal records during migration and compare canonical IDs at merge time. Add end-to-end sync tests for both `qgate` values with no `steps` key, driven through real `remove-step` plus `sync-defaults` with exact dotted-path assertions.

## Impact

Any default-reconciliation path with a legacy-to-lane migration. Prevents curated-map corruption and misreported held vs re-added buckets.
