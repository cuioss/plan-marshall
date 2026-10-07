envelope_version=1
sender_type=plan
sender_id=wait-for-comments-counts-rows
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T17:44:46Z

# Assert the resolved plugin-cache version against the newest cached version

component: plan-marshall:marshall-steward
category: bug
confidence: high
source_plan: wait-for-comments-counts-rows
source_pr: 1071

## Context

Throughout this plan's entire run the Claude runtime resolved the `plan-marshall` bundle from
`~/.claude/plugins/cache/plan-marshall/plan-marshall/0.1.1240/`. Thirty version directories exist in
that cache; the newest is `0.1.1275`. The pinned `0.1.1240` tree differs from `0.1.1275` by **299
changed files, 49 files present only in the newest, and 177 files present only in the pin** (for the
`plan-marshall` bundle alone; `pm-plugin-development` adds another 78 changed). Nothing in six phases
of plan execution noticed, questioned, or reported the divergence.

The concrete damage is documented in the sibling candidate-lesson "Pre-merge review barrier must fail
closed when its own producer call fails": the `branch-cleanup` pre-merge barrier executed the
**pre-#1041** shape of `branch-cleanup.md` — a one-predicate "Pre-Merge Comment-Completeness Barrier"
that reads `enabled_bots` and passes `--enabled-bots` — while the repo (and the plan's own worktree)
carried the two-predicate "Pre-Merge Review-Completeness Barrier" that reads `required_bots` /
`optional_bots`. `--enabled-bots` was removed from the codebase on 2026-07-28 by `facb0df44` (#1041),
four days before this plan ran.

## Root cause

Plugin-cache version resolution has no freshness assertion. `marshall-steward preflight` reports
`fresh` on the basis of its own bookkeeping, not on the basis of which version directory the runtime
actually resolved. This is the same recurrence signature as the previously-recorded
"plugin registry pin + orphan-GC inversion" incident, in which orphan-GC marked the NEWEST version
orphaned and `generate_executor` silently downgraded.

## Proposed action

Add a deterministic, zero-LLM preflight verb that:

1. Resolves the version directory the runtime will actually load (the base dir reported to skill loads).
2. Compares it against `max(version)` present in the cache tree.
3. Compares the resolved tree's content hashes against the repo `marketplace/bundles/` source.
4. Emits a **blocking** finding — not an advisory one — when either comparison diverges.

The check is pure filesystem comparison. It must run at finalize entry, before any step executes a
cached workflow doc, because a stale doc can silently disarm a merge gate.

## Evidence

- Cache inventory: `0.1.1194 … 0.1.1240` all carry the stale `--enabled-bots` shape; `0.1.1250 … 0.1.1275` all carry the current `--required-bots` / `--optional-bots` shape. The runtime pinned `0.1.1240`.
- Drift measurement (pinned `0.1.1240` vs newest `0.1.1275`): `plan-marshall` changed=299 added=49 removed=177; `pm-plugin-development` changed=78; six domain bundles changed=2 each.
- `git log -S "--enabled-bots" --all -- marketplace/` → last touching commit `facb0df44` (#1041, 2026-07-28).
- `work.log` `2026-08-01T17:11:52Z` `[ERROR] ... exit_code=2 failure_kind=argparse_rejection ... unrecognized arguments: --enabled-bots pr-agent,coderabbit,sourcery`.
