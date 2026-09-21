envelope_version=1
sender_type=plan
sender_id=test-fidelity-rules-follow-up
epic=process-compliance
kind=finding
created=2026-09-20T08:31:27Z

# Process-rule observation: footprint helpers read the stale local base, not the merge base

## Observed

- The plan worktree was correctly based on `origin/main` (`1c56734ce`, PR #1539 merge), while the local `main` ref still pointed at its parent (`afce081b`, #1545).
- `compute-footprint` and the self-review surfacer resolve `base_ref: main` (the local ref), so the change surface listed 35 files: the plan's 12 plus 14 files from the already-merged upstream #1539.
- A self-review run against that surface would have examined (and potentially filed findings on) upstream code, and any loop-back fix would have amended files outside the plan.

## Conflict

- None with a written rule — no documented rule pins which ref (`main` vs `origin/main` vs merge-base) the footprint uses. The failure mode is silent scope widening after a correct rebase.

## What was done on this run

- Verified parentage (`1c56734ce` child of `afce081b`), fetched (remote still at #1539), fast-forwarded local `main` to `origin/main` from the main checkout.
- Recomputed the footprint: 12 files, exactly the plan's deliverables. Discarded the 333-candidate surface computed on the stale scope and re-surfaced.
- No upstream file was modified at any point; the widened scope never left the analysis.

## Request

- Pin the footprint/surfacer base to the merge base (or fail loudly when local `main` trails `origin/main`), so a stale base cannot silently widen review scope. Consider refreshing the local base ref as part of `sync-baseline`, which already owns base currency.
