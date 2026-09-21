envelope_version=1
sender_type=plan
sender_id=plan-02-worktree-discipline
epic=process-compliance
kind=candidate-lesson
created=2026-09-20T13:08:32Z

component=plan-marshall:workflow-integration-git
category=bug
bundle=plan-marshall
created=2026-09-20

# Worktree-materialized gate must read authoritative status, persist atomically, fail closed

Slipped-then-caught defect class from PR 1547 review (plan plan-02-worktree-discipline).
Four coderabbit inline findings on
marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/prepare_execute.py
were remediated in-run (resolutions `fixed`):

- line 286: worktree status is authoritative, so stop after the first existing
  readable candidate; an explicit false must stop the search instead of
  falling through to a stale main-checkout record.
- line 331: status.json persist must write a temp sibling plus os.replace with
  tmp cleanup; Path.write_text truncates before writing and an I/O failure can
  leave the plan record empty or partial.
- line 715: moved/noop/healed payloads must carry the read-back
  is_worktree_materialized value instead of hardcoded True; reporting success
  while _persist_worktree_materialized returned False lets the later admission
  check block Bucket-B dispatch.
- line 285: is_worktree_materialized must fall through only on
  FileNotFoundError; any other OSError on the authoritative copy fails closed
  instead of accepting a later main-checkout record.

## Solution

Authoritative-first read with fail-closed I/O, atomic persist via temp file
plus os.replace, and never report materialized True unless the persisted flag
read back True.

## Impact

Any worktree-gated dispatch (Bucket-B) that trusts a non-authoritative or
unpersisted materialized flag.
