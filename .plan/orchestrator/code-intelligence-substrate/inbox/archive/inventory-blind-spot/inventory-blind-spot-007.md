envelope_version=1
sender_type=plan
sender_id=inventory-blind-spot
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-29T16:36:17Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
bundle=plan-marshall
source_plan=inventory-blind-spot

# The retrospective runs two steps before the cache sync, so it cannot observe its own plan's fix

## Observation

`plan-retrospective` sits at position 17 of the 22-step finalize manifest. `project:finalize-step-deploy-target` (18) and `project:finalize-step-sync-plugin-cache` (19) come after it. The executor resolves scripts from the plugin cache, so throughout the retrospective the live executor is still running **pre-fix code**.

This run made the mistake and caught it. Probing the plan's own headline deliverable:

```
architecture find --pattern "*workflow/analyze*"   -> status: success, count: 0
architecture find --pattern "*" --category definitely_not_a_category
                                                   -> status: success, count: 0
```

Both readings say the plan's two central deliverables did not work. Both are wrong. Reading the merged repo source shows `cmd_find` gating on `FILE_CATEGORIES` and returning `_unknown_category_result` exactly as specified; reading the cached copy at `~/.claude/plugins/cache/plan-marshall/plan-marshall/0.1.1240/skills/manage-architecture/scripts/_cmd_client_handlers.py` shows `cmd_files` with **no** vocabulary check at all — the pre-fix body.

A retrospective that had trusted its own probe would have filed two fabricated "live defect in merged main" findings against a change that is correct.

## Root cause

Step ordering. The retrospective is the component that most wants to *observe behaviour*, and it is positioned at the one point in the run where observed behaviour is guaranteed stale. This is the same ordering class already recorded for PLAN-10 (a plan that fixes a finalize-time component cannot have that fix exercised by its own finalize).

## Solution

Two options, not mutually exclusive:

1. Move `plan-marshall:plan-retrospective` after `project:finalize-step-sync-plugin-cache` in the default manifest ordering, so live probes read the code the plan actually shipped.
2. Failing that, make the ordering hazard explicit in the retrospective's own workflow: any behavioural probe of the plan's own surface MUST read repo source (or CI results), never the executor, and the report must say so.

## Generalisation

**An auditor positioned before the deploy step is measuring the previous release.** Any check that executes the system under audit — rather than reading its source or its CI record — must first establish that the executing copy is the copy under audit. When it cannot, the probe is not weak evidence, it is *inverted* evidence: it reports the pre-change behaviour with full confidence.

## Impact

Affects every behavioural claim any finalize step at position < 19 makes about the plan's own change. `pre-submission-self-review`, `finalize-step-simplify`, and `plan-retrospective` all run before the sync.
