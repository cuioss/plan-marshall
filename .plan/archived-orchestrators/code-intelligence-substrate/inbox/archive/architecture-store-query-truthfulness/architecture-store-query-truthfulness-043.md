envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:56:19Z

component=plan-marshall:manage-architecture
category=bug

# One live writer bypassed the index write-through the other writers had been given

Source: PR #1489 CodeRabbit inline finding d82638 (resolution=fixed, TASK-042).

save_module_enriched updates only enriched.json. api_init calls it DIRECTLY when it
repairs or resets documents, so the document receives a new generation header while
_project.json retains its old mirrored header.

## Solution

Fix by moving the index write-through into a shared persistence operation, or by routing
api_init through the same synchronized operation the enrich path uses — explicitly NOT
by adding a second parallel write path. The existing constraint recorded in
stamp_concept_document's docstring is preserved: `discover --force` stages documents
under a tmp directory it later swaps into place and must not be redirected through the
live-path writer.

The reviewer's framing is the reusable part: "When a change states that something is
skipped, disabled, guarded, validated, enforced or removed, verify that the mechanism
exists in the file that would have to implement it." The synchronization mechanism was
absent from this live writer while the contract documents said every live write
synchronizes.

## Impact

Directly falsifies the mirrored-header freshness signal the same plan was hardening.
